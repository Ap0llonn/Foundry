# Foundry configuration guide

This guide explains the public settings that can be changed in `config.yml`.
It is written for a new Foundry user.

Foundry reads this file, validates it, and applies the desired state to the
target VM with Ansible. YAML indentation matters: use spaces, not tabs.

## Before editing

Never commit these values in plain text:

- PostgreSQL, Redis, Dokploy, or sudo passwords;
- Cloudflare API tokens;
- Tailscale auth keys;
- private SSH keys.

Use Ansible Vault or another secret-injection mechanism for secrets. Public SSH
keys are safe to put in `config.yml`; private keys are not.

The smallest useful configuration normally contains:

```yaml
vm_ip: 203.0.113.10

project:
  name: my-project

environments:
  - name: dev
  - name: production

identity:
  users:
    - name: admin
      state: present
      admin: true
      groups: [developer]
      ssh_keys:
        - "ssh-ed25519 AAAA... admin@example.com"

management:
  restrict_by_cidr: true
  allowed_cidrs:
    - 198.51.100.20/32
```

## 1. VM and project identity

### `vm_ip`

The public IPv4 address of the VM managed by Foundry.

### `project.name`

Unique project name used in Docker network names, resource names, ownership
labels, and Dokploy metadata. Use lowercase letters, numbers, and hyphens. Do
not change it casually after deployment.

```yaml
project:
  name: my-project
```

### `project.resource_prefix`

Optional prefix (up to 20 lowercase letters, numbers, or hyphens) for new
shared-object-storage bucket and Dokploy S3 destination names. It defaults to
`foundry`; set it to an empty string to omit that prefix. This affects future
resource names only: changing it does not rename or remove resources that
already exist.

```yaml
project:
  name: my-project
  resource_prefix: ""  # buckets begin with my-project-... instead of foundry-...
```

### `environments[].name`

An isolated environment such as `dev`, `staging`, or `production`. Enabled
services are created separately in each selected environment.

```yaml
environments:
  - name: dev
  - name: production
```

### `environments[].network.name`

Optional explicit Docker network name. If omitted, Foundry generates
`foundry-<project>-<environment>`.

```yaml
environments:
  - name: production
    network:
      name: custom-production-network
```

## 2. Networking

### `networking.stale_network_policy`

Controls old Foundry-owned networks that are no longer declared.

| Value | Behavior |
|---|---|
| `report` | Report and preserve them. Recommended. |
| `fail` | Stop before changing anything. |
| `remove_unused` | Remove only when no container is attached. |

### `networking.overlay_migration_approved`

One-time approval for converting an empty Foundry-owned bridge network to a
Swarm overlay network. Keep `false`; set it to `true` only for an approved
migration and return it to `false afterward`.

## 3. Domains and Cloudflare

### `domains.base`

Base DNS domain used to generate hostnames. Leave empty for domainless mode.

### `domains.environment_style`

Places the environment in generated hostnames:

| Value | Example |
|---|---|
| `hyphen` | `dev-api.example.com` |
| `nested` | `dev.api.example.com` |

### `domains.dokploy_label`

Hostname label used for Dokploy, normally `dokploy`.

### `domains.service_names`

Application service labels for which Foundry may generate domains.

```yaml
domains:
  service_names: [api, web]
```

### `domains.cloudflare.enabled`

Enables Foundry-managed Cloudflare DNS and edge security.

### `domains.cloudflare.zone`

Cloudflare zone name, normally the same as `domains.base`.

### `domains.cloudflare.api_token`

Cloudflare API token. Supply it through Vault or a secure extra variable; do
not commit it to `config.yml`.

### `domains.cloudflare.proxied`

Routes DNS records through the Cloudflare edge when `true`. Required by the
enabled Cloudflare security profile.

### `domains.cloudflare.wildcard`

Manages a wildcard DNS record for generated service hostnames.

### `domains.cloudflare.apex_record`

Also manages the zone apex, such as `example.com`, when `true`.

### `domains.cloudflare.ttl`

DNS TTL in seconds. `1` means Cloudflare automatic TTL and is required for
proxied records.

### `domains.cloudflare.security.enabled`

Enables Foundry-managed Cloudflare security settings.

### `domains.cloudflare.security.ssl_mode`

TLS mode between Cloudflare and the VM. Foundry requires `strict`.

### `domains.cloudflare.security.always_use_https`

Redirects HTTP requests to HTTPS.

### `domains.cloudflare.security.min_tls_version`

Minimum client TLS version. The supported secure value is `1.2`.

### `domains.cloudflare.security.tls_1_3`

Enables TLS 1.3 at Cloudflare.

### `domains.cloudflare.security.managed_waf`

Enables Cloudflare managed WAF rules.

### `domains.cloudflare.security.rate_limit.enabled`

Enables rate limiting.

### `domains.cloudflare.security.rate_limit.requests_per_period`

Maximum matching requests allowed in one period.

### `domains.cloudflare.security.rate_limit.period`

Rate-limit window in seconds. Supported range: 10 to 3600.

### `domains.cloudflare.security.rate_limit.mitigation_timeout`

How long the mitigation remains active after the limit is exceeded.

### `domains.cloudflare.security.rate_limit.action`

Action after the limit is exceeded. Use `block` for the secure default.

## 4. Docker runtime

### `runtime.docker.enabled`

Installs and validates Docker when `true`.

### `runtime.docker.data_root`

Optional Docker data directory. Change only as part of a storage migration.

### `runtime.docker.legacy_package_migration_approved`

One-time approval to replace an older package such as `docker.io` with the
Foundry-managed Docker package.

### `runtime.docker.daemon_config_adoption`

Existing Docker daemon policy: `refuse` is safest; `matching` accepts an
already matching configuration.

### `runtime.docker.logging.driver`

Docker log driver: `json-file` or `local`.

### `runtime.docker.logging.max_size`

Maximum size of one log file, for example `10m`.

### `runtime.docker.logging.max_files`

Number of rotated log files to retain.

### `runtime.docker.restart.approved`

Approves a Docker service restart caused by runtime changes.

### `runtime.docker.restart.maintenance_window`

Required maintenance identifier for an approved Docker restart.

### `runtime.docker.smoke_test.enabled`

Runs a Docker smoke test after installation.

### `runtime.docker.smoke_test.image`

Immutable digest-pinned image used for the smoke test.

### `runtime.docker.privileged_users`

Optional users explicitly allowed privileged Docker access. An empty list is
safest.

## 5. Operating-system lifecycle

### `os.operation_mode`

Selects the OS operation:

| Value | Behavior |
|---|---|
| `bootstrap` | Install and validate the baseline. |
| `security_patching` | Apply approved security updates. |
| `full_maintenance` | Run an explicitly approved broad maintenance. |

Use `bootstrap` for normal deployments.

### `os.mounts[]`

Persistent filesystem mounts. Use this to declare the dedicated VM disk used
by MinIO. Create and format the disk through the VM provider first, then use a
stable `/dev/disk/by-uuid/...` source; Foundry writes the mount to `/etc/fstab`
and validates it, but never formats an unspecified device.

```yaml
os:
  mounts:
    - path: /srv/foundry/minio
      src: /dev/disk/by-uuid/REPLACE-WITH-DISK-UUID
      fstype: ext4
      opts: defaults,noatime
      state: mounted
      min_free_percent: 10
```

### `os.maintenance.approved`

Required approval for `full_maintenance`.

### `os.maintenance.window`

Required non-empty identifier, for example `change-2026-08-22`.

### `os.maintenance.autoremove`

Allows package autoremove during full maintenance.

### `os.maintenance.removals_approved`

Separate approval required when autoremove or purge is enabled.

### `os.maintenance.autoclean`

Allows APT cache cleanup during full maintenance.

### `os.reboot.enabled`

Allows Foundry to perform its final controlled reboot phase.

### `os.reboot.approved`

Explicit approval required for the reboot.

### `os.reboot.only_if_required`

Reboots only when the VM reports that a reboot is required.

### `os.reboot.precheck_commands` and `os.reboot.postcheck_commands`

Optional absolute commands to run before and after a controlled reboot.

## 6. Users and access

### `identity.groups`

Optional logical groups mapped to `foundry-*` Linux groups.

```yaml
identity:
  groups:
    - name: team1
      replaces: developers
    - name: database-team
```

### `identity.groups[].name`

Custom logical group name.

### `identity.groups[].replaces`

Optional built-in group replaced by the custom group. Built-ins are
`developer`, `operator`, and `viewer`.

### `identity.default_admin_sudo.mode`

Default sudo policy for users with `sudo.mode: inherit`. Supported values are
`passwordless`, `password`, and `constrained`.

### `identity.users[].name`

Linux username to manage.

### `identity.users[].state`

`present` manages the account; `absent` removes the Foundry-owned account.

### `identity.users[].admin`

Whether the user receives the administrator policy.

### `identity.users[].groups`

Logical Foundry groups assigned to the user. Do not add privileged system
groups such as `docker`, `sudo`, `root`, or `wheel`.

### `identity.users[].ssh_keys`

Public SSH keys authorized for the user.

### `identity.users[].sudo.mode`

User sudo policy: `inherit`, `passwordless`, `password`, `constrained`, or
`none`.

### `identity.users[].sudo.authentication`

Authentication for constrained sudo: `passwordless` or `password`.

### `identity.users[].sudo.password_hash`

Linux password hash for password-authenticated sudo. Supply it through Vault;
never put a plaintext password here.

### `identity.users[].sudo.commands`

Absolute commands allowed by constrained sudo. Shell pipelines and wildcards
are not allowed.

## 7. Firewall and management

### `network.exposure[]`

Declares services that should be exposed before Security converges. Foundry
owns the resulting firewall rules; do not edit UFW manually.

### `network.exposure[].name`

Unique exposure identifier, such as `ssh` or `web`.

### `network.exposure[].port`

TCP or UDP port number.

### `network.exposure[].protocol`

`tcp` or `udp`.

### `network.exposure[].scope`

Use `management` for administration, `public` for public application traffic,
or `internal` for non-public service traffic.

### `network.exposure[].source_cidrs`

Optional source allow-list. Use `/32` for one IPv4 address. Never use
`0.0.0.0/0` or `::/0` for management or database access.

### `management.restrict_by_cidr`

Restricts management services to `management.allowed_cidrs`. Keep `true`.

### `management.allowed_cidrs`

Public source addresses allowed to reach management services such as SSH and
domainless Dokploy. Update this when the administrator's public IP changes.

## 8. PostgreSQL developer access

### `database_access.enabled`

Creates a private PostgreSQL access proxy when `true`.

### `database_access.mode`

Select one method: `tunnel` for SSH forwarding or `tailscale` for a Tailscale
listener.

### `database_access.environment`

Environment whose PostgreSQL service is exposed. It must exist in
`environments` and be enabled in `services.postgres.environments`.

### `database_access.tunnel.allowed_cidrs`

Public source CIDRs allowed to create the SSH tunnel. These are added to the
SSH firewall allow-list; a public SSH key is still required.

### `database_access.tunnel.local_port`

Local port used by `scripts/foundry-db-tunnel.sh`. Default: `15432`.

### `database_access.tailscale.auth_key`

Auth key used to register the VM in Tailscale. Supply it through Vault. Do not
give this server key to developers.

### `database_access.tailscale.hostname`

Optional Tailscale machine hostname. Foundry generates one when empty.

### `database_access.tailscale.port`

PostgreSQL port on the Tailscale address. Default: `5432`.

### `database_access.tailscale.cidr`

Source CIDR allowed by the VM firewall. The usual Tailscale range is
`100.64.0.0/10`. Use Tailscale ACLs/grants for identity-based restrictions.

Foundry currently creates a TCP proxy, not a database web UI. Use DBeaver,
TablePlus, or pgAdmin Desktop, or deploy a separate pgAdmin service through
Dokploy.

## 9. Security policy

### `security.ssh.enabled`

Enables SSH security management.

### `security.ssh.port`

Desired SSH port. Foundry can migrate from the current port transactionally.

### `security.ssh.root_login`

Allows direct root SSH login. Keep `false`.

### `security.ssh.password_authentication`

Allows SSH password login. Keep `false` and use public keys.

### `security.ssh.public_key_authentication`

Requires public-key authentication. Keep `true`.

### `security.ssh.empty_passwords`

Allows empty-password accounts. Keep `false`.

### `security.ssh.forwarding.agent`, `tcp`, and `x11`

Controls SSH agent, TCP, and X11 forwarding. Keep all `false` unless required.

### `security.ssh.max_auth_tries`

Maximum authentication attempts per connection.

### `security.ssh.login_grace_time`

Seconds allowed for authentication.

### `security.ssh.max_sessions`

Maximum concurrent sessions per connection.

### `security.ssh.max_startups`

Unauthenticated connection limit in `start:rate:full` format, for example
`10:30:60`.

### `security.ssh.allow_groups`

Optional Linux group allow-list for SSH. Empty means use managed users and
keys.

### `security.ssh.accept_host_key_change`

Allows intentional SSH host-key rotation. Keep `false` normally.

### `security.firewall.enabled`

Enables Foundry firewall management.

### `security.firewall.default_incoming`

Default incoming policy. Use `deny`.

### `security.firewall.default_outgoing`

Default outgoing policy. Normally `allow`.

### `security.firewall.ipv6`

Enables IPv6 firewall parity.

### `security.firewall.unexpected_listener_policy`

Action for undeclared wildcard listeners: `fail` stops convergence; `warn`
continues with a warning. Use `fail` for production.

### `security.fail2ban.enabled`

Enables Fail2ban.

### `security.fail2ban.ssh.enabled`

Enables the SSH brute-force jail.

### `security.fail2ban.ssh.maxretry`

Failed attempts before an address is banned.

### `security.fail2ban.ssh.findtime`

Time window in which failed attempts are counted, such as `10m`.

### `security.fail2ban.ssh.bantime`

Ban duration, such as `1h`.

### `security.fail2ban.backend`

Log backend. The normal Ubuntu value is `systemd`.

### `security.fail2ban.banaction`

Ban mechanism. The normal value is `ufw`.

### `security.fail2ban.ignore`

Addresses Fail2ban must never ban.

### `security.updates.automatic_security_updates`

Enables automatic security-update policy.

### `security.updates.automatic_reboot`

Allows automatic reboot after updates. Keep `false`.

### `security.updates.validate_dry_run`

Validates the update plan without applying it.

### `security.apparmor.enabled`

Enables AppArmor capability validation.

### `security.logging.persistent_journal`

Persists systemd journal logs across reboots.

## 10. PostgreSQL and Redis

### `services.postgres.enabled`

Creates PostgreSQL through the Dokploy API.

### `services.postgres.environments`

Environments receiving PostgreSQL. Empty means all declared environments.

### `services.postgres.image`

Optional immutable `@sha256:` PostgreSQL image digest. Mutable tags such as
`latest` are rejected.

### `services.postgres.major`

PostgreSQL major-version policy. The tested default is `17`.

### `services.postgres.user`

Database user. Default: `foundry`.

### `services.postgres.database`

Database name. Default: `foundry`.

### `services.postgres.credentials.<environment>.password`

Password for one environment. Use a strong Vault-supplied value, and use a
different password per environment.

### `services.postgres.backup`

Creates one scheduled Dokploy PostgreSQL backup per selected environment. It
requires `services.object_storage.enabled: true` and the same environments in
both services. Foundry creates a Dokploy S3 destination only for the private
`db-backups` bucket; application asset buckets are used directly through their
MinIO credentials.

```yaml
backup:
  enabled: true
  schedule: "0 3 * * *" # standard five-field cron, daily at 03:00
  keep_latest: 7
```

`schedule` controls the period with a standard five-field cron expression.
For example, `0 */6 * * *` runs every six hours and `0 3 * * 0` runs every
Sunday at 03:00. `keep_latest` is the number of most recent backups Dokploy
keeps in the environment’s `db-backups` bucket.

### `services.postgres.resources.memory` and `cpus`

Optional memory and CPU limits, for example `512m` and `1`.

### `services.redis.enabled`

Creates Redis through the Dokploy API.

### `services.redis.environments`

Environments receiving Redis. Empty means all declared environments.

### `services.redis.image`

Optional immutable Redis image digest.

### `services.redis.version`

Redis version policy. The tested default is `8.2`.

### `services.redis.credentials.<environment>.password`

Optional Redis password. Do not reuse the PostgreSQL password.

### `services.redis.persistence`

Keeps Redis data on persistent storage when `true`.

### `services.redis.maxmemory`

Optional Redis memory limit, for example `256m`.

### `services.redis.maxmemory_policy`

Redis eviction policy. Supported values include `noeviction`, `allkeys-lru`,
`allkeys-lfu`, `allkeys-random`, `volatile-lru`, `volatile-lfu`,
`volatile-random`, and `volatile-ttl`.

### `services.redis.resources.memory` and `cpus`

Optional Redis memory and CPU limits.

### `services.object_storage`

Creates one digest-pinned MinIO Docker Compose service in Dokploy for every
selected environment. Each service is visible in its Dokploy environment and
contains three separate versioned buckets, each with a dedicated limited MinIO
access key:

- `assets-public`: anonymous read only, intended for genuinely public static
  assets such as product or article images.
- `assets-private`: private application uploads, accessed with its bucket
  credential or short-lived signed URLs.
- `db-backups`: private database backups; this is the destination to select for
  PostgreSQL backups in Dokploy. It is the only bucket registered as a Dokploy
  S3 destination.

Only `assets-public` is readable without credentials through the published S3
endpoint. Never store backups, user documents, or private uploads in it.

It requires `platform.dokploy.enabled`, TLS-enabled Traefik, and `domains.base`.
By default, `data_root` must match a dedicated `os.mounts[].path`. Do not enable
it together with the legacy MinIO section.

```yaml
services:
  object_storage:
    enabled: true
    environments: [dev, production]
    data_root: /srv/foundry/minio
    allow_root_filesystem: false
    domain_name: ""  # defaults to minio.<domains.base>
    region: us-east-1
    console:
      enabled: true
      tailscale_port: 9001
    credentials:
      root_user: foundryminio
      root_password: "{{ vault_minio_root_password }}"
```

The production S3 API is HTTPS at `https://minio.<domains.base>` by default;
other environments use an environment prefix, for example
`https://dev-minio.example.com`. Set `domain_name` to a hostname inside
`domains.base` to change the suffix; Foundry prefixes non-production
environments only. Only the S3 APIs are published; every MinIO administration
console remains private. Dokploy connects to each environment's internal
`http://minio-<environment>:9000` endpoint, so backups do not traverse
Cloudflare.

### `services.object_storage.environments`

Environments that receive the three isolated buckets. The `db-backups` bucket
is also registered as the Dokploy S3 destination. Empty means every declared
environment.

### `services.object_storage.data_root`

The exact mount path for the dedicated MinIO data disk, normally
`/srv/foundry/minio`. It must exactly match one `os.mounts[].path`; Foundry
refuses to put MinIO data on the root filesystem unless explicitly allowed.

### `services.object_storage.allow_root_filesystem`

Defaults to `false`. Set to `true` only when the VM has no separate data volume
and you intentionally want MinIO to use the root filesystem beneath
`data_root`. Monitor disk capacity carefully: MinIO data and backups can fill
the VM’s operating-system volume.

### `services.object_storage.domain_name`

Optional full external S3 hostname. Empty resolves to
`minio.<domains.base>`. The override must be inside the configured base domain
so DNS and TLS can be managed consistently.

### `services.object_storage.console`

Optional private MinIO Console access through Tailscale. It requires
`database_access.enabled: true` and `database_access.mode: tailscale`. Foundry
binds the Console only to VM loopback and uses Tailscale Serve to make it
available at `http://<tailscale-ip>:tailscale_port` for the first environment,
then the following ports for subsequent environments; it is never exposed
through a public MinIO domain.

### `services.object_storage.credentials.root_user` and `root_password`

MinIO administrator credential used only by Foundry to create buckets and
bucket-scoped service credentials. Leave `root_password` empty to generate and
persist a stable value on the VM, or supply it through Vault. It is never used
as the Dokploy destination credential.

## 11. Swarm, Traefik, and Dokploy

### `platform.swarm.enabled`

Enables the single-manager Docker Swarm required by Dokploy.

### `platform.swarm.advertise_address`

Optional Swarm advertise address. Empty means automatic resolution.

### `platform.swarm.default_address_pool`

Swarm overlay address pool. Default: `10.240.0.0/16`.

### `platform.swarm.subnet_size`

Subnet size for Swarm overlay networks. Default: `24`.

### `platform.traefik.enabled`

Enables Foundry-managed Traefik ingress.

### `platform.traefik.image`

Optional immutable Traefik image digest.

### `platform.traefik.ingress_network`

Network used by Traefik and Dokploy ingress. Normal value: `dokploy-network`.

### `platform.traefik.http_port` and `https_port`

HTTP and HTTPS listener ports. Normal values are `80` and `443`.

### `platform.traefik.tls.enabled`

Enables TLS configuration.

### `platform.traefik.tls.mode`

Selects how Traefik obtains its origin certificate:

- `public_acme` (default): Traefik requests a publicly trusted certificate
  through ACME / Let's Encrypt. Use this when the server is directly reachable
  from the Internet, including deployments that do not use Cloudflare.
- `cloudflare_origin`: Foundry creates a Cloudflare Origin CA certificate for
  `domains.base` and `*.domains.base`, then installs it only on the origin VM.
  Use this only with Cloudflare proxying enabled and SSL/TLS mode **Full
  (strict)**. The certificate is intentionally not trusted by browsers that
  bypass Cloudflare.

For `cloudflare_origin`, the Cloudflare API token also needs **Zone → SSL and
Certificates → Edit**. `platform.traefik.tls.email` is required only by
`public_acme`.

### `platform.traefik.tls.email`

Certificate issuer notification email for `public_acme`.

### `platform.dokploy.enabled`

Enables Dokploy installation and configuration. It also requires the
single-manager Swarm and compatible Traefik setup.

### `platform.dokploy.image`

Immutable Dokploy image digest.

### `platform.dokploy.postgres_image`

Immutable image digest for Dokploy's internal PostgreSQL.

### `platform.dokploy.management_port`

Dokploy management port. Domainless access is protected by the management CIDR
policy.

### `platform.dokploy.credentials.postgres_password`

Optional Vault-supplied password for Dokploy's internal PostgreSQL.

### `platform.dokploy.credentials.auth_secret`

Optional Vault-supplied Dokploy authentication secret.

### `platform.dokploy.secret_version`

Version label for persisted generated Dokploy secrets. Change only for an
intentional rotation.

### `platform.dokploy.bootstrap.email`, `password`, `name`, and `last_name`

Initial Dokploy administrator information used during first-time onboarding.
The password must be supplied securely.

## 12. Observability

### `observability`

Enables the Foundry host observability agent on Debian 12. It installs the
checksum-pinned `otelcol-contrib` system package and exposes OTLP only on the
local VM:

- gRPC: `127.0.0.1:4317`
- HTTP: `127.0.0.1:4318`

The Collector sends host CPU, memory, load, disk, filesystem, and network
metrics together with application OTLP traces, metrics, and logs to the
configured OTLP backend. Its stable interface is OTLP, so changing the backend
does not require changing application instrumentation.

```yaml
observability:
  enabled: true
  dashboard: signoz
  backend:
    endpoint: "127.0.0.1:14317"
    headers: {}
    tls_insecure: true
  signoz:
    enabled: true
    host: app-vm
    project: monitoring
    environment: monitoring
    hostname: ""
```

`dashboard` is currently restricted to `signoz`; it documents the supported UI
without coupling the Collector pipeline to SigNoz. `backend.endpoint` accepts
any OTLP/gRPC `host:port` target. `backend.headers` is an optional string map
used for backend authentication; keep its values in Vault or another secure
variable source. Set `tls_insecure: true` only for a trusted internal backend
using plaintext or an untrusted certificate.

### `observability.signoz`

Deploys the self-hosted SigNoz dashboard through Dokploy. The dashboard URL is
`https://signoz.<domains.base>` unless `hostname` is set. It is a shared
operations service. Foundry creates the separate Dokploy project and
environment selected by `project` and `environment` (by default both are named
`monitoring`), then collects telemetry from every Foundry environment. It is
not deployed in the application's `dev` or `production` environments.

`host` is the inventory host that owns the SigNoz Compose service, ClickHouse
data, and local ingestion listener. Set it explicitly when the inventory has
more than one VM. The selected VM needs at least 4 GB of RAM, Dokploy,
TLS-enabled Traefik, and a domain under `domains.base`.

Foundry accepts at least 3,800 MiB as a 4 GB provider allocation because some
providers advertise memory in decimal GB while Linux reports MiB.

Foundry binds SigNoz OTLP/gRPC to `127.0.0.1:14317` on this dashboard VM. This
keeps unauthenticated self-hosted ingestion off the public Internet. For a
single-VM installation, use exactly the backend endpoint shown above. For
additional application VMs, set `backend.endpoint` to a mutually reachable
private OTLP address protected by your private-network policy; do not expose
the unauthenticated receiver publicly.

Foundry validates the rendered Collector configuration, systemd service state,
both loopback OTLP listeners, the Collector’s own hostmetrics pipeline, the
SigNoz dashboard health endpoint, and the local SigNoz OTLP listener.

## 13. Legacy MinIO interface

### `infrastructure_services.minio.enabled`

Legacy MinIO-only interface. Keep `false` when using `services.object_storage`.

### `infrastructure_services.minio.run_as_uid` and `run_as_gid`

Linux UID and GID for the legacy MinIO process.

### `infrastructure_services.minio.instances[]`

Legacy per-environment declarations. Each instance can define `environment`,
immutable `image`, `data_path`, `root_user`, and `root_password`.

## 14. Apply and verify

Syntax check:

```bash
ansible-playbook --syntax-check -i localhost, playbook.yml
```

Read-only plan:

```bash
ansible-playbook -i inventory.yml playbook.yml --check
```

Apply:

```bash
ansible-playbook -i inventory.yml playbook.yml
```

Useful targeted runs:

```bash
ansible-playbook -i inventory.yml playbook.yml --tags security
ansible-playbook -i inventory.yml playbook.yml --tags infrastructure_services
ansible-playbook -i inventory.yml playbook.yml --tags os_security_patching
```

Non-secret service information is written on the VM to:

```text
/var/lib/foundry/infrastructure-services/resolved-services.yml
```

## 15. Common database-access choices

### Tailscale

```yaml
database_access:
  enabled: true
  mode: tailscale
  environment: dev
  tailscale:
    auth_key: "{{ vault_tailscale_auth_key }}"
    hostname: foundry-db
    port: 5432
    cidr: 100.64.0.0/10
```

The developer joins the same tailnet and connects to the reported Tailscale
IP on port `5432`.

### SSH tunnel

```yaml
database_access:
  enabled: true
  mode: tunnel
  environment: dev
  tunnel:
    allowed_cidrs:
      - 198.51.100.20/32
    local_port: 15432
```

The developer runs `scripts/foundry-db-tunnel.sh` and connects to
`127.0.0.1:15432`.

### No external database access

```yaml
database_access:
  enabled: false
```

The database remains internal to Dokploy and no access proxy is created.
