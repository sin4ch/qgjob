import json
import uuid
from datetime import datetime
from .database import redis_client
from .models import Job, JobStatus

class JobQueue:
    QUEUE_KEY = "job_queue"
    STATUS_KEY = "job_status"
    
    def enqueue_job(self, job_data: dict) -> str:
        job_id = str(uuid.uuid4())
        job_payload = {
            "id": job_id,
            **job_data,
            "created_at": datetime.utcnow().isoformat()
        }
        
        redis_client.lpush(self.QUEUE_KEY, json.dumps(job_payload))
        redis_client.hset(self.STATUS_KEY, job_id, JobStatus.QUEUED.value)
        
        return job_id
    
    def dequeue_job(self):
        job_json = redis_client.rpop(self.QUEUE_KEY)
        if job_json:
            return json.loads(job_json)
        return None
    
    def update_job_status(self, job_id: str, status: JobStatus):
        redis_client.hset(self.STATUS_KEY, job_id, status.value)
    
    def get_job_status(self, job_id: str) -> str:
        return redis_client.hget(self.STATUS_KEY, job_id)
    
    def get_jobs_by_app_version(self, app_version_id: str) -> list:
        jobs = []
        queue_length = redis_client.llen(self.QUEUE_KEY)
        
        for i in range(queue_length):
            job_json = redis_client.lindex(self.QUEUE_KEY, i)
            if job_json:
                job = json.loads(job_json)
                if job.get("app_version_id") == app_version_id:
                    jobs.append(job)
        
        return jobs
    
    def get_queue_size(self) -> int:
        return redis_client.llen(self.QUEUE_KEY)
    
    def get_processing_jobs_count(self) -> int:
        processing_jobs = redis_client.hgetall(self.STATUS_KEY)
        return sum(1 for status in processing_jobs.values() if status == JobStatus.PROCESSING.value)
