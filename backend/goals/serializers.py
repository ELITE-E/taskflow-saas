# goals/serializers.py
"""
Goals App Serializers
=====================

Serializers for the Goals and GoalWeights models.
"""

from decimal import Decimal, ROUND_HALF_UP
from rest_framework import serializers
from django.core.exceptions import ValidationError as DjangoValidationError
from .models import Goal, GoalWeights


# ---------------------------------------------------------------------------
# GOAL SERIALIZER
# ---------------------------------------------------------------------------

class GoalSerializer(serializers.ModelSerializer):
    """
    Serializer for the Goal model.
    
    Handles CRUD operations for individual goals.
    """
    # Field to represent the user's email read-only for display purposes
    user_email = serializers.ReadOnlyField(source='user.email') 

    class Meta:
        model = Goal
        fields = (
            'id', 'user', 'user_email', 'title', 'description', 
            'weight', 'created_at', 'updated_at', 'is_archived'
        )
        read_only_fields = ('id', 'user', 'created_at', 'updated_at')

    def create(self, validated_data):
        """
        Assigns the current user before saving.
        
        This is CRITICAL for security: prevents users from creating
        goals under other users' accounts.
        """
        user = self.context['request'].user
        if not user.is_authenticated:
            raise serializers.ValidationError("Authentication required to create a goal.")
            
        validated_data['user'] = user
        return super().create(validated_data)


# ---------------------------------------------------------------------------
# GOAL WEIGHTS SERIALIZER
# ---------------------------------------------------------------------------

class GoalWeightsSerializer(serializers.ModelSerializer):
    """
    Serializer for the GoalWeights model.
    
    Handles the user's strategic weight configuration with strict validation:
    - All weights must be between 0.0 and 1.0
    - The sum of all weights must equal exactly 1.0 (within epsilon)
    
    Normalization Math:
    -------------------
    Weights represent the relative importance of life domains:
        work_bills + study + health + relationships = 1.0 (100%)
    
    Example: A work-focused user might have:
        work_bills: 0.50 (50%)
        study: 0.20 (20%)
        health: 0.20 (20%)
        relationships: 0.10 (10%)
    """
    
    # Computed field showing the current sum (helpful for UI)
    total_sum = serializers.SerializerMethodField()
    
    # Computed field indicating if weights are valid
    is_valid_sum = serializers.SerializerMethodField()

    class Meta:
        model = GoalWeights
        fields = (
            'id',
            'work_bills',
            'study',
            'health',
            'relationships',
            'total_sum',
            'is_valid_sum',
        )
        read_only_fields = ('id', 'total_sum', 'is_valid_sum')

    def get_total_sum(self, obj: GoalWeights) -> float:
        """
        Calculate the sum of all weights.
        
        Returns a rounded value to avoid floating-point display issues.
        """
        total = obj.work_bills + obj.study + obj.health + obj.relationships
        # Round to 4 decimal places to avoid 0.25000000001 type issues
        return round(total, 4)

    def get_is_valid_sum(self, obj: GoalWeights) -> bool:
        """
        Check if weights sum to exactly 1.0 (within epsilon).
        """
        total = obj.work_bills + obj.study + obj.health + obj.relationships
        return 0.999 <= total <= 1.001

    def validate_work_bills(self, value: float) -> float:
        """Validate and normalize work_bills weight."""
        return self._validate_weight(value, 'work_bills')

    def validate_study(self, value: float) -> float:
        """Validate and normalize study weight."""
        return self._validate_weight(value, 'study')

    def validate_health(self, value: float) -> float:
        """Validate and normalize health weight."""
        return self._validate_weight(value, 'health')

    def validate_relationships(self, value: float) -> float:
        """Validate and normalize relationships weight."""
        return self._validate_weight(value, 'relationships')

    def _validate_weight(self, value: float, field_name: str) -> float:
        """
        Validate a single weight value.
        
        - Must be a valid number
        - Must be between 0.0 and 1.0
        - Rounds to 4 decimal places for precision
        """
        try:
            value = float(value)
        except (TypeError, ValueError):
            raise serializers.ValidationError(
                f"{field_name} must be a valid number."
            )
        
        if value < 0.0 or value > 1.0:
            raise serializers.ValidationError(
                f"{field_name} must be between 0.0 and 1.0."
            )
        
        # Round to 4 decimal places to prevent floating-point issues
        return round(value, 4)

    def validate(self, attrs: dict) -> dict:
        """
        Cross-field validation: ensure weights sum to 1.0.
        
        This is called after individual field validation.
        We need to consider both new values and existing instance values.
        """
        # Get current instance values as defaults
        instance = self.instance
        
        work_bills = attrs.get('work_bills', instance.work_bills if instance else 0.25)
        study = attrs.get('study', instance.study if instance else 0.25)
        health = attrs.get('health', instance.health if instance else 0.25)
        relationships = attrs.get('relationships', instance.relationships if instance else 0.25)
        
        total = work_bills + study + health + relationships
        
        # Check sum within epsilon (accounts for floating-point imprecision)
        if not (0.999 <= total <= 1.001):
            raise serializers.ValidationError({
                'non_field_errors': [
                    f"The sum of all weights must be exactly 1.0. Current sum: {round(total, 4)}"
                ],
                'total_sum': round(total, 4),
            })
        
        return attrs

    def update(self, instance: GoalWeights, validated_data: dict) -> GoalWeights:
        """
        Update weights with additional model-level validation.
        
        Calls full_clean() to trigger Django's model validation
        before saving to the database.
        """
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        try:
            # Trigger model validation (includes sum check)
            instance.full_clean()
        except DjangoValidationError as e:
            # Convert Django ValidationError to DRF ValidationError
            raise serializers.ValidationError(e.message_dict if hasattr(e, 'message_dict') else str(e))
        
        instance.save()
        return instance

    def create(self, validated_data: dict) -> GoalWeights:
        """
        Create new GoalWeights instance for the authenticated user.
        """
        user = self.context['request'].user
        
        # Check if user already has weights configured
        if GoalWeights.objects.filter(user=user).exists():
            raise serializers.ValidationError(
                "User already has weights configured. Use PATCH to update."
            )
        
        validated_data['user'] = user
        instance = GoalWeights(**validated_data)
        
        try:
            instance.full_clean()
        except DjangoValidationError as e:
            raise serializers.ValidationError(e.message_dict if hasattr(e, 'message_dict') else str(e))
        
        instance.save()
        return instance