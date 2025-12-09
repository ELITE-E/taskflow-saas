from django.shortcuts import render

from rest_framework import generics
from rest_framework.permissions import AllowAny
from .serializers import RegisterSerializer
# Create your views here.

class RegisterAPIView(generics.CreateAPIView):
    serializer_class=RegisterSerializer
    permission_classes=[AllowAny]

register_api_view=RegisterAPIView.as_view()