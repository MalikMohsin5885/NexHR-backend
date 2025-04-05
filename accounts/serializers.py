from rest_framework import serializers
from django.contrib.auth import get_user_model, authenticate
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .utils import send_verification_email
from .utils import send_reset_password_email
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

User = get_user_model()
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

# class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
#     @classmethod
#     def get_token(cls, user):
#         if not user.is_verified:
#             raise serializers.ValidationError("Email is not verified. Please check your inbox.")

#         token = super().get_token(user)
#         token["fname"] = user.fname
#         token["lname"] = user.lname
#         token["email"] = user.email
        
#         return token

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        email = attrs.get('email', '').lower()
        password = attrs.get('password', '')

        user = authenticate(email=email, password=password)
        if user is None:
            raise serializers.ValidationError("Invalid email or password.")

        if not user.is_verified:
            raise serializers.ValidationError("Email is not verified. Please check your inbox.")

        refresh = self.get_token(user)

        return {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
        }

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["fname"] = user.fname
        token["lname"] = user.lname
        token["email"] = user.email
        return token

class UserListSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'fname', 'lname', 'phone', 'is_verified', 'company_id']


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        try:
            user = User.objects.get(email=value)
            if not user.is_verified:
                raise serializers.ValidationError("Email is not verified.")
            return value
        except User.DoesNotExist:
            raise serializers.ValidationError("User with this email does not exist.")

    def save(self):
        email = self.validated_data['email']
        user = User.objects.get(email=email)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        request = self.context.get('request')

        send_reset_password_email(user, uid, token, request)     
