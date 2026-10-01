# Notification and Audit Service Technical Specification

## 1. Purpose

Define a Notification and Audit service that consumes lifecycle events from the Project service. The service provides durable, tenant-scoped audit history and user-facing notifications without making Project API availability depend on notification delivery.

This document specifies the target integration. The current repository contains a synchronous FastAPI Project service and an empty `src/notifications/` package; it does not yet contain a broker, authentication implementation, user directory, or notification delivery provider.

## 2. Goals and Non-goals

### Goals

- Record auditable Project create, status-change, and delete actions.
- Deliver notifications asynchronously and at least once, with duplicate-safe processing.
- Preserve tenant isolation in event publication, persistence, querying, and delivery.
- Ensure Project mutations do not succeed without a durable record of their corresponding event.
- Expose APIs for listing audit records and a user's notifications, and for marking notifications read.
- Support retry, replay, operational monitoring, and configurable retention.

### Non-goals

- Replacing or owning Project data or Project CRUD operations.
- Defining authentication, authorization, or team membership systems.
- Sending arbitrary user-authored messages, push notifications, or realtime websocket updates in the initial release.
- Treating notification delivery as part of the Project mutation's synchronous response.
- Allowing audit records to be modified or deleted through public APIs.

## 3. Existing Project Service Contract

The current Project API derives `team_id` from trusted request state. Project data is tenant-scoped by `team_id`. Create, status update, and delete operations run inside SQLAlchemy database transactions. The current Project model has integer `id` and `team_id`, plus `name` and `status`; it has no actor identity, recipients, or event history.

The data models below use UUID `project_id` and `organization_id`, as required by this service contract. Before implementation, the Project service must migrate its project and organization identifiers to UUIDs, or an explicit, stable identifier-mapping contract must be introduced. Do not cast integer IDs to UUIDs or silently treat `team_id` as a UUID. `organization_id` is the canonical tenant identifier for the new service and maps to the authenticated Project tenant only through trusted service context.

The integration must preserve those boundaries:

- Never accept `team_id` from an untrusted event field as proof of ownership. It is event context established by the authenticated Project service.
- Do not query Project tables from the Notification and Audit service.
- Include enough safe event data to build audit records and notifications without a synchronous callback to Project.
- Do not assume a `user_id` or recipient can be derived from the current Project schema. Recipient resolution requires a trusted identity or membership contract.

## 4. Service Boundaries and Data Flow

1. An authenticated caller invokes a Project mutation.
2. The Project service validates tenant context and performs the data change.
3. In the same database transaction, Project writes a corresponding outbox event.
4. An outbox publisher reads committed, unpublished rows and publishes them to the event transport. Publishing may be retried.
5. The Notification and Audit consumer validates the event, deduplicates by `event_id`, appends an audit record, and creates zero or more notification records in its own transaction.
6. A delivery worker sends eligible notifications through configured providers and records delivery state. Provider failure does not change Project state or audit history.

The outbox is the reliability boundary: a committed Project mutation must have its outbox event committed atomically. Do not publish directly to a broker before the Project transaction commits, and do not make a broker call inside the request transaction.

### Deployment

The initial deployment may run the API, publisher, consumer, and delivery worker as separate processes or separately managed worker roles. They may share a deployable codebase, but the Notification and Audit service owns its tables and APIs. Event transport and database technology are deployment decisions; the contract below is transport-neutral.

## 5. Project Events

### Event envelope

Events use a versioned JSON envelope. Timestamps are UTC RFC 3339 strings. The transport must preserve the complete envelope and support a stable event key.

```json
{
	"event_id": "UUID",
	"event_type": "project.created",
	"schema_version": 1,
	"occurred_at": "2026-10-01T12:00:00Z",
	"producer": "project-service",
	"organization_id": "UUID",
	"actor_id": "user-123",
	"correlation_id": "request-or-trace-id",
	"data": {
		"project_id": "UUID",
		"name": "Migration",
		"status": "active"
	}
}
```

`actor_id` and `correlation_id` are nullable when unavailable. The Project service must obtain actor identity from trusted authentication context, never from a caller-controlled body field. `organization_id` is a UUID and must be derived from trusted tenant context, never accepted from an untrusted event producer or caller.

### Event types and payloads

- `project.created`: `project_id`, `name`, and `status` after creation.
- `project.status_changed`: `project_id`, `previous_status`, and `status` after the update.
- `project.deleted`: `project_id`, `name`, and `status` immediately before deletion. These values are a minimal historical snapshot; no Project lookup is possible after deletion.

Each event is immutable after publication. Include only fields needed for audit and notification. Do not place credentials, authorization data, or sensitive free-form content in event payloads. If status updates become no-ops when the value is unchanged, they should not emit an event; this behavior must be consistent and tested.

### Outbox requirements

The Project service owns an outbox table with at least:

- `event_id` (primary key / globally unique identifier)
- `event_type`, `schema_version`, `organization_id`, and serialized envelope
- `created_at`, `published_at`, `attempt_count`, and `last_error` (sanitized)

Outbox writes occur in the same transaction as Project insert/update/delete. The publisher claims rows safely across concurrent workers, publishes with `event_id` as the transport message key, and marks rows published only after broker acknowledgement. A crash after broker acknowledgement but before marking the row may cause redelivery; consumers must deduplicate. Outbox retention and cleanup must not delete unpublished rows.

## 6. Notification and Audit Data

The service owns the following logical records:

### Audit entry

| Field | Type | Requirements |
| --- | --- | --- |
| `id` | UUID | Primary key and idempotency key; derived from or uniquely associated with the source `event_id`. |
| `project_id` | UUID | Project identifier from the event snapshot. |
| `event_type` | string | For example, `project.created`, `project.status_changed`, or `project.deleted`. |
| `actor_id` | string | Authenticated actor identifier; use a stable system actor identifier for automated actions. |
| `organization_id` | UUID | Trusted organization/tenant scope for every read and write. |
| `old_state` | JSON | Previous state; nullable for creation or when not applicable. |
| `new_state` | JSON | Resulting state; nullable for deletion or when not applicable. |
| `timestamp` | datetime | Event occurrence time in UTC. |

Audit entries are immutable and append-only. The API MUST NOT expose `PUT /audit`, `DELETE /audit`, or update/delete operations for individual audit records. Corrections are represented by a later event or an administrative, separately audited process; ordinary application APIs cannot update or delete entries. Store `event_id`, `correlation_id`, `producer`, `schema_version`, and `recorded_at` as additional ingestion metadata where needed for deduplication and operations. Enforce uniqueness for the source event so redelivery cannot create a second audit entry.

For create, `old_state` is null and `new_state` contains the created project snapshot. For status change, `old_state` and `new_state` contain the relevant before/after state. For delete, `old_state` contains the last project snapshot and `new_state` is null.

### Notification

| Field | Type | Requirements |
| --- | --- | --- |
| `id` | UUID | Primary key. |
| `recipient_id` | string | Recipient resolved through the trusted, tenant-scoped identity/membership contract. |
| `project_id` | UUID | Project identifier from the source event. |
| `message` | string | Concise, user-safe message; do not include sensitive event payloads. |
| `read` | bool | Defaults to `false`; changes to `true` through an idempotent read action. |
| `created_at` | datetime | Notification creation time in UTC. |

Notification records must be scoped to the authenticated recipient and organization. Since this requested model does not include `organization_id`, either `recipient_id` must be an organization-scoped identity or the persisted model must add `organization_id` before users can receive notifications in multiple organizations. Do not rely on recipient-only filtering when recipient IDs are globally shared.

Delivery attempts should be stored separately or as bounded attempt metadata. Do not store provider credentials, full provider responses, or unnecessary personal data in notification rows or logs.

Notification creation is rule-driven. Initial rules may notify configured project members for project creation, status changes, and deletion. The service must resolve recipients through an authenticated, tenant-scoped membership/identity contract. Until that contract exists, audit ingestion remains enabled and notifications are not generated; do not guess recipients or broadcast to every tenant user by default.

## 7. APIs

All APIs use the application's established authentication and error conventions. Organization and user identity are derived from trusted authentication context, not request parameters. The endpoint paths below are unversioned as specified; any version prefix should be applied consistently at the API gateway.

### Create audit entry

`POST /audit`

The body supplies `event_id`, `project_id`, `event_type`, optional `old_state` and `new_state`, and an ISO 8601 `timestamp`. The authenticated actor and `organization_id` are derived from trusted request context, not the body. Requires audit-write permission. Repeated submissions with the same event ID in the same organization return the existing entry; a conflicting cross-organization event ID returns `409`.

Audit entries cannot be updated or deleted. `PUT /audit`, `DELETE /audit`, and per-entry update/delete routes are intentionally not defined.

### Get project audit history

`GET /audit/{projectId}`

The project ID is a UUID. Query parameters: `offset` (default 0) and `limit` (default 50, maximum 100). Returns records for the authenticated organization only, ordered by `timestamp DESC` then `id DESC`. Audit access requires audit-read permission; ordinary organization authentication alone is insufficient. Another organization's records are never disclosed.

### Get user notifications

`GET /notifications/{userId}`

Returns notifications for the authenticated user only, scoped to the active organization. A mismatched user ID returns the standard not-found response. Query parameters: `unread_only` (default false), `offset` (default 0), and `limit` (default 50, maximum 100). Results are ordered newest first.

### Mark notification read

`PATCH /notifications/{id}/read`

Sets `read` to `true` and is idempotent. The lookup and update must constrain both `notification_id` and authenticated recipient/tenant. Return the project's standard not-found response for missing or unauthorized records, without disclosing cross-tenant existence.

### Response and errors

Use explicit request/response schemas. Do not expose ORM objects, internal retry state, provider details, or raw event envelopes through end-user APIs. Validate pagination and timestamp ranges. Use consistent structured error bodies and standard HTTP status codes; reads return `200`, a successful read-state update returns `200` (or `204` if adopted consistently by the API), and invalid filters return `422`.

## 8. Delivery and Reliability

- Delivery is asynchronous and at least once. Exactly-once delivery to external providers is not assumed.
- Consumers use a unique constraint on `event_id`; duplicate events must not create duplicate audit records or duplicate logical notifications.
- Audit persistence and notification creation for one event occur atomically in the Notification and Audit database. Provider delivery occurs after commit.
- Retry transient transport and provider failures with bounded exponential backoff and jitter. Classify permanent validation failures separately.
- After the configured retry limit, route events to a dead-letter queue or equivalent durable quarantine with alerting and an operator replay path.
- Replaying an event preserves its `event_id` and remains idempotent. Schema incompatibilities must be quarantined rather than silently dropped.
- Use bounded worker concurrency and provider rate limits. A slow provider must not block event ingestion or other providers.
- On delete, the audit snapshot remains available and notification generation must not require a Project read.

## 9. Security, Privacy, and Tenant Isolation

- Authenticate service-to-service publication using workload identity, mTLS, or an equivalent managed credential. Authorize the Project producer explicitly.
- Validate producer, event type, schema version, required fields, and tenant context before persistence.
- Tenant scope every audit query and write. User scope every notification query and state mutation by both tenant and authenticated recipient.
- Do not trust tenant, actor, or recipient values from public API payloads. Bind them to verified service or authentication context.
- Audit reads are privileged and should themselves produce an access log/audit event without recursively creating user notifications.
- Encrypt transport and stored sensitive data according to platform policy. Minimize event data and define retention/deletion behavior for user-linked notifications separately from immutable audit retention obligations.
- Sanitize event/provider errors before persistence or logging. Never log tokens, authorization headers, message contents containing sensitive data, or provider secrets.

## 10. Observability and Operations

Emit structured logs and metrics with service, event type, event ID, tenant ID where permitted, and correlation ID. Never use project names or user identifiers as unbounded metric labels.

Minimum metrics and alerts:

- Outbox oldest-unpublished age, row count, publish attempts, and publish failures.
- Consumer lag, processing rate, validation failures, duplicates, and dead-letter count.
- Notification delivery attempts, success/failure rate, provider latency, and oldest pending notification age.
- API request latency/error rate and authorization denials.

Provide health/readiness checks that distinguish process health from dependencies needed to serve traffic. Operators need documented procedures to inspect quarantined events, replay safely, pause a provider, and drain queues during deployment.

## 11. Data Lifecycle and Migration

- Add the Project outbox schema through a backward-compatible database migration before enabling publication.
- Add Notification and Audit tables with indexes for `(organization_id, timestamp)`, `(organization_id, project_id, timestamp)`, `(recipient_id, created_at)`, and a unique source `event_id` constraint for audit idempotency. If notifications persist an `organization_id` extension, include it in the recipient index.
- Deploy consumers before enabling event publication, then enable the publisher with monitoring. This prevents initial events from being published without a consumer.
- Define separate configurable retention periods for outbox rows after successful publication, notification delivery metadata, user-facing notifications, and audit records. Unpublished outbox rows are never aged out automatically.
- Audit retention must follow applicable product and regulatory policy. No fixed legal retention period is assumed by this specification.
- Keep event schema changes additive where possible. Consumers must support the current and previous event versions during rolling deployment; incompatible changes require a new schema version and a migration plan.

## 12. Testing and Acceptance Criteria

Implementation is acceptable when tests demonstrate:

- Project create, status change, and delete persist exactly one matching outbox event in the same transaction; rollback persists neither mutation nor event.
- Publisher retries safely after failure, and a crash/retry can result in redelivery without duplicate audit or notification records.
- Invalid or unsupported events are quarantined and observable; transient failures are retried.
- Audit and notification endpoints enforce tenant and recipient isolation, including attempts to access another tenant's records.
- Audit records cannot be changed through public APIs; marking a notification read is idempotent and cannot affect another user's notification.
- Project API success does not depend on broker or notification-provider availability after the outbox commit.
- Event snapshots for deletion remain usable without a live Project row.
- Pagination, filter validation, ordering, and authorization requirements behave as specified.

Unit tests should cover schemas, event conversion, idempotency, and recipient rules. Integration tests should use deterministic database and broker/provider fakes; no test should require live external services.

## 13. Decisions Required Before Implementation

- Select event transport and operational ownership (managed broker, database-backed queue, or equivalent).
- Select Notification and Audit database ownership and backup/restore policy.
- Define the trusted identity and membership contract for actor capture, audit-reader roles, and notification recipients.
- Decide initial recipient rules and supported delivery channels. In-app notifications are the lowest-dependency starting point.
- Set audit, notification, and outbox retention periods according to product and compliance needs.
- Confirm route prefix, audit-read permissions, and whether the service is deployed independently or as a worker role alongside the API.
