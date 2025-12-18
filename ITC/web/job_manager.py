"""
Job Manager - Tracks Invoice Automation Job State
Stage 1: Simple in-memory storage
"""

import uuid
import threading
from datetime import datetime
from enum import Enum

class JobStatus(Enum):
    """ Job Status States """
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

class Job:
    """ Represents a single automation job """

    def __init__(self, job_id=None, metadata=None):
        self.job_id = job_id or str(uuid.uuid4())
        self.status = JobStatus.PENDING
        self.created_at = datetime.now()
        self.started_at = None
        self.completed_at = None
        
        # Progress Tracking
        self.total_accounts = 0
        self.completed_accounts = 0
        self.current_vendor = None
        self.current_account = None

        # Results
        self.results = [] # List of {vendor, account, status, filename, error}
        self.error_message = None

        # Job metadata (email_to, mode, vendor, account, requested_by)
        self.metadata = metadata or {}


    def to_dict(self):
        """ Convert job to dictionary for API response """
        # Calculate percentage complete
        percent_complete = 0
        if self.total_accounts > 0:
            percent_complete = round((self.completed_accounts / self.total_accounts) * 100)

        # Create current label
        current_label = None
        if self.current_vendor and self.current_account is not None:
            current_label = f"{self.current_vendor.upper()} - Account #{self.current_account + 1}"

        return {
            'job_id': self.job_id,
            'status': self.status.value,
            'created_at': self.created_at.isoformat(),
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'total_accounts': self.total_accounts,
            'completed_accounts': self.completed_accounts,
            'current_vendor': self.current_vendor,
            'current_account': self.current_account,
            'results': self.results,
            'error_message': self.error_message,
            'metadata': self.metadata,
            # Computed fiels for UI convenience
            'percent_complete': percent_complete,
            'current_label': current_label
        }
    
class JobManager:
    """ Manages all automation jobs """

    def __init__(self):
        self.jobs = {} # job_id -> Job
        self.lock = threading.Lock()

    def create_job(self, metadata=None):
        """ Create a new job with optional metadata """
        job = Job(metadata=metadata)
        with self.lock:
            self.jobs[job.job_id] = job
        return job
    
    def get_jobs(self, job_id):
        """ Get job by ID """
        with self.lock:
            return self.jobs.get(job_id)
        
    def has_active_job(self):
        """ Check if any job is currently PENDING or RUNNING """
        with self.lock: 
            for job in self.jobs.values():
                if job.status in [JobStatus.PENDING, JobStatus.RUNNING]:
                    return True
            return False
        
    def update_job(self, job_id, **kwargs):
        """ Update job fields """
        with self.lock:
            job = self.jobs.get(job_id)
            if job:
                for key, value in kwargs.items():
                    if hasattr(job, key):
                        setattr(job, key, value)
                return job
            return None
        
    def mark_started(self, job_id):
        """ Mark job as started """
        return self.update_job(
            job_id,
            status = JobStatus.RUNNING,
            started_at = datetime.now()
        )
    
    def mark_completed(self, job_id):
        """ Mark job as completed """
        return self.update_job(
            job_id,
            status = JobStatus.COMPLETED,
            completed_at = datetime.now()
        )
    
    def mark_failed(self, job_id, error_message):
        """ Mark job as failed """
        return self.update_job(
            job_id,
            status = JobStatus.FAILED,
            completed_at = datetime.now(),
            error_message = error_message
        )
    
    def add_result(self, job_id, vendor, account, status, filename=None, error=None):
        """ Add a result for one account """
        with self.lock:
            job = self.jobs.get(job_id)
            if job:
                job.results.append({
                    'vendor': vendor,
                    'account': account,
                    'status': status,
                    'filename': filename,
                    'error': error
                })
                job.completed_accounts += 1
                return job
            return None
        
# Global job manager instance
job_manager = JobManager()

