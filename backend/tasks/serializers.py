# tasks/serializers.py

from django.db import transaction
from rest_framework import serializers
from .models import Task
from .ai_engine.celery_tasks import run_ai_relevance_scoring
from goals.models import Goal, GoalWeights  # GoalWeights expected to exist per instructions
import logging

logger = logging.getLogger(__name__)

class TaskSerializer(serializers.ModelSerializer):
    # Field to return the Celery ID to the frontend for polling/tracking
    async_status_id = serializers.ReadOnlyField(source='celery_task_id')

    class Meta:
        model = Task
        fields = [
            'id', 'title', 'description', 'goal', 'due_date', 'effort_estimate',
            'is_prioritized', 'priority_score', 'async_status_id'
        ]
        read_only_fields = ['is_prioritized', 'priority_score']

    def _fetch_user_weights(self, user):
        """
        Fetch user weights from GoalWeights (preferred) or derive from Goals as fallback.
        Returns dict[str,float] raw weights (may be 1-10 or already normalized).
        """
        # Primary: try GoalWeights model
        try:
            gw = GoalWeights.objects.filter(user=user).first()
        except Exception:
            gw = None

        if gw:
            # Accept multiple shapes (dict field 'weights' or individual fields)
            if hasattr(gw, 'weights'):
                raw = gw.weights or {}
                if isinstance(raw, dict):
                    return {str(k): float(v) for k, v in raw.items()}
            # If GoalWeights has attributes per-domain, try to build a dict
            # (best-effort fallback)
            try:
                # expose all numeric fields except id/user
                raw = {}
                for f in gw._meta.get_fields():
                    name = getattr(f, 'name', None)
                    if name and name not in ('id', 'user'):
                        val = getattr(gw, name, None)
                        if isinstance(val, (int, float)):
                            raw[name] = float(val)
                if raw:
                    return raw
            except Exception:
                pass

        # Fallback: derive from user's Goal objects if they have a 'weight' field
        raw = {}
        try:
            for g in Goal.objects.filter(user=user):
                w = getattr(g, 'weight', None)
                key = getattr(g, 'slug', None) or g.title
                if w is None:
                    continue
                raw[str(key)] = float(w)
        except Exception:
            pass

        return raw

    def _normalize_weights(self, raw_weights: dict) -> dict:
        """
        Normalize weights so their sum == 1.0 (within tolerance).
        Accepts raw numeric values (e.g., 1-10 or already fractional).
        """
        if not raw_weights:
            raise serializers.ValidationError("No strategic weights found for user.")
        items = {k: float(v) for k, v in raw_weights.items()}
        total = sum(items.values())
        if total == 0:
            raise serializers.ValidationError("User weights sum to zero.")
        normalized = {k: v / total for k, v in items.items()}
        # ensure numerical stability
        s = sum(normalized.values())
        if abs(s - 1.0) > 0.001:
            # last-resort renormalize
            normalized = {k: v / s for k, v in normalized.items()}
        return normalized

    def create(self, validated_data: dict) -> Task:
        """
        Creates a task and triggers the AI orchestration pipeline.

        Creates DB record with required fields:
          - description
          - due_date
          - effort_estimate
          - goal (nullable)

        Removes placeholder weights and uses user GoalWeights (normalized).
        """
        user = self.context['request'].user

        # 1. Fetch raw weights and normalize them (no placeholders)
        raw_weights = self._fetch_user_weights(user)
        normalized_weights = self._normalize_weights(raw_weights)

        # 2. Persist Task with validated data (ensure effort_estimate present)
        with transaction.atomic():
            task = Task.objects.create(user=user, **validated_data)

            # 3. Define the async trigger logic that passes normalized weights
            def trigger_ai():
                # Celery accepts dicts — pass normalized weights as-is
                celery_result = run_ai_relevance_scoring.delay(
                    task_id=task.id,
                    task_title=task.title,
                    task_description=task.description,
                    due_date=(task.due_date.isoformat() if task.due_date else None),
                    effort_estimate=int(task.effort_estimate) if task.effort_estimate is not None else None,
                    user_weights=normalized_weights
                )
                # Update task with the process ID for frontend tracking
                Task.objects.filter(id=task.id).update(celery_task_id=celery_result.id)

            transaction.on_commit(trigger_ai)

        return task