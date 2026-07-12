"""
ASGI config for meeting_minutes project.
"""
import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from channels.security.websocket import AllowedHostsOriginValidator

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'meeting_minutes.settings')

django_asgi_app = get_asgi_application()

from recording import routing as recording_routing
from transcription import routing as transcription_routing

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AllowedHostsOriginValidator(
        URLRouter(
            recording_routing.websocket_urlpatterns +
            transcription_routing.websocket_urlpatterns
        )
    ),
})
