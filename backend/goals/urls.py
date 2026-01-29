# goals/urls.py
"""
Goals App URL Configuration
===========================

URL patterns for Goals and Strategic Weights APIs.
"""

from django.urls import path
from .views import list_create_view, retreive_update_destroy_view, weights_view

urlpatterns = [
    # ----- GOALS ENDPOINTS -----
    # GET: List all goals / POST: Create new goal
    path('', list_create_view, name='goal-list-create'), 
    
    # GET/PUT/PATCH/DELETE: Individual goal operations
    path('<int:pk>/', retreive_update_destroy_view, name='goal-detail'), 
    
    # ----- STRATEGIC WEIGHTS ENDPOINTS -----
    # GET: Retrieve current weights / PATCH/PUT: Update weights
    path('weights/', weights_view, name='goal-weights'),
]