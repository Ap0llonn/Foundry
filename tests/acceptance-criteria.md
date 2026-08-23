# Foundry V1 acceptance criteria

These criteria define what “solid” means for an implemented Foundry role. A
feature is accepted only when its implementation, negative behavior, resulting
host state, and idempotence are all tested.

## Global safety and stability

### AC-GLOBAL-001 — Reproducible controller

Given a clean controller using the pinned Python environment, when the
controller verification runs, then the exact Python, ansible-core, Python
packages, and Ansible collections must match the repository locks.

### AC-GLOBAL-002 — Parse every executed task path

All main playbooks and dynamically selected helper task files must pass syntax
validation. A helper that is not parsed by the normal syntax path requires a
dedicated syntax playbook.

### AC-GLOBAL-003 — Safe test tiers

The default static tier must not contact a VM. The live tier must not mutate a
VM. A mutating test must require an explicit disposable-VM confirmation and
must refuse the production/default inventory.

### AC-GLOBAL-004 — Secret-safe output

Tests and failure messages must not expose private keys, plaintext passwords,
password hashes, Vault values, tokens, or complete secret-bearing structures.
SSH fingerprints may be reported; private key material may not.

### AC-GLOBAL-005 — Idempotent convergence

After a successful first convergence, a second convergence with identical
inputs must finish successfully with `changed=0`. Validation-only runs must
also report `changed=0`.

## Identity and access V1

### AC-IDENTITY-001 — Explicit administrative elevation

Every `admin: true` user must resolve to one explicit sudo mode. Generated rules
must live under `/etc/sudoers.d`, be `root:root` mode `0440`, pass `visudo`, and
match the declared commands and authentication policy. Non-admins must have no
Foundry sudoers file and no effective unmanaged sudo grant.

Acceptance coverage must include `passwordless`, `password`, constrained
passwordless, constrained password-authenticated, `inherit`, and `none`.

### AC-IDENTITY-002 — Fresh VM and recovery safety

Before root login or SSH password authentication is disabled, at least two
independent tested access paths must exist. One path must be the active
provisioning identity or an explicitly declared break-glass identity. A fresh
VM test must open a new SSH connection through each path and prove usable
elevation where required. A failed transition must preserve a working recovery
path.

### AC-IDENTITY-003 — Foundry-only group ownership

Foundry may add or remove memberships only for groups in its owned namespace.
Package-managed, application-managed, and administrator-managed groups must be
equivalent before and after reconciliation. Stale Foundry-owned memberships and
obsolete Foundry-owned groups must be removed.

### AC-IDENTITY-004 — Cryptographic SSH public-key validation

Every configured public key must be parsed successfully by `ssh-keygen` before
any account or SSH file mutation. Duplicate credentials must be detected by
canonical key blob or fingerprint, ignoring comments and harmless whitespace.
Failure output may identify the user and fingerprint but must not print
unnecessary key material.

### AC-IDENTITY-005 — Explicit authorized-keys ownership

The configuration must explicitly select the authority model for SSH keys. In
exclusive mode, Foundry may replace only the declared managed file and must
clearly reject or deliberately remove pre-existing external keys according to
policy. In coexistence mode, Foundry must use a dedicated file/directory and
preserve external and break-glass keys. Both modes require regression tests.

### AC-IDENTITY-006 — Path and symlink safety

Before writing, Foundry must prove that the home path is the expected directory
with trusted ownership, `.ssh` is an actual directory, and the managed key file
is absent or a regular file. Unexpected symlinks, devices, FIFOs, sockets,
hard-link anomalies, or ownership must fail before mutation.

### AC-IDENTITY-007 — Home permissions and umask

The home-directory mode and login umask must be declared, applied, and validated.
New files created by a fresh login must not be world-readable or writable. The
selected policy must remain stable after a second convergence.

### AC-IDENTITY-008 — Identity idempotence and drift repair

The identity role must converge with `changed=0` on its second run. Controlled
drift in owned sudoers files, owned group memberships, SSH modes, home modes,
and managed key content must be repaired. Unowned state must be preserved.

## OS/base-system regression floor

### AC-OS-001 — Safe bootstrap default

The default OS mode must not perform a distribution upgrade, autoremove/purge,
or reboot. Broad maintenance and reboot paths must fail closed without their
independent approvals.

### AC-OS-002 — Baseline idempotence

On every supported platform in the published matrix, bootstrap must pass a
second convergence with `changed=0`, and all final host, package, time, locale,
filesystem, service, and reboot-required validations must succeed.

## Security V1

### AC-SECURITY-001 — Complete SSH baseline and transactional migration

The effective SSH configuration must match every declared V1 directive. Port
migration must authenticate and elevate through a new connection before the old
listener or firewall endpoint is retired, and rollback must preserve access.

### AC-SECURITY-002 — Owned default-deny firewall exposure

UFW must enforce default-deny inbound. Only `network.exposure` produces
Foundry-owned rules, every owned rule has a stable comment, stale owned rules
are removed, and equivalent external rules are preserved.

### AC-SECURITY-003 — Effective exposure validation

Declared exposure must be compared with UFW, wildcard listeners, and IPv4/IPv6
state. Unexpected listeners must fail or emit an explicit warning according to
the configured policy.

### AC-SECURITY-004 — Fail2ban protection and recovery

The SSH jail must enforce the declared retry window, ban duration, backend,
action, and trusted sources. Controlled testing must prove ban and unban without
risking the active controller.

### AC-SECURITY-005 — Security-update health

Effective unattended-upgrades settings, approved origins, timers, dry-run,
failure visibility, and pending-reboot detection must match policy. Automatic
reboot remains prohibited in this slice.

### AC-SECURITY-006 — AppArmor capability

AppArmor packages, kernel capability, service, loaded policy, and enforcing
profiles must be healthy without creating generic workload profiles.

### AC-SECURITY-007 — Persistent journal

Journald must use persistent storage with trusted permissions and retain
security-service records across a real reboot.

### AC-SECURITY-008 — SSH host-key preservation

Ordinary convergence must not regenerate host keys. Existing public
fingerprints must match the approved inventory, and replacement requires
explicit approval.

### AC-SECURITY-009 — Security drift and idempotence

A second convergence must report `changed=0`; owned drift must be repaired and
unowned firewall/configuration state must remain unchanged.

## Networking V1

### AC-NETWORKING-001 — Deterministic environment network resolution

Every unique declared environment must resolve exactly once to either its
explicit valid network name or `foundry-<project>-<environment>`. Duplicate
environment names, reserved names, and resolved-name collisions must fail before
Docker access or mutation.

### AC-NETWORKING-002 — Label-scoped ownership and safe reconciliation

Foundry may create, validate, report, or remove only networks with matching
managed/project/environment/resource labels. Same-name external networks must
cause safe collision failure. Stale attached networks must never be force
removed or have workloads disconnected.

### AC-NETWORKING-003 — Environment isolation and persistence

Each environment network must be distinct and non-internal. Ordinary hosts use
a bridge; enabling the Dokploy platform requires a Swarm-scoped attachable
overlay so standalone infrastructure containers and future Dokploy services can
consume the same authoritative environment mapping. A same-name bridge is never
silently replaced by an overlay.
Foundry-labeled workloads must not cross environment boundaries. Networks must
survive Docker restart and host reboot and converge a second time with
`changed=0`.

### AC-NETWORKING-004 — Certified Runtime dependency

Role 5 must require role 6's root-owned Runtime manifest, active and enabled
Docker service, operational CLI, and Compose plugin before network mutation. It
must not install Docker packages, configure the daemon, or own Docker services.

## Runtime V1

### AC-RUNTIME-001 — Trusted deterministic Docker supply chain

On Ubuntu 26.04 x86_64 and Debian 12 (Bookworm) x86_64, Runtime must use
Docker's official HTTPS repository, a checksum-pinned signing key, signed-by
repository configuration, exact platform-specific package versions, and
package holds. Unsupported platforms and unowned existing Docker installations
must fail before mutation.

### AC-RUNTIME-002 — Safe owned daemon configuration

Foundry must own the complete daemon configuration or refuse it. A candidate
must validate before apply; running workloads require approved maintenance;
activation failure must restore the previous recoverable state. Effective logs
must be bounded and a no-drift run must not restart Docker.

### AC-RUNTIME-003 — Complete runtime health and privilege boundary

Docker and containerd must be active/enabled, CLI/API/Compose operational,
storage driver and capacity healthy, and the Unix socket root:docker `0660`.
Docker group membership and every TCP API listener must fail closed.

### AC-RUNTIME-004 — Execution, cleanup, reboot, and idempotence

A digest-pinned disposable container must execute and leave no container,
network, or volume behind. Service/config drift must repair without deleting
external resources. After a controlled reboot the full health contract must
pass, and second convergence must report `changed=0`.

## MinIO S3 V1

### AC-MINIO-001 — Internal environment-scoped S3 service

Every declared MinIO instance must consume role 5's authoritative network for
its environment, use persistent data, carry exact ownership labels, expose the
S3 health endpoint internally, and publish no host ports.

### AC-MINIO-002 — Secret, collision, and lifecycle safety

Credentials must be supplied from secret-capable variables and suppressed from
task output. External same-name containers and incompatible owned state must not
be adopted or destructively recreated. Stale MinIO instances and data are
reported but never automatically deleted.

## Infrastructure Services V1

### AC-INFRA-001 — Explicit orchestration and private data services

PostgreSQL, Redis, and MinIO must consume only their environment network, use
digest-pinned images, service-level health checks, ownership labels, deliberate
restart policy, and no host-published data ports. Per-environment credentials
and persistent state must be distinct.

### AC-INFRA-002 — Stateful ownership and non-destructive lifecycle

Same-name unowned containers, services, volumes, networks, secrets, or trusted
paths must fail before mutation. Disabling or drifting a stateful service must
never delete its volume/data automatically. Backup metadata must identify data
locations without including credentials.

### AC-INFRA-003 — Narrow Dokploy Swarm and ingress authority

Dokploy may enable only Foundry's owned single-host, single-manager Swarm.
Runtime must refuse an active foreign Swarm and never force-leave one. Exactly
one digest-pinned Traefik authority uses the Foundry ingress overlay,
`exposedByDefault=false`, no public dashboard, and only declared listeners.

### AC-INFRA-004 — Safe Dokploy bootstrap

Dokploy and its internal PostgreSQL use persistent labeled resources and stable
Docker secrets. Dokploy itself publishes no host port; Traefik enforces the
declared management CIDR allowlist. A healthy but unclaimed installation must
be reported as `onboarding_required`, not ready for application deployment.

### AC-INFRA-005 — Optional deterministic domains

With `environment_style: hyphen`, environment application names resolve as
`dev-api.example.com`; with `nested`, they resolve as `dev.api.example.com`.
Dokploy is host-global at `dokploy.example.com`. Without a domain, no hostname
is fabricated from an IP and management resolves to `http://<vm_ip>:<port>`.

### AC-INFRA-006 — Persistence, isolation, reboot, and idempotence

Disposable-host certification must prove environment credential/network
isolation, data survival across recreation and reboot, negative external
exposure, collision/failure handling, stable secret IDs, and a final identical
convergence with `changed=0`. Until those tests execute, status is
`implemented; certification pending`.
