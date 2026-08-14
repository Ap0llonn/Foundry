#!/usr/bin/env python3
"""Verify non-negotiable Infrastructure Services V1 safety invariants."""

from pathlib import Path
import re

import yaml


ROOT = Path(__file__).resolve().parent.parent
ROLE = ROOT / "roles" / "7_infrastructure_services"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"Infrastructure Services policy verification failed: {message}")


required_files = [
    "defaults/main.yml",
    "tasks/main.yml",
    "tasks/01_validate.yml",
    "tasks/plan/main.yml",
    "tasks/common/resolve_domains.yml",
    "tasks/postgres/main.yml",
    "tasks/redis/main.yml",
    "tasks/minio/validate.yml",
    "tasks/swarm/main.yml",
    "tasks/ingress/main.yml",
    "tasks/traefik/main.yml",
    "tasks/dokploy/main.yml",
    "tasks/dokploy/validate.yml",
    "tasks/output/main.yml",
    "tasks/validation/main.yml",
    "templates/traefik.yml.j2",
    "Doc.MD",
]
for relative in required_files:
    require((ROLE / relative).is_file(), f"missing {relative}")

defaults = yaml.safe_load((ROLE / "defaults/main.yml").read_text())
for image in [
    defaults["services_defaults"]["postgres"]["image"],
    defaults["services_defaults"]["redis"]["image"],
    defaults["platform_defaults"]["traefik"]["image"],
    defaults["platform_defaults"]["dokploy"]["image"],
    defaults["platform_defaults"]["dokploy"]["postgres_image"],
]:
    require(re.search(r"@sha256:[a-f0-9]{64}$", image) is not None, f"mutable image default: {image}")

all_tasks = "\n".join(path.read_text() for path in (ROLE / "tasks").rglob("*.yml"))
for forbidden in [
    "dokploy.com/install.sh",
    "swarm leave",
    "docker system prune",
    "docker volume prune",
    "docker network prune",
    "chmod 777",
]:
    require(forbidden not in all_tasks, f"forbidden destructive behavior: {forbidden}")

main = (ROLE / "tasks/main.yml").read_text()
for required in [
    "postgres/main.yml",
    "redis/main.yml",
    "minio/converge.yml",
    "swarm/main.yml",
    "ingress/main.yml",
    "traefik/main.yml",
    "dokploy/main.yml",
    "output/main.yml",
]:
    require(required in main, f"orchestrator omits {required}")

validation = (ROLE / "tasks/01_validate.yml").read_text()
for required in [
    "infrastructure_services_immutable_image_pattern",
    "management",
    "restrict_by_cidr",
    "infrastructure_services_absolute_safe_path_pattern",
    "network.exposure",
]:
    require(required in validation, f"validation lacks {required}")

postgres = "\n".join(path.read_text() for path in (ROLE / "tasks/postgres").rglob("*.yml"))
redis = "\n".join(path.read_text() for path in (ROLE / "tasks/redis").rglob("*.yml"))
minio = "\n".join(path.read_text() for path in (ROLE / "tasks/minio").rglob("*.yml"))
require("POSTGRES_PASSWORD_FILE=" in postgres, "PostgreSQL password is not file-mounted")
require("POSTGRES_PASSWORD='" not in postgres, "PostgreSQL password is in Docker metadata")
require("/usr/local/etc/redis/redis.conf:ro" in redis, "Redis secret config is not mounted read-only")
require("'REDIS_PASSWORD=' +" not in redis, "Redis password is in Docker metadata")
require("--publish" not in postgres, "PostgreSQL publishes a host port")
require("--publish" not in redis, "Redis publishes a host port")
require("--publish" not in minio, "MinIO publishes a host port")
require("pg_isready" in postgres, "PostgreSQL service-level health is missing")
require("redis-cli" in redis and "PONG" in redis, "Redis authenticated health is missing")
require("/minio/health/live" in minio, "MinIO health probe is missing")

traefik = (ROLE / "templates/traefik.yml.j2").read_text()
require("exposedByDefault: false" in traefik, "Traefik exposes undeclared services")
require("docker:" in traefik and "swarm:" in traefik, "Dokploy requires both Docker and Swarm providers")
require("dashboard: false" in traefik, "Traefik dashboard is not disabled")
dokploy = (ROLE / "tasks/dokploy/main.yml").read_text()
for required in [
    "ipallowlist.sourcerange",
    "foundry.managed=true",
    "Docker secrets",
    "dokploy-postgres",
]:
    require(required in dokploy, f"Dokploy safety contract lacks {required}")

config = yaml.safe_load((ROOT / "config.yml").read_text())
require("services" in config and "platform" in config and "domains" in config, "global high-level config is incomplete")
require(config["platform"]["dokploy"]["enabled"] is False, "Dokploy must not be enabled implicitly")

print("Infrastructure Services policy invariants verified.")
