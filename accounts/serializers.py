from rest_framework import serializers
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .utils import send_verification_email

User = get_user_model()

# class RegisterSerializer(serializers.ModelSerializer):
#     password = serializers.CharField(write_only=True, min_length=6)

#     class Meta:
#         model = User
#         fields = ['id', 'fname', 'lname', 'email', 'phone', 'password']
#         extra_kwargs = {'password': {'write_only': True}}

#     def create(self, validated_data):
#         password = validated_data.pop('password', None)
#         user = User.objects.create(**validated_data)
#         if password:
#             user.set_password(password)
#         user.save()
#         return user


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model = User
        fields = ['id', 'fname', 'lname', 'email', 'phone', 'password']

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        user = User.objects.create(**validated_data)
        if password:
            user.set_password(password)
        user.is_verified = False  # Ensure user is not verified initially
        user.save()
        
        # Send email verification
        request = self.context.get("request")  # Get the request object
        send_verification_email(user, request)

        return user

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        if not user.is_verified:
            raise serializers.ValidationError("Email is not verified. Please check your inbox.")

        token = super().get_token(user)
        token["fname"] = user.fname
        token["lname"] = user.lname
        token["email"] = user.email
        
        return token
