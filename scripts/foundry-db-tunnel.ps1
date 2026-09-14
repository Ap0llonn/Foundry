#Requires -Version 5.1

[CmdletBinding(PositionalBinding = $false)]
param(
    [switch] $Password,

    [string] $SshExecutable = '',

    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]] $UnexpectedArguments = @()
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# The Ansible database_access=tunnel mode keeps PostgreSQL and the optional
# OpenTelemetry Collector on VM loopback. This script forwards both endpoints
# through one encrypted SSH connection and never handles database credentials.

function Get-FoundryEnvironmentValue {
    param(
        [AllowNull()]
        [string] $Value,

        [Parameter(Mandatory = $true)]
        [string] $DefaultValue
    )

    if ([string]::IsNullOrEmpty($Value)) {
        return $DefaultValue
    }

    return $Value
}

function Stop-FoundryTunnel {
    param(
        [Parameter(Mandatory = $true)]
        [string] $Message
    )

    [Console]::Error.WriteLine($Message)
    exit 2
}

function ConvertTo-FoundryPort {
    param(
        [Parameter(Mandatory = $true)]
        [string] $Name,

        [Parameter(Mandatory = $true)]
        [string] $Value
    )

    $parsedPort = 0
    if (
        $Value -notmatch '^[0-9]+$' -or
        -not [int]::TryParse($Value, [ref] $parsedPort) -or
        $parsedPort -lt 1 -or
        $parsedPort -gt 65535
    ) {
        Stop-FoundryTunnel "$Name must be an integer between 1 and 65535."
    }

    return $parsedPort
}

if ($UnexpectedArguments.Count -gt 0) {
    Stop-FoundryTunnel 'Unexpected positional argument. Use -Password without a value, then enter the password at the OpenSSH prompt.'
}

$sshUser = Get-FoundryEnvironmentValue -Value $env:FOUNDRY_SSH_USER -DefaultValue 'ubuntu'
$sshHost = Get-FoundryEnvironmentValue -Value $env:FOUNDRY_SSH_HOST -DefaultValue '149.56.96.110'
$sshTarget = Get-FoundryEnvironmentValue `
    -Value $env:FOUNDRY_SSH_TARGET `
    -DefaultValue ('{0}@{1}' -f $sshUser, $sshHost)
$sshAuth = if ($Password.IsPresent) {
    'password'
}
else {
    Get-FoundryEnvironmentValue -Value $env:FOUNDRY_SSH_AUTH -DefaultValue 'key'
}
$sshKey = Get-FoundryEnvironmentValue `
    -Value $env:FOUNDRY_SSH_KEY `
    -DefaultValue (Join-Path (Join-Path $HOME '.ssh') 'ansible')
$sshPort = Get-FoundryEnvironmentValue -Value $env:FOUNDRY_SSH_PORT -DefaultValue '22'
$dbLocalPort = Get-FoundryEnvironmentValue -Value $env:FOUNDRY_DB_LOCAL_PORT -DefaultValue '15432'
$dbRemotePort = Get-FoundryEnvironmentValue -Value $env:FOUNDRY_DB_REMOTE_PORT -DefaultValue '15432'
$otlpLocalPort = Get-FoundryEnvironmentValue -Value $env:FOUNDRY_OTLP_LOCAL_PORT -DefaultValue '4318'
$otlpRemotePort = Get-FoundryEnvironmentValue -Value $env:FOUNDRY_OTLP_REMOTE_PORT -DefaultValue '4318'

if ([string]::IsNullOrWhiteSpace($sshTarget)) {
    Stop-FoundryTunnel 'Set FOUNDRY_SSH_TARGET or both FOUNDRY_SSH_USER and FOUNDRY_SSH_HOST.'
}

if ($sshTarget.StartsWith('-')) {
    Stop-FoundryTunnel 'The SSH target cannot begin with a dash.'
}

if ($sshTarget -match '[\s\p{Cc}]') {
    Stop-FoundryTunnel 'The SSH target cannot contain whitespace or control characters.'
}

if (
    $sshAuth -notin @('key', 'password') -or
    ($sshAuth -cne 'key' -and $sshAuth -cne 'password')
) {
    Stop-FoundryTunnel 'FOUNDRY_SSH_AUTH must be either key or password.'
}

$sshPort = ConvertTo-FoundryPort -Name 'FOUNDRY_SSH_PORT' -Value $sshPort
$dbLocalPort = ConvertTo-FoundryPort -Name 'FOUNDRY_DB_LOCAL_PORT' -Value $dbLocalPort
$dbRemotePort = ConvertTo-FoundryPort -Name 'FOUNDRY_DB_REMOTE_PORT' -Value $dbRemotePort
$otlpLocalPort = ConvertTo-FoundryPort -Name 'FOUNDRY_OTLP_LOCAL_PORT' -Value $otlpLocalPort
$otlpRemotePort = ConvertTo-FoundryPort -Name 'FOUNDRY_OTLP_REMOTE_PORT' -Value $otlpRemotePort

if ($dbLocalPort -eq $otlpLocalPort) {
    Stop-FoundryTunnel 'Database and OTLP local ports must be different.'
}

[string[]] $sshArgs = @('-p', [string] $sshPort)
if ($sshAuth -eq 'key') {
    if (-not (Test-Path -LiteralPath $sshKey -PathType Leaf)) {
        Stop-FoundryTunnel "SSH key is not a readable file: $sshKey"
    }

    try {
        $sshKeyItem = Get-Item -LiteralPath $sshKey -ErrorAction Stop
        $keyStream = [System.IO.File]::Open(
            $sshKeyItem.FullName,
            [System.IO.FileMode]::Open,
            [System.IO.FileAccess]::Read,
            [System.IO.FileShare]::Read
        )
        $keyStream.Dispose()
        $sshKey = $sshKeyItem.FullName
    }
    catch {
        Stop-FoundryTunnel "SSH key is not readable: $sshKey"
    }

    $sshArgs += @(
        '-i', $sshKey,
        '-o', 'BatchMode=no',
        '-o', 'IdentitiesOnly=yes',
        '-o', 'PreferredAuthentications=publickey'
    )
}
else {
    # OpenSSH prompts in the terminal. The -Password switch selects this mode;
    # it never accepts the password itself, which would expose the secret in
    # shell history, process arguments, logs, or tooling.
    $sshArgs += @(
        '-o', 'BatchMode=no',
        '-o', 'PubkeyAuthentication=no',
        '-o', 'PasswordAuthentication=yes',
        '-o', 'KbdInteractiveAuthentication=yes',
        '-o', 'PreferredAuthentications=password,keyboard-interactive'
    )
}

$sshCommand = $null
if (-not [string]::IsNullOrWhiteSpace($SshExecutable)) {
    if (-not (Test-Path -LiteralPath $SshExecutable -PathType Leaf)) {
        Stop-FoundryTunnel "The requested SSH executable is not a file: $SshExecutable"
    }
    $sshCommand = (Get-Item -LiteralPath $SshExecutable -ErrorAction Stop).FullName
}
elseif (-not [string]::IsNullOrWhiteSpace($env:WINDIR)) {
    $systemSsh = Join-Path $env:WINDIR 'System32\OpenSSH\ssh.exe'
    if (Test-Path -LiteralPath $systemSsh -PathType Leaf) {
        $sshCommand = (Get-Item -LiteralPath $systemSsh -ErrorAction Stop).FullName
    }
}

if ($null -eq $sshCommand) {
    $sshApplication = Get-Command -Name 'ssh.exe' -CommandType Application -ErrorAction SilentlyContinue |
        Select-Object -First 1
    if ($null -ne $sshApplication) {
        $sshCommand = $sshApplication.Source
    }
}

if ($null -eq $sshCommand) {
    Stop-FoundryTunnel 'ssh.exe was not found. Install the Windows OpenSSH Client and ensure it is on PATH.'
}

$sshArgs += @(
    '-o', 'ExitOnForwardFailure=yes',
    '-o', 'ServerAliveInterval=30',
    '-o', 'ServerAliveCountMax=3',
    '-o', 'StrictHostKeyChecking=ask',
    '-L', "127.0.0.1:$($dbLocalPort):127.0.0.1:$($dbRemotePort)",
    '-L', "127.0.0.1:$($otlpLocalPort):127.0.0.1:$($otlpRemotePort)",
    '-N',
    $sshTarget
)

Write-Host "Opening $sshAuth SSH tunnel to ${sshTarget}:${sshPort}"
& $sshCommand @sshArgs
$sshExitCode = $LASTEXITCODE
exit $sshExitCode
