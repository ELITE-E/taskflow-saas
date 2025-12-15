# goals/urls.py

from django.urls import path
from .views import list_create_view, retreive_update_destroy_view

urlpatterns = [
    # GET and POST (List and Create)
    path('', list_create_view, name='goal-list-create'), 
    
    # GET, PUT, PATCH, DELETE (Detail and Manipulation)
    path('<int:pk>/', retreive_update_destroy_view, name='goal-detail'), 
]