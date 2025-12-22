# tasks/ai_engine/celery_tasks.py

import logging
from typing import Dict, Any, Optional
from celery import shared_task
from .orchestrator import AIOrchestrator
from ..models import Task
from django.db import transaction

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
    due_date: Optional[str],
    effort_estimate: Optional[int],
    user_weights: Dict[str, float]
) -> Dict[str, Any]:
    """
    Asynchronous Celery task for executing the AI scoring pipeline.

    Now: orchestrator returns full decision contract; this task MUST persist results
    to the Task DB row before exiting.
    """
    logger.info(f"Starting AI relevance scoring for Task ID: {task_id}")

    try:
        # Initialize the Orchestrator (internalizes rules, cache, and services)
        orchestrator = AIOrchestrator()
        
        # Execute the tiered scoring pipeline and compute importance/urgency/quadrant
        result = orchestrator.get_relevance_scores(
            task_title=task_title,
            task_description=task_description,
            user_weights=user_weights,
            due_date=due_date,
            effort_estimate=effort_estimate
        )

        logger.info(f"Successfully scored Task ID: {task_id} (Confidence: {result.get('confidence')})")

        # Persist results to the DB in a transaction
        try:
            with transaction.atomic():
                Task.objects.filter(id=task_id).update(
                    importance_score=result.get('importance_score', 0.0),
                    urgency_score=result.get('urgency_score', 0.0),
                    quadrant=result.get('quadrant', None),
                    rationale=result.get('rationale', "") or "",
                    priority_score=result.get('importance_score', 0.0),
                    is_prioritized=True
                )
        except Exception as e:
            logger.exception(f"Failed to persist AI results for Task ID {task_id}: {str(e)}")
            # Raise to trigger retry according to task decorator
            raise

        return result

    except Exception as exc:
        # Log specifically which task failed to assist with debugging
        logger.error(
            f"AI Scoring Pipeline error for Task ID: {task_id}. "
            f"Attempt {self.request.retries}/{self.max_retries}. Error: {str(exc)}"
        )
        # Re-raise to trigger the autoretry mechanism defined in the decorator
        raise exc