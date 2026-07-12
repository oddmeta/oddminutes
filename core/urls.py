from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('meeting/<str:meeting_id>/', views.meeting_detail, name='meeting_detail'),
]
