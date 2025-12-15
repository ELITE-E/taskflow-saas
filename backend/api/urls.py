from django.urls import path,include

urlpatterns=[
    path('v1/auth/',include('users.urls')),
    path('v1/goals/',include('goals.urls')),
    path('v1/tasks/',include('tasks.urls'))
]