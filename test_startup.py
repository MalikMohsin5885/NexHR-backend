#!/usr/bin/env python3
"""
Simple Django startup test
"""
import os
import sys

# Minimal Django test without database
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nexhr_backend.settings')
os.environ.setdefault('DEBUG', 'False')

try:
    import django
    from django.conf import settings
    
    # Setup Django
    django.setup()
    
    print("✅ Django setup successful!")
    print(f"DEBUG: {settings.DEBUG}")
    print(f"SECRET_KEY: {'***' if settings.SECRET_KEY else 'NOT SET'}")
    print(f"ALLOWED_HOSTS: {settings.ALLOWED_HOSTS}")
    
    # Test if we can import WSGI application
    from nexhr_backend.wsgi import application
    print("✅ WSGI application import successful!")
    
    print("🎉 Container should be able to start!")
    
except Exception as e:
    print("test startup failed:")
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
