#!/usr/bin/env python3
"""Verify non-negotiable Foundry Security V1 policy invariants."""

from pathlib import Path
import sys

import yaml


ROOT = Path(__file__).resolve().parent.parent
ROLE = ROOT / "roles" / "4_security"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"Security role policy verification failed: {message}")


required_files = [
    "tasks/firewall/main.yml",
    "tasks/firewall/resolve.yml",
    "tasks/firewall/ownership.yml",
    "tasks/firewall/converge.yml",
    "tasks/ssh/main.yml",
    "tasks/ssh/apply_policy.yml",
    "tasks/ssh/migrate_connection.yml",
    "tasks/fail2ban/main.yml",
    "tasks/updates/main.yml",
    "tasks/apparmor/main.yml",
    "tasks/logging/main.yml",
    "tasks/validation/main.yml",
]
for relative_path in required_files:
    require((ROLE / relative_path).is_file(), f"missing modular task {relative_path}")

defaults = yaml.safe_load((ROLE / "defaults/main.yml").read_text())["security_defaults"]
require(defaults["ssh"]["empty_passwords"] is False, "empty passwords must default off")
require(defaults["firewall"]["default_incoming"] == "deny", "incoming policy must default deny")
require(defaults["updates"]["automatic_reboot"] is False, "automatic reboot must default off")
require(defaults["apparmor"]["enabled"] is True, "AppArmor must default on")
require(defaults["logging"]["persistent_journal"] is True, "persistent journal must default on")

ssh_template = (ROLE / "templates/foundry-sshd.conf.j2").read_text()
for directive in [
    "PermitRootLogin",
    "PasswordAuthentication",
    "PermitEmptyPasswords",
    "AllowAgentForwarding",
    "AllowTcpForwarding",
    "X11Forwarding",
    "MaxSessions",
    "MaxStartups",
]:
    require(directive in ssh_template, f"SSH template missing {directive}")
for forbidden in ["Ciphers ", "KexAlgorithms ", "MACs "]:
    require(forbidden not in ssh_template, f"custom SSH crypto is out of V1 scope: {forbidden.strip()}")

firewall_text = (ROLE / "tasks/firewall/converge.yml").read_text()
require(firewall_text.count('comment: "{{ item.comment }}"') >= 2, "add and delete must use ownership comments")
require("state: disabled" not in firewall_text, "disabled ownership must not disable external firewall state")

all_task_text = "\n".join(path.read_text() for path in (ROLE / "tasks").rglob("*.yml"))
require("ssh-keygen, -A" not in all_task_text, "ordinary convergence must not regenerate host keys")
require("security_firewall_comment_prefix" in all_task_text, "firewall ownership prefix is unused")
require("Storage=persistent" in (ROLE / "templates/foundry-journald.conf.j2").read_text(), "journal is not persistent")

config = yaml.safe_load((ROOT / "config.yml").read_text())
require(config.get("network", {}).get("exposure"), "global network.exposure manifest is empty")
require("management" in config, "management CIDR policy is missing")

print("Security role policy invariants verified.")
