from sqlalchemy import Column, String, Integer, DateTime, Text, Enum as SQLEnum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from enum import Enum

Base = declarative_base()

class JobStatus(str, Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class JobTarget(str, Enum):
    EMULATOR = "emulator"
    DEVICE = "device"
    BROWSERSTACK = "browserstack"

class Job(Base):
    __tablename__ = "jobs"
    
    id = Column(String, primary_key=True)
    org_id = Column(String, nullable=False, index=True)
    app_version_id = Column(String, nullable=False, index=True)
    test_path = Column(Text, nullable=False)
    priority = Column(Integer, default=5)
    target = Column(SQLEnum(JobTarget), nullable=False)
    status = Column(SQLEnum(JobStatus), default=JobStatus.QUEUED)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    result = Column(Text)
    error_message = Column(Text)
