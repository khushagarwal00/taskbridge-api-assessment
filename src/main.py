from fastapi import FastAPI

from src.notifications.controllers.notification_controller import router as notification_router
from src.projects.controllers.project_controller import router as project_router

app = FastAPI(
    title="TaskBridge API",
    version="1.0.0"
)

@app.get("/")
def health():
    return {"status": "running"}


app.include_router(project_router)
app.include_router(notification_router)