from django.db import models
from core.models import BaseModel


class TranscriptionJob(BaseModel):
    """转录任务"""
    meeting = models.ForeignKey('meetings.Meeting', on_delete=models.CASCADE, related_name='transcription_jobs')
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', '待处理'),
            ('processing', '处理中'),
            ('completed', '已完成'),
            ('failed', '失败'),
        ],
        default='pending'
    )
    source = models.CharField(
        max_length=20,
        choices=[
            ('realtime', '实时转录'),
            ('file', '文件导入'),
            ('reprocess', '重新转录'),
        ]
    )
    audio_file = models.FileField(upload_to='audio/imports/%Y/%m/%d/', null=True, blank=True)
    language = models.CharField(max_length=10, default='auto')
    model = models.CharField(max_length=50, default='default')
    result_text = models.TextField(blank=True)
    error_message = models.TextField(blank=True)
    processing_time = models.FloatField(null=True, blank=True)

    class Meta:
        db_table = 'transcription_jobs'
        ordering = ['-created_at']


class TranscriptionConfig(BaseModel):
    """转录配置"""
    provider = models.CharField(max_length=50, default='oddasr')
    model = models.CharField(max_length=50, default='default')
    language = models.CharField(max_length=10, default='auto')
    api_key = models.CharField(max_length=255, blank=True)
    extra_config = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = 'transcription_configs'
