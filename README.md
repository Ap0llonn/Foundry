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
2.21. Foundry currently supports target Python `3.9` through `3.14` and tests
the Ubuntu/Debian path implemented by the existing roles.

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
