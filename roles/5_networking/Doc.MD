# Foundry environment networking

Role 5 executes after Runtime, validates its published Docker contract, and
creates one authoritative network per Foundry environment. It does not install Docker,
modify the Docker daemon, open host ports, configure DNS, or deploy workloads.

## Configuration

```yaml
project:
  name: my-project

environments:
  - name: dev
  - name: prod
    network:
      name: custom-prod-network

networking:
  stale_network_policy: report
```

This resolves to:

```yaml
foundry_resolved_networks:
  dev: foundry-my-project-dev
  prod: custom-prod-network
```

Workload roles consume `foundry_resolved_networks`; they must not reconstruct
the naming rule or create environment networks themselves. The mapping is also
persisted at `/var/lib/foundry/networking/resolved-networks.yml` for a later role
or a tagged infrastructure-service run.

## Ownership and collisions

Every owned network has these labels:

```text
foundry.managed=true
foundry.project=<project>
foundry.environment=<environment>
foundry.resource=environment-network
```

A matching, compatible network is reused. A same-name network without all
matching ownership labels is external and causes a safe failure. Name prefixes
are never treated as proof of ownership. Foundry discovers stale networks only
through labels scoped to the current project and resource type.

`stale_network_policy` supports:

- `report`: default; report stale owned networks without mutation.
- `fail`: reject stale owned state before creating or removing anything.
- `remove_unused`: remove only stale owned networks with zero attachments;
  attached containers cause failure and are never disconnected.

Changing a custom network name therefore creates a migration boundary. The old
network remains until workloads leave it and lifecycle policy permits removal.

## Isolation contract

Ordinary hosts use the Docker `bridge` driver. When Dokploy or its narrow Swarm
dependency is enabled, Runtime initializes Swarm first and Networking creates
`overlay`, Swarm-scoped, attachable environment networks. This lets standalone
infrastructure containers and future Dokploy services consume the same resolved
network names. Networks are not `internal` by default, so
containers retain ordinary outbound access. Role validation rejects a labeled
Foundry workload attached to a network whose environment label does not match.
Unlabeled external containers are observed but not claimed or modified.

An existing same-name bridge is incompatible with an overlay declaration.
Foundry may replace it only when `overlay_migration_approved: true`, every
ownership label matches, and it has zero attachments. Foundry never disconnects
workloads; an attached bridge fails and requires a separate workload migration.

Role 5 never manages UFW or `network.exposure`. Docker host publishing and
external exposure remain separate explicit contracts.

## Runtime dependency

Role 6 owns the official Docker repository, exact package versions, Compose,
daemon configuration, socket security, storage, and service health. Role 5
requires that complete contract before touching networks:

```bash
ansible-playbook playbook.yml --tags networking
```

Foundry does not add human users to the privileged `docker` group. Networking
tasks access the certified daemon through `become: true`.

Docker can create packet-filtering rules independently of UFW. Role 5 and the
current MinIO implementation publish no host ports; future workload port
publishing must be coordinated explicitly with `network.exposure` and the
Docker `DOCKER-USER` policy rather than assuming UFW alone controls it.

Use `tests/networking-v1-certification.md` for isolation, stale-state,
restart/reboot, external-preservation, and idempotence evidence.
