import random
import string
from django.core.mail import send_mail
from django.conf import settings

def generate_random_password(length=10):
    chars = string.ascii_letters + string.digits + string.punctuation
    return ''.join(random.choices(chars, k=length))

def send_invitation_email(user, temp_password):
    subject = "Welcome to NexHR - Your Account Details"
    message = f"""Hi {user.fname},

Your NexHR account has been created.

Login Email: {user.email}
Temporary Password: {temp_password}

Please log in and change your password as soon as possible.

Thanks,
NexHR Team
"""

    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=False,
    )
