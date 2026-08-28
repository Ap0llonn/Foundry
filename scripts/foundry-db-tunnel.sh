#!/usr/bin/env bash
set -euo pipefail

# The Ansible database_access=tunnel mode keeps the PostgreSQL proxy and the
# OpenTelemetry Collector on VM localhost. This script forwards both endpoints
# through one encrypted SSH connection. It never contains database credentials.

ssh_user="${FOUNDRY_SSH_USER:-ubuntu}"
ssh_host="${FOUNDRY_SSH_HOST:-149.56.96.110}"
ssh_target="${FOUNDRY_SSH_TARGET:-${ssh_user}@${ssh_host}}"
ssh_auth="${FOUNDRY_SSH_AUTH:-key}"
ssh_key="${FOUNDRY_SSH_KEY:-$HOME/.ssh/ansible}"
ssh_port="${FOUNDRY_SSH_PORT:-22}"
local_port="${FOUNDRY_DB_LOCAL_PORT:-15432}"
remote_port="${FOUNDRY_DB_REMOTE_PORT:-15432}"
otlp_local_port="${FOUNDRY_OTLP_LOCAL_PORT:-4318}"
otlp_remote_port="${FOUNDRY_OTLP_REMOTE_PORT:-4318}"

if [[ -z "${ssh_target}" ]]; then
  echo "Set FOUNDRY_SSH_TARGET or both FOUNDRY_SSH_USER and FOUNDRY_SSH_HOST." >&2
  exit 2
fi

if [[ "${ssh_target}" == -* ]]; then
  echo "The SSH target cannot begin with a dash." >&2
  exit 2
fi

if [[ "${ssh_auth}" != "key" && "${ssh_auth}" != "password" ]]; then
  echo "FOUNDRY_SSH_AUTH must be either key or password." >&2
  exit 2
fi

if [[ ! "${ssh_port}" =~ ^[0-9]+$ || ! "${local_port}" =~ ^[0-9]+$ || ! "${remote_port}" =~ ^[0-9]+$ || ! "${otlp_local_port}" =~ ^[0-9]+$ || ! "${otlp_remote_port}" =~ ^[0-9]+$ ]]; then
  echo "FOUNDRY_SSH_PORT, database ports, and OTLP ports must be numeric" >&2
  exit 2
fi

ssh_args=(-p "${ssh_port}")
if [[ "${ssh_auth}" == "key" ]]; then
  if [[ -z "${ssh_key}" || ! -r "${ssh_key}" ]]; then
    echo "SSH key is not readable: ${ssh_key}" >&2
    echo "Set FOUNDRY_SSH_KEY, or use FOUNDRY_SSH_AUTH=password." >&2
    exit 2
  fi
  ssh_args+=(
    -i "${ssh_key}"
    -o BatchMode=no
    -o IdentitiesOnly=yes
    -o PreferredAuthentications=publickey
  )
else
  # OpenSSH reads the password from the terminal without echoing it. Do not
  # accept a password environment variable because it can leak through shell
  # history, process inspection, logs, or crash reports.
  ssh_args+=(
    -o BatchMode=no
    -o PubkeyAuthentication=no
    -o PreferredAuthentications=password,keyboard-interactive
  )
fi

echo "Opening ${ssh_auth} SSH tunnel to ${ssh_target}:${ssh_port}"
exec ssh \
  "${ssh_args[@]}" \
  -o ExitOnForwardFailure=yes \
  -o ServerAliveInterval=30 \
  -o ServerAliveCountMax=3 \
  -L "${local_port}:127.0.0.1:${remote_port}" \
  -L "${otlp_local_port}:127.0.0.1:${otlp_remote_port}" \
  -N "${ssh_target}"
