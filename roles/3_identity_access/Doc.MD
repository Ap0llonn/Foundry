# Foundry Identity & Access Guide

This role manages local human users, Foundry authorization groups, SSH public keys, and explicit sudo policies.

The global configuration is defined in the root [`config.yml`](../../config.yml):

```yaml
identity:
  groups: []

  default_admin_sudo:
    mode: passwordless

  users:
    - name: alice
      state: present
      admin: true
      groups:
        - developer
      ssh_keys:
        - "ssh-ed25519 AAAA... alice@example"
      sudo:
        mode: inherit
```

## User properties

| Property | Required | Default | Description |
|---|---:|---|---|
| `name` | Yes | — | Linux username. It must be unique and use a supported lowercase Linux username format. |
| `state` | No | `present` | Either `present` or `absent`. |
| `admin` | No | `false` | Whether the user is authorized to receive an explicit sudo policy. |
| `groups` | No | `[]` | Foundry authorization groups assigned to the user. |
| `ssh_keys` | No | `[]` | Complete SSH public keys installed in the user's `authorized_keys` file. |
| `sudo` | For admins unless a default exists | — | Explicit privilege-elevation policy. |

## Foundry authorization groups

Configuration group names are translated to Linux groups:

| Configuration value | Linux group |
|---|---|
| `developer` | `foundry-developer` |
| `operator` | `foundry-operator` |
| `viewer` | `foundry-viewer` |

Example:

```yaml
groups:
  - developer
  - viewer
```

### Rename or add Foundry groups

Use `identity.groups` to replace a built-in logical role or add a new one:

```yaml
identity:
  groups:
    - name: team1
      replaces: developers

    - name: devteam
      replaces: operators

    - name: database-team
```

`replaces` accepts the singular or plural built-in names: `developer(s)`, `operator(s)`, and `viewer(s)`.

After this configuration, users may request `team1`, `devteam`, `database-team`, or the unreplaced `viewer` role:

```yaml
users:
  - name: alice
    groups:
      - team1
      - database-team
```

The resulting Linux groups are `foundry-team1`, `foundry-devteam`, `foundry-database-team`, and `foundry-viewer`. A replaced logical name is no longer valid in `identity.users[].groups`.

### Group ownership boundary

Foundry owns only Linux groups whose names begin with `foundry-`:

- Desired Foundry memberships are added.
- Stale Foundry memberships are removed.
- Obsolete `foundry-*` groups are removed after their memberships are reconciled.
- Every unrelated host membership is preserved, including groups created by packages, applications, or administrators.

The role does not use a whole-account `append: false` replacement. It adds desired Foundry groups with `append: true` and removes stale memberships individually only from the owned namespace.

Do not manually create groups beginning with `foundry-`; that namespace belongs to this role. Do not place privileged system groups such as `sudo`, `root`, `docker`, or `lxd` in `identity.users[].groups`. Administrative access must use `admin: true` and an explicit sudo policy. If an unrelated privileged membership already exists, Foundry preserves it but fails final validation so an administrator can resolve the conflict explicitly.

### Migrating from the previous sudo-group behavior

Earlier versions of this role added admins to the system `sudo` group. The new ownership boundary deliberately does not remove that unrelated group automatically.

On the first migration run, Foundry installs and validates the user's explicit `/etc/sudoers.d/foundry-<username>` policy, preserves the old `sudo` membership, and reports the conflict during final validation. After confirming the new per-user policy works, remove the legacy membership explicitly:

```bash
sudo gpasswd -d alice sudo
```

Then run the identity role again. Do not remove the old membership until the new sudoers file has passed `visudo` and the user's configured elevation path has been tested.

## SSH public keys

Users generate their SSH key pair on their own machine and provide only the public key to the system administrator.

Example key generation:

```bash
ssh-keygen -t ed25519 -C "alice@example"
```

The administrator copies the complete public-key line into `ssh_keys`:

```yaml
ssh_keys:
  - "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAA... alice@example"
```

Never copy a private key into Foundry. Public keys are installed in:

```text
/home/<user>/.ssh/authorized_keys
```

Foundry owns the complete managed `authorized_keys` content. Removing a key from `config.yml` removes it from the VM on the next run.

## Sudo modes

SSH authentication and sudo authentication are separate:

- An SSH public key proves that the user may open an SSH session.
- An SSH private-key passphrase protects the private key on the user's machine.
- A Linux account password may be used by sudo.
- Enabling a Linux password for sudo does not enable SSH password login.

### `inherit`

Uses the policy under `identity.default_admin_sudo`:

```yaml
identity:
  default_admin_sudo:
    mode: passwordless

  users:
    - name: alice
      admin: true
      sudo:
        mode: inherit
```

If an admin uses `inherit`, a valid global default must exist. Foundry never silently chooses a sudo mode.

### `passwordless`

Grants unrestricted sudo without requesting the Linux account password:

```yaml
sudo:
  mode: passwordless
```

Generated policy:

```text
alice ALL=(ALL:ALL) NOPASSWD: ALL
```

This is convenient for automation and bootstrap administration, but it grants full root-level access to anyone who controls the account's SSH credentials.

### `password`

Grants unrestricted sudo and requires the user's Linux account password:

```yaml
sudo:
  mode: password
  password_hash: "{{ vault_alice_password_hash }}"
```

Generated policy:

```text
alice ALL=(ALL:ALL) PASSWD: ALL
```

`password_hash` must contain a supported Linux password hash, never a plaintext password. Keep the value in Ansible Vault or retrieve it from an external secret source.

### `constrained`

Grants access only to explicitly listed commands. The policy must also declare whether those commands require the Linux account password.

Passwordless constrained example:

```yaml
sudo:
  mode: constrained
  authentication: passwordless
  commands:
    - /usr/bin/systemctl status foundry.service
    - /usr/bin/systemctl restart foundry.service
```

Password-authenticated constrained example:

```yaml
sudo:
  mode: constrained
  authentication: password
  password_hash: "{{ vault_operator_password_hash }}"
  commands:
    - /usr/bin/systemctl restart foundry.service
```

Commands must be absolute command specifications. Commas, backslashes, and line breaks are rejected because they could change sudoers syntax.

Be careful when granting commands that can execute shells, edit arbitrary files, load plugins, or run user-controlled scripts. A constrained rule can still become equivalent to unrestricted root access if the allowed command is too powerful.

### `none`

Creates no Foundry sudo policy:

```yaml
- name: charlie
  admin: false
  groups:
    - viewer
  ssh_keys:
    - "ssh-ed25519 AAAA... charlie@example"
  sudo:
    mode: none
```

For `admin: false`, `sudo` may be omitted entirely. If it is declared, its only valid setting is `mode: none`.

For `admin: true`, `none` is invalid because `admin: true` means the user must have a usable elevation policy.

## Global default policy

A global default reduces repeated configuration:

```yaml
identity:
  default_admin_sudo:
    mode: passwordless
```

The global default supports `passwordless`, `password`, and `constrained`. It cannot use `inherit` or `none`.

For a global `password` default, every inheriting user must provide their own password hash:

```yaml
identity:
  default_admin_sudo:
    mode: password

  users:
    - name: alice
      admin: true
      sudo:
        mode: inherit
        password_hash: "{{ vault_alice_password_hash }}"
```

A global constrained policy must include its authentication method and commands:

```yaml
identity:
  default_admin_sudo:
    mode: constrained
    authentication: passwordless
    commands:
      - /usr/bin/systemctl status foundry.service
```

## Using Ansible Vault

One option is to store secret variables in an encrypted Vault file:

```yaml
# vault.yml — encrypt this file with ansible-vault
vault_alice_password_hash: "$y$..."
```

Reference the variable without placing the hash directly in the public configuration:

```yaml
sudo:
  mode: password
  password_hash: "{{ vault_alice_password_hash }}"
```

Run the playbook while loading the encrypted variables:

```bash
ansible-playbook \
  -i inventory.yml \
  playbook.yml \
  -e @config.yml \
  -e @vault.yml \
  --ask-vault-pass
```

Do not store plaintext account passwords in `config.yml`, Git, terminal history, or playbook output. The identity role suppresses password-hash task output with `no_log`.

## Removing a user

An absent user entry may contain only `name` and `state`:

```yaml
identity:
  users:
    - name: alice
      state: absent
```

The Linux account and Foundry-managed sudoers file are removed. The current role preserves the user's home directory and data.

## Managed sudoers files

Foundry does not edit `/etc/sudoers` directly. It manages one file per administrator:

```text
/etc/sudoers.d/foundry-<username>
```

Each file is owned by `root:root`, uses mode `0440`, and is validated with `visudo -cf` before installation. Obsolete Foundry-managed files are removed when a user becomes non-administrative, is removed, or changes policy.

If an unmanaged sudo rule still grants access to a non-admin, final validation fails instead of deleting an unknown administrator-owned file.

## Running the role

Run the complete identity layer:

```bash
ansible-playbook -i inventory.yml playbook.yml -e @config.yml --tags identity_access
```

Useful narrower tags:

| Tag | Purpose |
|---|---|
| `identity_validation` | Validate and resolve identity configuration without provisioning users. |
| `identity_groups` | Manage Foundry and private user groups. |
| `identity_users` | Create, update, or remove Linux users and required password hashes. |
| `identity_ssh` | Reconcile SSH directories and public keys. |
| `identity_privileges` | Reconcile sudoers policies and group memberships. |
| `identity_result` | Validate the resulting account, SSH, group, and sudo state. |

Configuration validation automatically runs with every identity subtag because later steps depend on the resolved policy.

## Validation and idempotence

Before applying changes, run:

```bash
ansible-playbook --syntax-check -i inventory.yml playbook.yml -e @config.yml

ansible-playbook \
  -i inventory.yml \
  playbook.yml \
  -e @config.yml \
  --check \
  --diff \
  --tags identity_validation,identity_groups,identity_users,identity_ssh,identity_privileges
```

The first check-mode run intentionally excludes `identity_result`, because final-state assertions inspect the current VM and cannot validate files that check mode only predicts. After the role has been applied once, `identity_result` can be run normally.

After provisioning, run the role a second time:

```bash
ansible-playbook -i inventory.yml playbook.yml -e @config.yml --tags identity_access
```

The second run should report no unnecessary changes.

Final validation checks include:

- Linux account presence, home, and shell.
- Exact managed group membership.
- SSH key content, ownership, and permissions.
- Sudoers file content, ownership, mode, and complete `visudo` syntax.
- Effective sudo authorization for admins and denial for non-admins.
- `sudo -n true` for unrestricted passwordless admins.
- Valid Linux password state for password-authenticated policies.

## Complete examples

```yaml
identity:
  default_admin_sudo:
    mode: passwordless

  users:
    - name: alice
      state: present
      admin: true
      groups:
        - developer
      ssh_keys:
        - "ssh-ed25519 AAAA... alice@example"
      sudo:
        mode: inherit

    - name: bob
      state: present
      admin: true
      groups:
        - operator
      ssh_keys:
        - "ssh-ed25519 BBBB... bob@example"
      sudo:
        mode: password
        password_hash: "{{ vault_bob_password_hash }}"

    - name: deployer
      state: present
      admin: true
      groups:
        - operator
      ssh_keys:
        - "ssh-ed25519 CCCC... deployer@example"
      sudo:
        mode: constrained
        authentication: passwordless
        commands:
          - /usr/bin/systemctl restart foundry.service
          - /usr/bin/systemctl status foundry.service

    - name: charlie
      state: present
      admin: false
      groups:
        - viewer
      ssh_keys:
        - "ssh-ed25519 DDDD... charlie@example"
```

The SSH public keys above are shortened examples and are not valid real keys.
