# Copilot Instructions

## Project Context

This is a Python FastAPI multi-service SaaS application. Preserve the repository's existing conventions and service boundaries. Avoid introducing new frameworks, dependencies, or architectural patterns unless the task requires them.

## Coding Standards

- Use Python type hints for public functions, service interfaces, and data models.
- Keep functions and modules focused; use clear names and avoid hidden side effects.
- Follow existing formatting, linting, and import conventions. Prefer standard-library solutions where practical.
- Use Pydantic models for request and response validation, and SQLAlchemy patterns already established in the project.
- Make configuration explicit and environment-based. Do not hardcode credentials, secrets, or environment-specific values.
- Handle expected errors explicitly. Do not swallow exceptions or return success-shaped defaults after failures.
- Keep changes scoped to the requested behavior and update relevant tests and documentation.

## Layered Architecture

- Keep HTTP concerns in FastAPI routers: parse and validate input, apply dependencies, call application logic, and translate results to HTTP responses.
- Put use-case orchestration in service or application modules. Keep business rules out of routers and ORM models.
- Keep persistence and external-system access behind repository or client boundaries where the project uses them.
- Keep schemas, domain logic, and infrastructure concerns separate. Avoid circular imports and cross-service access to another service's internals.
- Share code only for stable, genuinely common concerns. Prefer explicit service contracts over tightly coupling services to each other's database models.
- Make transaction ownership and external side effects clear; do not hide network or database operations inside validation or model serialization.

## Security and Tenant Isolation

- Treat all input as untrusted. Validate and constrain request data, and use parameterized database operations.
- Authenticate requests and enforce authorization for every protected operation. Authentication alone does not grant access to a resource.
- Derive the active tenant from trusted authenticated context, never from an unverified request field or header.
- Scope every tenant-owned read, update, and delete by the active tenant. Include tenant ownership in lookups and writes, and prevent cross-tenant references.
- Apply tenant scoping in background jobs, scheduled tasks, caches, exports, and external-service calls as well as HTTP handlers.
- Do not expose whether another tenant's resource exists. Return the project's standard not-found or authorization response.
- Store secrets in approved secret management or environment configuration. Never log credentials, tokens, session identifiers, or sensitive personal data.
- Use least-privilege permissions, safe defaults, and explicit CORS and trusted-host configuration where applicable.

## API Conventions

- Use resource-oriented routes and the project's established versioning and naming conventions.
- Define explicit Pydantic request and response schemas; do not expose ORM objects or internal fields directly.
- Return consistent status codes and error response shapes. Use 201 for created resources, 204 for successful empty responses, and appropriate 4xx/5xx responses.
- Keep pagination, filtering, sorting, and error formats consistent across endpoints. Bound page sizes and validate filter inputs.
- Make state-changing operations safe and predictable. Use idempotency controls where retries could duplicate important effects.
- Document endpoint behavior, authentication requirements, and meaningful error cases using FastAPI's OpenAPI metadata.
- Avoid breaking API changes without an explicit compatibility or migration plan.

## Testing Standards

- Use pytest and the test patterns already present in the repository.
- Add or update tests for changed behavior, including success cases, validation failures, authorization failures, and relevant edge cases.
- Test tenant isolation explicitly: verify one tenant cannot read, modify, or delete another tenant's data.
- Keep tests deterministic and independent. Avoid relying on live external services; use fixtures, dependency overrides, or mocks at integration boundaries.
- Test API behavior through the HTTP client where appropriate, and test business logic at its owning layer.
- Ensure tests clean up database state and do not depend on execution order.

## Logging and Observability

- Use the application's configured logger; do not use `print` for runtime diagnostics.
- Log useful operational context such as service, operation, request or trace ID, and tenant ID only when safe and permitted.
- Never log secrets, authorization headers, raw credentials, or sensitive request and response bodies.
- Keep logs structured and consistent with existing observability tooling. Use appropriate levels: debug for diagnostic detail, info for significant operations, warning for recoverable problems, and error for failures needing attention.
- Include exception context when logging failures, but avoid logging the same exception at multiple layers without adding useful information.
- Do not use logs as a substitute for clear API errors, metrics, or audit events.

## Changes and Verification

- Before changing code, inspect the owning service and nearby tests to follow local patterns.
- Prefer focused changes over broad refactors.
- Run the most relevant tests after a change, then the full test suite when practical.
- Report checks that could not be run and any assumptions that affect the implementation.