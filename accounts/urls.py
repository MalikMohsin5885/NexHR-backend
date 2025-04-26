from django.urls import path, include
from rest_framework_simplejwt.views import TokenRefreshView
from .views import RegisterView, CustomTokenObtainPairView, VerifyEmailView, UserView, PasswordResetRequestView, PasswordResetConfirmView, CompanyCreateView, AuthenticatedUserView
from django.urls import path
from .views import GoogleLogin


urlpatterns = [
    path("users/", UserView.as_view(), name="list_user"),
    
    path("profile/", AuthenticatedUserView.as_view(), name='authenticated-user'),
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", CustomTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("verify-email/<uidb64>/<token>/", VerifyEmailView.as_view(), name="verify-email"),
    
    path("google/", GoogleLogin.as_view(), name="google_login"),
    # path("google/callback/", GoogleLoginCallback.as_view(), name="google_login_callback"),  # callback used if we used auth lib so that other tables also included 
    
    path("forgot-password/", PasswordResetRequestView.as_view(), name="forgot-password"),
    path("reset-password/<uidb64>/<token>/", PasswordResetConfirmView.as_view(), name="reset-password"),
    
    # company registration
    path('register-company/', CompanyCreateView.as_view(), name='register-company'),
]