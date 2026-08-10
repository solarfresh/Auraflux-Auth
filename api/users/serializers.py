from adrf.serializers import ModelSerializer, Serializer
from django.contrib.auth import get_user_model
from rest_framework import serializers

User = get_user_model()


class LoginRequestSerializer(Serializer):
    """Defines the expected input fields for the Login endpoint."""
    username = serializers.CharField(max_length=150, required=True, help_text="User's unique username.")
    password = serializers.CharField(required=True, help_text="User's password.")


class LoginResponseSerializer(Serializer):
    """Defines the expected successful response body."""
    message = serializers.CharField(default='Login successful.')
    username = serializers.CharField(max_length=150)
    # Note: Tokens are set in HttpOnly cookies and not returned in the body.


class UserSerializer(ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'password')
        extra_kwargs = {'email': {'required': True, 'allow_blank': False}}

    def create(self, validated_data):
        # Hash the password and create the user
        password = validated_data.pop('password')
        user = User.objects.create_user(password=password, **validated_data)
        return user