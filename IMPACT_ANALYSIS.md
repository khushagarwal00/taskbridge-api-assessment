# Impact Analysis: Audit Event Type and Actor IP

## Summary

Adding an audit event type requires a defined event name and payload contract. This analysis uses `<domain>.<action>` as a placeholder until the name is confirmed. Recording actor IP requires a nullable `actor_ip` field and trusted server-side IP resolution. Audit entries remain append-only; no update or delete API is introduced.

## Database

- Add nullable `actor_ip VARCHAR(45)` to `audit_entries` for IPv4 and IPv6.
- Leave existing rows null; historical IPs cannot be safely reconstructed.
- Do not index IP unless an approved query use case requires it.
- The repository has no migration framework today. Choose a versioned migration approach and apply the additive schema change before deploying code that reads or writes the column.

## API

- Keep `POST /audit`; do not accept `actor_ip` from the request body.
- Derive IP from the direct client connection or trusted proxy metadata. Ignore forwarding headers from untrusted proxies.
- Include nullable `actor_ip` in audit responses; old records return `null`.
- Define and validate the new event type and payload. The current request schema accepts any non-empty event-type string, so an allowlist or producer contract is needed to prevent drift.
- Preserve existing organization scoping, audit permissions, and immutable audit behavior.

## Model

- Add nullable `actor_ip` to the SQLAlchemy `AuditEntry` model and read schema.
- Store a normalized address in a portable string column; validate with Python's `ipaddress` module.
- Keep event-type values compatible with existing records. If a registry is added, include the new type without invalidating historical values.

## Service

- Pass the server-derived IP through the audit creation service and repository; never trust a client-supplied value.
- Validate the new event's state snapshot and required fields at the service boundary.
- Permit null IP for system-generated events. Decide whether it is required for interactive user actions.
- Do not add audit update or delete operations.

## Testing

- Verify the new event type and payload validation, including unsupported values if an allowlist is used.
- Verify IPv4/IPv6 validation, persistence, and response serialization.
- Verify legacy entries remain readable with `actor_ip: null`.
- Verify body-supplied IP cannot override the trusted request IP, and untrusted forwarding headers are ignored.
- Retest organization isolation, permissions, and absence of audit update/delete routes.
- Test migration against existing data before rollout.

## Risks

| Risk | Mitigation |
| --- | --- |
| Spoofed forwarded IP | Trust forwarding headers only from configured proxies; otherwise use the connection peer. |
| Privacy or retention obligations | Document purpose, access, retention, and deletion policy for IP data; avoid logging it unnecessarily. |
| Existing rows have no IP | Keep the field nullable; do not fabricate historical values. |
| Event-type inconsistency | Confirm the event name and payload, then validate against a shared contract. |
| Schema/code rollout mismatch | Apply the additive migration before deploying code that depends on `actor_ip`. |
| System events lack client IP | Permit null for automated actions and define policy for user-originated events. |

## Decisions Required

1. Confirm the exact event type and its state-transition semantics.
2. Decide whether IP is mandatory for interactive events or best-effort.
3. Confirm the trusted proxy/IP source and IP retention policy.
4. Select and document the migration mechanism.
