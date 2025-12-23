from django.urls import path
from .views import RegisterView,user_detail_view
from rest_framework_simplejwt.views import (TokenRefreshView,
                                            TokenObtainPairView)# We still import the base TokenObtainPairView
from .serializers import CustomTokenObtainPairSerializer 


urlpatterns = [
    # Custom registration endpoiNT
    path('register/',RegisterView, name='auth_register'),
    
    # Simple JWT login endpoint, customized to use the email field
    # We pass the custom serializer to the view
    path(
        'login/', 
        TokenObtainPairView.as_view(serializer_class=CustomTokenObtainPairSerializer), 
        name='token_obtain_pair'
    ),
    
    # TokenRefreshView 
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('user/',user_detail_view ,name='user_detail')
]