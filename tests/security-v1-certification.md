# Security V1 certification matrix

Code availability is not certification. The status `IMPLEMENTED; CERTIFICATION
PENDING` means the control exists and static/read-only checks may pass, but its
required disposable-VM scenario has not completed successfully.

| Control | Status | Required disposable-VM evidence |
|---|---|---|
| SSH baseline | IMPLEMENTED; CERTIFICATION PENDING | Effective directives and fresh login/elevation |
| 22 → custom migration | IMPLEMENTED; CERTIFICATION PENDING | New connection before retirement |
| custom → custom migration | IMPLEMENTED; CERTIFICATION PENDING | Saved endpoint discovery and migration |
| SSH rollback | IMPLEMENTED; CERTIFICATION PENDING | Injected sshd and connection failures |
| Old SSH endpoint retirement | IMPLEMENTED; CERTIFICATION PENDING | Controller probe reports stopped |
| Post-reboot SSH | CERTIFICATION PENDING | Reboot, reconnect, authenticate, elevate |
| Default-deny firewall | IMPLEMENTED; CERTIFICATION PENDING | Effective UFW policy |
| Public exposure | IMPLEMENTED; CERTIFICATION PENDING | External allowed-source probe |
| Management CIDR restriction | IMPLEMENTED; CERTIFICATION PENDING | Allowed and denied source probes |
| External firewall preservation | IMPLEMENTED; CERTIFICATION PENDING | Synthetic external rule survives drift repair |
| IPv4/IPv6 parity | IMPLEMENTED; CERTIFICATION PENDING | Dual-stack rule and connection probes |
| Unexpected listener detection | IMPLEMENTED; CERTIFICATION PENDING | Synthetic listener warning/failure |
| Fail2ban enforcement | IMPLEMENTED; CERTIFICATION PENDING | Controlled failed logins produce a ban |
| Fail2ban recovery | DOCUMENTED; CERTIFICATION PENDING | Trusted controller and explicit unban |
| Security updates policy | IMPLEMENTED; CERTIFICATION PENDING | Effective config, origins, timers, dry-run |
| Pending reboot detection | IMPLEMENTED; CERTIFICATION PENDING | Controlled marker/package scenario |
| AppArmor active/enforcing | IMPLEMENTED; CERTIFICATION PENDING | Kernel/service/enforcement checks |
| Persistent logs after reboot | IMPLEMENTED; CERTIFICATION PENDING | Pre-reboot record survives |
| SSH host-key preservation | IMPLEMENTED; CERTIFICATION PENDING | Fingerprints stable; unapproved replacement fails |
| Idempotence `changed=0` | CERTIFICATION PENDING | Second complete convergence |

Certification must use a disposable VM and the `fresh` safety tier described in
[README.md](README.md). Never inject SSH, firewall, or Fail2ban failures into a
production/default inventory.
