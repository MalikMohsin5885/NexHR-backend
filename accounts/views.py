# from rest_framework import generics, status
# from rest_framework.response import Response
# from rest_framework.permissions import AllowAny
# from rest_framework.views import APIView
# from rest_framework_simplejwt.views import TokenObtainPairView
# from rest_framework_simplejwt.tokens import RefreshToken
# from django.contrib.auth import get_user_model
# from django.utils.http import urlsafe_base64_decode
# from django.utils.encoding import force_str
# from django.contrib.auth.tokens import default_token_generator
# from django.conf import settings

# from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
# from allauth.socialaccount.providers.oauth2.client import OAuth2Client
# from dj_rest_auth.registration.views import SocialLoginView

# from .serializers import (
#     RegisterSerializer,
#     CustomTokenObtainPairSerializer,
#     UserListSerializer,
# )

# import requests


# User = get_user_model()


# def get_google_user_info(access_token):
#     """Helper function to fetch user info from Google."""
#     google_user_info_url = "https://www.googleapis.com/oauth2/v3/userinfo"
#     headers = {"Authorization": f"Bearer {access_token}"}
#     response = requests.get(google_user_info_url, headers=headers)
#     if response.status_code != 200:
#         return None
#     return response.json()


# def get_or_create_user_and_tokens(email, name):
#     """Helper function to create user and generate JWT tokens."""
#     user, created = User.objects.get_or_create(email=email, defaults={"fname": name})
#     refresh = RefreshToken.for_user(user)
#     return {
#         "message": "Google login successful",
#         "email": email,
#         "name": name,
#         "access": str(refresh.access_token),
#         "refresh": str(refresh),
#     }


# class GoogleLogin(SocialLoginView):
#     adapter_class = GoogleOAuth2Adapter
#     callback_url = settings.GOOGLE_OAUTH_CALLBACK_URL
#     client_class = OAuth2Client

#     def post(self, request, *args, **kwargs):
#         access_token = request.data.get("access_token")
#         if not access_token:
#             return Response({"error": "Access token is required."}, status=status.HTTP_400_BAD_REQUEST)

#         google_user = get_google_user_info(access_token)
#         if not google_user:
#             return Response({"error": "Failed to fetch user info from Google"}, status=status.HTTP_400_BAD_REQUEST)

#         email = google_user.get("email")
#         name = google_user.get("name")

#         data = get_or_create_user_and_tokens(email, name)
#         data["profile_picture"] = google_user.get("picture")

#         return Response(data, status=status.HTTP_200_OK)


# class GoogleLoginCallback(APIView):
#     permission_classes = [AllowAny]

#     def post(self, request, *args, **kwargs):
#         access_token = request.data.get("access_token")
#         if not access_token:
#             return Response({"error": "Access token is required."}, status=status.HTTP_400_BAD_REQUEST)

#         google_user = get_google_user_info(access_token)
#         if not google_user:
#             return Response({"error": "Failed to fetch user info from Google"}, status=status.HTTP_400_BAD_REQUEST)

#         email = google_user.get("email")
#         name = google_user.get("name")

#         data = get_or_create_user_and_tokens(email, name)
#         data["profile_picture"] = google_user.get("picture")

#         return Response(data, status=status.HTTP_200_OK)



# class VerifyEmailView(APIView):
#     def get(self, request, uidb64, token):
#         try:
#             uid = force_str(urlsafe_base64_decode(uidb64))
#             user = User.objects.get(pk=uid)
#         except (TypeError, ValueError, OverflowError, User.DoesNotExist):
#             return Response({"error": "Invalid token or user ID"}, status=status.HTTP_400_BAD_REQUEST)

#         if user.is_verified:
#             return Response({"message": "Email already verified"}, status=status.HTTP_200_OK)

#         if default_token_generator.check_token(user, token):
#             user.is_verified = True
#             user.save()
#             return Response({"message": "Email successfully verified"}, status=status.HTTP_200_OK)
#         else:
#             return Response({"error": "Invalid or expired token"}, status=status.HTTP_400_BAD_REQUEST)
        



# class RegisterView(generics.CreateAPIView):
#     queryset = User.objects.all()
#     serializer_class = RegisterSerializer
#     permission_classes = [AllowAny]

#     def create(self, request, *args, **kwargs):
#         response = super().create(request, *args, **kwargs)
#         user = User.objects.get(email=request.data["email"])
#         return response

# # class RegisterView(generics.CreateAPIView):
# #     queryset = User.objects.all()
# #     serializer_class = RegisterSerializer
# #     permission_classes = [AllowAny]

# class UserView(generics.ListAPIView):
#     queryset = User.objects.all()
#     serializer_class = UserListSerializer
#     permission_classes = [AllowAny]

# class CustomTokenObtainPairView(TokenObtainPairView):
#     serializer_class = CustomTokenObtainPairSerializer







from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_str
from django.contrib.contenttypes.models import ContentType

from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from .serializers import RegisterSerializer, CustomTokenObtainPairSerializer, UserListSerializer, PasswordResetRequestSerializer, CompanySerializer, UserProfileSerializer

from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.socialaccount.providers.oauth2.client import OAuth2Client

from dj_rest_auth.registration.views import SocialLoginView
from rest_framework_simplejwt.tokens import RefreshToken
from django.shortcuts import redirect

from .models import Company, Department

import requests

User = get_user_model()

class GoogleLogin(SocialLoginView):
    adapter_class = GoogleOAuth2Adapter
    callback_url = settings.GOOGLE_OAUTH_CALLBACK_URL
    client_class = OAuth2Client

    def post(self, request, *args, **kwargs):
        access_token = request.data.get("access_token")
        if not access_token:
            return Response({"error": "Access token is required."}, status=status.HTTP_400_BAD_REQUEST)

        # Fetch user info from Google API
        headers = {"Authorization": f"Bearer {access_token}"}
        google_response = requests.get("https://www.googleapis.com/oauth2/v3/userinfo", headers=headers)

        if google_response.status_code != 200:
            return Response({"error": "Failed to fetch user info from Google"}, status=status.HTTP_400_BAD_REQUEST)

        google_user = google_response.json()
        email = google_user.get("email")
        name = google_user.get("name")
        profile_picture = google_user.get("picture")

        first_name, *rest = name.strip().split()
        last_name = " ".join(rest) if rest else None
        
        user, created = User.objects.get_or_create(email=email, defaults={"fname": first_name, "lname" : last_name})
        user.login_method = 'google'
        user.is_verified = True
        user.save()
        
        refresh = RefreshToken.for_user(user)

        return Response({
            "message": "Google login successful",
            "email": email,
            "name": name,
            "profile_picture": profile_picture,
            "access": str(refresh.access_token),
            "refresh": str(refresh),
        })


class VerifyEmailView(APIView):
    def get(self, request, uidb64, token):
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return Response({"error": "Invalid token or user ID"}, status=status.HTTP_400_BAD_REQUEST)

        if user.is_verified:
            return Response({"message": "Email already verified"}, status=status.HTTP_200_OK)

        if default_token_generator.check_token(user, token):
            user.is_verified = True
            user.save()
            return redirect("http://localhost:8080/login")

            # return Response({"message": "Email successfully verified"}, status=status.HTTP_200_OK)
        else:
            return Response({"error": "Invalid or expired token"}, status=status.HTTP_400_BAD_REQUEST)

    
class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            {"message": "User registered successfully. Please verify your email."},
            status=status.HTTP_201_CREATED
        )


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "Password reset email sent."}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, uidb64, token):
        password = request.data.get("password")
        print("reset password ",password)
        if not password or len(password) < 6:
            return Response({"error": "Password must be at least 6 characters."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return Response({"error": "Invalid token or user ID."}, status=status.HTTP_400_BAD_REQUEST)

        if default_token_generator.check_token(user, token):
            user.set_password(password)
            user.save()
            return Response({"message": "Password has been reset successfully."}, status=status.HTTP_200_OK)
        else:
            return Response({"error": "Invalid or expired token."}, status=status.HTTP_400_BAD_REQUEST)

# generic api view
class UserView(generics.ListAPIView):
    queryset = User.objects.all()
    serializer_class = UserListSerializer
    permission_classes = [AllowAny]

class AuthenticatedUserView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserProfileSerializer(request.user)
        return Response(serializer.data)

    
# comapny registration
class CompanyCreateView(generics.CreateAPIView):
    queryset = Company.objects.all()
    serializer_class = CompanySerializer
    permission_classes = [IsAuthenticated]
    
    def perform_create(self, serializer):
        # Step 1: Create the company
        company = serializer.save()

        # Step 2: Create HR department linked to this company via polymorphic relation
        content_type = ContentType.objects.get_for_model(Company)
        hr_department = Department.objects.create(
            name="HR",
            content_type=content_type,
            object_id=company.id
        )

        # Step 3: Assign company and HR department to the current user
        user = self.request.user
        user.company = company
        user.department = hr_department  # assumes `User` model has `department = models.ForeignKey(Department, null=True, blank=True, on_delete=models.SET_NULL)`
        user.save()
        
        