"""
WSGI config for meeting_minutes project.
"""
import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'meeting_minutes.settings')

application = get_wsgi_application()
