from rest_framework import serializers
from .models import Task

class TaskSerializer(serializers.ModelSerializer):
    # Read-only field for user identification
    user_email = serializers.ReadOnlyField(source='user.email') 

    class Meta:
        model = Task
        fields = (
            'id', 'user', 'user_email', 'title', 'description', 
            'due_date', 'effort_estimate', 'is_completed', 
            'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'user', 'created_at', 'updated_at')

    # Security measure: automatically assign the current authenticated user on creation.
    def create(self, validated_data):
        user = self.context['request'].user
        if not user.is_authenticated:
            raise serializers.ValidationError("Authentication required.")
            
        validated_data['user'] = user
        return super().create(validated_data)