from django.urls import path
from .views import list_create_view
from .views import retreive_update_destroy_view
from .views  import tasks_list_view

urlpatterns=[
    # GET and POST (List active tasks and Create new task)
    path('',list_create_view,name="create-list-view"),

    path('prioritized-list/',tasks_list_view,name="prioritized-list"),
    
    # GET, PUT, PATCH, DELETE (Detail and Manipulation)
    path('<int:pk>/',retreive_update_destroy_view,name="task-detail")

]