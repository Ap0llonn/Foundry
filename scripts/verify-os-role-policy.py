#!/usr/bin/env python3
"""Static safety invariants for Foundry's OS/base-system role."""

from __future__ import annotations

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parent.parent
ROLE = ROOT / "roles" / "2_os_base_system"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"OS role policy verification failed: {message}")


defaults = yaml.safe_load((ROLE / "defaults" / "main.yml").read_text())
require(defaults["os_base_operation_mode"] == "bootstrap", "default mode is not bootstrap")
for setting in (
    "os_base_maintenance_approved",
    "os_base_maintenance_autoremove",
    "os_base_maintenance_removals_approved",
    "os_base_maintenance_autoclean",
    "os_base_reboot_enabled",
    "os_base_reboot_approved",
):
    require(defaults[setting] is False, f"{setting} must fail closed")

require(
    defaults["os_base_supported_platforms"]
    == [{"distribution": "Ubuntu", "versions": ["26.04"], "architectures": ["x86_64"]}],
    "supported-platform tuple changed without updating its evidence",
)
require(defaults["os_base_allowed_needrestart_modes"] == ["report"], "needrestart may restart workloads")

task_files = list((ROLE / "tasks").glob("*.yml"))
task_text = {path.name: path.read_text() for path in task_files}
for token in ("upgrade: dist", "autoremove: true", "purge: true"):
    owners = [name for name, content in task_text.items() if token in content]
    require(owners == ["02_full_maintenance.yml"], f"{token!r} is not isolated: {owners}")

reboot_owners = [name for name, content in task_text.items() if "ansible.builtin.reboot:" in content]
require(reboot_owners == ["10_controlled_reboot.yml"], f"reboot is not isolated: {reboot_owners}")
require("10_controlled_reboot.yml" not in task_text["main.yml"], "normal role imports reboot")

full_maintenance = task_text["02_full_maintenance.yml"]
for guard in (
    "os_base_maintenance_approved",
    "os_base_maintenance_window",
    "os_base_maintenance_removals_approved",
    "--simulate",
):
    require(guard in full_maintenance, f"maintenance guard/plan missing: {guard}")

preflight = task_text["main.yml"]
for operation_tag in ("os_security_patching", "os_full_maintenance"):
    require(operation_tag in preflight, f"preflight is not selected by {operation_tag}")

apt_configuration = task_text["02_apt_configuration.yml"]
for cleared_list in (
    "#clear Unattended-Upgrade::Allowed-Origins;",
    "#clear Unattended-Upgrade::Origins-Pattern;",
):
    require(cleared_list in apt_configuration, f"security origins are additive: {cleared_list}")
require("99foundry-security-upgrades" in apt_configuration, "exclusive origin policy does not load last")

playbook = (ROOT / "playbook.yml").read_text()
for operation_tag in ("os_security_patching", "os_full_maintenance", "os_reboot"):
    require(operation_tag in playbook, f"role-level tag missing: {operation_tag}")
require("tags: [os_reboot]" in playbook, "dynamic reboot role does not propagate its tag")

require("/dev/stdin" in task_text["05_time.yml"], "Chrony candidate validation writes during check mode")
require("NTS key establishment" in task_text["validate_time.yml"], "NTS cryptographic state is not asserted")

security_validation = (ROOT / "roles" / "4_security" / "tasks" / "01_validate.yml").read_text()
security_updates = (ROOT / "roles" / "4_security" / "tasks" / "06_updates.yml").read_text()
require("not security_resolved.updates.automatic_reboot" in security_validation, "security can bypass reboot gates")
require('Automatic-Reboot "false"' in security_updates, "unattended upgrades can reboot")

print("OS role policy invariants verified.")
