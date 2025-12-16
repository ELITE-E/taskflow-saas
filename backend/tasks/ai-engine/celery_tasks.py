# tasks/ai_engine/celery_tasks.py

import logging
from typing import Dict, Any
from celery import shared_task
from .orchestrator import AIOrchestrator

# Configure logging for background worker monitoring
logger = logging.getLogger(__name__)

@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,  # Max backoff of 10 minutes
    max_retries=3,
    time_limit=30,          # Hard limit for the task process
    soft_time_limit=25      # Soft limit to allow cleanup
)
def run_ai_relevance_scoring(
    self, 
    task_id: int,
    task_title: str, 
    task_description: str, 
    user_weights: Dict[str, float]
) -> Dict[str, Any]:
    """
    Asynchronous Celery task for executing the AI scoring pipeline.
    
    This task wraps the AIOrchestrator to perform rule-based, cached, 
    or LLM-based relevance scoring without blocking the main request-response cycle.

    Args:
        self: The task instance (provided by bind=True).
        task_id: The database ID of the task (used for logging context).
        task_title: Title string of the task.
        task_description: Description string of the task.
        user_weights: Dict mapping strategic goals to user-defined weights.

    Returns:
        Dict: The structured relevance scores and confidence level.
        Example: {"relevance_scores": {"work": 0.9, ...}, "confidence": 1.0}
    """
    logger.info(f"Starting AI relevance scoring for Task ID: {task_id}")

    try:
        # Initialize the Orchestrator (internalizes rules, cache, and services)
        orchestrator = AIOrchestrator()
        
        # Execute the tiered scoring pipeline
        result = orchestrator.get_relevance_scores(
            task_title=task_title,
            task_description=task_description,
            user_weights=user_weights
        )

        logger.info(f"Successfully scored Task ID: {task_id} (Confidence: {result.get('confidence')})")
        return result

    except Exception as exc:
        # Log specifically which task failed to assist with debugging
        logger.error(
            f"AI Scoring Pipeline error for Task ID: {task_id}. "
            f"Attempt {self.request.retries}/{self.max_retries}. Error: {str(exc)}"
        )
        # Re-raise to trigger the autoretry mechanism defined in the decorator
        raise exc