# Foundry OS / Base System role

This role turns a reasonably initialized Ubuntu VM into a known base-system
state. The only currently accepted managed-host tuple is Ubuntu 26.04 on
x86_64. See the repository's [supported-platform matrix](../../docs/supported-platforms.md)
for test status and promotion requirements.

## Safe default

```yaml
os_base_operation_mode: bootstrap
os_base_maintenance_approved: false
os_base_reboot_enabled: false
```

`bootstrap` refreshes APT metadata, installs the baseline, and validates the
host. It does not run `dist-upgrade`, autoremove/purge, or reboot.

## Security patching

```yaml
os_base_operation_mode: security_patching
os_base_apt_security_origins:
  - "origin=Ubuntu,codename=${distro_codename}-security,label=Ubuntu"
```

Foundry first records an `unattended-upgrade --dry-run` plan under
`/var/lib/foundry/os-base`, then applies only packages matching the approved
origins. This mode is independent of SSH password authentication and user sudo
policy.

## Full maintenance

```yaml
os_base_operation_mode: full_maintenance
os_base_maintenance_approved: true
os_base_maintenance_window: change-2026-08-14
os_base_maintenance_autoremove: false
os_base_maintenance_removals_approved: false
os_base_maintenance_autoclean: false
```

The mode, approval, and non-empty window identifier are all required. Foundry
captures the simulated APT plan before the distribution upgrade. Autoremove
with purge requires its own approval and produces a separate persisted plan
immediately before removal. Autoclean remains independently opt-in.

Foundry records only its own custom keyrings, `foundry-*.sources` files, and
package holds in `/var/lib/foundry/os-base/apt-ownership.yml`. Only entries in
that manifest may be reconciled as stale; existing external resources are
rejected rather than adopted. Proxy credentials must come from Ansible Vault
or an external secret source and are written without task output or diffs.
`needrestart` is report/defer only and never restarts arbitrary services.

## Controlled reboot

Reboot is detached from the normal role and can be invoked only as a final
rolling phase after the other implemented roles:

```yaml
os_base_reboot_enabled: true
os_base_reboot_approved: true
os_base_reboot_only_if_required: true
os_base_reboot_precheck_commands:
  - [/usr/local/bin/foundry-app-health, pre-reboot]
os_base_reboot_postcheck_commands:
  - [/usr/local/bin/foundry-app-health, post-reboot]
```

A `/var/run/reboot-required` marker never authorizes a reboot by itself. Keep
Security's unattended automatic reboot disabled so all reboots pass through
this final health-gated phase. If a reboot will run, at least one custom pre-
and post-workload gate is mandatory in addition to Foundry's package, APT-lock,
fstab, SSH, sudo, service, mount, time, capacity, swap, and failed-unit checks.

## Host identity and time

- `os_base_hostname` is the short hostname; `os_base_fqdn` is separate.
- Foundry can own the matching `/etc/hosts` entry and a cloud-init
  `preserve_hostname` drop-in.
- DNS and reverse-DNS validation are opt-in, query DNS directly with `dig`, and
  use explicit expected addresses. Reverse checks require expected addresses.
  DNS record creation belongs to the Networking layer.
- Foundry owns the configured Chrony sources by default, masks conflicting time
  providers, and validates source selection and maximum clock offset.
- Chrony options are sanitized and candidate/full configuration is validated
  before restart. The selected source must map to a declaration.
- Set `nts: true` only for Chrony sources that support NTS; `chronyc authdata`
  must prove authenticated NTS before validation succeeds.

## Locale, mounts, swap, and services

- Foundry persists `LANG`, never global `LC_ALL`. Optional individual `LC_*`
  values belong in `os_base_locale_categories`.
- Mounts declare source, target, filesystem type, options, persistence, and
  optional free-space/inode thresholds. Foundry does not format devices.
- `os_base_swap_policy` is `preserve`, `required`, or `disabled`. Required mode
  validates active and persistent swap. Disabled mode is validation-only, so
  Foundry never rewrites or disables unrelated swap it cannot prove it owns.
- Explicit service declarations use `presence: required|optional|forbidden`
  plus active, enabled, and masking policy. Optional absent units are accepted;
  static/alias unit semantics are normalized. Undeclared services are untouched.

## Common tags

| Tag | Purpose |
|---|---|
| `os_base` | Complete normal OS convergence |
| `os_validation` | Platform and policy validation |
| `os_bootstrap` | Safe APT/bootstrap configuration |
| `os_security_patching` | Security-only package workflow |
| `os_full_maintenance` | Approved broad maintenance workflow |
| `os_reboot` | Approved final controlled-reboot phase |

Selecting a tag never overrides configuration approval.
