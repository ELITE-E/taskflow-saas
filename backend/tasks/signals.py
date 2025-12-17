import logging
from django.db import transaction
from django.shortcuts import get_object_or_404
from tasks.models import Task
from tasks.ai_engine.urgency import compute_urgency
# Assuming importance_logic contains the business logic for weights and quadrants
from .ai_engine.importance_logic import compute_task_ranking 

logger = logging.getLogger(__name__)

def finalize_task_prioritization(task_id: int, relevance_scores: dict):
    """
    Celery callback or post-processing function executed after AI relevance 
    analysis is complete. Performs deterministic calculations to rank the task.
    
    This function is idempotent; re-running it with the same scores will 
    produce the same resulting Task state.
    """
    try:
        # Use select_for_update to handle potential race conditions during save
        with transaction.atomic():
            task = Task.objects.select_for_update().get(id=task_id)
            user_weights = task.user.goal_weights  # Access OneToOne from goals.models

            # 1. Compute Urgency (Deterministic)
            urgency_score = compute_urgency(
                due_date=task.due_date,
                effort_hours=task.effort_hours
            )

            # 2. Compute Importance and Quadrant
            # This integrates relevance_scores, user_defined weights, and urgency
            ranking_results = compute_task_ranking(
                relevance_scores=relevance_scores,
                weights=user_weights,
                urgency=urgency_score
            )

            # 3. Update Model Fields
            task.urgency_score = urgency_score
            task.importance_score = ranking_results["importance_score"]
            task.quadrant = ranking_results["quadrant"]
            
            # 4. State Management
            task.is_prioritized = True
            
            task.save(update_fields=[
                'urgency_score', 
                'importance_score', 
                'quadrant', 
                'is_prioritized'
            ])

            logger.info(f"Successfully prioritized Task {task_id}: Score {task.importance_score}")

    except Task.DoesNotExist:
        logger.error(f"Priority Finalization Failed: Task {task_id} not found.")
    except Exception as e:
        logger.exception(f"Unexpected error finalizing Task {task_id}: {str(e)}")
        raise  # Re-raise for Celery retry mechanisms if applicable