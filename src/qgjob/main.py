from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from .database import get_db, create_tables
from .models import Job, JobStatus
from .schemas import JobCreate, JobResponse
from .job_queue import JobQueue
import uuid
import logging
from typing import Optional, List
from datetime import datetime, timezone
import os

# Configure production logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('qgjob.log')
    ]
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="QualGent Job Orchestrator",
    description="Production-ready job orchestration system for AppWright tests",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

job_queue = JobQueue()

@app.on_event("startup")
async def startup_event():
    logger.info("Starting QualGent Job Orchestrator in production mode")

    # Validate required environment variables
    required_env_vars = [
        "DATABASE_URL",
        "REDIS_URL",
        "BROWSERSTACK_USERNAME",
        "BROWSERSTACK_ACCESS_KEY"
    ]

    missing_vars = []
    for var in required_env_vars:
        if not os.getenv(var) or os.getenv(var) == f"your_{var.lower()}":
            missing_vars.append(var)

    if missing_vars:
        error_msg = f"Missing required environment variables: {', '.join(missing_vars)}"
        logger.error(error_msg)
        logger.error("Please configure all required environment variables before starting the application")
        raise RuntimeError(error_msg)

    # Create database tables
    try:
        create_tables()
        logger.info("Database initialization completed successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise

    logger.info("QualGent Job Orchestrator started successfully")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("QualGent Job Orchestrator shutting down")

@app.post("/jobs", response_model=dict)
async def submit_job(job: JobCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    try:
        job_id = str(uuid.uuid4())
        
        db_job = Job(
            id=job_id,
            org_id=job.org_id,
            app_version_id=job.app_version_id,
            test_path=job.test_path,
            priority=job.priority,
            target=job.target,
            status=JobStatus.QUEUED
        )
        
        db.add(db_job)
        db.commit()
        
        job_queue.enqueue_job({
            "id": job_id,
            "org_id": job.org_id,
            "app_version_id": job.app_version_id,
            "test_path": job.test_path,
            "priority": job.priority,
            "target": job.target.value
        })
        
        logger.info(f"Job {job_id} submitted by org {job.org_id} for app {job.app_version_id}")
        
        return {
            "job_id": job_id,
            "status": "queued",
            "message": "Job submitted successfully"
        }
        
    except Exception as e:
        logger.error(f"Error submitting job: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to submit job: {str(e)}")

@app.get("/jobs/{job_id}", response_model=dict)
async def get_job_status(job_id: str, db: Session = Depends(get_db)):
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        response = {
            "job_id": job.id,
            "status": job.status.value,
            "org_id": job.org_id,
            "app_version_id": job.app_version_id,
            "test_path": job.test_path,
            "priority": job.priority,
            "target": job.target.value,
            "created_at": job.created_at.isoformat(),
            "updated_at": job.updated_at.isoformat()
        }
        
        if job.result:
            import json
            response["result"] = json.loads(job.result)
        
        if job.error_message:
            response["error_message"] = job.error_message
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting job status for {job_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get job status: {str(e)}")

@app.get("/jobs", response_model=List[dict])
async def list_jobs(
    org_id: Optional[str] = None,
    status: Optional[str] = None,
    app_version_id: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    try:
        query = db.query(Job)
        
        if org_id:
            query = query.filter(Job.org_id == org_id)
        if status:
            query = query.filter(Job.status == status)
        if app_version_id:
            query = query.filter(Job.app_version_id == app_version_id)
        
        jobs = query.order_by(Job.created_at.desc()).offset(offset).limit(limit).all()
        
        return [
            {
                "job_id": job.id,
                "status": job.status.value,
                "org_id": job.org_id,
                "app_version_id": job.app_version_id,
                "test_path": job.test_path,
                "priority": job.priority,
                "target": job.target.value,
                "created_at": job.created_at.isoformat(),
                "updated_at": job.updated_at.isoformat()
            }
            for job in jobs
        ]
        
    except Exception as e:
        logger.error(f"Error listing jobs: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list jobs: {str(e)}")

@app.delete("/jobs/{job_id}")
async def cancel_job(job_id: str, db: Session = Depends(get_db)):
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        if job.status in [JobStatus.COMPLETED, JobStatus.FAILED]:
            raise HTTPException(status_code=400, detail="Cannot cancel completed or failed job")
        
        job.status = JobStatus.FAILED
        job.error_message = "Job cancelled by user"
        job.updated_at = datetime.now(timezone.utc)
        db.commit()
        
        job_queue.update_job_status(job_id, JobStatus.FAILED)
        
        logger.info(f"Job {job_id} cancelled")
        
        return {"message": "Job cancelled successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling job {job_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to cancel job: {str(e)}")

@app.get("/health")
async def health_check():
    try:
        queue_size = job_queue.get_queue_size()
        return {
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "queue_size": queue_size,
            "service": "QualGent Job Orchestrator"
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(status_code=503, detail="Service unhealthy")

@app.get("/metrics")
async def get_metrics(db: Session = Depends(get_db)):
    try:
        total_jobs = db.query(Job).count()
        queued_jobs = db.query(Job).filter(Job.status == JobStatus.QUEUED).count()
        processing_jobs = db.query(Job).filter(Job.status == JobStatus.PROCESSING).count()
        completed_jobs = db.query(Job).filter(Job.status == JobStatus.COMPLETED).count()
        failed_jobs = db.query(Job).filter(Job.status == JobStatus.FAILED).count()
        
        queue_size = job_queue.get_queue_size()
        
        return {
            "total_jobs": total_jobs,
            "queued_jobs": queued_jobs,
            "processing_jobs": processing_jobs,
            "completed_jobs": completed_jobs,
            "failed_jobs": failed_jobs,
            "queue_size": queue_size,
            "success_rate": (completed_jobs / total_jobs * 100) if total_jobs > 0 else 0
        }
        
    except Exception as e:
        logger.error(f"Error getting metrics: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get metrics: {str(e)}")

@app.get("/jobs/{job_id}/retry")
async def retry_job(job_id: str, db: Session = Depends(get_db)):
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        if job.status != JobStatus.FAILED:
            raise HTTPException(status_code=400, detail="Can only retry failed jobs")
        
        job.status = JobStatus.QUEUED
        job.error_message = None
        job.updated_at = datetime.now(timezone.utc)
        db.commit()
        
        job_queue.enqueue_job({
            "id": job.id,
            "org_id": job.org_id,
            "app_version_id": job.app_version_id,
            "test_path": job.test_path,
            "priority": job.priority,
            "target": job.target.value
        })
        
        logger.info(f"Job {job_id} queued for retry")
        
        return {"message": "Job queued for retry"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrying job {job_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retry job: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=int(os.getenv("PORT", 8000)),
        log_level=os.getenv("LOG_LEVEL", "info").lower()
    )
