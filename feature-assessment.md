# Foundry VM Feature and Production-Readiness Assessment

Date: 2026-08-14  
Scope: implemented roles `2_os_base_system`, `3_identity_access`, `4_security`,
`5_networking`, and the MinIO portion of `7_infrastructure_services`

## Executive verdict

The implemented roles provide a useful bootstrap baseline, but Foundry is **not yet production-ready**. The strongest existing parts are the modular role structure, early input validation, explicit identity/sudo policy, ownership-scoped UFW convergence, transactional SSH management, Fail2ban, unattended security updates, and end-of-role assertions.

The next milestone should certify access, SSH migration/rollback, Docker Runtime and networking, MinIO persistence, reboot recovery, and dependency reproducibility on disposable machines and CI. A robust VM also requires the remaining infrastructure-service, application, external-networking, and observability layers.

“Production-ready” in this document means that a fresh supported VM can be converged, safely re-run, rebooted, recovered, monitored, and restored without accidental loss of administrative access.

## Current implementation

| Layer | Implemented baseline | Current maturity |
|---|---|---|
| [2. OS / Base System](roles/2_os_base_system/tasks/main.yml) | OS checks, package maintenance, base packages, hostname, Chrony, locale, filesystems/directories, services, final validation | Functional bootstrap; maintenance and recovery controls incomplete |
| [3. Identity & Access](roles/3_identity_access/tasks/main.yml) | Input validation, Foundry-owned groups, local users/SSH keys, explicit sudo policy, state validation | V1 controls implemented; fresh-VM and recovery certification remain |
| [4. Security](roles/4_security/tasks/main.yml) | Owned UFW exposure, transactional SSH hardening/migration, host-key identity, Fail2ban, unattended upgrades, AppArmor, persistent journal, final validation | V1 controls implemented; disposable-VM failure, migration, and reboot certification remain |
| [6. Runtime](roles/6_runtime_platform/tasks/main.yml) | Official pinned Docker Engine/CLI/containerd/Buildx/Compose supply chain, owned validated daemon policy, bounded logging, socket/storage/service health, smoke test | Implemented and live-validated; fresh-VM, injected drift/rollback, and reboot certification pending |
| [5. Networking](roles/5_networking/tasks/main.yml) | Certified Runtime dependency plus deterministic per-environment bridge networks, label-scoped ownership, collision/stale safety, authoritative resolver, isolation validation | Implemented; Docker-host reboot/isolation certification pending |
| [7. Infrastructure services](roles/7_infrastructure_services/tasks/main.yml) | Internal environment-scoped MinIO S3 instances consuming role-5 networks | MinIO implemented; runtime, persistence, recovery, and idempotence certification pending |

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
| P0-08 | End-to-end platform | Docker Runtime, environment networking, and internal MinIO now have explicit contracts, but remaining infrastructure services, applications, external networking, backup, and observability are not implemented. Runtime fresh-VM/reboot/drift certification also remains open. | Implement the remaining layers and complete Runtime certification. “VM production-ready” cannot be declared until the actual workload is deployed, exposed only as intended, monitored, backed up, and exercised through an end-to-end health and restore test. |

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
| P1 | The former support declaration was broader than the end-to-end tested security behavior. | **Narrowed and expanded deliberately.** The role accepts Ubuntu 26.04 x86_64 and Debian 12 (Bookworm) x86_64. Ubuntu has live convergence evidence; Debian's distribution-specific APT, Docker, and security path is implemented but clean-cloud-image, reboot, and failure-injection certification remain pending. |
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

### Implemented controls and certification status

- Configuration and lockout risks are validated before package, firewall, or SSH mutation.
- A complete SSH baseline is managed through a validated drop-in. Port migration keeps both
  endpoints until a fresh authenticated and privileged connection succeeds, persists the
  validated controller endpoint, and then retires the old listener and owned firewall rule.
- SSH host keys are preserved and fingerprinted; unexpected replacement fails closed unless
  rotation is explicitly approved.
- Global `network.exposure` intent is expanded into stable, comment-owned UFW rules. Foundry
  removes only its own stale rules and validates default-deny policy, IPv4/IPv6 parity, and
  wildcard listeners.
- Fail2ban owns explicit timing, retry, backend, action, and trusted-source policy. The active
  controller source is automatically protected from accidental banning.
- Automatic security updates remain separate from broad OS maintenance; effective APT policy,
  timers, failures, and pending reboot state are validated without authorizing a reboot.
- AppArmor kernel/service/enforcement state and persistent journald storage are validated.
- Static policy tests and a converged-host idempotency run pass. The destructive port migration,
  rollback, reboot, and safe ban/unban scenarios remain **disposable-VM certification pending**.

### Missing or incomplete features

| Priority | Finding | Recommended feature and acceptance test |
|---|---|---|
| P0 | **Implemented in code; disposable-VM certification pending.** SSH migration, controller-side post-reload authentication/elevation, rollback, old-endpoint retirement, endpoint persistence, and owned firewall cleanup form one transaction. | Exercise `22 -> custom`, `custom -> custom`, `custom -> 22`, invalid-candidate rollback, authentication/elevation failure, interrupted runs, and reboot/reconnect on disposable VMs. Run every successful path twice before release. |
| P1 | Local UFW intent cannot prove provider-side firewall/security-group state. | Add a provider adapter in the compute/network layer and compare provider ingress with the same exposure manifest. Keep local validation fail-closed for undeclared wildcard listeners. |
| P1 | Security runs before runtime/services/apps, so all required exposure must be declared globally before convergence. | Keep `network.exposure` as the single contract, or later introduce a deliberate collect/apply two-pass design. Application roles must not directly bypass firewall ownership. |
| P1 | Automatic-update dry-run, fleet rollout, and failed-update alert delivery need environment certification. | Exercise the optional dry-run and failure paths on disposable VMs, then add maintenance windows/canaries and alert routing. Keep automatic reboot opt-in and health-gated. |
| P1 | Fail2ban safe ban/unban and recovery are implemented as documented procedures but not certified against a disposable remote source. | Test a ban from a non-management test address, verify management/controller exclusions, unban through the recovery path, and capture evidence without risking the bootstrap source. |
| P1 | Workload-specific AppArmor profiles are not yet part of the platform contract. | Let workload roles own tested profiles and fail production validation when a required workload profile is absent or not enforcing. |
| P1 | Persistent local journald is implemented, but audit rules, off-host forwarding, retention/integrity policy, and alerts remain absent. | Add audit requirements, authenticated off-host transport, retention, time-consistent event fields, and alerts for SSH bans, sudo failures, firewall changes, and update failures. Keep secrets out of logs. |
| P1 | There is no vulnerability scan, compliance report, or configuration drift signal independent of Ansible. | Add authenticated vulnerability scanning and a selected benchmark/profile. Record exceptions with owners and expiry dates; do not blindly enforce every CIS recommendation. |
| P1 | SSH host-key fingerprint inventory and explicit rotation approval are implemented, but encrypted backup and trusted out-of-band fingerprint distribution remain operational responsibilities. | Integrate encrypted backup and publish fingerprints through a trusted inventory/CMDB channel before production certification. Test approved and unapproved replacement paths. |
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


devrait pas avoir de prefix matching pour foundry
