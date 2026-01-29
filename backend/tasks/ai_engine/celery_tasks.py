# tasks/ai_engine/celery_tasks.py
"""
Celery Tasks for AI Scoring
===========================

This module contains the Celery task definitions for asynchronous AI scoring.

Design Principles:
------------------
1. Idempotency: Running the same task twice produces the same result
2. Atomicity: Database updates are wrapped in transactions
3. Resilience: Graceful handling of failures with proper retry logic
4. Observability: Comprehensive logging for production monitoring

Task Flow:
----------
1. Receive (task_id, user_id) from queue
2. Acquire row lock with select_for_update (prevents race conditions)
3. Skip if already processed (idempotency check)
4. Build user weights from GoalWeights or Goals
5. Call AIOrchestrator for scoring
6. Persist results atomically
7. Update last_analyzed_at timestamp
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from celery import shared_task
from celery.exceptions import MaxRetriesExceededError, SoftTimeLimitExceeded
from django.db import DatabaseError, IntegrityError, transaction

from goals.models import Goal, GoalWeights

from ..models import Task
from .orchestrator import AIOrchestrator

# ---------------------------------------------------------------------------
# Logging Configuration
# ---------------------------------------------------------------------------

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------


def _normalize_goal_weights_from_goals(goals_qs) -> Dict[str, float]:
    """
    Derive normalized weights from a queryset of Goal objects.

    This is a fallback when GoalWeights is not configured. It takes the
    raw weight values (1-10 scale) from Goals and normalizes them to sum to 1.0.

    Args:
        goals_qs: QuerySet of Goal objects.

    Returns:
        Dictionary of normalized weights (sum to 1.0), or empty dict if no goals.
    """
    raw: Dict[str, float] = {}

    for goal in goals_qs:
        if goal.weight is None:
            continue
        # Use slug if available, otherwise title
        key = getattr(goal, "slug", None) or goal.title
        raw[str(key)] = float(goal.weight)

    total = sum(raw.values()) if raw else 0.0

    if total <= 0:
        logger.debug("_normalize_goal_weights_from_goals: No valid weights found")
        return {}

    # Normalize to sum to 1.0
    normalized = {k: (v / total) for k, v in raw.items()}
    logger.debug(f"_normalize_goal_weights_from_goals: Normalized weights = {normalized}")
    return normalized


def _get_user_weights(user_id: int) -> Dict[str, float]:
    """
    Retrieve user's strategic weights for importance calculation.

    Priority:
    1. GoalWeights model (explicit, normalized weights)
    2. Goals model (derived from goal weights)
    3. Default equal weights (fallback)

    Args:
        user_id: The user's ID.

    Returns:
        Dictionary of domain weights (always sums to 1.0).
    """
    # Try GoalWeights first (preferred source)
    goal_weights = GoalWeights.objects.filter(user_id=user_id).first()

    if goal_weights:
        weights = {
            "work_bills": float(goal_weights.work_bills),
            "study": float(goal_weights.study),
            "health": float(goal_weights.health),
            "relationships": float(goal_weights.relationships),
        }
        logger.debug(f"_get_user_weights: Using GoalWeights for user {user_id}")
        return weights

    # Fallback: derive from Goals
    user_goals = Goal.objects.filter(user_id=user_id, is_archived=False)
    derived_weights = _normalize_goal_weights_from_goals(user_goals)

    if derived_weights:
        logger.debug(f"_get_user_weights: Using derived weights for user {user_id}")
        return derived_weights

    # Final fallback: equal weights for canonical domains
    logger.info(
        f"_get_user_weights: Using default equal weights for user {user_id} "
        "(no GoalWeights or Goals found)"
    )
    return {
        "work_bills": 0.25,
        "study": 0.25,
        "health": 0.25,
        "relationships": 0.25,
    }


def _should_skip_scoring(task: Task) -> bool:
    """
    Check if a task should skip scoring (idempotency check).

    A task should be skipped if:
    - It's already prioritized AND
    - It was analyzed recently (within the last hour)

    This prevents redundant processing during retries while still
    allowing re-scoring if the task was updated.

    Args:
        task: The Task instance to check.

    Returns:
        True if scoring should be skipped, False otherwise.
    """
    if not task.is_prioritized:
        return False

    # Check if analyzed recently (prevents retry loops)
    if hasattr(task, "last_analyzed_at") and task.last_analyzed_at:
        age_seconds = (datetime.now(timezone.utc) - task.last_analyzed_at).total_seconds()
        if age_seconds < 3600:  # Within last hour
            logger.info(
                f"Task {task.id} already analyzed {age_seconds:.0f}s ago, skipping"
            )
            return True

    return False


# ---------------------------------------------------------------------------
# Main Celery Task
# ---------------------------------------------------------------------------


@shared_task(
    bind=True,
    name="tasks.ai_engine.run_ai_relevance_scoring",
    autoretry_for=(DatabaseError, IntegrityError),
    retry_backoff=True,
    retry_backoff_max=600,  # Max backoff of 10 minutes
    max_retries=3,
    time_limit=60,  # Hard limit for the task process
    soft_time_limit=50,  # Soft limit to allow cleanup
    acks_late=True,  # Acknowledge after completion (safer for retries)
    reject_on_worker_lost=True,  # Requeue if worker dies
)
def run_ai_relevance_scoring(
    self,
    task_id: int,
    user_id: int,
    force_rescore: bool = False,
) -> Optional[Dict[str, Any]]:
    """
    Celery worker task for AI-powered task relevance scoring.

    This task fetches a Task from the database, computes its prioritization
    scores via the AIOrchestrator, and persists the results atomically.

    Idempotency:
    - Uses select_for_update to prevent race conditions
    - Checks is_prioritized flag to skip already-processed tasks
    - Updates last_analyzed_at for audit trail

    Error Handling:
    - Retries on database errors (with exponential backoff)
    - Logs all failures for production monitoring
    - Never leaves tasks in "infinite processing" state

    Args:
        self: Celery task instance (for retry access).
        task_id: Primary key of the Task to score.
        user_id: Primary key of the User who owns the task.
        force_rescore: If True, rescore even if already prioritized.

    Returns:
        The decision contract dictionary on success, or None on failure/skip.
    """
    correlation_id = f"task-{task_id}-user-{user_id}-attempt-{self.request.retries}"
    logger.info(
        f"[{correlation_id}] AI scoring started "
        f"(retry {self.request.retries}/{self.max_retries})"
    )

    try:
        # ─────────────────────────────────────────────────────────────────────
        # STEP 1: Acquire lock and fetch task
        # ─────────────────────────────────────────────────────────────────────
        with transaction.atomic():
            # select_for_update prevents concurrent modifications
            task = (
                Task.objects.select_for_update(nowait=False)
                .filter(id=task_id)
                .first()
            )

            if not task:
                logger.warning(f"[{correlation_id}] Task {task_id} not found, exiting")
                return None

            # Verify ownership
            if task.user_id != user_id:
                logger.error(
                    f"[{correlation_id}] Task {task_id} belongs to user {task.user_id}, "
                    f"not {user_id}. Aborting."
                )
                return None

            # ─────────────────────────────────────────────────────────────────
            # STEP 2: Idempotency check
            # ─────────────────────────────────────────────────────────────────
            if not force_rescore and _should_skip_scoring(task):
                logger.info(
                    f"[{correlation_id}] Task already processed, skipping "
                    f"(use force_rescore=True to override)"
                )
                return {
                    "status": "skipped",
                    "reason": "already_processed",
                    "task_id": task_id,
                }

            # ─────────────────────────────────────────────────────────────────
            # STEP 3: Build user weights
            # ─────────────────────────────────────────────────────────────────
            user_weights = _get_user_weights(user_id)
            logger.debug(f"[{correlation_id}] User weights: {user_weights}")

            # ─────────────────────────────────────────────────────────────────
            # STEP 4: Run orchestrator
            # ─────────────────────────────────────────────────────────────────
            orchestrator = AIOrchestrator()

            result = orchestrator.get_relevance_scores(
                task_title=task.title,
                task_description=task.description or "",
                user_weights=user_weights,
                due_date=(task.due_date.isoformat() if task.due_date else None),
                effort_estimate=(
                    int(task.effort_estimate) if task.effort_estimate is not None else None
                ),
            )

            logger.debug(f"[{correlation_id}] Orchestrator result: {result}")

            # ─────────────────────────────────────────────────────────────────
            # STEP 5: Persist results atomically
            # ─────────────────────────────────────────────────────────────────
            update_fields: Dict[str, Any] = {
                "importance_score": result.get("importance_score", 0.0),
                "urgency_score": result.get("urgency_score", 0.0),
                "quadrant": result.get("quadrant"),
                "rationale": result.get("rationale", "") or "",
                "priority_score": result.get("importance_score", 0.0),
                "is_prioritized": True,
            }

            # Update last_analyzed_at if the field exists
            if hasattr(Task, "last_analyzed_at"):
                update_fields["last_analyzed_at"] = datetime.now(timezone.utc)

            # Atomic update using .update() for idempotency
            rows_updated = Task.objects.filter(id=task_id).update(**update_fields)

            if rows_updated == 0:
                logger.error(
                    f"[{correlation_id}] Failed to update task {task_id} - "
                    "no rows affected"
                )
                return None

            logger.info(
                f"[{correlation_id}] AI scoring completed successfully - "
                f"quadrant={result.get('quadrant')}, "
                f"importance={result.get('importance_score', 0):.2f}, "
                f"method={result.get('scoring_method')}"
            )

            return result

    except SoftTimeLimitExceeded:
        logger.error(
            f"[{correlation_id}] Soft time limit exceeded, marking task as failed"
        )
        # Mark task as needing retry, don't leave in processing state
        Task.objects.filter(id=task_id).update(
            is_prioritized=False,
            rationale="Scoring timed out - will retry",
        )
        raise  # Let Celery handle the retry

    except MaxRetriesExceededError:
        logger.error(
            f"[{correlation_id}] Max retries exceeded, marking task as failed"
        )
        # Mark task as failed permanently
        Task.objects.filter(id=task_id).update(
            is_prioritized=False,
            rationale="Scoring failed after maximum retries",
            quadrant="Q4",  # Default to lowest priority
        )
        return None

    except (DatabaseError, IntegrityError) as exc:
        logger.warning(
            f"[{correlation_id}] Database error: {exc}. Will retry."
        )
        raise  # Celery will retry based on autoretry_for

    except Exception as exc:
        logger.exception(
            f"[{correlation_id}] Unexpected error during AI scoring: {exc}"
        )

        # Don't leave task in infinite processing state
        try:
            Task.objects.filter(id=task_id).update(
                is_prioritized=False,
                rationale=f"Scoring error: {type(exc).__name__}",
            )
        except Exception as update_exc:
            logger.error(
                f"[{correlation_id}] Failed to update task state: {update_exc}"
            )

        # Re-raise for Celery retry if retries remain
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc, countdown=60 * (self.request.retries + 1))

        return None


# ---------------------------------------------------------------------------
# Utility Tasks
# ---------------------------------------------------------------------------


@shared_task(name="tasks.ai_engine.bulk_rescore_tasks")
def bulk_rescore_tasks(task_ids: List[int], user_id: int) -> Dict[str, Any]:
    """
    Queue multiple tasks for rescoring.

    This is useful for re-analyzing tasks when user weights change.

    Args:
        task_ids: List of Task IDs to rescore.
        user_id: User ID (for validation).

    Returns:
        Summary of queued tasks.
    """
    queued = 0
    skipped = 0

    for task_id in task_ids:
        try:
            # Verify task belongs to user before queueing
            if Task.objects.filter(id=task_id, user_id=user_id).exists():
                run_ai_relevance_scoring.delay(task_id, user_id, force_rescore=True)
                queued += 1
            else:
                skipped += 1
                logger.warning(
                    f"bulk_rescore_tasks: Task {task_id} not found or "
                    f"doesn't belong to user {user_id}"
                )
        except Exception as e:
            logger.error(f"bulk_rescore_tasks: Failed to queue task {task_id}: {e}")
            skipped += 1

    logger.info(
        f"bulk_rescore_tasks: Queued {queued} tasks, skipped {skipped}"
    )

    return {
        "queued": queued,
        "skipped": skipped,
        "total": len(task_ids),
    }
