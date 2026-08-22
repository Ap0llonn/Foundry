# Foundry Infrastructure Services V1

Role 7 prepares infrastructure before any application is deployed. It owns
environment PostgreSQL, Redis, MinIO object storage, the single ingress
Traefik, and Dokploy. It does not deploy APIs, frontends, workers, migrations,
repositories, or business configuration.

## Minimal high-level configuration

```yaml
services:
  postgres:
    enabled: true
    environments: []       # empty means every declared environment

  redis:
    enabled: true
    environments: [dev, production]
    persistence: true
    maxmemory: 256m
    resources:
      memory: 512m
      cpus: "1"

  object_storage:
    enabled: false
    provider: minio
    environments: []
    image: "registry.example/minio@sha256:<approved-digest>"

platform:
  traefik:
    enabled: true

  dokploy:
    enabled: true

management:
  restrict_by_cidr: true
  allowed_cidrs:
    - 203.0.113.10/32
```

PostgreSQL 17 and Redis 8.2 are the only data-service versions accepted for V1.
PostgreSQL databases are created and deployed through the Dokploy API inside
their exact Foundry project/environment. Redis services are created and
deployed through the Dokploy API in the same way. Traefik, Dokploy, and
Dokploy's internal PostgreSQL also have digest-pinned defaults. MinIO must be
supplied as an approved immutable digest; Foundry deliberately has no mutable
or unreviewed fallback image.

Credentials may be supplied from Ansible Vault:

```yaml
services:
  postgres:
    credentials:
      dev:
        password: "{{ vault_postgres_dev_password }}"

  redis:
    credentials:
      dev:
        password: "{{ vault_redis_dev_password }}"

platform:
  dokploy:
    credentials:
      postgres_password: "{{ vault_dokploy_postgres_password }}"
      auth_secret: "{{ vault_dokploy_auth_secret }}"
```

When a value is omitted, Foundry generates it once on the VM beneath
`/var/lib/foundry/infrastructure-services/secrets/<project>/`. Parent
directories are root-only. Ordinary convergence reuses the same value. Secret
values are suppressed with `no_log`, excluded from resolved outputs, and are
not committed to configuration. PostgreSQL and Redis credentials are sent only
in protected Dokploy API requests.

## Domains and environment names

Domain configuration is optional:

```yaml
domains:
  base: example.com
  environment_style: hyphen
  dokploy_label: dokploy
  service_names:
    - api
```

Resolution is deterministic:

```text
hyphen  -> dev-api.example.com
nested  -> dev.api.example.com
Dokploy -> dokploy.example.com
```

`hyphen` is the default because `*.example.com` normally covers
`dev-api.example.com`. It does not cover the deeper
`dev.api.example.com`; nested mode needs matching DNS and certificate policy.

### Optional Cloudflare DNS and edge security

Foundry can create the wildcard DNS record and manage a focused Cloudflare
security baseline entirely from the Ansible controller. The token is never
sent to the VM or Dokploy.

```yaml
domains:
  base: example.com
  environment_style: hyphen
  cloudflare:
    enabled: true
    zone: example.com
    api_token: "{{ vault_cloudflare_api_token }}"
    proxied: true
    wildcard: true
    apex_record: false
    security:
      enabled: true
      managed_waf: true # Selects the best Cloudflare-managed WAF entitled for the zone.
      rate_limit:
        enabled: true
        requests_per_period: 20
        period: 10
        mitigation_timeout: 10
```

The API token requires access only to that zone: DNS edit, Zone settings edit,
and Zone WAF edit. With the security profile enabled, Foundry creates a
proxied `*.example.com` record, enables HTTPS-only/strict TLS/TLS 1.2+, enables
Cloudflare Managed WAF, restricts `dokploy.example.com` to
`management.allowed_cidrs`, and rate-limits Dokploy authentication requests.
It does not create broad application-specific WAF rules, modify e-mail DNS,
or enable HSTS automatically.

For proxied Dokploy traffic, Traefik accepts the management route only from
Cloudflare origin CIDRs. The management CIDR decision is enforced at
Cloudflare using the original client IP, so direct requests to the VM cannot
bypass it. `wildcard: true` currently requires `environment_style: hyphen`;
`*.example.com` cannot cover `dev.api.example.com`.

Supply `cloudflare_api_token` through Vault, an encrypted inventory value, or
a secure extra variable. Do not put a real API token in tracked `config.yml`.

With `domains.base: ""`, Foundry does not invent a subdomain of the VM IP.
Private services keep Docker DNS names and Dokploy resolves to
`http://<vm_ip>:3000` through Traefik's management entrypoint.

## Dokploy and Swarm boundary

Dokploy overrides the original no-Swarm V1 assumption only as narrowly as
required:

- Runtime initializes and owns one single-host manager/leader;
- an active foreign Swarm is refused;
- Foundry never runs `docker swarm leave --force`;
- multi-node, workers, HA, and horizontal scaling remain unsupported;
- Networking uses attachable overlay environment networks when Dokploy/Swarm
  is enabled;
- an existing same-name bridge is replaced only with one-time approval and only
  when it is Foundry-owned and has zero attachments.

Foundry does not execute Dokploy's installer. It creates the compatible
`dokploy`, `dokploy-postgres`, `dokploy-network`, persistent volumes, versioned
Docker secrets, and `dokploy-traefik` resources itself with ownership checks.
Runtime remains the only Docker installer.

Exactly one Traefik authority is used. Its dashboard is disabled,
`exposedByDefault` is false, and PostgreSQL, Redis, and MinIO never join the
ingress network. Dokploy itself publishes no host port. Traefik enforces the
configured management CIDR allowlist, including during initial onboarding.
Foundry owns the `dokploy-traefik` container and its configuration. Do not use
Dokploy's Traefik reset/recreate operation: replacing that resource would break
the ownership boundary and the next Foundry convergence will fail closed.
Normal Dokploy project and application deployments remain supported through
the Docker and Swarm providers configured by Foundry.

After first convergence, open the reported endpoint and create the first
Dokploy administrator. Foundry checks Dokploy's registration redirect without
creating an account and reports:

```yaml
onboarding_required: true
```

Healthy plus onboarding pending is not reported as ready for application
deployment.

## Ownership, persistence, and outputs

Resources use `foundry.managed`, `foundry.project`, `foundry.environment`, and
`foundry.service` labels where Docker supports them. Same-name external
containers, services, volumes, networks, and secrets fail before mutation.
Foundry never runs broad Docker cleanup.

Persistent data is independent per environment. Removing a declaration reports
stale state and preserves volumes/data. Destructive removal or secret rotation
requires a future explicit lifecycle workflow.

Non-secret outputs are written to:

```text
/var/lib/foundry/infrastructure-services/resolved-services.yml
/var/lib/foundry/infrastructure-services/backup-metadata.yml
```

The resolved service map contains internal hosts, ports, network/resource
names, domains, platform endpoint, and backup integration locations—never
passwords or Docker secret contents.

## Validation

Static validation:

```bash
ansible-playbook --syntax-check playbook.yml
python tests/run_acceptance.py static
```

Targeted convergence:

```bash
ansible-playbook -i inventory.yml playbook.yml --tags infrastructure_services
```

Fresh-VM certification must additionally prove data persistence, dev/prod
credential and network isolation, external negative exposure, collision and
failure behavior, Docker restart, a real host reboot, secret stability, and a
second convergence with `changed=0`.

The implementation and static fixtures exist. Live Docker 29/Dokploy operation,
reboot, persistence, failure-injection, and idempotence certification are
pending; do not describe the slice as V1-certified until those tests execute.
