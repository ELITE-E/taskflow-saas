from django.shortcuts import render

# Create your views here.
from datetime import date
from rest_framework import generics, permissions
from .models import Task
from .serializers import TaskSerializer

class TaskOwnerPermission(permissions.BasePermission):
    """
    Custom permission to only allow owners of a Task to view, edit, or delete it.
    """
    def has_object_permission(self, request, view, obj):
        return obj.user == request.user

class TaskListCreateView(generics.ListCreateAPIView):
    """
    GET: List all active tasks for the authenticated user, sorted by due_date.
    POST: Create a new task.
    """
    serializer_class = TaskSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = Task.objects.all()

    def get_queryset(self):
        # ensure user only sees own tasks
        return Task.objects.filter(user=self.request.user)

list_create_view=TaskListCreateView.as_view()

class TaskRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET, PUT, PATCH, DELETE for a specific task instance. 
    Used for marking tasks as complete (PATCH is_completed=True).
    """
    serializer_class = TaskSerializer
    permission_classes = [permissions.IsAuthenticated, TaskOwnerPermission]
    
    # Ensures the user can only access tasks they own.
    def get_queryset(self):
        return Task.objects.filter(user=self.request.user)
    
retreive_update_destroy_view=TaskRetrieveUpdateDestroyView.as_view()


    
class PrioritizedTaskListView(generics.ListAPIView):
    """
    Returns a list of tasks that have completed the AI prioritization pipeline.
    Ordered by priority_score descending.
    """
    serializer_class = TaskSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Task.objects.filter(
            user=self.request.user,
            is_prioritized=True,
            is_completed=False
        ).order_by('-priority_score')
    
tasks_list_view=PrioritizedTaskListView.as_view()