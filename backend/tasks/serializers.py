# tasks/serializers.py

from django.db import transaction
from rest_framework import serializers
from .models import Task
import logging

logger = logging.getLogger(__name__)

class TaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        # explicit whitelist: only user-truth fields + system-read fields required by UI
        fields = [
            'id', 'title', 'description', 'goal', 'due_date', 'effort_estimate',
            'is_prioritized', 'importance_score', 'urgency_score', 'quadrant', 'rationale',
            'is_completed', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'is_prioritized', 'importance_score', 'urgency_score',
            'quadrant', 'rationale', 'created_at', 'updated_at'
        ]

    def validate_effort_estimate(self, value):
        if not (1 <= value <= 5):
            raise serializers.ValidationError("effort_estimate must be an integer between 1 and 5.")
        return value

    def create(self, validated_data):
        """
        Persist the task with the authenticated user, then enqueue the background
        prioritization job with minimal context (task_id, user_id). Do NOT compute
        weights or call AI here.
        """
        user = self.context['request'].user
        if not user or not user.is_authenticated:
            raise serializers.ValidationError("Authentication required to create a task.")

        # Persist task in DB; transaction ensures on_commit trigger enqueues job only after commit.
        with transaction.atomic():
            task = Task.objects.create(user=user, **validated_data)

            # Enqueue Celery worker after transaction commit with minimal context.
            def trigger_ai():
                from .ai_engine.celery_tasks import run_ai_relevance_scoring
                # Pass only the task id and user id. Worker will fetch required context.
                run_ai_relevance_scoring.delay(task.id, user.id)

            transaction.on_commit(trigger_ai)

        return task