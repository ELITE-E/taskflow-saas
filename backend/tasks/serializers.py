from rest_framework import serializers
from .models import Task

class TaskSerializer(serializers.ModelSerializer):
    # Read-only field for user identification
    user_email = serializers.ReadOnlyField(source='user.email') 

    goal_weight=serializers.ReadOnlyField(source='goal.weight')

    #Introducing the READONLY fields
    priority_score=serializers.ReadOnlyField()
    is_prioritized=serializers.ReadOnlyField()

    class Meta:
        model = Task
        fields = (
            'id', 'user', 'user_email', 'title', 'description', 
            'due_date', 'effort_estimate', 'is_completed', 
            'created_at', 'updated_at','goal','goal_weight',
            'priority_score','is_prioritized'
        )
        read_only_fields = ('id', 'user', 'is_prioritized','goal_weight','priority_score','created_at', 'updated_at')

    # Security measure: automatically assign the current authenticated user on creation.
    def create(self, validated_data):
        user = self.context['request'].user
        if not user.is_authenticated:
            raise serializers.ValidationError("Authentication required.")
            
        validated_data['user'] = user
        return super().create(validated_data)