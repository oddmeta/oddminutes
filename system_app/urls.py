from django.urls import path
from . import views

urlpatterns = [
    path('settings/', views.system_settings, name='system_settings'),
    path('check-updates/', views.check_updates, name='check_updates'),
    path('notifications/', views.get_notifications, name='get_notifications'),
    path('notifications/read/', views.mark_notification_read, name='mark_notification_read'),
    path('notifications/send/', views.send_notification, name='send_notification'),
    path('onboarding/complete/', views.complete_onboarding, name='complete_onboarding'),
    path('info/', views.system_info, name='system_info'),
]
