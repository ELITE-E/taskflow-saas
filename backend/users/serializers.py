from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

#Dynamically retrieve user model created in settings.py
User=get_user_model

class UserRegistrationSerializer(serializers.ModelSerializer):
    password=serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password]
    )

    password2=serializers.CharField(write_only=True,required=True)

    class Meta:
        model=User

        fields=(
            'email',
            'username',
            'password',
            'password2',
            'first_name',
            'last_name',
            'timezone'

        )
        # Ensure these are required inputs
        extra_kwargs = {
            'email': {'required': True},
            'username': {'required': True},
            'first_name': {'required': True},
            'last_name': {'required': True},
        }

    def validate(self, attrs):
        # 1. Password Match Validation
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        
        # 2. Strong Email/Username Validation (Model's unique constraint handles uniqueness)
        try:
            # Leverage the validation from the User Manager (will raise ValueError if email is empty)
            get_user_model().objects.normalize_email(attrs['email'])
        except ValueError as e:
            raise serializers.ValidationError({"email": str(e)})

        return attrs

    def create(self, validated_data):
        validated_data.pop('password2')
        
        # Use the custom manager's creation method
        user = User.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password'],
            username=validated_data['username'],
            first_name=validated_data.get('first_name'),
            last_name=validated_data.get('last_name'),
            timezone=validated_data.get('timezone', 'UTC'),
        )
        return user
    
# users/serializers.py (Ensure this is present)

class UserDetailsSerializer(serializers.ModelSerializer):
    """
    Docstring for UserDetailSeralizer
    Serializer for returning authenticated user details
    """
    class Meta:
        model=User
        fields=(
            'id',
            'email',
            'username',
            'first_name',
            'last_name',
            'timezone'
        )
        read_only_fields=fields

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Customizes the TokenObtainPairSerializer to use 'email' 
    instead of 'username' for the authentication field.
    """
    # Overriding the default `username_field` to 'email' ensures the serializer
    # looks up the user based on the email provided in the login payload.
    username_field = 'email' 
    
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        # Add custom claims to the token payload (accessible in the frontend)
        token['email'] = user.email 
        token['full_name'] = user.get_full_name()
        return token