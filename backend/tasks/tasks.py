# tasks/tasks.py

from celery import shared_task
from .models import Task
# We'll need a service file for the external AI call (Step 4)
from .services import external_ai_scoring 
# Import Goal to access weight
from goals.models import Goal 


@shared_task
def process_task_prioritization(task_id):
    """
    Celery task to handle the asynchronous prioritization logic (Orchestration).
    """
    try:
        task = Task.objects.get(pk=task_id)
    except Task.DoesNotExist:
        return f"Task {task_id} not found."

    # 1. CALL EXTERNAL API FOR RELEVANCE SCORES (Simulated Step 4)
    # The external service would typically analyze the title/description
    ai_relevance_scores = external_ai_scoring(task.title, task.description)
    
    # 2. RETRIEVE USER'S STRATEGIC WEIGHTS
    # We'll use the weight of the associated Goal.
    goal_weight = task.goal.weight if task.goal else 1 
    
    # 3. APPLY WEIGHTED AVERAGE FORMULA (Final Scoring)
    # We'll calculate a simple score based on the simulation:
    
    # Simplified Formula Example:
    # Score = (Goal Weight * 0.5) + (AI Relevance * 0.5)
    
    # Assuming the AI returns a single 'Relevance' key for now (e.g., 0.1 to 1.0)
    ai_relevance_score = ai_relevance_scores.get('Relevance', 0.5)
    
    # Adjusting for effort and urgency (internal formula remains for now)
    final_priority_score = (goal_weight * 0.5) + (ai_relevance_score * 0.5)
    
    # 4. UPDATE TASK OBJECT
    task.priority_score = final_priority_score 
    task.is_prioritized = True # Mark as ready for the final list
    task.save(update_fields=['priority_score', 'is_prioritized', 'updated_at'])
    
    return f"Task {task_id} prioritized successfully with score: {final_priority_score}"