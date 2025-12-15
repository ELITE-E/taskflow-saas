# goals/serializers.py

from rest_framework import serializers
from .models import Goal

class GoalSerializer(serializers.ModelSerializer):
    # Field to represent the user's email read-only for display purposes
    user_email = serializers.ReadOnlyField(source='user.email') 

    class Meta:
        model = Goal
        fields = (
            'id', 'user', 'user_email', 'title', 'description', 
            'weight', 'created_at', 'updated_at', 'is_archived'
        )
        read_only_fields = ('id', 'user', 'created_at', 'updated_at')

    # This method is CRITICAL for security: it assigns the current user before saving.
    def create(self, validated_data):
        # We retrieve the user from the view's context (request.user)
        user = self.context['request'].user
        if not user.is_authenticated:
            # Should not happen with IsAuthenticated permission, but is a safe guard
            raise serializers.ValidationError("Authentication required to create a goal.")
            
        validated_data['user'] = user
        return super().create(validated_data)