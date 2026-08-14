#!/usr/bin/env bash
set -euo pipefail

repository_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${repository_root}"

python_binary="${PYTHON_BIN:-python3}"
expected_python="$(tr -d '[:space:]' < .python-version)"
actual_python="$("${python_binary}" -c 'import platform; print(platform.python_version())')"

if [[ "${actual_python}" != "${expected_python}" ]]; then
  echo "Foundry requires Python ${expected_python}; ${python_binary} is ${actual_python}." >&2
  echo "Install the required version or set PYTHON_BIN to its executable." >&2
  exit 1
fi

if ! "${python_binary}" -c 'import ssl, venv, xml.parsers.expat' >/dev/null 2>&1; then
  echo "Python ${expected_python} is incomplete or has broken native libraries." >&2
  echo "Repair/reinstall that Python interpreter before creating the Foundry environment." >&2
  exit 1
fi

if [[ ! -d .venv ]]; then
  "${python_binary}" -m venv .venv
fi

if ! .venv/bin/python -m pip --version >/dev/null 2>&1; then
  echo "The existing .venv is incomplete. Move or remove it, then rerun this script." >&2
  exit 1
fi

.venv/bin/python -m pip install --disable-pip-version-check "pip==26.2.1"
.venv/bin/python -m pip install --disable-pip-version-check \
  --requirement requirements-controller.lock
.venv/bin/ansible-galaxy collection install \
  --requirements-file collections/requirements.yml \
  --collections-path collections \
  --no-deps \
  --force

.venv/bin/python scripts/verify-controller.py

echo
echo "Foundry controller environment is ready."
echo "Activate it with: source .venv/bin/activate"
