from django.urls import path
from . import views

urlpatterns = [
    path('generate/', views.generate_summary, name='generate_summary'),
    path('status/<uuid:meeting_id>/', views.get_summary_status, name='summary_status'),
    path('regenerate/', views.regenerate_summary, name='regenerate_summary'),
    path('templates/', views.summary_templates, name='summary_templates'),
    path('model-config/', views.ai_model_config, name='ai_model_config'),
    path('language-preferences/', views.language_preferences, name='language_preferences'),
    path('stream/', views.stream_summary, name='stream_summary'),
]
