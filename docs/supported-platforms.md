# Foundry supported-platform matrix

Foundry support is end-to-end: a platform is listed as supported only when the
implemented OS, Identity, and Security layers use compatible package, service,
firewall, SSH, and validation behavior on that platform.

| Distribution | Version | Architecture | Status | Evidence |
|---|---:|---|---|---|
| Ubuntu | 26.04 | x86_64 | Current implementation target | Live bootstrap convergence and a second `changed=0` run passed; security/full-maintenance plans passed in check mode; clean-image destructive maintenance/reboot certification remains required |
| Ubuntu | 26.04 | aarch64 | Planned | No clean-image convergence and reboot test yet |
| Ubuntu | 24.04 LTS | x86_64/aarch64 | Planned | No clean-image convergence and reboot test yet |
| Ubuntu | 22.04 LTS | x86_64/aarch64 | Planned | No clean-image convergence and reboot test yet |
| Debian | Any | Any | Unsupported | Security currently assumes Ubuntu service names, UFW, and Ubuntu policy |

## Promotion criteria

A new matrix entry becomes supported only after all of these checks pass on a
clean image:

1. Bootstrap convergence succeeds.
2. A second convergence reports no unintended changes.
3. Identity and explicit sudo policy tests pass.
4. Firewall and fresh SSH connection tests pass.
5. Security patching mode succeeds without a broad distribution upgrade.
6. Approved full-maintenance mode captures its package plan and passes all
   post-maintenance validation.
7. An opt-in reboot reconnects and passes kernel, system-service, mount, clock,
   and configured workload health gates.
8. Drift and negative-configuration tests fail safely.

Syntax checks alone do not promote a platform to supported status.

The role currently rejects every tuple except Ubuntu 26.04 x86_64. This narrow
gate prevents accidental execution on an unimplemented Debian or Ubuntu path;
it does not replace the promotion evidence above.
