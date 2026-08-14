# Foundry Security role

The Security role manages the VM firewall, SSH daemon policy, Fail2ban, and
automatic security updates. `security.ssh.port` is always the **desired** port;
you do not configure the current port.

## Default ports

Foundry uses the conventional default of `22` for a new VM's SSH bootstrap
connection. If no custom SSH port is needed, keep:

```yaml
security:
  ssh:
    port: 22
```

Port `80` is the conventional default for HTTP, but the Security role does not
open it automatically. The application or infrastructure-service layer must
declare an HTTP firewall requirement when an HTTP service is actually deployed.

## Changing the SSH port

Only change the desired value in `config.yml`:

```yaml
security:
  ssh:
    enabled: true
    port: 2222
```

Do not add `ansible_port` to `inventory.yml` for a normal Foundry-managed
migration. Foundry performs this sequence:

1. Connect through the last validated port, with port `22` as bootstrap fallback.
2. Open the desired port in UFW.
3. Configure `sshd` temporarily with both the current and desired listeners.
4. Validate the complete SSH configuration and reload the daemon.
5. Confirm an SSH banner and establish a fresh authenticated Ansible connection
   through the desired port.
6. Switch the live Ansible connection state to the desired port.
7. Replace the temporary SSH policy with the desired port only.
8. Remove the temporary old-port UFW rule.
9. Verify from the controller that the old port no longer accepts connections.
10. Persist the validated port in `.foundry/state/<inventory-host>.yml`.

The controller state directory is intentionally ignored by Git. It is runtime
state, not desired infrastructure configuration.

If the fresh authenticated connection fails, the play stops and reconnects to
the previous port. Both temporary listeners and firewall rules remain available
for safe recovery. A later run can resume the migration.

## Supported migration paths

- First bootstrap: `22 -> 22`
- Default to custom: `22 -> 2222`
- Custom to another custom port: `2222 -> 2200`
- Custom back to default: `2222 -> 22`

For emergency recovery, `ansible_port` in inventory remains a possible initial
candidate when no saved Foundry state exists. Under normal operation, it is not
required.

## Validation commands

Syntax and read-only convergence checks:

```bash
ansible-playbook -i inventory.yml playbook.yml --syntax-check
ansible-playbook -i inventory.yml playbook.yml --check --diff --tags security
```

Apply a configured migration:

```bash
ansible-playbook -i inventory.yml playbook.yml --tags security
```

After a successful custom-port migration, Foundry will use the saved endpoint on
the next run without any inventory edit.
