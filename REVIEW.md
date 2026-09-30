# Code Review

## Findings

### Tenant identity is caller-controlled
**Location:** `src/projects/project_service.py` — `create_project`, `update_project_status`, `get_projects_by_team`, `delete_project`  
**Severity:** High  
**Impact:** Operations filter by `team_id`, but the service does not verify that the caller is authorized for that team. If an untrusted caller can supply the ID, cross-tenant reads or changes are possible.  
**Detection Method:** Trace `team_id` from future API entry points; test with a project belonging to another team.  
**Recommended Fix:** Derive the active team from authenticated context and verify membership before service calls. Preserve tenant scoping in every read and mutation.

### Project inputs are not validated
**Location:** `src/projects/project_service.py` — `create_project`, `update_project_status`; `src/projects/project_model.py` — `Project`  
**Severity:** High  
**Impact:** Empty or oversized names and arbitrary status values can be persisted, creating invalid or inconsistent project data.  
**Detection Method:** Try blank/over-limit names and unknown statuses; inspect for request and domain validation.  
**Recommended Fix:** Add explicit schema and service validation, normalize names, and constrain status to supported values. Add database constraints for invariants that must always hold.

### No project API security boundary is present
**Location:** `src/main.py`; `src/projects/project_service.py`  
**Severity:** Medium  
**Impact:** The app currently exposes only a health endpoint. Project operations have no visible request schemas, authentication, authorization, or consistent HTTP error mapping, leaving these requirements undefined before exposure.  
**Detection Method:** Inspect registered routes and dependencies; `src/main.py` defines only `/`.  
**Recommended Fix:** Before exposing project operations, add request/response schemas, authentication and authorization dependencies, and consistent mapping of service outcomes to HTTP responses.

### Database failures have no explicit transaction handling
**Location:** `src/projects/project_service.py` — `db.commit()` calls  
**Severity:** Medium  
**Impact:** A commit failure propagates without explicit rollback handling. If the session is reused, subsequent operations may fail until it is rolled back.  
**Detection Method:** Trigger a database failure during commit and verify transaction/session recovery.  
**Recommended Fix:** Define transaction ownership and ensure failed transactions are rolled back; translate expected persistence failures at the application/API boundary.

### Raw SQL injection
**Location:** `src/projects/project_service.py`  
**Severity:** Informational (no finding)  
**Impact:** No raw SQL or string-interpolated query was found; the project queries use SQLAlchemy expressions.  
**Detection Method:** Search for textual SQL, direct `execute` calls, and interpolated query strings.  
**Recommended Fix:** No change indicated. Continue using SQLAlchemy expressions or bound parameters if raw SQL is introduced.

## Review Gaps

No tests were present in the inspected workspace. Add service tests for tenant scoping, validation, missing projects, and database failures.
