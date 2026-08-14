# Foundry VM Feature and Production-Readiness Assessment

Date: 2026-08-14  
Scope: implemented roles `2_os_base_system`, `3_identity_access`, and `4_security`

## Executive verdict

The implemented roles provide a useful bootstrap baseline, but Foundry is **not yet production-ready**. The strongest existing parts are the modular role structure, early input validation, explicit SSH-key management, UFW defaults, SSH syntax checks, Fail2ban, unattended security updates, and end-of-role assertions.

The next milestone should focus on access safety, transactional SSH changes, firewall/SSH port migration, group ownership boundaries, reproducible dependencies, reboot recovery, and external validation. A robust VM also requires the currently unimplemented networking, runtime, infrastructure-service, application, and observability layers.

“Production-ready” in this document means that a fresh supported VM can be converged, safely re-run, rebooted, recovered, monitored, and restored without accidental loss of administrative access.

## Current implementation

| Layer | Implemented baseline | Current maturity |
|---|---|---|
| [2. OS / Base System](roles/2_os_base_system/tasks/main.yml) | OS checks, package maintenance, base packages, hostname, Chrony, locale, filesystems/directories, services, final validation | Functional bootstrap; maintenance and recovery controls incomplete |
| [3. Identity & Access](roles/3_identity_access/tasks/main.yml) | Input validation, local groups/users, SSH keys, admin group assignment, state validation | Good declarative start; privilege and ownership-boundary risks remain |
| [4. Security](roles/4_security/tasks/main.yml) | UFW, SSH hardening, transactional SSH-port migration, Fail2ban, unattended upgrades, preflight lockout checks, final validation | Useful host hardening; deployment and failure-injection verification remain |

## Priority definitions

- **P0 — release blocker:** can cause lockout, security loss, destructive drift, or unrecoverable failure.
- **P1 — required for a robust production VM:** needed for reliable operation, auditability, and repeatable maintenance.
- **P2 — environment or threat-model dependent:** valuable after the platform requirements are known.

## P0 release blockers

| ID | Affected area | Finding and risk | Required feature / completion evidence |
|---|---|---|---|
| P0-01 | Identity | **Implemented in code; deployment verification pending.** Admins now resolve to explicit `passwordless`, `password`, or `constrained` per-user sudoers policies. Managed users no longer gain elevation through implicit sudo-group membership. | Apply the role to a clean VM, prove each policy mode, run it twice for idempotence, and verify the independent recovery path before closing this release blocker. Password hashes must continue to come from Ansible Vault or an external secret store. |
| P0-02 | Identity | **Implemented in code; deployment verification pending.** Foundry now owns only the `foundry-*` namespace, adds desired memberships with `append: true`, removes stale Foundry memberships individually, and verifies that unrelated host groups remain unchanged. Default roles can also be replaced and custom Foundry roles declared. | Apply the migration to a test VM containing unrelated package/admin groups, prove those memberships remain unchanged, prove stale `foundry-*` memberships disappear, and run a second convergence before closing this blocker. |
| P0-03 | Security / inventory | **Implemented in code; migration testing pending.** Foundry treats `security.ssh.port` as desired state, discovers the current endpoint from controller runtime state with port 22 fallback, switches the live Ansible port, retires the old listener/rule, and persists only the successfully validated endpoint. | Exercise `22 -> custom`, `custom -> custom`, `custom -> 22`, and interrupted-run recovery on disposable VMs. Run each path twice to prove convergence before closing this blocker. |
| P0-04 | Security | **Implemented in code; failure-injection testing pending.** SSH policy changes now keep a known-good backup, validate the candidate and complete merged configuration, reload only validated changes, and restore/reload the previous policy through `block`/`rescue` on failure. | Inject invalid candidate and merged configurations, then prove the previous configuration remains usable after the failed run and after reboot. |
| P0-05 | Security | **Implemented in code; migration testing pending.** The controller checks the new SSH banner, resets Ansible's persistent connection, establishes a fresh authenticated transport, and executes a task before removing the old endpoint. | Prove success and authentication-failure rollback with the expected controller user/key. Add a reboot-and-reconnect test before closing this blocker. |
| P0-06 | Delivery | **Implemented in code; first CI execution pending.** Foundry now owns a Python 3.14.7 virtualenv, pins `ansible-core` and every Python dependency, installs exact project-local collection versions, verifies the resolved environment, and recreates the same controller in CI. | Run the new workflow successfully on the remote repository. Dependency updates must modify the input, lock, collection requirements, and immutable CI action references intentionally and together. |
| P0-07 | Recovery / operations | There is no backup policy, restore workflow, persistent/central log path, monitoring, or alerting. A correctly configured VM can still fail silently or be impossible to recover. | Implement role 9 with health, capacity, security-event, update/reboot, time-sync, and backup alerts. Define off-host backups and complete at least one timed restore test. |
| P0-08 | End-to-end platform | Roles 5–9 are placeholders. Network policy, runtime, infrastructure services, applications, and observability are not provisioned or validated. | Implement those layers with explicit contracts. “VM production-ready” cannot be declared until the actual workload is deployed, exposed only as intended, monitored, backed up, and exercised through an end-to-end health check. |

## Role 2 — OS / Base System

### What is already solid

- Tasks are split into small orchestration units and can be selected with tags.
- An exact distribution/version/architecture tuple is validated before mutation.
- Base packages, time synchronization, locale, directories, mounts, and services are declarative.
- The final task file checks package/service/filesystem state and reports whether a reboot is required.

### Implemented hardening and remaining evidence

| Priority | Finding | Current state and remaining acceptance evidence |
|---|---|---|
| P0 | Broad upgrade and package removal used to run during normal convergence. | **Implemented and live bootstrap-tested.** `bootstrap`, `security_patching`, and `full_maintenance` are separate modes. Maintenance requires approval plus a window; autoremove/purge has a second approval and separate simulated plan. Repeated bootstrap completed with `changed=0`; security and maintenance plans passed in check mode. Destructive maintenance still requires disposable-image execution evidence. |
| P1 | The former support declaration was broader than the end-to-end tested security behavior. | **Narrowed.** The role accepts only Ubuntu 26.04 x86_64 and the repository publishes a promotion matrix. The current VM passed convergence and idempotence; clean-cloud-image, reboot, and failure-injection certification remain pending, so the matrix labels this an implementation target rather than production-certified support. |
| P1 | Hostname, cloud-init, `/etc/hosts`, FQDN, and DNS ownership were ambiguous. | **Implemented in code; reboot/DNS integration evidence pending.** Short hostname and FQDN are separate, cloud-init preservation and the local hosts entry are explicit, and optional forward/reverse checks query DNS directly with declared expected addresses. DNS record creation remains a Networking responsibility. |
| P1 | Chrony did not own trusted sources, authentication policy, offset, or conflicting providers. | **Implemented; non-NTS live path verified.** Foundry validates a candidate before replacing sources, masks conflicting providers, proves the selected source is declared, and checks the system offset. `nts: true` additionally requires authenticated `chronyc authdata`; an NTS-enabled disposable-host test is still pending. |
| P1 | Global `LC_ALL` overrode application-specific locale behavior. | **Implemented and live-tested.** Foundry persists `LANG`, permits validated individual `LC_*` values, forbids global `LC_ALL`, generates locales, and validates `localectl` plus a fresh login session. |
| P1 | Mount validation did not prove source, type, options, persistence, capacity, inodes, or swap policy. | **Implemented in code; custom-mount reboot matrix pending.** `findmnt` and global fstab validation cover source/type/options/dump/passno, with forbidden options, space/inode thresholds, and explicit swap policies. Foundry never formats a disk; required swap is validation-only. |
| P1 | A reboot requirement was reported but not safely orchestrated. | **Implemented in code; reboot deliberately not executed on the active VM.** Reboot is an opt-in, separately approved, final rolling phase with package locks, dpkg, fstab, SSH/elevation, service/mount, workload, kernel, clock, capacity, swap, marker, and reconnect checks. Disposable-VM reboot/failure testing remains required. |
| P1 | Repository trust, holds, proxies, APT locks, and `needrestart` ownership were undefined. | **Implemented; custom-resource drift tests pending.** Checksum-pinned keyrings, signed-by repositories, protected proxy secrets, bounded lock retries, report-only `needrestart`, and a Foundry ownership manifest reconcile only Foundry-owned repositories/keyrings/holds. Pre-manifest adoption requires an explicit migration. |
| P1 | Service validation mishandled absent, disabled, masked, enabled, and active states. | **Implemented; fixture matrix pending.** Services use explicit `required`, `optional`, or `forbidden` presence with independent active/enabled/masked policy; optional absent and static/alias states are normalized, and undeclared services are untouched. Chrony passed live validation; synthetic state coverage remains to be added to CI. |
| P2 | No kernel/sysctl hardening profile is applied. | Add a conservative, versioned profile only after networking and runtime requirements are known. Avoid copying a generic benchmark that could break forwarding, containers, databases, or IPv6. |

## Role 3 — Identity & Access

### What is already solid

- User input, usernames, groups, duplicate users, key format, and protected accounts are validated early.
- Local groups and users are created declaratively with explicit state.
- `.ssh` and `authorized_keys` ownership and permissions are asserted.
- Administrative access is considered before security hardening runs.

### Missing or incomplete features

| Priority | Finding | Recommended feature and acceptance test |
|---|---|---|
| P0 | Explicit administrative elevation is implemented but has not yet completed fresh-VM and recovery-path testing. | Complete the deployment evidence described in P0-01. Ensure at least two independent recovery paths before disabling root/password access. |
| P0 | Supplementary group reconciliation can remove memberships outside Foundry ownership. | Implement the ownership boundary described in P0-02. Include a regression test with a package-managed group. |
| P1 | SSH key validation is lexical. A malformed key payload may pass, and duplicate keys with different comments may not be detected as the same credential. | Validate keys with `ssh-keygen`, compare fingerprints/key blobs rather than whole lines, and report fingerprints without exposing unnecessary key material. |
| P1 | Foundry owns the complete `authorized_keys` file. That is deterministic, but it can remove break-glass or external automation keys. | Make exclusivity explicit. Prefer a dedicated Foundry-managed authorized-keys file/directory when multiple authorities must coexist. Test preservation or intentional removal according to policy. |
| P1 | Writes under an existing user-controlled home are not preceded by explicit symlink/path-safety checks. | Assert the home, `.ssh`, and key file are not unexpected symlinks and have trusted ownership before writing. Refuse unsafe paths. |
| P1 | Home-directory mode and default umask are not part of the declared policy. | Set and validate a home mode such as `0750` or `0700`, define umask, and test that newly created files do not become world-readable. |
| P1 | `state: absent` preserves the home but lacks an offboarding workflow for sessions, scheduled jobs, owned files outside home, tokens, and later deletion. | Add phased states: active, suspended/locked, and removed. Inventory running processes, cron/systemd jobs, owned files, keys/tokens, and transfer ownership before destructive deletion. |
| P1 | Accounts and keys do not have expiry, rotation, provenance, or revocation metadata. | Add optional account expiry and key metadata; alert before expiry; support rapid revocation and periodic stale-account reports. |
| P1 | UID/GID allocation is not stable across hosts. | Allow explicit UID/GID or integrate a directory service before using shared storage or cross-host file ownership. Validate uniqueness. |
| P1 | `developer`, `operator`, `viewer`, and configured custom roles are labels until later roles bind them to concrete resources. | Define authorization contracts consumed by application/runtime/service roles. Test least-privilege access and negative cases for every group. |
| P2 | Local accounts do not scale well to a fleet. | Plan centralized identity (for example SSSD-backed identity) and short-lived SSH certificates when the number of hosts/users justifies it. Preserve an audited local break-glass path. |

## Role 4 — Security

### What is already solid

- Configuration and lockout risks are validated before package/firewall/SSH changes.
- UFW defaults to deny incoming traffic and allow outgoing traffic.
- SSH is managed through a drop-in and syntax validation is attempted before reload.
- Root/password login hardening, Fail2ban, and unattended security updates are configurable.
- The final phase checks effective SSH, firewall, Fail2ban, and update state.

### Missing or incomplete features

| Priority | Finding | Recommended feature and acceptance test |
|---|---|---|
| P0 | **Implemented in code; deployment verification pending.** SSH migration, controller-side post-reload authentication, rollback, old-endpoint retirement, and endpoint persistence now form one transaction. | Exercise failure injection, all supported migration directions, a second idempotence run, and reboot/reconnect before release. |
| P1 | SSH hardening does not yet define empty-password behavior, forwarding, session/channel limits, startup throttling, access allow-lists, or audit verbosity. | Add a documented profile with `PermitEmptyPasswords no`, deliberate forwarding policy, `MaxSessions`, `MaxStartups`, optional `AllowGroups`, and suitable logging. Keep crypto defaults unless a tested compliance profile requires overrides. |
| P1 | Automatically generated SSH firewall rules allow any source. | Support one or more management CIDRs and a documented emergency override. Test from allowed and denied networks before enforcing a restricted rule. |
| P1 | Firewall validation is mostly rule-oriented; it does not reconcile the complete listening-socket exposure, IPv4/IPv6 parity, cloud firewall/security groups, or unmanaged equivalent rules. | Build a single exposure manifest and compare it with `ufw status`, `ss -lntup`, IPv6 state, and provider-side controls. Fail if an unexpected public listener exists. |
| P1 | Stale-rule cleanup identifies rules by network fields, which can collide with equivalent rules not owned by Foundry. | Give generated rules stable ownership identifiers/comments or use a dedicated managed ruleset. Remove only owned rules and test coexistence with an external rule. |
| P1 | Security runs before runtime/services/apps, so later roles cannot safely “discover then open” their required ports in the same one-pass order. | Declare the complete exposure manifest in global configuration before the security role, or use a deliberate collect/apply two-pass design. Application roles must not directly bypass firewall ownership. |
| P1 | Unattended-upgrades files are validated, but effective `apt-daily` timer scheduling, allowed origins, dry-run behavior, reboot notification, and fleet rollout are not fully proven. | Validate timers and effective policy, run a dry-run test, define maintenance windows/canaries, and alert on failure or pending reboot. Keep automatic reboot opt-in and health-gated. |
| P1 | Fail2ban lacks an explicit observation window, trusted-source exclusions, action policy, and operational visibility. | Manage `findtime`, `ignoreip`, backend/action, log source, and alerts. Test a ban from a safe test source and confirm a recovery mechanism. |
| P1 | AppArmor is not asserted as loaded/enforcing, and service-specific profiles are not part of the platform contract. | Verify AppArmor status in the security layer. Let workload roles own tested profiles and fail production validation when a required profile is not enforcing. |
| P1 | Security event auditing, persistent logs, forwarding, retention, integrity, and alerting are absent. | Add audit requirements, persistent journald/rsyslog policy, off-host transport, retention, time-consistent event fields, and alerts for SSH bans, sudo failures, firewall changes, and update failures. Keep secrets out of logs. |
| P1 | There is no vulnerability scan, compliance report, or configuration drift signal independent of Ansible. | Add authenticated vulnerability scanning and a selected benchmark/profile. Record exceptions with owners and expiry dates; do not blindly enforce every CIS recommendation. |
| P1 | SSH host-key lifecycle is not managed or reported. | Preserve/backup host keys securely, report fingerprints through a trusted channel, define rotation/reprovisioning behavior, and detect unexpected changes. |
| P2 | Host egress is broadly allowed. | If the threat model requires it, introduce DNS/NTP/repository/proxy-aware egress policy after all service dependencies are mapped. |
| P2 | Advanced controls such as Livepatch, Secure Boot/TPM attestation, file-integrity monitoring, or endpoint detection are not represented. | Add only where infrastructure and risk requirements justify them, with monitoring and recovery procedures. |

## Cross-role architecture gaps

### Configuration and secrets

- Add a versioned schema for `config.yml` with unknown-key rejection, types, ranges, and mutually exclusive options.
- Keep public SSH keys in configuration if desired—they are not secrets—but encrypt future passwords, API keys, private keys, tokens, and recovery material.
- Separate environment data from reusable defaults, and clearly document which role owns every setting.
- Protect secret-bearing tasks with `no_log` and review Ansible diff output before enabling it in CI.

### Orchestration safety

- Define task-tag dependencies. Running a narrow tag such as firewall, Fail2ban, or validation must either include all required facts/prerequisites or fail with a clear message.
- Use `serial`/rolling deployment and canaries once multiple hosts exist.
- Add pre-change and post-change health gates for package updates, reboots, SSH, firewall, runtime, and applications.
- Establish `block`/`rescue` rollback for access-sensitive operations. A successful Ansible task is not sufficient evidence of service availability.

### Reproducibility and quality

- **Implemented:** pinned controller Python, `ansible-core`, transitive Python packages, and all required collections, with a project-local virtualenv and CI verification.
- Add `ansible-lint`, `yamllint`, syntax checks, and secret scanning.
- Test on clean supported images with Molecule or ephemeral VMs.
- Run every convergence twice and require the second run to report `changed=0` unless a task is intentionally non-idempotent.
- Add drift-repair, negative configuration, check-mode, reboot, rollback, and upgrade tests.

### Backup and disaster recovery

- Define what is backed up, frequency, retention, encryption, off-host location, ownership, and recovery-time/recovery-point objectives.
- Back up workload data and irreplaceable identity/host material; do not treat the VM image or Git repository as a complete backup.
- Automate restore verification. A backup is not considered valid until restoration has succeeded in an isolated environment.

## Required production release gates

A VM should not be called production-ready until all applicable checks below pass:

- [ ] Fresh supported image converges successfully.
- [ ] Second identical run reports no unintended changes.
- [ ] Check mode and diff mode complete without leaking secrets.
- [ ] Invalid user, key, firewall, and SSH configurations fail before mutation.
- [ ] A new managed administrator can log in and elevate privileges.
- [ ] A second independent administrative/recovery path is proven.
- [ ] SSH port migration is externally validated and automatically rolls back on failure.
- [ ] Effective firewall rules and listening sockets match one approved exposure manifest for IPv4 and IPv6.
- [ ] The VM reboots, reconnects, and passes all service/application health checks.
- [ ] Package update, pending-reboot, time-sync, disk, memory, SSH-ban, firewall, and service failures produce actionable alerts.
- [ ] Off-host backup succeeds and a timed isolated restore is demonstrated.
- [ ] Every declared OS/version/architecture passes the same matrix, or unsupported combinations are rejected.
- [ ] Roles 5–9 deploy and validate the complete workload rather than only the base host.

## Recommended delivery sequence

1. **Access-safety milestone:** fix sudo authentication, group ownership, SSH staging/rollback, and two-phase port migration.
2. **Reproducibility milestone:** pin dependencies; add schema validation, linting, clean-image convergence, idempotence, and negative tests.
3. **Recovery milestone:** implement controlled reboot/reconnect, backups/restores, persistent logs, monitoring, and alerts.
4. **Workload milestone:** implement networking, runtime, infrastructure services, applications, and one shared exposure manifest.
5. **Assurance milestone:** add vulnerability/compliance evidence, platform matrix testing, canary/rolling updates, and threat-model-dependent controls.

## Authoritative references

- [Ubuntu OpenSSH server guidance](https://documentation.ubuntu.com/server/how-to/security/openssh-server/)
- [Ubuntu firewall guidance](https://documentation.ubuntu.com/server/how-to/security/firewalls/)
- [Ubuntu automatic updates](https://documentation.ubuntu.com/server/how-to/software/automatic-updates/)
- [Ubuntu AppArmor guidance](https://documentation.ubuntu.com/server/how-to/security/apparmor/index.html)
- [Ubuntu time synchronization overview](https://documentation.ubuntu.com/server/explanation/networking/about-time-synchronisation/)
- [Ubuntu Chrony client configuration](https://documentation.ubuntu.com/server/how-to/networking/chrony-client/)
- [Ubuntu backups guidance](https://documentation.ubuntu.com/server/how-to/backups/)
- [Ansible `user` module — supplementary group behavior](https://docs.ansible.com/projects/ansible/latest/collections/ansible/builtin/user_module.html)
- [Ansible `authorized_key` module](https://docs.ansible.com/projects/ansible/latest/collections/ansible/posix/authorized_key_module.html)
- [Ansible check and diff modes](https://docs.ansible.com/projects/ansible-core/devel/playbook_guide/playbooks_checkmode.html)
- [Ansible Vault](https://docs.ansible.com/projects/ansible/latest/vault_guide/vault.html)
- [Ansible collection requirements files](https://docs.ansible.com/projects/ansible/latest/galaxy/user_guide.html)
- [OpenBSD `sshd_config` reference](https://man.openbsd.org/sshd_config)

## Assessment maintenance

Review this file whenever a role gains a feature, a supported operating-system version changes, or an exposure/access policy changes. Close an item only when its automated acceptance test exists and passes—not only when configuration has been added.
