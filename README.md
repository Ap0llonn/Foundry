# Foundry

Foundry provisions a VM through ordered Ansible layers. Every operator should
run it from the project-owned Python environment so workstation-global Ansible
packages and collections cannot change provisioning behavior.

## Supported controller

- CPython `3.14.7`
- `ansible-core 2.21.3`
- Collection versions declared in `collections/requirements.yml`
- Python package versions declared in `requirements-controller.lock`

The managed Linux VM must expose a Python version supported by ansible-core
2.21. Foundry currently supports target Python `3.9` through `3.14`. Managed
host support is narrower and is published in the
[supported-platform matrix](docs/supported-platforms.md); a distribution is not
considered supported until the complete implemented provisioning path has been
tested on it.

## First-time setup

Install the Python version from `.python-version`, then run:

```bash
make bootstrap
source .venv/bin/activate
```

If the required interpreter is not named `python3`, select it explicitly:

```bash
make bootstrap PYTHON_BIN=/path/to/python3.14
```

The bootstrap creates `.venv`, installs every Python dependency at its locked
version, installs collections under `collections/ansible_collections`, and runs
the controller verification. Generated dependencies remain local and are
ignored by Git.

If bootstrap reports that Python has broken native libraries, repair the
interpreter before retrying. For a Homebrew-managed controller, the usual repair
is:

```bash
brew reinstall python@3.14
```

Foundry intentionally refuses to build an environment from an incomplete Python
installation.

## Running Foundry

After activating the environment:

```bash
ansible-playbook playbook.yml
```

`ansible.cfg` automatically selects `inventory.yml`, `roles/`, and the local
collection directory. To validate without connecting to or modifying a VM:

```bash
make check
```

The central [acceptance-test suite](tests/README.md) adds negative configuration
fixtures, read-only VM stability checks, and explicitly gated disposable-VM
convergence tests:

```bash
make test-static
make test-live
```

The acceptance suite fails when a V1 requirement is not implemented; an
unexpectedly accepted negative fixture is never treated as a pass.

## Runtime, networking, and infrastructure services

`project.name` plus `environments` resolves deterministic Docker networks such
as `foundry-my-project-dev`. They are bridges normally and attachable overlays
when Dokploy's single-manager Swarm is enabled. Role 5 owns only networks carrying
the complete Foundry label set, preserves external networks, and refuses to
remove an attached stale network. See the
[networking guide](roles/5_networking/Doc.MD).

Role 7 consumes those networks to provide private per-environment PostgreSQL,
Redis, and MinIO, plus one Traefik ingress and Dokploy platform. The global
config supports `dev-api.example.com`, `dev.api.example.com`, or domainless
operation. Stateful data ports are private by default and enabling Dokploy
requires a management CIDR allowlist. See the
[Infrastructure Services guide](roles/7_infrastructure_services/Doc.MD).

Role 6 installs Docker from its official repository, pins and validates the
runtime, and executes before role 5. When Dokploy is requested, Runtime also
owns the narrowly scoped single-manager Swarm; it never adopts or force-leaves
an external cluster. Infrastructure Services consumes both contracts and never
installs Docker.

## OS lifecycle modes

The OS role has three explicit modes configured in `config.yml`:

- `bootstrap` installs and validates the baseline. It never performs a broad
  upgrade, package autoremove/purge, or reboot.
- `security_patching` applies packages only from the configured security
  origins and records the simulated plan first.
- `full_maintenance` performs a distribution upgrade only when
  `os_base_maintenance_approved` is true and
  `os_base_maintenance_window` identifies the approved window. Autoremove and
  autoclean have separate switches, and autoremove/purge additionally requires
  `os_base_maintenance_removals_approved`.

Tags select work; they neither select the lifecycle mode nor authorize it. Set
`os_base_operation_mode` in `config.yml` first. Maintenance still fails closed
unless its independent configuration approval is present:

```bash
ansible-playbook playbook.yml --tags os_base
ansible-playbook playbook.yml --tags os_security_patching
ansible-playbook playbook.yml --tags os_full_maintenance
```

An OS-required reboot is reported by default. If reboot is explicitly enabled
and approved, Foundry evaluates it only in the final, rolling playbook phase
after Identity and Security have converged. See the
[OS role guide](roles/2_os_base_system/Doc.MD) for policy examples and safety
requirements.

## Updating dependencies

Dependency changes must be intentional and reviewed together:

1. Update direct Python requirements in `requirements-controller.in`.
2. Resolve and pin every transitive package in `requirements-controller.lock`.
3. Update exact collection versions in `collections/requirements.yml`, including
   collection dependencies.
4. Recreate `.venv` and `collections/ansible_collections` from scratch.
5. Run `make check` and let the CI workflow validate the same clean setup.

Do not install the full `ansible` package for Foundry. The repository uses the
minimal pinned `ansible-core` controller plus only the collections referenced by
the implemented roles.
