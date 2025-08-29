import random
import string
from django.core.mail import send_mail
from django.conf import settings
from .tasks import send_invitation_email_task


def generate_random_password(length=10):
    chars = string.ascii_letters + string.digits + string.punctuation
    return ''.join(random.choices(chars, k=length))

def send_invitation_email(user, temp_password):
    # Call the Celery task asynchronously
    send_invitation_email_task.delay(user.email, user.fname, temp_password)