# Foundry Runtime V1

Runtime executes after Security and before Networking. It owns Docker Engine,
the official Docker APT repository, exact package versions, system services,
and the complete `/etc/docker/daemon.json` file.

The minimal configuration is:

```yaml
runtime:
  docker:
    enabled: true
```

The defaults bound container logs to `10m` with three files, use
`/var/lib/docker`, disable remote TCP access, keep the Docker group empty, and
run a disposable digest-pinned smoke test. Docker group access is equivalent to
root access; V1 administrators should invoke Docker through their explicit sudo
policy.

Standalone Runtime enables Docker live-restore. When Swarm or Dokploy is
requested, Foundry disables live-restore before Swarm initialization because
that daemon feature applies to standalone containers rather than Swarm
services. Foundry validates and restarts the owned daemon configuration before
creating the cluster.

The single-node manager necessarily listens on `2377/tcp`, `7946/tcp+udp`, and
`4789/udp`. Runtime rejects every other Docker-owned TCP listener, including the
remote Docker API ports `2375/2376`. Security treats the Swarm sockets as
expected internal listeners but requires them to remain blocked by UFW; V1 does
not open them publicly.

## Version and repository policy

V1 supports Ubuntu 26.04 `x86_64` and Debian 12 `x86_64` (Bookworm). Docker
Engine is installed from Docker's official distribution-specific stable
repository. The signing key is checksum-pinned. Docker Engine, CLI,
containerd, Buildx, and Compose package versions are exact and held against
incidental upgrades. Updating versions is a reviewed dependency change that
requires fresh-VM, drift, reboot, and idempotence certification.

## Existing hosts and restart safety

Foundry refuses an existing unowned `/etc/docker/daemon.json`. It may adopt only
an exactly matching file when `daemon_config_adoption: matching` is explicit.
It never adopts containers, images, volumes, or networks and never runs broad
cleanup commands.

If a first bootstrap stops after installing the daemon configuration but before
publishing the Runtime ownership manifest, recovery remains fail-closed. Foundry
accepts only its complete current daemon document or the exact historical
variant that differs solely in the boolean `live-restore` policy. Any additional
key or value drift is refused as external configuration.

The former role-5 Ubuntu `docker.io` installation can be migrated without
deleting `/var/lib/docker` only with:

```yaml
runtime:
  docker:
    enabled: true
    legacy_package_migration_approved: true
```

If workloads are running, package migration or a daemon restart additionally
requires `restart.approved: true` and a named `maintenance_window`. Foundry
validates a candidate daemon configuration before applying it and restores the
previous configuration if activation fails.

## Dokploy single-manager Swarm

When `platform.dokploy.enabled` or `platform.swarm.enabled` is true, Runtime
initializes the narrow Swarm capability required before Networking. It records
the Cluster ID, Node ID, advertise address, and `single-manager` topology in a
root-only ownership manifest. An active Swarm without that manifest is treated
as external and is never adopted or force-left. V1 rejects multi-node and HA
topologies.

This exception does not make Runtime a general orchestrator. Infrastructure
Services owns Dokploy services; Networking owns attachable overlays.

## Ownership boundary

Runtime does not create Docker networks or application containers. Networking owns
environment networks. Infrastructure Services and Applications own their own
containers and persistent data.

Run Runtime alone with:

```bash
ansible-playbook -i inventory.yml playbook.yml --tags runtime
```

Run read-only final validation with:

```bash
ansible-playbook -i inventory.yml playbook.yml --tags runtime_result
```
