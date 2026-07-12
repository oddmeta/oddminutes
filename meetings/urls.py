from django.urls import path
from . import views

urlpatterns = [
    path('', views.meeting_list, name='meeting_list'),
    path('<uuid:pk>/', views.meeting_detail, name='meeting_detail'),
    path('<uuid:pk>/export/', views.export_meeting, name='export_meeting'),
    path('search/', views.search_meetings, name='search_meetings'),
    path('cleanup/', views.cleanup_old_meetings, name='cleanup_old_meetings'),
    path('transcript-segments/<uuid:pk>/', views.transcript_segment_update, name='transcript_segment_update'),
]
