"""
Async Task Queue for Concurrent SOAP Note Processing
Supports multiple doctors recording and processing simultaneously
"""

import asyncio
import logging
import threading
from datetime import datetime, timedelta
from typing import Dict, Optional, Callable, Any
from enum import Enum
import uuid

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """Task processing status"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Task:
    """Represents a processing task"""
    
    def __init__(self, task_id: str, session_id: str, func: Callable, *args, **kwargs):
        self.task_id = task_id
        self.session_id = session_id
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self.status = TaskStatus.PENDING
        self.result = None
        self.error = None
        self.created_at = datetime.now()
        self.started_at = None
        self.completed_at = None
        self.progress = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert task to dictionary"""
        return {
            "task_id": self.task_id,
            "session_id": self.session_id,
            "status": self.status.value,
            "progress": self.progress,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error": self.error
        }


class ProcessingQueue:
    """
    Async task queue with worker pool for concurrent processing
    Supports multiple simultaneous SOAP note generations
    """
    
    def __init__(self, max_workers: int = 5):
        self.max_workers = max_workers
        self.tasks: Dict[str, Task] = {}
        self.queue = asyncio.Queue()
        self.workers = []
        self.running = False
        self.lock = threading.Lock()
        
        logger.info(f"🔧 Initialized ProcessingQueue with {max_workers} workers")
    
    def start(self):
        """Start worker threads"""
        if self.running:
            return
        
        self.running = True
        
        # Start worker threads
        for i in range(self.max_workers):
            worker = threading.Thread(
                target=self._worker_loop,
                args=(i,),
                daemon=True,
                name=f"Worker-{i}"
            )
            worker.start()
            self.workers.append(worker)
            logger.info(f"✅ Started worker thread {i}")
        
        # Start cleanup thread
        cleanup = threading.Thread(
            target=self._cleanup_loop,
            daemon=True,
            name="Cleanup-Worker"
        )
        cleanup.start()
        logger.info("✅ Started cleanup worker")
    
    def stop(self):
        """Stop all workers"""
        self.running = False
        logger.info("🛑 Stopping ProcessingQueue workers")
    
    def submit_task(self, session_id: str, func: Callable, *args, **kwargs) -> str:
        """
        Submit a task for async processing
        
        Args:
            session_id: Session ID for tracking
            func: Function to execute
            *args, **kwargs: Arguments for the function
        
        Returns:
            task_id: Unique task identifier
        """
        task_id = str(uuid.uuid4())
        task = Task(task_id, session_id, func, *args, **kwargs)
        
        with self.lock:
            self.tasks[task_id] = task
        
        # Add to queue (non-blocking)
        threading.Thread(
            target=self._add_to_queue,
            args=(task,),
            daemon=True
        ).start()
        
        logger.info(f"📝 Submitted task {task_id} for session {session_id}")
        return task_id
    
    def _add_to_queue(self, task: Task):
        """Add task to async queue"""
        try:
            # Create new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.queue.put(task))
            loop.close()
        except Exception as e:
            logger.error(f"Error adding task to queue: {e}")
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task status by ID"""
        with self.lock:
            task = self.tasks.get(task_id)
            return task.to_dict() if task else None
    
    def get_session_tasks(self, session_id: str) -> list:
        """Get all tasks for a session"""
        with self.lock:
            return [
                task.to_dict()
                for task in self.tasks.values()
                if task.session_id == session_id
            ]
    
    def _worker_loop(self, worker_id: int):
        """Worker thread that processes tasks from queue"""
        logger.info(f"🔄 Worker {worker_id} started")
        
        # Create event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        while self.running:
            try:
                # Get task from queue (with timeout)
                task = loop.run_until_complete(
                    asyncio.wait_for(self.queue.get(), timeout=1.0)
                )
                
                logger.info(f"⚙️ Worker {worker_id} processing task {task.task_id}")
                
                # Update status
                task.status = TaskStatus.PROCESSING
                task.started_at = datetime.now()
                task.progress = 10
                
                # Execute the task
                try:
                    result = task.func(*task.args, **task.kwargs)
                    task.result = result
                    task.status = TaskStatus.COMPLETED
                    task.progress = 100
                    logger.info(f"✅ Worker {worker_id} completed task {task.task_id}")
                    
                except Exception as e:
                    task.status = TaskStatus.FAILED
                    task.error = str(e)
                    task.progress = 0
                    logger.error(f"❌ Worker {worker_id} failed task {task.task_id}: {e}")
                
                finally:
                    task.completed_at = datetime.now()
                    self.queue.task_done()
                
            except asyncio.TimeoutError:
                # No tasks in queue, continue waiting
                continue
            except Exception as e:
                logger.error(f"Worker {worker_id} error: {e}")
        
        loop.close()
        logger.info(f"🛑 Worker {worker_id} stopped")
    
    def _cleanup_loop(self):
        """Cleanup old completed tasks"""
        logger.info("🧹 Cleanup worker started")
        
        while self.running:
            try:
                # Sleep for 5 minutes between cleanups
                threading.Event().wait(300)
                
                # Remove tasks older than 1 hour
                cutoff = datetime.now() - timedelta(hours=1)
                
                with self.lock:
                    to_remove = [
                        task_id
                        for task_id, task in self.tasks.items()
                        if task.completed_at and task.completed_at < cutoff
                    ]
                    
                    for task_id in to_remove:
                        del self.tasks[task_id]
                    
                    if to_remove:
                        logger.info(f"🧹 Cleaned up {len(to_remove)} old tasks")
            
            except Exception as e:
                logger.error(f"Cleanup error: {e}")
        
        logger.info("🛑 Cleanup worker stopped")


# Global queue instance
processing_queue = None


def get_processing_queue(max_workers: int = 5) -> ProcessingQueue:
    """Get or create the global processing queue"""
    global processing_queue
    
    if processing_queue is None:
        processing_queue = ProcessingQueue(max_workers=max_workers)
        processing_queue.start()
    
    return processing_queue


def shutdown_queue():
    """Shutdown the processing queue"""
    global processing_queue
    
    if processing_queue:
        processing_queue.stop()
        processing_queue = None
