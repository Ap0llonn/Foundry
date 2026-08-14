#!/usr/bin/env python3
"""Verify non-negotiable environment-network ownership boundaries."""

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parent.parent
NETWORKING = ROOT / "roles" / "5_networking"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"Networking policy verification failed: {message}")


for relative in [
    "tasks/01_validate.yml",
    "tasks/02_docker_dependency.yml",
    "tasks/discovery/main.yml",
    "tasks/networks/main.yml",
    "tasks/validation/main.yml",
]:
    require((NETWORKING / relative).is_file(), f"missing {relative}")

networking_defaults_text = (NETWORKING / "defaults/main.yml").read_text()
networking_defaults = yaml.safe_load(networking_defaults_text)
network_driver_policy = networking_defaults["networking_network_driver"]
require("bridge" in network_driver_policy, "ordinary environment driver must support bridge")
require("overlay" in network_driver_policy, "Dokploy environments must support overlay")
require(networking_defaults["networking_network_internal"] is False, "networks must not default internal")
require(
    networking_defaults["networking_defaults"]["stale_network_policy"] == "report",
    "stale networks must default to non-destructive reporting",
)

networking_tasks = "\n".join(path.read_text() for path in (NETWORKING / "tasks").rglob("*.yml"))
for label in [
    "foundry.managed",
    "foundry.project",
    "foundry.environment",
    "foundry.resource",
]:
    require(label in (NETWORKING / "defaults/main.yml").read_text(), f"missing ownership label {label}")
for forbidden in ["state: absent\n  loop: \"{{ networking_owned"]:
    require(forbidden not in networking_tasks, f"networking crosses ownership boundary: {forbidden}")
docker_tasks = (NETWORKING / "tasks/02_docker_dependency.yml").read_text()
require("ansible.builtin.apt" not in networking_tasks, "Networking must not install Docker")
require("ansible.builtin.systemd_service" not in networking_tasks, "Networking must not own Docker services")
require("networking_runtime_ownership_manifest" in docker_tasks, "Runtime ownership contract is not required")
require("networking_docker_binary" in docker_tasks, "Docker daemon is not validated")
require("item.Containers" in networking_tasks, "stale attachment safety is missing")
require("--attachable" in networking_tasks, "Swarm overlays must be attachable")
require("Scope == 'swarm'" in networking_tasks, "overlay scope validation is missing")

config = yaml.safe_load((ROOT / "config.yml").read_text())
require(config.get("project", {}).get("name"), "project.name is absent")
require(config.get("environments"), "environments are absent")
require("object_storage" in config.get("services", {}), "object-storage config is absent")

print("Networking policy invariants verified.")
