from django.urls import path
from .views import (list_create_view,retreive_update_destroy_view)

urlpatterns=[
    # GET and POST (List active tasks and Create new task)
    path('',list_create_view,name="Create-list-view"),

    # GET, PUT, PATCH, DELETE (Detail and Manipulation)
    path('<int:pk>/',retreive_update_destroy_view,name="detail-list")
]