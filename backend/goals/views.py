# goals/views.py
"""
Goals App Views
===============

API views for Goals and Strategic Weights management.
"""

import logging

from django.db import transaction
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Goal, GoalWeights
from .serializers import GoalSerializer, GoalWeightsSerializer

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# PERMISSIONS
# ---------------------------------------------------------------------------

class GoalOwnerPermission(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object to edit or delete it.
    """
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.user == request.user


# ---------------------------------------------------------------------------
# GOAL VIEWS
# ---------------------------------------------------------------------------

class GoalListCreateView(generics.ListCreateAPIView):
    """
    GET: List all non-archived goals for the authenticated user.
    POST: Create a new goal for the authenticated user.
    """
    serializer_class = GoalSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Goal.objects.filter(user=self.request.user, is_archived=False)


list_create_view = GoalListCreateView.as_view()


class GoalRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET, PUT, PATCH, DELETE for a specific goal instance.
    """
    serializer_class = GoalSerializer
    permission_classes = [permissions.IsAuthenticated, GoalOwnerPermission]
    
    def get_queryset(self):
        return Goal.objects.filter(user=self.request.user)


retreive_update_destroy_view = GoalRetrieveUpdateDestroyView.as_view()


# ---------------------------------------------------------------------------
# STRATEGIC WEIGHTS VIEWS
# ---------------------------------------------------------------------------

class WeightsRetrieveUpdateView(APIView):
    """
    API endpoint for managing user's strategic weights.
    
    Endpoints:
    ----------
    GET /api/v1/goals/weights/
        Retrieve the current user's strategic weights.
        Creates default weights (0.25 each) if none exist.
    
    PATCH /api/v1/goals/weights/
        Update strategic weights. Partial updates are supported.
        Validation ensures weights sum to exactly 1.0.
    
    Validation:
    -----------
    - Each weight must be between 0.0 and 1.0
    - The sum of all weights must equal 1.0 (within epsilon 0.001)
    - Invalid sums return 400 Bad Request with detailed error
    
    Response Format:
    ----------------
    {
        "id": 1,
        "work_bills": 0.25,
        "study": 0.25,
        "health": 0.25,
        "relationships": 0.25,
        "total_sum": 1.0,
        "is_valid_sum": true
    }
    """
    
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """
        Retrieve the current user's strategic weights.
        
        Creates default weights if none exist (lazy initialization).
        """
        user = request.user
        
        # Get or create weights for the user
        weights, created = GoalWeights.objects.get_or_create(
            user=user,
            defaults={
                'work_bills': 0.25,
                'study': 0.25,
                'health': 0.25,
                'relationships': 0.25,
            }
        )
        
        if created:
            logger.info(f"Created default weights for user {user.id}")
        
        serializer = GoalWeightsSerializer(weights)
        return Response(serializer.data)

    def patch(self, request):
        """
        Update strategic weights with strict validation.
        
        The update is wrapped in a database transaction to ensure atomicity.
        Model-level validation (full_clean) is explicitly called.
        
        Request Body (all fields optional, but sum must equal 1.0):
        {
            "work_bills": 0.40,
            "study": 0.30,
            "health": 0.20,
            "relationships": 0.10
        }
        
        Error Response (400 Bad Request):
        {
            "non_field_errors": ["The sum of all weights must be exactly 1.0. Current sum: 0.8"],
            "total_sum": 0.8
        }
        """
        user = request.user
        
        # Get existing weights or return 404
        try:
            weights = GoalWeights.objects.get(user=user)
        except GoalWeights.DoesNotExist:
            # Create default weights first
            weights = GoalWeights.objects.create(
                user=user,
                work_bills=0.25,
                study=0.25,
                health=0.25,
                relationships=0.25,
            )
        
        serializer = GoalWeightsSerializer(
            weights,
            data=request.data,
            partial=True,
            context={'request': request}
        )
        
        if not serializer.is_valid():
            logger.warning(
                f"Invalid weights update for user {user.id}: {serializer.errors}"
            )
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Wrap update in transaction for atomicity
        with transaction.atomic():
            try:
                updated_weights = serializer.save()
                logger.info(
                    f"Updated weights for user {user.id}: "
                    f"work={updated_weights.work_bills}, "
                    f"study={updated_weights.study}, "
                    f"health={updated_weights.health}, "
                    f"relationships={updated_weights.relationships}"
                )
            except Exception as e:
                logger.error(f"Failed to update weights for user {user.id}: {e}")
                return Response(
                    {'error': str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        return Response(GoalWeightsSerializer(updated_weights).data)

    def put(self, request):
        """
        Full update of strategic weights (all fields required).
        
        Delegates to PATCH for consistency.
        """
        return self.patch(request)


weights_view = WeightsRetrieveUpdateView.as_view()