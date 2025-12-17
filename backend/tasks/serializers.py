# tasks/serializers.py

from django.db import transaction
from rest_framework import serializers
from .models import Task
from .ai_engine.celery_tasks import run_ai_relevance_scoring

class TaskSerializer(serializers.ModelSerializer):
    # Field to return the Celery ID to the frontend for polling/tracking
    async_status_id = serializers.ReadOnlyField(source='celery_task_id')

    class Meta:
        model = Task
        fields = [
            'id', 'title', 'description', 'goal', 'due_date', 
            'is_prioritized', 'priority_score', 'async_status_id'
        ]
        read_only_fields = ['is_prioritized', 'priority_score']

    def create(self, validated_data: dict) -> Task:
        """
        Creates a task and triggers the AI orchestration pipeline.
        
        Uses an atomic transaction to ensure data integrity and triggers 
        Celery only after a successful DB commit.
        """
        user = self.context['request'].user
        
        # 1. Extract weights (In production, fetch from UserProfile or StrategicGoals model)
        # Here we use a placeholder dict; in a real app, you'd fetch user.profile.weights
        user_weights = {
            "work_bills": 0.8,
            "study": 0.5,
            "health": 0.4,
            "relationships": 0.3
        }

        with transaction.atomic():
            # 2. Save the initial Task record
            task = Task.objects.create(user=user, **validated_data)
            
            # 3. Define the async trigger logic
            def trigger_ai():
                celery_result = run_ai_relevance_scoring.delay(
                    task_id=task.id,
                    task_title=task.title,
                    task_description=task.description,
                    user_weights=user_weights
                )
                # Update task with the process ID for frontend tracking
                Task.objects.filter(id=task.id).update(celery_task_id=celery_result.id)

            # 4. Schedule the trigger for AFTER the DB transaction closes
            transaction.on_commit(trigger_ai)

        return task