from typing import Optional
import datetime

# Maximum horizon for urgency scaling (e.g., tasks 30 days out have base urgency 0)
MAX_LOOKAHEAD_DAYS = 30

def compute_urgency(
    due_date: Optional[str],
    effort_hours: Optional[float] = None,
    now: Optional[datetime.datetime] = None
) -> float:
    """
    Calculates a normalized urgency score between 0.0 and 1.0.

    due_date: ISO date string 'YYYY-MM-DD' or None
    effort_hours: numeric estimate (use effort_estimate field)
    """
    if now is None:
        now = datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc)

    # Default low urgency when no due date
    if not due_date:
        # incorporate effort slightly: map effort 1-5 -> 0-0.2
        effort_component = 0.0
        if effort_hours is not None:
            try:
                effort_component = max(0.0, min(1.0, (float(effort_hours) - 1.0) / 4.0)) * 0.2
            except Exception:
                effort_component = 0.0
        return round(min(1.0, effort_component), 4)

    # Parse date (assume YYYY-MM-DD)
    try:
        d = datetime.datetime.strptime(due_date, "%Y-%m-%d").date()
    except Exception:
        # invalid date -> fallback low urgency
        return 0.0

    today = now.date()
    days_until = (d - today).days

    if days_until <= 0:
        # Due now or past -> maximum urgency
        return 1.0

    # Scale linearly: 0 days -> 1.0, MAX_LOOKAHEAD_DAYS or beyond -> 0.0
    due_component = max(0.0, min(1.0, 1.0 - (days_until / float(MAX_LOOKAHEAD_DAYS))))

    # effort component: map 1..5 -> 0..1 then weight small (20%)
    effort_component = 0.0
    if effort_hours is not None:
        try:
            effort_component = max(0.0, min(1.0, (float(effort_hours) - 1.0) / 4.0))
        except Exception:
            effort_component = 0.0

    urgency = min(1.0, due_component * 0.8 + effort_component * 0.2)
    return round(urgency, 4)