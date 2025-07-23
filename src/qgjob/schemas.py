from pydantic import BaseModel
from typing import Optional
from .models import JobStatus, JobTarget

class JobCreate(BaseModel):
    org_id: str
    app_version_id: str
    test_path: str
    priority: int = 5
    target: JobTarget

class JobResponse(BaseModel):
    id: str
    org_id: str
    app_version_id: str
    test_path: str
    priority: int
    target: JobTarget
    status: JobStatus
    created_at: str
    updated_at: str
    result: Optional[str] = None
    error_message: Optional[str] = None
