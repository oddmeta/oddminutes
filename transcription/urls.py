from django.urls import path
from . import views

urlpatterns = [
    path('transcribe/', views.transcribe_audio_file, name='transcribe_audio'),
    path('retranscribe/', views.retranscribe, name='retranscribe'),
    path('upload/', views.upload_and_transcribe, name='upload_and_transcribe'),
    path('status/<uuid:job_id>/', views.get_transcription_status, name='transcription_status'),
    path('config/', views.transcription_config, name='transcription_config'),
    path('oddasr-status/', views.check_oddasr_status, name='oddasr_status'),
]
