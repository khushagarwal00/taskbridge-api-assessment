# TaskBridge Architecture

The FastAPI application exposes Project, Notification, and Audit APIs. All use the shared SQLAlchemy engine configured by `DATABASE_URL`, which defaults to `sqlite:///./taskbridge.db`.

```mermaid
flowchart LR
	Client[API Client] --> App[FastAPI Application]
	Auth[Trusted Authentication Context] -. tenant, user, permissions .-> App

	App --> ProjectAPI[Project Controller]
	App --> NotificationAPI[Notification Controller]
	App --> AuditAPI[Audit Endpoints]

	ProjectAPI --> ProjectService[Project Service]
	NotificationAPI --> NotificationService[Notification Service]
	AuditAPI --> AuditService[Audit Service Boundary]
	AuditService -. currently implemented within .-> NotificationService

	ProjectService --> ProjectRepository[Project Repository]
	NotificationService --> NotificationRepository[Notification Repository]
	AuditService --> NotificationRepository

	ProjectRepository --> SQLAlchemy[Shared SQLAlchemy Engine]
	NotificationRepository --> SQLAlchemy
	SQLAlchemy --> SQLite[(Shared SQLite Database)]

	SQLite --> Projects[(projects)]
	SQLite --> Notifications[(notifications)]
	SQLite --> AuditEntries[(audit_entries)]
```

Project, Notification, and Audit data use the same database engine and database file. Audit is shown as a separate logical responsibility; its current service methods and repository operations are implemented alongside Notification functionality. Project CRUD does not currently publish events directly to Notification or Audit services.
