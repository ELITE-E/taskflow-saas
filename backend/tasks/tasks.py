# tasks/tasks.py

from celery import shared_task
from .models import Task

@shared_task
def finalize_task_prioritization(scoring_result: dict, task_id: int):
    """
    Subsequent task (or callback) that applies business logic to AI scores.
    
    This is where the 'Final Scoring' from your original design happens:
    Score = (AI Relevance * User Strategic Weights) + Urgency Factor
    """
    try:
        task = Task.objects.get(id=task_id)
        relevance = scoring_result.get('relevance_scores', {})
        
        # --- WEIGHTED AVERAGE FORMULA ---
        # Implementation of your PRD logic: Apply weights to the AI relevance
        # (This logic is kept here to keep the Orchestrator pure)
        final_score = 0.0
        # ... logic to multiply relevance by user_weights ...
        
        task.priority_score = final_score
        task.is_prioritized = True
        task.save()
    except Task.DoesNotExist:
        pass