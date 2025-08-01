import time
import json
import logging
import os
import sys
from typing import Optional
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import sessionmaker
from .database import engine, redis_client
from .models import Job, JobStatus
from .job_queue import JobQueue
from .test_executor import TestExecutor
from filelock import FileLock

# Configure production logging for worker
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('qgjob-worker.log')
    ]
)

logger = logging.getLogger(__name__)

class JobWorker:
    def __init__(self, worker_id: Optional[str] = None):
        self.worker_id = worker_id or f"worker-{os.getpid()}"
        logger.info(f"Initializing QualGent Job Worker {self.worker_id} in production mode")

        # Validate production dependencies
        self._validate_production_dependencies()

        try:
            self.job_queue = JobQueue()
            self.executor = TestExecutor()
            self.SessionLocal = sessionmaker(bind=engine)
            self.grouped_jobs = {}
            self.max_retries = int(os.getenv("MAX_JOB_RETRIES", "3"))
            logger.info(f"Job Worker {self.worker_id} initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Job Worker {self.worker_id}: {e}")
            raise RuntimeError(f"Worker initialization failed: {e}")

    def _validate_production_dependencies(self):
        """Validate that all production dependencies are available"""
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
            logger.error("Worker requires all production dependencies to be configured")
            raise RuntimeError(error_msg)
        self.processing_lock = FileLock(f"/tmp/worker-{self.worker_id}.lock")
        
        logger.info(f"Worker {self.worker_id} initialized")
    
    def get_db_session(self):
        """Create a new database session"""
        return self.SessionLocal()
    
    def group_jobs_by_app_version(self):
        jobs_to_process = []
        
        while True:
            job = self.job_queue.dequeue_job()
            if not job:
                break
            
            app_version_id = job["app_version_id"]
            if app_version_id not in self.grouped_jobs:
                self.grouped_jobs[app_version_id] = []
            
            self.grouped_jobs[app_version_id].append(job)
            jobs_to_process.append(job)
        
        logger.info(f"Grouped {len(jobs_to_process)} jobs into {len(self.grouped_jobs)} app version groups")
        return self.grouped_jobs
    
    def process_job_group(self, app_version_id: str, jobs: list):
        logger.info(f"Processing {len(jobs)} jobs for app_version_id: {app_version_id}")
        
        jobs.sort(key=lambda x: x.get("priority", 5))
        
        start_time = time.time()
        successful_jobs = 0
        failed_jobs = 0
        
        for job in jobs:
            try:
                success = self.process_single_job(job)
                if success:
                    successful_jobs += 1
                else:
                    failed_jobs += 1
            except Exception as e:
                logger.error(f"Unexpected error processing job {job['id']}: {str(e)}")
                failed_jobs += 1
        
        total_time = time.time() - start_time
        logger.info(f"Group {app_version_id} completed in {total_time:.2f}s: {successful_jobs} successful, {failed_jobs} failed")
    
    def process_single_job(self, job_data: dict) -> bool:
        job_id = job_data["id"]
        retry_count = 0
        
        while retry_count <= self.max_retries:
            session = self.get_db_session()
            try:
                logger.info(f"Processing job {job_id} (attempt {retry_count + 1})")
                
                db_job = session.query(Job).filter(Job.id == job_id).first()
                if not db_job:
                    logger.error(f"Job {job_id} not found in database")
                    return False
                
                if db_job.status == JobStatus.COMPLETED:
                    logger.info(f"Job {job_id} already completed, skipping")
                    return True
                
                self.update_job_status(db_job, JobStatus.PROCESSING, session)
                
                start_time = time.time()
                result = self.executor.execute_test(job_data)
                execution_time = time.time() - start_time
                
                if result["success"]:
                    db_job.status = JobStatus.COMPLETED
                    db_job.result = json.dumps({
                        "success": True,
                        "video_url": result.get("video_url"),
                        "test_results": result.get("test_results"),
                        "session_id": result.get("session_id"),
                        "browserstack_url": result.get("browserstack_url"),
                        "execution_time": execution_time
                    })
                    
                    session.commit()
                    self.job_queue.update_job_status(job_id, JobStatus.COMPLETED)
                    
                    logger.info(f"Job {job_id} completed successfully in {execution_time:.2f}s")
                    return True
                else:
                    error_msg = result.get("error", "Test execution failed")
                    
                    if retry_count < self.max_retries:
                        retry_count += 1
                        logger.warning(f"Job {job_id} failed (attempt {retry_count}), retrying: {error_msg}")
                        time.sleep(min(2 ** retry_count, 30))
                        continue
                    else:
                        db_job.status = JobStatus.FAILED
                        db_job.error_message = error_msg
                        db_job.result = json.dumps({
                            "success": False,
                            "error": error_msg,
                            "test_results": result.get("test_results"),
                            "execution_time": execution_time,
                            "retry_count": retry_count
                        })
                        
                        session.commit()
                        self.job_queue.update_job_status(job_id, JobStatus.FAILED)
                        
                        logger.error(f"Job {job_id} failed after {retry_count} retries: {error_msg}")
                        return False
                
            except Exception as e:
                error_msg = f"Job processing error: {str(e)}"
                logger.error(f"Job {job_id} error (attempt {retry_count + 1}): {error_msg}")
                
                if retry_count < self.max_retries:
                    retry_count += 1
                    time.sleep(min(2 ** retry_count, 30))
                    continue
                else:
                    db_job = session.query(Job).filter(Job.id == job_id).first()
                    if db_job:
                        db_job.status = JobStatus.FAILED
                        db_job.error_message = error_msg
                        db_job.updated_at = datetime.now(timezone.utc)
                        session.commit()
                    
                    self.job_queue.update_job_status(job_id, JobStatus.FAILED)
                    return False
            finally:
                session.close()
        
        return False
    
    def update_job_status(self, db_job: Job, status: JobStatus, session):
        db_job.status = status
        db_job.updated_at = datetime.now(timezone.utc)
        session.commit()
        self.job_queue.update_job_status(db_job.id, status)
    
    def cleanup_stale_jobs(self):
        session = self.get_db_session()
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=1)
            stale_jobs = session.query(Job).filter(
                Job.status == JobStatus.PROCESSING,
                Job.updated_at < cutoff_time
            ).all()
            
            for job in stale_jobs:
                logger.warning(f"Cleaning up stale job {job.id}")
                job.status = JobStatus.FAILED
                job.error_message = "Job timeout - no updates for over 1 hour"
                job.updated_at = datetime.now(timezone.utc)
            
            session.commit()
            logger.info(f"Cleaned up {len(stale_jobs)} stale jobs")
        finally:
            session.close()
    
    def run(self):
        logger.info(f"Worker {self.worker_id} started...")
        
        while True:
            try:
                with self.processing_lock:
                    self.cleanup_stale_jobs()
                    
                    grouped_jobs = self.group_jobs_by_app_version()
                    
                    if not grouped_jobs:
                        logger.debug("No jobs to process, waiting...")
                        time.sleep(5)
                        continue
                    
                    for app_version_id, jobs in grouped_jobs.items():
                        self.process_job_group(app_version_id, jobs)
                    
                    self.grouped_jobs.clear()
                
            except KeyboardInterrupt:
                logger.info(f"Worker {self.worker_id} shutting down...")
                break
            except Exception as e:
                logger.error(f"Worker {self.worker_id} error: {e}")
                time.sleep(10)
        
        logger.info(f"Worker {self.worker_id} stopped")

if __name__ == "__main__":
    worker = JobWorker()
    worker.run()
