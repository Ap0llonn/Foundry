#!/usr/bin/env python3
"""Run Foundry acceptance tests with explicit mutation boundaries."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

import yaml


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INVENTORY = (ROOT / "inventory.yml").resolve()


class AcceptanceFailure(RuntimeError):
    """Raised when an acceptance test does not meet its expected outcome."""


def verify_catalog() -> None:
    criteria_text = (ROOT / "tests" / "acceptance-criteria.md").read_text()
    criterion_ids = set(re.findall(r"^### (AC-[A-Z0-9-]+) —", criteria_text, re.MULTILINE))
    catalog = yaml.safe_load((ROOT / "tests" / "test-cases.yml").read_text())
    cases = catalog.get("test_cases", []) if isinstance(catalog, dict) else []
    if not cases:
        raise AcceptanceFailure("TC-GLOBAL-003 acceptance catalog is empty")

    case_ids = [case.get("id") for case in cases]
    if len(case_ids) != len(set(case_ids)):
        raise AcceptanceFailure("TC-GLOBAL-003 contains duplicate test-case IDs")

    for case in cases:
        test_id = case.get("id", "unnamed test")
        criterion = case.get("criterion")
        tier = case.get("tier")
        destructive = case.get("destructive")
        automated = case.get("automated")
        if criterion not in criterion_ids:
            raise AcceptanceFailure(
                f"TC-GLOBAL-003 {test_id} references unknown criterion {criterion}"
            )
        if tier not in {"static", "live", "fresh"}:
            raise AcceptanceFailure(
                f"TC-GLOBAL-003 {test_id} has invalid tier {tier}"
            )
        if not isinstance(destructive, bool) or not isinstance(automated, bool):
            raise AcceptanceFailure(
                f"TC-GLOBAL-003 {test_id} must declare boolean safety fields"
            )
        if tier in {"static", "live"} and destructive:
            raise AcceptanceFailure(
                f"TC-GLOBAL-003 {test_id} cannot mutate in tier {tier}"
            )
        if tier == "fresh" and not destructive:
            raise AcceptanceFailure(
                f"TC-GLOBAL-003 {test_id} must acknowledge fresh-tier mutation"
            )
        fixture_name = case.get("fixture")
        if fixture_name:
            fixture = ROOT / "tests" / fixture_name
            if not fixture.is_file():
                raise AcceptanceFailure(
                    f"TC-GLOBAL-003 {test_id} fixture does not exist: {fixture_name}"
                )
            fixture_text = fixture.read_text()
            if "PRIVATE KEY" in fixture_text or "password_hash:" in fixture_text:
                raise AcceptanceFailure(
                    f"TC-GLOBAL-003 {test_id} fixture may contain secret material"
                )

    print("PASS TC-GLOBAL-003")


def executable(name: str) -> str:
    sibling = Path(sys.executable).with_name(name)
    if sibling.exists():
        return str(sibling)
    resolved = shutil.which(name)
    if resolved:
        return resolved
    raise AcceptanceFailure(f"missing executable: {name}")


def run_command(
    test_id: str,
    command: list[str],
    *,
    expect_success: bool = True,
    require_zero_changes: bool = False,
) -> None:
    environment = os.environ.copy()
    environment["ANSIBLE_FORCE_COLOR"] = "0"
    result = subprocess.run(
        command,
        cwd=ROOT,
        env=environment,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )

    outcome_matches = (result.returncode == 0) == expect_success
    if not outcome_matches:
        expectation = "succeed" if expect_success else "be rejected"
        details = result.stdout if expect_success else "unsafe fixture was accepted"
        raise AcceptanceFailure(
            f"{test_id} expected command to {expectation}, rc={result.returncode}\n"
            f"{details}"
        )

    if require_zero_changes:
        changed_counts = [
            int(value) for value in re.findall(r"\bchanged=(\d+)\b", result.stdout)
        ]
        if not changed_counts:
            raise AcceptanceFailure(
                f"{test_id} produced no parseable PLAY RECAP\n{result.stdout}"
            )
        if any(changed_counts):
            raise AcceptanceFailure(
                f"{test_id} expected changed=0, found {changed_counts}\n"
                f"{result.stdout}"
            )

    print(f"PASS {test_id}")


def collect_command(
    failures: list[str],
    test_id: str,
    command: list[str],
    **options: bool,
) -> bool:
    try:
        run_command(test_id, command, **options)
    except AcceptanceFailure as error:
        message = str(error)
        failures.append(message)
        print(f"FAIL {message}", file=sys.stderr)
        return False
    return True


def fixture_command(ansible_playbook: str, fixture_name: str) -> list[str]:
    fixture = ROOT / "tests" / "fixtures" / "identity" / fixture_name
    return [
        ansible_playbook,
        "-i",
        "localhost,",
        "tests/playbooks/identity_validate_fixture.yml",
        "-e",
        f"fixture_file={fixture}",
    ]


def role_fixture_command(
    ansible_playbook: str,
    playbook: str,
    fixture: str,
) -> list[str]:
    return [
        ansible_playbook,
        "-i",
        "localhost,",
        playbook,
        "-e",
        f"fixture_file={ROOT / 'tests' / fixture}",
    ]


def run_static() -> None:
    ansible_playbook = executable("ansible-playbook")
    failures: list[str] = []

    collect_command(
        failures,
        "TC-GLOBAL-001",
        [sys.executable, "scripts/verify-controller.py"],
    )
    collect_command(
        failures,
        "TC-GLOBAL-002",
        [
            ansible_playbook,
            "--syntax-check",
            "-i",
            "localhost,",
            "tests/playbooks/identity_syntax.yml",
        ],
    )
    collect_command(
        failures,
        "TC-OS-001",
        [sys.executable, "scripts/verify-os-role-policy.py"],
    )
    collect_command(
        failures,
        "TC-SECURITY-001",
        [sys.executable, "scripts/verify-security-role-policy.py"],
    )
    collect_command(
        failures,
        "TC-RUNTIME-001",
        [sys.executable, "scripts/verify-runtime-role-policy.py"],
    )
    collect_command(
        failures,
        "TC-RUNTIME-002",
        [
            ansible_playbook,
            "--syntax-check",
            "-i",
            "localhost,",
            "roles/6_runtime_platform/tests/syntax.yml",
        ],
    )
    collect_command(
        failures,
        "TC-NETWORKING-001",
        [sys.executable, "scripts/verify-networking-role-policy.py"],
    )
    collect_command(
        failures,
        "TC-NETWORKING-008",
        [sys.executable, "scripts/verify-networking-role-policy.py"],
    )
    try:
        verify_catalog()
    except AcceptanceFailure as error:
        failures.append(str(error))
        print(f"FAIL {error}", file=sys.stderr)
    collect_command(
        failures,
        "TC-IDENTITY-001",
        fixture_command(ansible_playbook, "valid-passwordless.yml"),
    )
    collect_command(
        failures,
        "TC-IDENTITY-002",
        fixture_command(ansible_playbook, "invalid-missing-sudo-policy.yml"),
        expect_success=False,
    )
    collect_command(
        failures,
        "TC-IDENTITY-003",
        fixture_command(ansible_playbook, "invalid-malformed-key.yml"),
        expect_success=False,
    )
    collect_command(
        failures,
        "TC-IDENTITY-004",
        fixture_command(ansible_playbook, "invalid-duplicate-key-comments.yml"),
        expect_success=False,
    )
    for test_id, fixture_name, expect_success in [
        ("TC-NETWORKING-002", "fixtures/networking/valid.yml", True),
        ("TC-NETWORKING-003", "fixtures/networking/invalid-duplicate-environment.yml", False),
        ("TC-NETWORKING-004", "fixtures/networking/invalid-resolved-collision.yml", False),
        ("TC-NETWORKING-005", "fixtures/networking/invalid-reserved-name.yml", False),
    ]:
        collect_command(
            failures,
            test_id,
            role_fixture_command(
                ansible_playbook,
                "tests/playbooks/networking_validate_fixture.yml",
                fixture_name,
            ),
            expect_success=expect_success,
        )
    collect_command(
        failures,
        "TC-INFRA-008",
        [
            ansible_playbook,
            "-i",
            "localhost,",
            "tests/playbooks/infrastructure_plan_fixture.yml",
        ],
    )
    collect_command(
        failures,
        "TC-MINIO-001",
        role_fixture_command(
            ansible_playbook,
            "tests/playbooks/minio_validate_fixture.yml",
            "fixtures/minio/valid.yml",
        ),
    )
    collect_command(
        failures,
        "TC-MINIO-002",
        role_fixture_command(
            ansible_playbook,
            "tests/playbooks/minio_validate_fixture.yml",
            "fixtures/minio/invalid-latest-image.yml",
        ),
        expect_success=False,
    )
    collect_command(
        failures,
        "TC-MINIO-005",
        [
            ansible_playbook,
            "-i",
            "localhost,",
            "tests/playbooks/minio_collision_sanitization.yml",
        ],
    )
    collect_command(
        failures,
        "TC-INFRA-001",
        [sys.executable, "scripts/verify-infrastructure-services-role-policy.py"],
    )
    collect_command(
        failures,
        "TC-INFRA-002",
        [
            ansible_playbook,
            "--syntax-check",
            "-i",
            "localhost,",
            "roles/7_infrastructure_services/tests/syntax.yml",
        ],
    )
    for test_id, fixture_name, expect_success in [
        ("TC-INFRA-003", "fixtures/infrastructure/valid-hyphen.yml", True),
        ("TC-INFRA-004", "fixtures/infrastructure/valid-nested.yml", True),
        ("TC-INFRA-005", "fixtures/infrastructure/valid-domainless.yml", True),
        ("TC-INFRA-006", "fixtures/infrastructure/invalid-dokploy-public-bootstrap.yml", False),
        ("TC-INFRA-007", "fixtures/infrastructure/invalid-mutable-postgres.yml", False),
        ("TC-INFRA-009", "fixtures/infrastructure/valid-domainless-ipv6.yml", True),
        ("TC-INFRA-010", "fixtures/infrastructure/invalid-memory-suffix.yml", False),
        ("TC-INFRA-011", "fixtures/infrastructure/invalid-zero-cpu.yml", False),
        ("TC-INFRA-012", "fixtures/infrastructure/invalid-missing-postgres-database.yml", False),
    ]:
        collect_command(
            failures,
            test_id,
            role_fixture_command(
                ansible_playbook,
                "tests/playbooks/infrastructure_validate_fixture.yml",
                fixture_name,
            ),
            expect_success=expect_success,
        )
    if failures:
        raise AcceptanceFailure(
            f"static tier failed {len(failures)} acceptance test(s)"
        )


def playbook_command(inventory: Path, config: Path) -> list[str]:
    return [
        executable("ansible-playbook"),
        "-i",
        str(inventory),
        "playbook.yml",
        "-e",
        f"@{config}",
    ]


def run_live(inventory: Path, config: Path) -> None:
    base = playbook_command(inventory, config)
    failures: list[str] = []
    collect_command(
        failures,
        "TC-IDENTITY-013-CHECK",
        base + ["--check", "--tags", "identity_access"],
        require_zero_changes=True,
    )
    collect_command(
        failures,
        "TC-IDENTITY-013-RESULT",
        base + ["--tags", "identity_result"],
        require_zero_changes=True,
    )
    collect_command(
        failures,
        "TC-SECURITY-012-CHECK",
        base + ["--check", "--tags", "security"],
        require_zero_changes=True,
    )
    collect_command(
        failures,
        "TC-SECURITY-012-RESULT",
        base + ["--tags", "security_result"],
        require_zero_changes=True,
    )
    collect_command(
        failures,
        "TC-RUNTIME-005",
        base + ["--tags", "runtime_result"],
        require_zero_changes=True,
    )
    if failures:
        raise AcceptanceFailure(
            f"live tier failed {len(failures)} acceptance test(s)"
        )


def run_fresh(inventory: Path, config: Path, confirmation: str) -> None:
    if confirmation != "FOUNDRY-EPHEMERAL-VM":
        raise AcceptanceFailure(
            "fresh tests require --confirm FOUNDRY-EPHEMERAL-VM"
        )
    if inventory.resolve() == DEFAULT_INVENTORY:
        raise AcceptanceFailure(
            "fresh tests refuse the repository default inventory.yml"
        )
    if not inventory.is_file() or not config.is_file():
        raise AcceptanceFailure("fresh inventory and config must be existing files")

    inventory_data = yaml.safe_load(inventory.read_text())

    def has_ephemeral_marker(value: object) -> bool:
        if isinstance(value, dict):
            if value.get("foundry_test_target") == "ephemeral":
                return True
            return any(has_ephemeral_marker(child) for child in value.values())
        if isinstance(value, list):
            return any(has_ephemeral_marker(child) for child in value)
        return False

    if not has_ephemeral_marker(inventory_data):
        raise AcceptanceFailure(
            "fresh inventory must declare foundry_test_target: ephemeral"
        )

    config_data = yaml.safe_load(config.read_text()) or {}
    service_config = config_data.get("services", {})
    platform_config = config_data.get("platform", {})
    infrastructure_enabled = any(
        service_config.get(name, {}).get("enabled", False)
        for name in ("postgres", "redis", "object_storage")
    ) or any(
        platform_config.get(name, {}).get("enabled", False)
        for name in ("traefik", "dokploy")
    )
    if not infrastructure_enabled:
        raise AcceptanceFailure(
            "fresh Infrastructure Services certification requires an enabled service or platform component"
        )

    identity_base = playbook_command(inventory, config) + ["--tags", "identity_access"]
    run_command("TC-IDENTITY-012-FIRST", identity_base)
    run_command(
        "TC-IDENTITY-012-SECOND",
        identity_base,
        require_zero_changes=True,
    )
    runtime_base = playbook_command(inventory, config) + ["--tags", "runtime"]
    run_command("TC-RUNTIME-003", runtime_base)
    run_command("TC-RUNTIME-004", runtime_base, require_zero_changes=True)
    infrastructure_base = playbook_command(inventory, config) + [
        "--tags",
        "identity_access,security,runtime,networking,infrastructure_services",
    ]
    run_command("TC-INFRA-100-FIRST", infrastructure_base)
    run_command(
        "TC-INFRA-100-SECOND",
        infrastructure_base,
        require_zero_changes=True,
    )


def path_argument(value: str) -> Path:
    return Path(value).expanduser().resolve()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="tier", required=True)
    subparsers.add_parser("static", help="Run tests that never contact a VM")

    live = subparsers.add_parser("live", help="Run non-mutating tests on a VM")
    live.add_argument("--inventory", type=path_argument, required=True)
    live.add_argument("--config", type=path_argument, required=True)

    fresh = subparsers.add_parser(
        "fresh", help="Converge a disposable VM and verify idempotence"
    )
    fresh.add_argument("--inventory", type=path_argument, required=True)
    fresh.add_argument("--config", type=path_argument, required=True)
    fresh.add_argument("--confirm", required=True)
    return parser


def main() -> int:
    arguments = build_parser().parse_args()
    try:
        if arguments.tier == "static":
            run_static()
        elif arguments.tier == "live":
            run_live(arguments.inventory, arguments.config)
        else:
            run_fresh(arguments.inventory, arguments.config, arguments.confirm)
    except AcceptanceFailure as error:
        print(f"FAIL {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
