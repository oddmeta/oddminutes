"""
URL configuration for meeting_minutes project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic.base import RedirectView

urlpatterns = [
    path('favicon.ico', RedirectView.as_view(url=settings.STATIC_URL + 'favicon.ico', permanent=True)),
    path('admin/', admin.site.urls),
    path('api/meetings/', include('meetings.urls')),
    path('api/recording/', include('recording.urls')),
    path('api/transcription/', include('transcription.urls')),
    path('api/summary/', include('summary.urls')),
    path('api/system/', include('system_app.urls')),
    path('', include('core.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])
