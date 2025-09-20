# api/tasks.py
from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings


@shared_task
def send_invitation_email_task(user_email, fname, temp_password):
    subject = "Welcome to NexHR - Your Account Details"
    message = f"""Hi {fname},

Your NexHR account has been created.

Login Email: {user_email}
Temporary Password: {temp_password}

Please log in and change your password as soon as possible.

Thanks,
NexHR Team
"""
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [user_email],
        fail_silently=False,
    )
