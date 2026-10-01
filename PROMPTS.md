## Prompt 1

### Objective
Initial project implementation

### Prompt
Generate a Project model and a Project service with create, update status, get by team, and delete functions. Use a database.

### Outcome
Generated project_model.py and project_service.py.

### Action Taken
Reviewed and refactored the code.


## Prompt 2
Perform a senior engineer review of this code. Identify architectural issues, security flaws, validation gaps, and maintainability concerns.
make it one pager review and include - Issue
Location
Severity
Impact
Detection Method
Recommended Fix

Examples you'll likely find:
### Missing Validation
Severity : High 
Impact : Invalid project data accepted
Show more lines

#####Raw SQL
Severity:High
Impact :SQL injection risk
Show more lines


## Prompt 3
Create a production-ready FastAPI layered architecture project service using SQLAlchemy ORM with model, repository, service and controller layers. Include tenant isolation and validation.

## Prompt 4
Generate a technical specification for a Notification and Audit service integrating with a Project service.
Include:
Data Models

Audit entry –
id : UUID
project_id : UUID
event_type : string
actor_id : string
organization_id : string
old_state : JSON
new_state : JSON
timestamp : datetime

Notification – 
id : UUID
recipient_id : string
project_id : UUID
message : string
read : bool
created_at : datetime

## Prompt 5
Generate audit and notification models for FastAPI and SQLAlchemy.


## Prompt 6
1.Create Audit
POST /audit
2. Get Audit History 
GET /audit/{projectId}

3.Get notification 
GET /notifications/{userId}
4. Mark read 
PATCH /notifications/{id}/read
Create FastAPI routes for audit history, notification retrieval and mark-as-read operations.



## Prompt 7
Assessment specifically requires audit entries to be immutable
Do NOT create:
PUT /audit
DELETE /audit

## Prompt 8
Generate an impact analysis document for introducing a new audit event and storing actor IP address. Include database, API, model, service, testing and risk analysis sections


## Prompt 9
Generate pytest test cases for notification and audit services.
Create tests for:
1.	Notification sent to all team members
2.	Audit record created
3.	Audit immutable
4.	Date filter works



## Prompt 10
Generate a Mermaid architecture diagram for a FastAPI application containing Project, Notification and Audit services sharing a SQLite database.


## Prompt 11
Generate a Tool Strategy document for a GitHub Copilot assisted software engineering assessment.

Include:
- Overview
- Copilot features used
- Prompts used
- Strengths observed
- Limitations encountered
- Human review and remediation steps
- Examples of code that required modification
- Lessons learned
- Conclusion

Assume the project is a FastAPI application containing Project, Notification, and Audit services using SQLite and SQLAlchemy.


## Prompt 12
Generate a professional Pull Request description for a GitHub Copilot assisted FastAPI project called TaskBridge API.

The project includes:
- Project Service
- Notification Service
- Audit Service
- SQLite database
- SQLAlchemy ORM
- FastAPI REST APIs
- Pytest test suite

The PR should include:

1. Summary of Changes
2. Features Implemented
3. AI Assistance Disclosure
4. Code Review Findings and Remediation
5. Architectural Decisions
6. Testing Performed
7. Risks and Limitations
8. Future Improvements
9. Reviewer Checklist

Mention that initial Project model and Project service code were generated using GitHub Copilot, reviewed, documented in REVIEW.md, and refactored to improve
