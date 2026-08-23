# Runtime V1 certification matrix

`IMPLEMENTED; CERTIFICATION PENDING` means the safety mechanism exists but its
required disposable-host scenario has not completed. Static checks are not
reported as deployment certification.

| Control | Status | Required evidence |
|---|---|---|
| Fresh Ubuntu 26.04 x86_64 | IMPLEMENTED; CERTIFICATION PENDING | Disposable supported VM |
| Fresh Debian 12 (Bookworm) x86_64 | IMPLEMENTED; CERTIFICATION PENDING | Disposable supported VM |
| Official Docker repository | LIVE PASS on Ubuntu; DEBIAN PATH IMPLEMENTED | Foundry uses the distribution-specific official stable source |
| Repository key checksum | LIVE PASS | Checksum-pinned download accepted on managed VM |
| Exact Engine/CLI/containerd/Buildx/Compose packages | LIVE PASS | Every `dpkg-query` value equals defaults |
| Package holds | LIVE PASS | Holds converge without second-run change |
| Docker/containerd active and enabled | LIVE PASS; DRIFT TEST PENDING | systemd state passes; injected drift remains pending |
| Docker info/version/Compose | LIVE PASS | Complete standalone Runtime validation |
| Supported Engine/API versions | LIVE PASS | Engine 29.7.2; API 1.55 |
| Candidate daemon validation | LIVE PASS; INVALID NEGATIVE TEST PENDING | Candidate accepted before apply |
| Bounded logging | LIVE PASS | Effective `json-file`, `10m`, three-file policy |
| Unix socket security | LIVE PASS | socket root:docker `0660` |
| No Docker TCP API | LIVE PASS | listener and systemd checks |
| Storage driver/root/capacity/inodes | LIVE PASS | overlayfs, `/var/lib/docker`, 92%/97% free |
| Digest-pinned disposable container | LIVE PASS | successful execution and no remaining container |
| External resources preserved | NETWORK PRESERVATION LIVE; EXTERNAL DRIFT TEST PENDING | dev/prod networks survived migration and restart |
| Workload-aware restart gate and rollback | RESTART LIVE PASS; FAILURE INJECTION PENDING | initial config restart healthy; rollback injection pending |
| Service/config drift recovery | IMPLEMENTED; CERTIFICATION PENDING | stop/disable/edit then reconcile |
| Host reboot and reconnect | IMPLEMENTED; CERTIFICATION PENDING | controlled reboot plus Runtime result |
| Second convergence changed=0 | LIVE PASS | `ok=132 changed=0 failed=0` |
