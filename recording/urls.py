from django.urls import path
from . import views

urlpatterns = [
    path('devices/', views.get_devices, name='get_devices'),
    path('start/', views.start_recording, name='start_recording'),
    path('pause/', views.pause_recording, name='pause_recording'),
    path('resume/', views.resume_recording, name='resume_recording'),
    path('stop/', views.stop_recording, name='stop_recording'),
    path('level/', views.get_level, name='get_level'),
    path('status/', views.get_recording_status, name='get_recording_status'),
    path('monitoring/start/', views.start_monitoring, name='start_monitoring'),
    path('monitoring/stop/', views.stop_monitoring, name='stop_monitoring'),
]
