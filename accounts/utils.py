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

    subject = "Verify your email"
    message = f"Hi {user.fname},\n\nClick the link below to verify your email:\n{verification_link}\n\nThanks!"
    
    send_mail(subject, message, settings.EMAIL_HOST_USER, [user.email])
