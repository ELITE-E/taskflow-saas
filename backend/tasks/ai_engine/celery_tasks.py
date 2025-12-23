# tasks/ai_engine/celery_tasks.py

import logging
from typing import Dict, Any, Optional
from celery import shared_task
from .orchestrator import AIOrchestrator
from ..models import Task
from goals.models import GoalWeights, Goal
from django.db import transaction

# Configure logging for background worker monitoring
logger = logging.getLogger(__name__)

def _normalize_goal_weights_from_goals(goals_qs):
    raw = {}
    for g in goals_qs:
        if g.weight is None:
            continue
        key = getattr(g, 'slug', None) or g.title
        raw[str(key)] = float(g.weight)
    total = sum(raw.values()) if raw else 0.0
    if total <= 0:
        return {}
    return {k: (v / total) for k, v in raw.items()}

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
    user_id: int
) -> Optional[Dict[str, Any]]:
    """
    Worker: fetch Task + GoalWeights from DB, compute decision contract via orchestrator,
    persist results deterministically. Input = (task_id, user_id) only.
    """
    logger.info(f"AI scoring started for Task {task_id} (user {user_id})")
    try:
        task = Task.objects.filter(id=task_id).first()
        if not task:
            logger.warning(f"Task {task_id} not found. Exiting worker.")
            return None

        # Build normalized user_weights:
        gw = GoalWeights.objects.filter(user_id=user_id).first()
        if gw:
            # Use explicit GoalWeights fields (already normalized by model clean)
            user_weights = {
                'work_bills': float(gw.work_bills),
                'study': float(gw.study),
                'health': float(gw.health),
                'relationships': float(gw.relationships)
            }
        else:
            # Fallback: derive from Goals (weights 1..10) and normalize
            user_goals = Goal.objects.filter(user_id=user_id, is_archived=False)
            user_weights = _normalize_goal_weights_from_goals(user_goals)

        # Ensure there is at least a fallback set of dimensions
        if not user_weights:
            # deterministic fallback: equal weights for four canonical dimensions
            user_weights = {k: 0.25 for k in ['work_bills', 'study', 'health', 'relationships']}

        orchestrator = AIOrchestrator()

        result = orchestrator.get_relevance_scores(
            task_title=task.title,
            task_description=task.description,
            user_weights=user_weights,
            due_date=(task.due_date.isoformat() if task.due_date else None),
            effort_estimate=int(task.effort_estimate) if task.effort_estimate is not None else None
        )

        # Persist results atomically
        with transaction.atomic():
            Task.objects.filter(id=task_id).update(
                importance_score=result.get('importance_score', 0.0),
                urgency_score=result.get('urgency_score', 0.0),
                quadrant=result.get('quadrant'),
                rationale=result.get('rationale', "") or "",
                priority_score=result.get('importance_score', 0.0),
                is_prioritized=True
            )

        logger.info(f"AI scoring persisted for Task {task_id}")
        return result

    except Exception as exc:
        logger.exception(f"AI scoring failed for Task {task_id}: {exc}")
        # Re-raise for Celery retry policy
        raise