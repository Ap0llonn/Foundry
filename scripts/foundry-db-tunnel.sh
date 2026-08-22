#!/usr/bin/env bash
set -euo pipefail

# The Ansible database_access=tunnel mode keeps the proxy on VM localhost.
# This script only forwards that localhost listener to the developer laptop.
# It never contains or transmits the PostgreSQL password.

ssh_target="${FOUNDRY_SSH_TARGET:-}"
ssh_key="${FOUNDRY_SSH_KEY:-}"
ssh_port="${FOUNDRY_SSH_PORT:-22}"
local_port="${FOUNDRY_DB_LOCAL_PORT:-15432}"
remote_port="${FOUNDRY_DB_REMOTE_PORT:-15432}"

if [[ -z "${ssh_target}" ]]; then
  echo "FOUNDRY_SSH_TARGET is required, for example ubuntu@vm.example.com" >&2
  exit 2
fi

if [[ ! "${ssh_port}" =~ ^[0-9]+$ || ! "${local_port}" =~ ^[0-9]+$ || ! "${remote_port}" =~ ^[0-9]+$ ]]; then
  echo "FOUNDRY_SSH_PORT, FOUNDRY_DB_LOCAL_PORT, and FOUNDRY_DB_REMOTE_PORT must be numeric" >&2
  exit 2
fi

ssh_args=(-p "${ssh_port}")
if [[ -n "${ssh_key}" ]]; then
  ssh_args+=(-i "${ssh_key}")
fi

exec ssh \
  "${ssh_args[@]}" \
  -o ExitOnForwardFailure=yes \
  -o ServerAliveInterval=30 \
  -o ServerAliveCountMax=3 \
  -L "${local_port}:127.0.0.1:${remote_port}" \
  -N "${ssh_target}"
