#!/usr/bin/env python3
"""Verify the pinned Foundry controller without contacting managed hosts."""

from __future__ import annotations

import importlib.metadata
import json
import platform
from pathlib import Path
import re
import subprocess
import sys

import yaml


ROOT = Path(__file__).resolve().parent.parent


def fail(message: str) -> None:
    raise SystemExit(f"Controller verification failed: {message}")


expected_python = (ROOT / ".python-version").read_text().strip()
if platform.python_version() != expected_python:
    fail(
        f"expected Python {expected_python}, found {platform.python_version()}"
    )

locked_packages: dict[str, str] = {}
for line in (ROOT / "requirements-controller.lock").read_text().splitlines():
    match = re.fullmatch(r"([A-Za-z0-9_.-]+)==([^\s]+)", line.strip())
    if match:
        locked_packages[match.group(1)] = match.group(2)

for package_name, expected_version in locked_packages.items():
    try:
        actual_version = importlib.metadata.version(package_name)
    except importlib.metadata.PackageNotFoundError:
        fail(f"missing Python package {package_name}=={expected_version}")
    if actual_version != expected_version:
        fail(
            f"{package_name} must be {expected_version}, found {actual_version}"
        )

collection_requirements = yaml.safe_load(
    (ROOT / "collections/requirements.yml").read_text()
)["collections"]
for requirement in collection_requirements:
    namespace, collection = requirement["name"].split(".", maxsplit=1)
    manifest_path = (
        ROOT
        / "collections/ansible_collections"
        / namespace
        / collection
        / "MANIFEST.json"
    )
    if not manifest_path.exists():
        fail(
            f"missing collection {requirement['name']}=={requirement['version']}"
        )
    manifest = json.loads(manifest_path.read_text())
    actual_version = manifest["collection_info"]["version"]
    if actual_version != requirement["version"]:
        fail(
            f"{requirement['name']} must be {requirement['version']}, "
            f"found {actual_version}"
        )

ansible_playbook = Path(sys.executable).with_name("ansible-playbook")
if not ansible_playbook.exists():
    fail(f"{ansible_playbook} is missing; run the controller bootstrap")

subprocess.run(
    [str(ansible_playbook), "--syntax-check", "playbook.yml"],
    check=True,
    cwd=ROOT,
)
subprocess.run(
    [
        str(ansible_playbook),
        "--syntax-check",
        "-i",
        "localhost,",
        "roles/4_security/tests/syntax.yml",
    ],
    check=True,
    cwd=ROOT,
)
subprocess.run(
    [
        str(ansible_playbook),
        "--syntax-check",
        "-i",
        "localhost,",
        "roles/2_os_base_system/tests/syntax.yml",
    ],
    check=True,
    cwd=ROOT,
)
for role_syntax_playbook in [
    "roles/5_networking/tests/syntax.yml",
    "roles/7_infrastructure_services/tests/syntax.yml",
]:
    subprocess.run(
        [
            str(ansible_playbook),
            "--syntax-check",
            "-i",
            "localhost,",
            role_syntax_playbook,
        ],
        check=True,
        cwd=ROOT,
    )
subprocess.run(
    [sys.executable, "scripts/verify-security-role-policy.py"],
    check=True,
    cwd=ROOT,
)
subprocess.run(
    [sys.executable, "scripts/verify-os-role-policy.py"],
    check=True,
    cwd=ROOT,
)
subprocess.run(
    [sys.executable, "scripts/verify-networking-role-policy.py"],
    check=True,
    cwd=ROOT,
)
subprocess.run(
    [sys.executable, "scripts/verify-infrastructure-services-role-policy.py"],
    check=True,
    cwd=ROOT,
)

print(
    f"Controller verified: Python {expected_python}, "
    f"ansible-core {locked_packages['ansible-core']}, "
    f"{len(collection_requirements)} pinned collections."
)
