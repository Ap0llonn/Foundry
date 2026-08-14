# Networking and MinIO certification matrix

`IMPLEMENTED; CERTIFICATION PENDING` means code and static validation exist but
the disposable-Docker-host scenario has not executed successfully.

| Control | Status | Required evidence |
|---|---|---|
| Certified Runtime dependency | LIVE PASS | Role 5 checks Runtime manifest, daemon, service, and Compose |
| Single/multiple environment creation | LIVE PASS | dev/prod networks created and validated |
| Default/custom naming | DEFAULT LIVE PASS; CUSTOM INTEGRATION PENDING | Resolver fixtures pass; default names inspected live |
| Duplicate environment rejection | STATIC PASS | Validation fixture fails before Docker |
| Resolved-name collision rejection | STATIC PASS | Validation fixture fails before Docker |
| Foundry ownership labels | LIVE PASS | All four labels validated on dev/prod |
| External network preservation | IMPLEMENTED; CERTIFICATION PENDING | Synthetic external network unchanged |
| Unowned same-name collision refusal | IMPLEMENTED; CERTIFICATION PENDING | Collision fails without mutation |
| Dev/prod separation | IMPLEMENTED; CERTIFICATION PENDING | Disposable containers cannot cross-connect |
| No automatic cross-environment attachment | IMPLEMENTED; CERTIFICATION PENDING | Inspect and negative metadata test |
| Stale unused network handling | IMPLEMENTED; CERTIFICATION PENDING | report/fail/remove_unused paths |
| Stale in-use safe refusal | IMPLEMENTED; CERTIFICATION PENDING | Attached workload is preserved |
| Docker ownership boundary | STATIC PASS | Role 6 owns packages/services/config; role 5 owns networks only |
| Networking second convergence | PASS | `changed=0`, `failed=0` on managed host |
| Docker restart persistence | CERTIFICATION PENDING | Restart daemon and validate |
| Host reboot persistence | CERTIFICATION PENDING | Reboot, reconnect, validate |
| MinIO isolated S3 health | IMPLEMENTED; CERTIFICATION PENDING | One healthy internal instance per declaration |
| MinIO persistence | IMPLEMENTED; CERTIFICATION PENDING | Object survives container and host restart |
| MinIO external collision refusal | IMPLEMENTED; CERTIFICATION PENDING | External same-name container preserved |
| MinIO no host exposure | IMPLEMENTED; CERTIFICATION PENDING | No port bindings or host listeners |
| MinIO second convergence | CERTIFICATION PENDING | `changed=0`, `failed=0` |
