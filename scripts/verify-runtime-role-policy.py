#!/usr/bin/env python3
"""Verify non-negotiable Foundry Runtime V1 ownership and safety policy."""

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parent.parent
RUNTIME = ROOT / "roles" / "6_runtime_platform"
NETWORKING = ROOT / "roles" / "5_networking"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"Runtime policy verification failed: {message}")


required_runtime_files = [
    "defaults/main.yml",
    "tasks/main.yml",
    "tasks/01_validate.yml",
    "tasks/repository/main.yml",
    "tasks/install/main.yml",
    "tasks/configuration/main.yml",
    "tasks/service/main.yml",
    "tasks/storage/main.yml",
    "tasks/swarm/main.yml",
    "tasks/smoke/main.yml",
    "tasks/validation/main.yml",
    "tests/syntax.yml",
    "Doc.MD",
]
for relative in required_runtime_files:
    require((RUNTIME / relative).is_file(), f"missing {relative}")

defaults = yaml.safe_load((RUNTIME / "defaults/main.yml").read_text())
docker_defaults = defaults["runtime_defaults"]["docker"]
require(docker_defaults["enabled"] is False, "Docker must be opt-in by default")
require(docker_defaults["logging"]["max_size"] == "10m", "log size default drifted")
require(docker_defaults["logging"]["max_files"] == 3, "log count default drifted")
require("@sha256:" in docker_defaults["smoke_test"]["image"], "smoke image is mutable")
require(defaults["runtime_docker_key_checksum"].startswith("sha256:"), "key is not pinned")
require(defaults["runtime_docker_repository_url"].startswith("https://download.docker.com/"), "repository is not official HTTPS Docker")
require(set(defaults["runtime_docker_packages"]) == {
    "docker-ce",
    "docker-ce-cli",
    "containerd.io",
    "docker-buildx-plugin",
    "docker-compose-plugin",
}, "certified Docker package set is incomplete")
require(all(version for version in defaults["runtime_docker_packages"].values()), "package version is unpinned")

tasks = "\n".join(path.read_text() for path in (RUNTIME / "tasks").rglob("*.yml"))
for required in [
    "ansible.builtin.deb822_repository",
    "Inspect cached Docker Engine versions",
    "Require every certified Docker package before installation",
    "checksum:",
    "ansible.builtin.dpkg_selections",
    "download_only: true",
    "dockerd",
    "--validate",
    "daemon_config_adoption",
    "maintenance_window",
    "runtime_swarm_requested",
    "LiveRestoreEnabled",
    "Remote Docker API ports 2375/2376 are always forbidden",
    "docker, compose, version",
    "DockerRootDir",
    "runtime_docker_socket_state.stat.issock",
    "primary group",
    "tcp://",
    "@sha256:",
]:
    require(required in tasks or required in (RUNTIME / "defaults/main.yml").read_text(), f"missing policy evidence: {required}")

for forbidden in [
    "curl | sh",
    "get.docker.com",
    "docker system prune",
    "docker network create",
    "docker volume rm",
    "docker image prune",
    "state: absent\n  loop: \"{{ docker",
    "docker swarm leave",
    "swarm, leave",
]:
    require(forbidden not in tasks, f"forbidden Runtime behavior: {forbidden}")

configuration = (RUNTIME / "tasks/configuration/main.yml").read_text()
require(configuration.index("--validate") < configuration.index("Install the validated Docker daemon configuration"), "daemon config is applied before validation")
require("rescue:" in configuration and "Restore the previous Docker daemon configuration" in configuration, "daemon rollback is absent")
require("partial-run recovery" in configuration, "interrupted first-bootstrap recovery is absent")
require("runtime_docker_partial_recovery_documents" in configuration, "partial-bootstrap daemon documents are not bounded")

playbook = yaml.safe_load((ROOT / "playbook.yml").read_text())
standardize = next(play for play in playbook if play.get("name") == "Standardize infrastructure")
role_names = [entry["role"] for entry in standardize["roles"]]
require(role_names.index("4_security") < role_names.index("6_runtime_platform") < role_names.index("5_networking"), "Runtime must execute between Security and Networking")

networking_tasks = "\n".join(path.read_text() for path in (NETWORKING / "tasks").rglob("*.yml"))
require("ansible.builtin.apt:" not in networking_tasks, "Networking still installs packages")
require("ansible.builtin.systemd_service:" not in networking_tasks, "Networking still owns Docker services")
require("networking_runtime_ownership_manifest" in networking_tasks, "Networking does not consume Runtime ownership")
swarm_tasks = (RUNTIME / "tasks/swarm/main.yml").read_text()
for required in [
    "- docker\n      - swarm\n      - init",
    "runtime_swarm_state_file",
    "single-manager",
    "Refuse adoption of an active external Swarm",
]:
    require(required in swarm_tasks, f"missing safe Dokploy Swarm evidence: {required}")

config = yaml.safe_load((ROOT / "config.yml").read_text())
require(config.get("runtime", {}).get("docker", {}).get("enabled") is True, "global config does not enable Runtime Docker")

print("Runtime V1 policy invariants verified.")
