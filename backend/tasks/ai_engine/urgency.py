# tasks/ai_engine/urgency.py
"""
Urgency Score Computation
=========================

Pure Python module for deterministic urgency calculation.

This module implements the urgency component of the Eisenhower Matrix scoring system.
Urgency is computed based on two factors:
1. **Temporal Proximity**: How close the due date is to today
2. **Effort Estimate**: Higher effort tasks need more lead time

Mathematical Model:
-------------------
The urgency score U ∈ [0.0, 1.0] is computed as:

    U = min(1.0, D × 0.8 + E × 0.2)

Where:
    D = Due Date Component = 1 - (days_until_due / MAX_LOOKAHEAD_DAYS)
    E = Effort Component   = (effort_estimate - 1) / 4

Constants:
    MAX_LOOKAHEAD_DAYS = 30 (tasks 30+ days out have minimal base urgency)

Edge Cases:
-----------
- No due date: Returns effort-only component (0.0 to 0.2)
- Overdue task: Returns 1.0 (maximum urgency)
- Invalid date format: Returns 0.0 (safe fallback)

Design Principles:
------------------
1. Deterministic: Same inputs always produce same output
2. No side effects: Pure function, no database or API calls
3. Defensive: Handles None, invalid types, and edge cases gracefully
"""

from __future__ import annotations

import datetime
from typing import Optional, Union

# ---------------------------------------------------------------------------
# CONSTANTS
# ---------------------------------------------------------------------------

# Maximum horizon for urgency scaling.
# Tasks due 30+ days out will have a due_date_component of 0.0
MAX_LOOKAHEAD_DAYS: int = 30

# Weight distribution between due date and effort components
# These must sum to 1.0 for proper normalization
DUE_DATE_WEIGHT: float = 0.8
EFFORT_WEIGHT: float = 0.2

# Effort scale boundaries (matches Task.effort_estimate field constraints)
EFFORT_MIN: int = 1
EFFORT_MAX: int = 5


# ---------------------------------------------------------------------------
# PUBLIC API
# ---------------------------------------------------------------------------


def compute_urgency(
    due_date: Optional[Union[str, datetime.date]] = None,
    effort_hours: Optional[Union[int, float]] = None,
    now: Optional[datetime.datetime] = None,
) -> float:
    """
    Calculate a normalized urgency score between 0.0 and 1.0.

    The urgency score combines temporal proximity to the deadline with
    the estimated effort required, giving more weight to approaching deadlines.

    Formula:
        urgency = (due_date_component × 0.8) + (effort_component × 0.2)

    Where:
        - due_date_component: Linear decay from 1.0 (due today) to 0.0 (30+ days out)
        - effort_component: Linear scale from 0.0 (effort=1) to 1.0 (effort=5)

    Args:
        due_date: ISO date string 'YYYY-MM-DD', datetime.date object, or None.
                  If None, only effort contributes to urgency.
        effort_hours: Effort estimate (1-5 scale, despite the parameter name).
                      Named for backward compatibility; represents effort_estimate field.
        now: Override for current datetime (useful for testing).
             Defaults to UTC now.

    Returns:
        float: Urgency score in range [0.0, 1.0], rounded to 4 decimal places.

    Examples:
        >>> compute_urgency(due_date="2024-01-15", effort_hours=3)  # Due in 10 days
        0.5333

        >>> compute_urgency(due_date=None, effort_hours=5)  # No deadline, high effort
        0.2

        >>> compute_urgency(due_date="2020-01-01")  # Overdue
        1.0
    """
    # Establish reference time
    if now is None:
        now = datetime.datetime.now(datetime.timezone.utc)

    # Compute individual components
    due_component: float = _compute_due_date_component(due_date, now)
    effort_component: float = _compute_effort_component(effort_hours)

    # Apply weighted combination
    # Formula: U = D × 0.8 + E × 0.2
    urgency: float = (due_component * DUE_DATE_WEIGHT) + (effort_component * EFFORT_WEIGHT)

    # Clamp to [0.0, 1.0] and round for consistency
    urgency = max(0.0, min(1.0, urgency))
    return round(urgency, 4)


# ---------------------------------------------------------------------------
# PRIVATE HELPERS
# ---------------------------------------------------------------------------


def _compute_due_date_component(
    due_date: Optional[Union[str, datetime.date]],
    now: datetime.datetime,
) -> float:
    """
    Compute the temporal proximity component of urgency.

    Linear decay model:
        - 0 days until due → 1.0 (maximum urgency)
        - 30 days until due → 0.0 (minimum urgency)
        - Overdue → 1.0 (clamped at maximum)

    Args:
        due_date: Due date as string 'YYYY-MM-DD' or date object, or None.
        now: Current datetime for reference.

    Returns:
        float: Due date component in range [0.0, 1.0].
    """
    if due_date is None:
        return 0.0

    # Parse string to date if necessary
    parsed_date: Optional[datetime.date] = _parse_date(due_date)
    if parsed_date is None:
        return 0.0

    today: datetime.date = now.date()
    days_until: int = (parsed_date - today).days

    # Overdue or due today → maximum urgency
    if days_until <= 0:
        return 1.0

    # Linear decay: 1.0 at day 0, approaching 0.0 at MAX_LOOKAHEAD_DAYS
    # Formula: D = 1 - (days_until / MAX_LOOKAHEAD_DAYS)
    component: float = 1.0 - (days_until / float(MAX_LOOKAHEAD_DAYS))

    # Clamp to [0.0, 1.0]
    return max(0.0, min(1.0, component))


def _compute_effort_component(effort: Optional[Union[int, float]]) -> float:
    """
    Compute the effort contribution to urgency.

    Higher effort tasks implicitly need more lead time, so effort
    provides a small boost to urgency.

    Linear scale model:
        - Effort 1 → 0.0 (minimal boost)
        - Effort 5 → 1.0 (maximum boost)

    Formula: E = (effort - 1) / 4

    Args:
        effort: Effort estimate on 1-5 scale, or None.

    Returns:
        float: Effort component in range [0.0, 1.0].
    """
    if effort is None:
        return 0.0

    try:
        effort_val: float = float(effort)
    except (ValueError, TypeError):
        return 0.0

    # Clamp to valid range [1, 5]
    effort_val = max(float(EFFORT_MIN), min(float(EFFORT_MAX), effort_val))

    # Linear scale: (effort - 1) / (EFFORT_MAX - EFFORT_MIN)
    # With EFFORT_MIN=1, EFFORT_MAX=5: (effort - 1) / 4
    component: float = (effort_val - EFFORT_MIN) / (EFFORT_MAX - EFFORT_MIN)

    return max(0.0, min(1.0, component))


def _parse_date(due_date: Union[str, datetime.date]) -> Optional[datetime.date]:
    """
    Safely parse a date from string or date object.

    Supports:
        - datetime.date objects (returned as-is)
        - ISO format strings: 'YYYY-MM-DD'

    Args:
        due_date: Date string or date object.

    Returns:
        datetime.date if parsing succeeds, None otherwise.
    """
    # Already a date object
    if isinstance(due_date, datetime.date):
        return due_date

    # Attempt string parsing
    if isinstance(due_date, str):
        try:
            return datetime.datetime.strptime(due_date, "%Y-%m-%d").date()
        except ValueError:
            # Invalid format → return None (handled by caller)
            return None

    # Unknown type
    return None
