import random
import string
from django.core.mail import send_mail
from django.conf import settings
from .tasks import send_invitation_email_task
import docx
from PyPDF2 import PdfReader


def generate_random_password(length=10):
    chars = string.ascii_letters + string.digits + string.punctuation
    return ''.join(random.choices(chars, k=length))

def send_invitation_email(user, temp_password):
    # Call the Celery task asynchronously
    send_invitation_email_task.delay(user.email, user.fname, temp_password)
    



def extract_text_from_file(file):
    try:
        # Reset pointer (important for re-reading)
        file.seek(0)

        if file.name.endswith('.pdf'):
            reader = PdfReader(file)
            text = " ".join(page.extract_text() or "" for page in reader.pages)
            return text.strip()

        elif file.name.endswith('.docx'):
            doc = docx.Document(file)
            return " ".join(p.text for p in doc.paragraphs).strip()

        else:
            return ""
    except Exception as e:
        print(f"[ERROR] Failed to extract resume text from {file.name}: {e}")
        return ""