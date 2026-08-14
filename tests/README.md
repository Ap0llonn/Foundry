# Foundry acceptance tests

This directory is the central acceptance-test contract for Foundry. Tests are
split by risk so the default suite never modifies a managed VM.

## Test tiers

| Tier | Host access | Mutation | Purpose |
|---|---:|---:|---|
| `static` | No | No | Controller, syntax, policy fixtures, and negative configuration tests. |
| `live` | Yes | No | Check-mode convergence and read-only final-state validation. |
| `fresh` | Yes | Yes | First convergence and second-run idempotence on a disposable VM only. |

The normative requirements are in [acceptance-criteria.md](acceptance-criteria.md).
The detailed scenarios and their automation status are in
[test-cases.yml](test-cases.yml). Destructive Docker-network and MinIO evidence
is tracked separately in
[networking-v1-certification.md](networking-v1-certification.md).

## Run the tests

Activate the project controller environment first:

```bash
source .venv/bin/activate
```

Run tests that cannot contact a VM:

```bash
python tests/run_acceptance.py static
```

Run non-mutating tests against the configured VM:

```bash
python tests/run_acceptance.py live \
  --inventory inventory.yml \
  --config config.yml
```

The live tier runs the Identity and Security slices in check mode, then runs
their read-only result validations. Every run must report `changed=0`.

Run first-convergence and idempotence tests only against a disposable VM:

```bash
python tests/run_acceptance.py fresh \
  --inventory /absolute/path/to/disposable-inventory.yml \
  --config /absolute/path/to/test-config.yml \
  --confirm FOUNDRY-EPHEMERAL-VM
```

The runner refuses the repository's normal `inventory.yml`, requires the
explicit confirmation string, and requires this inventory marker:

```yaml
foundry_test_target: ephemeral
```

The fresh config must enable at least one Infrastructure Services component.
The runner converges Identity, Security, Runtime, Networking, and Infrastructure
Services twice and requires `changed=0` on the second complete pass. Persistence,
reboot, external probes, and failure injection remain separately tracked until
their dedicated automation is implemented.

## Result semantics

- A positive fixture must be accepted.
- A negative fixture must be rejected before host mutation.
- An unexpected acceptance is a failed test.
- `live` and the second `fresh` convergence must report zero changes.
- A skipped acceptance criterion is not a pass. Its status remains `manual` or
  `planned` in `test-cases.yml` until executable evidence exists.

## Adding a regression test

Every production defect should add:

1. A stable acceptance-criteria identifier.
2. A test case in `test-cases.yml` describing setup, action, and expected result.
3. A fixture or playbook that reproduces the defect when safe to automate.
4. A negative case proving that unsafe state is rejected.
5. An idempotence assertion when the scenario changes managed state.

Fixtures must contain only synthetic public data. Password hashes, private SSH
keys, tokens, production IPs, and Vault passwords must never be committed here.
