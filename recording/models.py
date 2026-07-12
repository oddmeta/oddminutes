from django.db import models
from core.models import BaseModel


class RecordingSession(BaseModel):
    """录音会话"""
    meeting = models.OneToOneField('meetings.Meeting', on_delete=models.CASCADE, related_name='recording')
    status = models.CharField(
        max_length=20,
        choices=[
            ('idle', '空闲'),
            ('recording', '录音中'),
            ('paused', '已暂停'),
            ('stopped', '已停止'),
            ('error', '错误'),
        ],
        default='idle'
    )
    mic_device = models.CharField(max_length=255, blank=True)
    system_device = models.CharField(max_length=255, blank=True)
    sample_rate = models.IntegerField(default=16000)
    channels = models.IntegerField(default=1)
    checkpoint_interval = models.IntegerField(default=30)
    last_checkpoint = models.DateTimeField(null=True, blank=True)
    total_duration = models.FloatField(default=0)
    error_message = models.TextField(blank=True)

    class Meta:
        db_table = 'recording_sessions'


class RecordingCheckpoint(BaseModel):
    """录音检查点，用于崩溃恢复"""
    session = models.ForeignKey(RecordingSession, on_delete=models.CASCADE, related_name='checkpoints')
    file_path = models.CharField(max_length=500)
    duration = models.FloatField()
    segment_index = models.IntegerField()

    class Meta:
        ordering = ['segment_index']
        db_table = 'recording_checkpoints'


class AudioDevice(BaseModel):
    """音频设备配置"""
    name = models.CharField(max_length=255)
    device_id = models.CharField(max_length=100)
    device_type = models.CharField(
        max_length=20,
        choices=[
            ('microphone', '麦克风'),
            ('system', '系统音频'),
            ('output', '输出设备'),
        ]
    )
    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    channels = models.IntegerField(default=1)
    sample_rate = models.IntegerField(default=16000)

    class Meta:
        db_table = 'audio_devices'
        unique_together = ['device_id', 'device_type']
