# Create your views here.
from rest_framework.views import APIView
from rest_framework import  status
from rest_framework.response import Response
from .serializers import (UserRegistrationSerializer,
                           CustomTokenObtainPairSerializer,
                           UserDetailsSerializer
                        ) 
from rest_framework.permissions import AllowAny,IsAuthenticated

class RegisterView(APIView):
    """
    Handles user registration. On successful creation, it automatically
    logs the user in by generating and returning the Access and Refresh tokens.
    """
    serializer_class = UserRegistrationSerializer
    permission_classes = [AllowAny]
    
    def post(self, request, *args, **kwargs):
        # 1. Validate incoming registration data
        serializer = UserRegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save() # User is created here

        # 2. Prepare payload for auto-login
        # We need to construct a payload that the CustomTokenObtainPairSerializer can process
        token_payload = {
            # Use the user's email and password directly
            'email': user.email,
            'password': request.data['password'] # We must use the raw password from the request
        }

        # 3. Generate Tokens using the Custom Serializer
        # We instantiate the CustomTokenObtainPairSerializer with the auto-login data
        token_serializer = CustomTokenObtainPairSerializer(data=token_payload)
        
        try:
            token_serializer.is_valid(raise_exception=True)
        except Exception as e:
            # Should not happen if registration was successful, but good for robustness
            print(f"Token generation failed: {e}")
            return Response(
                {"detail": "User created but failed to generate token."}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # 4. Return Success Response with Tokens
        response_data = token_serializer.validated_data
        
        # Optionally, include basic user data in the response
        response_data['user'] = {
            'email': user.email,
            'username': user.username,
            'first_name': user.first_name,
        }
        
        return Response(response_data, status=status.HTTP_201_CREATED)


register_view=RegisterView.as_view()
class UserDetailAPIView(APIView):
    """
    Docstring for UserDetailAPIView
    Protected endpoint to verify token validity and return current user data.
    Requires a valid JWT Access Token.
    """
    permission_classes=[IsAuthenticated]
    def get(self,request,format=None,*args,**kwargs):
        # request.user is automatically populated by JWTAuthentication if token is valid
        serializer = UserDetailsSerializer(request.user)
        return Response(serializer.data)

user_detail_view=UserDetailAPIView.as_view() 