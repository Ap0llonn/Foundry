#!/usr/bin/env python3
"""Verify the Windows developer SSH tunnel's static safety contract."""

from __future__ import annotations

import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "foundry-db-tunnel.ps1"
PREFIX = "Windows tunnel policy verification failed"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"{PREFIX}: {message}")


def require_pattern(pattern: str, text: str, message: str) -> None:
    require(re.search(pattern, text, re.IGNORECASE | re.MULTILINE | re.DOTALL) is not None, message)


def code_without_comments(text: str) -> str:
    """Remove comments so prohibited command names may be documented safely."""

    without_blocks = re.sub(r"<#.*?#>", "", text, flags=re.DOTALL)
    return re.sub(r"^[ \t]*#(?!requires\b).*?$", "", without_blocks, flags=re.IGNORECASE | re.MULTILINE)


def verify_static_contract(text: str) -> None:
    require_pattern(
        r"^\s*#requires\s+-version\s+5\.1\b",
        text,
        "missing '#requires -Version 5.1' compatibility marker",
    )
    require_pattern(
        r"\[CmdletBinding\s*\(\s*PositionalBinding\s*=\s*\$false\s*\)\s*\]",
        text,
        "positional parameter binding must be disabled",
    )

    default_patterns = {
        "FOUNDRY_SSH_USER": r"FOUNDRY_SSH_USER.{0,300}\bubuntu\b",
        "FOUNDRY_SSH_HOST": r"FOUNDRY_SSH_HOST.{0,300}\b149\.56\.96\.110\b",
        "FOUNDRY_SSH_TARGET": r"FOUNDRY_SSH_TARGET.{0,500}\$sshUser.{0,120}\$sshHost",
        "FOUNDRY_SSH_AUTH": r"FOUNDRY_SSH_AUTH.{0,300}\bkey\b",
        "FOUNDRY_SSH_KEY": r"FOUNDRY_SSH_KEY.{0,500}\.ssh.{0,120}ansible",
        "FOUNDRY_SSH_PORT": r"FOUNDRY_SSH_PORT.{0,300}(?:['\"]22['\"]|\b22\b)",
        "FOUNDRY_DB_LOCAL_PORT": r"FOUNDRY_DB_LOCAL_PORT.{0,300}(?:['\"]15432['\"]|\b15432\b)",
        "FOUNDRY_DB_REMOTE_PORT": r"FOUNDRY_DB_REMOTE_PORT.{0,300}(?:['\"]15432['\"]|\b15432\b)",
        "FOUNDRY_OTLP_LOCAL_PORT": r"FOUNDRY_OTLP_LOCAL_PORT.{0,300}(?:['\"]4318['\"]|\b4318\b)",
        "FOUNDRY_OTLP_REMOTE_PORT": r"FOUNDRY_OTLP_REMOTE_PORT.{0,300}(?:['\"]4318['\"]|\b4318\b)",
    }
    for name, pattern in default_patterns.items():
        require(f"$env:{name}".lower() in text.lower(), f"missing environment input {name}")
        require_pattern(pattern, text, f"{name} does not preserve the Bash default")

    code = code_without_comments(text)

    require_pattern(
        r"(?:IsNullOrWhiteSpace\s*\(\s*\$sshTarget|-not\s+\$sshTarget|\$sshTarget\s*-eq\s*['\"]{2})",
        code,
        "SSH target is not checked for an empty value",
    )
    require_pattern(
        r"(?:\$sshTarget\.StartsWith\s*\(\s*['\"]-['\"]|\$sshTarget\s*-match\s*['\"]\^-)",
        code,
        "SSH target is not rejected when it begins with a dash",
    )
    require_pattern(
        r"\$sshAuth.{0,500}(?:-notin|-ne).{0,300}['\"]key['\"].{0,300}['\"]password['\"]",
        code,
        "SSH authentication mode is not restricted to key or password",
    )
    require_pattern(
        r"\[switch\]\s*\$Password\b",
        code,
        "password mode is not available through the -Password switch",
    )
    require_pattern(
        r"\$sshAuth\s*=\s*if\s*\(\s*\$Password\.IsPresent\s*\).{0,200}['\"]password['\"]",
        code,
        "the -Password switch does not override the environment authentication mode",
    )
    require(
        re.search(r"\[(?:string|securestring|pscredential)\]\s*\$Password\b", code, re.IGNORECASE)
        is None,
        "-Password must select interactive authentication, not accept a secret value",
    )
    require_pattern(
        r"ValueFromRemainingArguments\s*=\s*\$true.{0,300}\$UnexpectedArguments",
        code,
        "unexpected values after -Password are not captured for safe rejection",
    )
    require_pattern(
        r"\$UnexpectedArguments\.Count\s*-gt\s*0.{0,300}Stop-FoundryTunnel",
        code,
        "unexpected positional arguments are not rejected before SSH runs",
    )

    require_pattern(
        r"(?:\[int\]::TryParse|TryParse\s*\(|-match\s*['\"]\^?\\d|\[int\]\s*\$)",
        code,
        "ports are not validated as integers",
    )
    for variable in [
        "sshPort",
        "dbLocalPort",
        "dbRemotePort",
        "otlpLocalPort",
        "otlpRemotePort",
    ]:
        require(
            len(re.findall(rf"\${variable}\b", code, re.IGNORECASE)) >= 2,
            f"${variable} is not included in port validation and forwarding",
        )

    require_pattern(
        r"\$sshAuth.{0,400}['\"]key['\"].{0,700}Test-Path.{0,300}\$sshKey",
        code,
        "key authentication does not validate the configured key path",
    )
    for option in [
        "PubkeyAuthentication=no",
        "PasswordAuthentication=yes",
        "KbdInteractiveAuthentication=yes",
        "PreferredAuthentications=password,keyboard-interactive",
    ]:
        require(option.lower() in code.lower(), f"password mode SSH argument {option} is missing")
    require_pattern(
        r"Get-Command.{0,300}(?:ssh\.exe|['\"]ssh['\"])",
        code,
        "ssh.exe availability is not validated with Get-Command",
    )
    require(
        "System32\\OpenSSH\\ssh.exe".lower() in code.lower(),
        "the trusted Windows system OpenSSH path is not preferred",
    )
    require(
        "[System.IO.File]::Open".lower() in code.lower(),
        "the configured SSH key is not opened to verify readability",
    )

    require_pattern(r"\$sshArgs\s*=\s*@\(", code, "SSH arguments are not built as an array")
    require(code.count("127.0.0.1") >= 2, "database and OTLP forwards must both target 127.0.0.1")
    require_pattern(
        r"\$(?:db)?LocalPort.{0,160}127\.0\.0\.1.{0,160}\$(?:db)?RemotePort",
        code,
        "database forward is not explicitly loopback-scoped",
    )
    require_pattern(
        r"\$otlpLocalPort.{0,160}127\.0\.0\.1.{0,160}\$otlpRemotePort",
        code,
        "OTLP forward is not explicitly loopback-scoped",
    )
    require(len(re.findall(r"['\"]-L['\"]", code, re.IGNORECASE)) >= 2, "both SSH local-forward arguments are required")
    for option in [
        "ExitOnForwardFailure=yes",
        "ServerAliveInterval=30",
        "ServerAliveCountMax=3",
    ]:
        require(option.lower() in code.lower(), f"SSH argument {option} is missing")
    require_pattern(r"['\"]-N['\"]", code, "SSH no-command mode (-N) is missing")
    require_pattern(
        r"^\s*&\s+(?:\$ssh(?:Command|Executable|Path)|['\"]?ssh(?:\.exe)?['\"]?)\s+@sshArgs\s*$",
        code,
        "ssh.exe must be invoked directly with the splatted $sshArgs array",
    )

    lowered = code.lower()
    for forbidden, label in [
        (r"\binvoke-expression\b", "Invoke-Expression"),
        (r"(?m)^\s*iex\b", "Invoke-Expression alias iex"),
        (r"\bstart-process\b", "Start-Process"),
        (r"\bsshpass\b", "sshpass"),
        (r"stricthostkeychecking\s*=\s*(?:no|off|accept-new)", "weakened StrictHostKeyChecking"),
        (r"(?:user|global)knownhostsfile\s*=", "host-key database override"),
        (r"\$env:[a-z0-9_]*(?:password|passwd|passphrase|askpass|sshpass)[a-z0-9_]*", "password environment variable"),
    ]:
        require(re.search(forbidden, lowered, re.MULTILINE) is None, f"forbidden {label} usage")

    require("$lastexitcode" in lowered, "OpenSSH exit status is not read from $LASTEXITCODE")
    require_pattern(
        r"(?:exit\s+\$LASTEXITCODE\b|\$(?:ssh)?exitCode\s*=\s*\$LASTEXITCODE.{0,300}exit\s+\$(?:ssh)?exitCode\b)",
        code,
        "OpenSSH $LASTEXITCODE is not propagated to the caller",
    )


def optional_powershell_preflight() -> None:
    powershell = (
        os.environ.get("FOUNDRY_TEST_POWERSHELL")
        or shutil.which("pwsh")
        or shutil.which("powershell")
    )
    if powershell is None:
        print("SKIP TC-INFRA-013 PowerShell runtime checks (pwsh/powershell unavailable)")
        return

    parser_environment = os.environ.copy()
    parser_environment["FOUNDRY_TUNNEL_SCRIPT_PATH"] = str(SCRIPT)
    parser_result = subprocess.run(
        [
            powershell,
            "-NoLogo",
            "-NoProfile",
            "-NonInteractive",
            "-Command",
            (
                "$tokens = $null; $errors = $null; "
                "$path = $env:FOUNDRY_TUNNEL_SCRIPT_PATH; "
                "[System.Management.Automation.Language.Parser]::ParseFile("
                "$path, [ref]$tokens, [ref]$errors) | Out-Null; "
                "if ($errors.Count -ne 0) { exit 1 }"
            ),
        ],
        cwd=ROOT,
        env=parser_environment,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=15,
        check=False,
    )
    require(parser_result.returncode == 0, "PowerShell parser rejected the tunnel script")

    base_environment = {
        key: value
        for key, value in os.environ.items()
        if not key.upper().startswith("FOUNDRY_")
    }
    base_environment.update(
        {
            "FOUNDRY_SSH_USER": "developer",
            "FOUNDRY_SSH_HOST": "example.invalid",
            "FOUNDRY_SSH_AUTH": "password",
            "FOUNDRY_SSH_PORT": "22",
            "FOUNDRY_DB_LOCAL_PORT": "15432",
            "FOUNDRY_DB_REMOTE_PORT": "15432",
            "FOUNDRY_OTLP_LOCAL_PORT": "4318",
            "FOUNDRY_OTLP_REMOTE_PORT": "4318",
        }
    )
    cases = [
        ("dash-prefixed target", {"FOUNDRY_SSH_TARGET": "-unsafe"}),
        ("whitespace target", {"FOUNDRY_SSH_TARGET": "developer@invalid host"}),
        ("unsupported authentication", {"FOUNDRY_SSH_TARGET": "developer@example.invalid", "FOUNDRY_SSH_AUTH": "token"}),
        ("non-numeric port", {"FOUNDRY_SSH_TARGET": "developer@example.invalid", "FOUNDRY_SSH_PORT": "not-a-port"}),
        ("zero port", {"FOUNDRY_SSH_TARGET": "developer@example.invalid", "FOUNDRY_SSH_PORT": "0"}),
        ("oversized port", {"FOUNDRY_SSH_TARGET": "developer@example.invalid", "FOUNDRY_SSH_PORT": "65536"}),
        (
            "missing key",
            {
                "FOUNDRY_SSH_TARGET": "developer@example.invalid",
                "FOUNDRY_SSH_AUTH": "key",
                "FOUNDRY_SSH_KEY": str(ROOT / "tests" / "definitely-missing-test-key"),
            },
        ),
        (
            "directory key",
            {
                "FOUNDRY_SSH_TARGET": "developer@example.invalid",
                "FOUNDRY_SSH_AUTH": "key",
                "FOUNDRY_SSH_KEY": str(ROOT),
            },
        ),
    ]
    for label, overrides in cases:
        environment = base_environment | overrides
        try:
            result = subprocess.run(
                [powershell, "-NoLogo", "-NoProfile", "-NonInteractive", "-File", str(SCRIPT)],
                cwd=ROOT,
                env=environment,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=15,
                check=False,
            )
        except subprocess.TimeoutExpired as error:
            raise SystemExit(f"{PREFIX}: {label} reached a blocking SSH invocation") from error
        require(result.returncode == 2, f"{label} returned {result.returncode}, not 2")

    with tempfile.TemporaryDirectory(prefix="foundry-tunnel-test-") as directory:
        temporary_directory = Path(directory)
        fake_ssh = temporary_directory / "ssh.exe"
        arguments_file = temporary_directory / "ssh-arguments.txt"
        if os.name == "nt":
            fake_source = temporary_directory / "FakeSsh.cs"
            fake_source.write_text(
                """
using System;
using System.IO;
using System.Text;

public static class FakeSsh
{
    public static int Main(string[] args)
    {
        string outputPath = Environment.GetEnvironmentVariable("FOUNDRY_TEST_SSH_ARGS");
        File.WriteAllText(outputPath, String.Join("\\n", args), new UTF8Encoding(false));
        int exitCode;
        if (!Int32.TryParse(Environment.GetEnvironmentVariable("FOUNDRY_TEST_SSH_EXIT"), out exitCode))
        {
            exitCode = 0;
        }
        return exitCode;
    }
}
""".lstrip(),
                encoding="utf-8",
            )
            windows_directory = Path(os.environ.get("WINDIR", r"C:\Windows"))
            compiler_candidates = [
                windows_directory / "Microsoft.NET" / "Framework64" / "v4.0.30319" / "csc.exe",
                windows_directory / "Microsoft.NET" / "Framework" / "v4.0.30319" / "csc.exe",
            ]
            compiler = next((path for path in compiler_candidates if path.is_file()), None)
            require(compiler is not None, "the Windows .NET Framework C# compiler is unavailable")
            compile_result = subprocess.run(
                [
                    str(compiler),
                    "/nologo",
                    "/target:exe",
                    f"/out:{fake_ssh}",
                    str(fake_source),
                ],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=30,
                check=False,
            )
            require(
                compile_result.returncode == 0,
                f"could not compile fake ssh.exe: {compile_result.stdout}",
            )
        else:
            fake_ssh.write_text(
                f"#!{sys.executable}\n"
                "import os, pathlib, sys\n"
                "pathlib.Path(os.environ['FOUNDRY_TEST_SSH_ARGS']).write_text("
                "'\\n'.join(sys.argv[1:]), encoding='utf-8')\n"
                "raise SystemExit(int(os.environ.get('FOUNDRY_TEST_SSH_EXIT', '0')))\n",
                encoding="utf-8",
            )
            fake_ssh.chmod(0o755)

        key_directory = temporary_directory / "key directory"
        key_directory.mkdir()
        key_file = key_directory / "foundry test key"
        key_file.write_text("synthetic test key\n", encoding="utf-8")

        environment = base_environment.copy()
        environment.update(
            {
                "FOUNDRY_SSH_TARGET": "developer@example.invalid",
                "FOUNDRY_SSH_AUTH": "key",
                "FOUNDRY_SSH_KEY": str(key_file),
                "FOUNDRY_SSH_PORT": "2222",
                "FOUNDRY_DB_LOCAL_PORT": "25432",
                "FOUNDRY_DB_REMOTE_PORT": "15432",
                "FOUNDRY_OTLP_LOCAL_PORT": "24318",
                "FOUNDRY_OTLP_REMOTE_PORT": "4318",
                "FOUNDRY_TEST_SSH_ARGS": str(arguments_file),
                "FOUNDRY_TEST_SSH_EXIT": "0",
            }
        )
        result = subprocess.run(
            [
                powershell,
                "-NoLogo",
                "-NoProfile",
                "-NonInteractive",
                "-File",
                str(SCRIPT),
                "-SshExecutable",
                str(fake_ssh),
            ],
            cwd=ROOT,
            env=environment,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=15,
            check=False,
        )
        require(result.returncode == 0, f"safe fake SSH invocation failed: {result.stdout}")

        require(arguments_file.is_file(), "fake ssh.exe did not record its argument array")
        arguments = arguments_file.read_text(encoding="utf-8-sig").splitlines()
        expected_arguments = [
            "-p",
            "2222",
            "-i",
            str(key_file.absolute()),
            "-o",
            "BatchMode=no",
            "-o",
            "IdentitiesOnly=yes",
            "-o",
            "PreferredAuthentications=publickey",
            "-o",
            "ExitOnForwardFailure=yes",
            "-o",
            "ServerAliveInterval=30",
            "-o",
            "ServerAliveCountMax=3",
            "-o",
            "StrictHostKeyChecking=ask",
            "-L",
            "127.0.0.1:25432:127.0.0.1:15432",
            "-L",
            "127.0.0.1:24318:127.0.0.1:4318",
            "-N",
            "developer@example.invalid",
        ]
        if os.name == "nt":
            arguments[3] = os.path.normcase(os.path.abspath(arguments[3]))
            expected_arguments[3] = os.path.normcase(os.path.abspath(expected_arguments[3]))
        require(arguments == expected_arguments, f"fake ssh.exe received unexpected arguments: {arguments!r}")

        # An explicit -Password switch must override key mode without taking a
        # secret value. Native OpenSSH owns the hidden interactive prompt.
        environment.update(
            {
                "FOUNDRY_SSH_AUTH": "key",
                "FOUNDRY_SSH_KEY": str(temporary_directory / "missing-password-mode-key"),
                "FOUNDRY_SSH_PORT": "22",
                "FOUNDRY_DB_LOCAL_PORT": "15432",
                "FOUNDRY_DB_REMOTE_PORT": "15432",
                "FOUNDRY_OTLP_LOCAL_PORT": "4318",
                "FOUNDRY_OTLP_REMOTE_PORT": "4318",
                "FOUNDRY_TEST_SSH_EXIT": "0",
            }
        )
        arguments_file.unlink()
        result = subprocess.run(
            [
                powershell,
                "-NoLogo",
                "-NoProfile",
                "-NonInteractive",
                "-File",
                str(SCRIPT),
                "-Password",
                "-SshExecutable",
                str(fake_ssh),
            ],
            cwd=ROOT,
            env=environment,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=15,
            check=False,
        )
        require(result.returncode == 0, f"password-mode fake SSH invocation failed: {result.stdout}")
        require(arguments_file.is_file(), "password-mode fake ssh.exe did not record its arguments")
        arguments = arguments_file.read_text(encoding="utf-8-sig").splitlines()
        expected_arguments = [
            "-p",
            "22",
            "-o",
            "BatchMode=no",
            "-o",
            "PubkeyAuthentication=no",
            "-o",
            "PasswordAuthentication=yes",
            "-o",
            "KbdInteractiveAuthentication=yes",
            "-o",
            "PreferredAuthentications=password,keyboard-interactive",
            "-o",
            "ExitOnForwardFailure=yes",
            "-o",
            "ServerAliveInterval=30",
            "-o",
            "ServerAliveCountMax=3",
            "-o",
            "StrictHostKeyChecking=ask",
            "-L",
            "127.0.0.1:15432:127.0.0.1:15432",
            "-L",
            "127.0.0.1:4318:127.0.0.1:4318",
            "-N",
            "developer@example.invalid",
        ]
        require(arguments == expected_arguments, f"password mode received unexpected arguments: {arguments!r}")
        require(str(key_file.absolute()) not in arguments, "password mode unexpectedly passed an SSH key")

        # Preserve the original environment-variable selector for parity with
        # the Bash helper and existing callers.
        arguments_file.unlink()
        environment["FOUNDRY_SSH_AUTH"] = "password"
        result = subprocess.run(
            [
                powershell,
                "-NoLogo",
                "-NoProfile",
                "-NonInteractive",
                "-File",
                str(SCRIPT),
                "-SshExecutable",
                str(fake_ssh),
            ],
            cwd=ROOT,
            env=environment,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=15,
            check=False,
        )
        require(result.returncode == 0, f"environment password mode failed: {result.stdout}")
        require(arguments_file.is_file(), "environment password mode did not invoke fake ssh.exe")
        arguments = arguments_file.read_text(encoding="utf-8-sig").splitlines()
        require(arguments == expected_arguments, f"environment password mode received unexpected arguments: {arguments!r}")

        # A user may mistake -Password for a secret-valued parameter. Reject
        # that form without invoking SSH or repeating the supplied value.
        arguments_file.unlink()
        sentinel = "SYNTHETIC_PASSWORD_MUST_NOT_BE_ECHOED"
        result = subprocess.run(
            [
                powershell,
                "-NoLogo",
                "-NoProfile",
                "-NonInteractive",
                "-File",
                str(SCRIPT),
                "-Password",
                sentinel,
                "-SshExecutable",
                str(fake_ssh),
            ],
            cwd=ROOT,
            env=environment,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=15,
            check=False,
        )
        require(result.returncode == 2, f"password-value misuse returned {result.returncode}, not 2")
        require(not arguments_file.exists(), "password-value misuse unexpectedly invoked ssh.exe")
        require(sentinel not in result.stdout, "password-value misuse echoed the supplied value")

        environment["FOUNDRY_TEST_SSH_EXIT"] = "37"
        result = subprocess.run(
            [
                powershell,
                "-NoLogo",
                "-NoProfile",
                "-NonInteractive",
                "-File",
                str(SCRIPT),
                "-SshExecutable",
                str(fake_ssh),
            ],
            cwd=ROOT,
            env=environment,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=15,
            check=False,
        )
        require(result.returncode == 37, "the fake OpenSSH exit status was not propagated")


def main() -> None:
    require(SCRIPT.is_file(), "missing scripts/foundry-db-tunnel.ps1")
    text = SCRIPT.read_text(encoding="utf-8")
    verify_static_contract(text)
    optional_powershell_preflight()
    print("PASS TC-INFRA-013 Windows PowerShell tunnel policy invariants verified.")


if __name__ == "__main__":
    main()
