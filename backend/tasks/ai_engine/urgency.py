import datetime
from typing import Optional

# Maximum horizon for urgency scaling (e.g., tasks 30 days out have base urgency 0)
MAX_LOOKAHEAD_DAYS = 30

def compute_urgency(
    due_date: Optional[datetime.datetime],
    effort_hours: Optional[float] = None,
    now: Optional[datetime.datetime] = None
) -> float:
    """
    Calculates a normalized urgency score between 0.0 and 1.0.
    
    The score is determined primarily by the proximity of the due_date, 
    with a small boost based on the estimated effort required.
    """
    
    # 1. Handle missing due date (Low default urgency)
    if due_date is None:
        return 0.2

    # Ensure 'now' is defined for the calculation
    if now is None:
        now = datetime.datetime.now(tz=due_date.tzinfo)

    # 2. Calculate time delta
    time_diff = due_date - now
    days_remaining = time_diff.total_seconds() / (24 * 3600)

    # 3. Handle overdue or immediate tasks
    if days_remaining <= 0:
        return 1.0

    # 4. Calculate Base Urgency
    # Inverse linear relationship: 0 days = 1.0 urgency, 30+ days = 0.0 urgency
    base_urgency = 1.0 - (days_remaining / MAX_LOOKAHEAD_DAYS)
    base_urgency = max(0.0, min(1.0, base_urgency))

    # 5. Calculate Effort Modifier
    # High effort increases urgency (max +0.2). 
    # Logic: If a task takes 10+ hours, we should start it sooner.
    effort = effort_hours or 0.0
    effort_modifier = min(effort / 10.0, 0.2)

    # 6. Final Combined Score
    # We clamp the result to ensure it stays within the [0, 1] contract
    final_score = base_urgency + effort_modifier
    return round(max(0.0, min(1.0, final_score)), 4)