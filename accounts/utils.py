from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.mail import send_mail
from django.urls import reverse
from django.conf import settings
from django.contrib.auth import get_user_model

User = get_user_model()

def send_verification_email(user, request):
    token = default_token_generator.make_token(user)
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    verification_link = request.build_absolute_uri(reverse("verify-email", kwargs={"uidb64": uid, "token": token}))
    # verification_link = request.build_absolute_uri("http://localhost:8080/login")

    subject = "Verify your email"
    message = f"Hi {user.fname},\n\nClick the link below to verify your email:\n{verification_link}\n\nThanks!"
    
    send_mail(subject, message, settings.EMAIL_HOST_USER, [user.email])


def send_reset_password_email(user, uid, token, request):
    # Use your frontend domain here, either via environment variable or hardcoded in dev
    frontend_url = "http://localhost:8080"  # Change to actual frontend domain in production
    reset_url = f"{frontend_url}/reset-password/{uid}/{token}/"

    subject = "Reset Your Password"
    message = f"Hi {user.fname},\n\nClick the link below to reset your password:\n{reset_url}\n\nIf you did not request this, ignore this email."

    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=False,
    )