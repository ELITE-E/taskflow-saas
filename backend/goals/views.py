from django.shortcuts import render

# Create your views here.
# goals/views.py

from rest_framework import generics, permissions
from .models import Goal
from .serializers import GoalSerializer

class GoalOwnerPermission(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object to edit or delete it.
    Read permissions are handled by the queryset filtering.
    """
    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any request authenticated user
        if request.method in permissions.SAFE_METHODS:
            return True
            
        # Write permissions are only allowed to the owner of the goal
        return obj.user == request.user

class GoalListCreateView(generics.ListCreateAPIView):
    """
    GET: List all goals for the authenticated user.
    POST: Create a new goal for the authenticated user.
    """
    serializer_class = GoalSerializer
    permission_classes = [permissions.IsAuthenticated]

    # CRITICAL: Ensures users only see their own goals
    def get_queryset(self):
        return Goal.objects.filter(user=self.request.user, is_archived=False)

list_create_view=GoalListCreateView.as_view()

    # Note: We override the serializer's create method to automatically set the user, 
    # so we don't need to override perform_create here.

class GoalRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET, PUT, PATCH, DELETE for a specific goal instance.
    """
    serializer_class = GoalSerializer
    permission_classes = [permissions.IsAuthenticated, GoalOwnerPermission]
    
    # We use this queryset to ensure a user can only retrieve/update goals they own.
    # The get_object() method will filter against this base queryset.
    def get_queryset(self):
        return Goal.objects.filter(user=self.request.user)
    
retreive_update_destroy_view=GoalRetrieveUpdateDestroyView.as_view()