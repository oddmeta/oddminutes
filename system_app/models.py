from django.db import models
from core.models import BaseModel


class SystemSettings(BaseModel):
    """系统设置"""
    auto_start = models.BooleanField(default=False)
    minimize_to_tray = models.BooleanField(default=True)
    dnd_mode = models.BooleanField(default=False)
    enable_notifications = models.BooleanField(default=True)
    enable_analytics = models.BooleanField(default=False)
    analytics_key = models.CharField(max_length=255, blank=True)
    auto_cleanup_days = models.IntegerField(default=7)
    global_shortcuts = models.JSONField(default=dict)
    theme = models.CharField(max_length=20, default='light')
    onboarding_completed = models.BooleanField(default=False)

    class Meta:
        db_table = 'system_settings'


class UpdateInfo(BaseModel):
    """更新信息"""
    current_version = models.CharField(max_length=50)
    latest_version = models.CharField(max_length=50, blank=True)
    download_url = models.URLField(blank=True)
    release_notes = models.TextField(blank=True)
    check_date = models.DateTimeField(null=True, blank=True)
    auto_check = models.BooleanField(default=True)

    class Meta:
        db_table = 'update_info'


class NotificationLog(BaseModel):
    """通知日志"""
    title = models.CharField(max_length=255)
    message = models.TextField()
    notification_type = models.CharField(max_length=50)
    is_read = models.BooleanField(default=False)

    class Meta:
        db_table = 'notification_logs'
        ordering = ['-created_at']
