# Foundry Security role

The Security slice provides a deterministic Ubuntu V1 baseline without claiming
enterprise security or compliance certification. It manages only resources with
explicit Foundry ownership and preserves unrelated host state.

## Internal architecture

`tasks/main.yml` is only the orchestrator. Implementation is split by bounded
responsibility:

```text
tasks/
├── firewall/
│   ├── resolve.yml
│   ├── ownership.yml
│   ├── converge.yml
│   └── finalize_ssh_transition.yml
├── ssh/
│   ├── prepare.yml
│   ├── host_keys.yml
│   ├── apply_policy.yml
│   ├── migrate_connection.yml
│   └── finalize_transition.yml
├── fail2ban/main.yml
├── updates/main.yml
├── apparmor/main.yml
├── logging/main.yml
└── validation/
    ├── ssh.yml
    ├── ssh_host_keys.yml
    ├── firewall.yml
    ├── fail2ban.yml
    ├── updates.yml
    ├── apparmor.yml
    └── logging.yml
```

## V1 configuration

```yaml
network:
  exposure:
    - name: ssh
      port: 22
      protocol: tcp
      scope: management
    - name: http
      port: 80
      protocol: tcp
      scope: public

management:
  restrict_by_cidr: true
  allowed_cidrs:
    - 203.0.113.0/24

security:
  ssh:
    enabled: true
    port: 22
    root_login: false
    password_authentication: false
    public_key_authentication: true
    empty_passwords: false
    forwarding:
      agent: false
      tcp: false
      x11: false
    max_auth_tries: 4
    login_grace_time: 60
    max_sessions: 10
    max_startups: "10:30:60"
    allow_groups: []
    accept_host_key_change: false

  firewall:
    enabled: true
    default_incoming: deny
    default_outgoing: allow
    ipv6: true
    unexpected_listener_policy: warn

  fail2ban:
    enabled: true
    backend: systemd
    banaction: ufw
    ignore: []
    ssh:
      enabled: true
      maxretry: 5
      findtime: 10m
      bantime: 1h

  updates:
    automatic_security_updates: true
    automatic_reboot: false
    validate_dry_run: false

  apparmor:
    enabled: true

  logging:
    persistent_journal: true
```

`PermitEmptyPasswords no` and default-deny inbound are mandatory V1 invariants.
Foundry does not configure custom cipher, MAC, or key-exchange lists; the
supported OpenSSH package owns those secure version-specific defaults.

## Exposure and firewall ownership

Only `network.exposure` declares desired inbound connectivity. Workload roles may
contribute requirements before Security runs, but may not edit UFW directly.

- `scope: public` produces an Internet-reachable rule.
- `scope: management` produces either a public management rule or one rule per
  `management.allowed_cidrs` when restriction is enabled.
- Every owned rule has a stable `foundry:<scope>:<name>` comment.
- Removal uses the same comment and network fields.
- Rules absent from the Foundry ownership manifest are preserved.
- Disabling Foundry firewall ownership does not disable UFW or erase external
  rules.

Final validation compares the manifest with UFW, IPv4/IPv6 mode, and wildcard
listeners from `ss`. Unexpected listeners either fail or emit an explicit
security warning according to `unexpected_listener_policy`.

## Transactional SSH migration

`security.ssh.port` is the desired port. Foundry discovers the current validated
endpoint from `.foundry/state/<host>.yml`, with inventory and port 22 as recovery
candidates.

For `22 → custom` and `custom → custom`, Foundry:

1. Keeps the current endpoint open.
2. Adds desired and temporary old-port Foundry firewall rules.
3. Installs a validated dual-listener SSH policy.
4. Reloads SSH only after `sshd -t` succeeds.
5. Opens a new controller connection on the desired port.
6. Proves authentication and root elevation on that new connection.
7. Installs and validates the final single-listener policy.
8. Removes only the owned temporary firewall rule.
9. Proves the old endpoint is stopped.
10. Persists the new management endpoint.

Connection failure restores Ansible to the old port and deliberately leaves both
listeners and rules available. Policy validation/reload failure restores the
previous drop-in and reloads it before failing.

## SSH host keys

Ordinary convergence never generates host keys. Foundry records SHA-256 public
fingerprints under `/var/lib/foundry` and fails if they change unexpectedly.
Private key material is never read or reported. Set
`accept_host_key_change: true` only during an approved rotation or reprovisioning,
then return it to `false`.

## Fail2ban recovery

The active controller address and management CIDRs are automatically included in
the effective ignore list to reduce lockout risk. A candidate jail is validated
before restart; invalid policy restores the prior file and leaves the running
service unchanged. A controlled disposable-VM test may unban its synthetic
source with:

```bash
sudo fail2ban-client set sshd unbanip 198.51.100.10
```

Never generate deliberate failed SSH attempts from the only recovery path.

## Updates, AppArmor, and journal

- Security updates configure periodic unattended-upgrades but never authorize a
  reboot. Reboots use the separately approved final OS phase.
- A pending reboot is detected and reported.
- `validate_dry_run` exercises `unattended-upgrade --dry-run` when explicitly
  enabled.
- AppArmor ownership is platform-only: installed, loaded, active, and enforcing.
  Workload roles own workload-specific profiles.
- Journald uses persistent `/var/log/journal` storage. Post-reboot persistence
  remains a disposable-VM certification requirement.

## Validation and certification

Safe checks:

```bash
ansible-playbook --syntax-check playbook.yml
ansible-playbook playbook.yml --check --tags security --skip-tags security_result
python tests/run_acceptance.py static
```

Read-only final-state validation on an already converged host:

```bash
ansible-playbook playbook.yml --tags security_result
```

The current implementation must be reported as **implemented; certification
pending** until every scenario in
[the Security V1 matrix](../../tests/security-v1-certification.md) passes on a
fresh disposable supported VM, including reboot/reconnect, injected rollback,
Fail2ban ban/unban, external firewall preservation, drift repair, and a second
convergence with `changed=0`.

## Explicitly outside V1

CIS engines, vulnerability scanners, custom SSH crypto profiles, egress
allow-listing, Livepatch, Secure Boot management, TPM attestation, FIM, EDR,
SIEM, canary rollout infrastructure, remote log aggregation, and generic
application AppArmor profiles are intentionally outside this role.
