from django.db import models
from core.models import BaseModel
import uuid


class Meeting(BaseModel):
    """会议记录"""
    title = models.CharField(max_length=255, default="新会议")
    status = models.CharField(
        max_length=20,
        choices=[
            ('idle', '待开始'),
            ('recording', '录音中'),
            ('paused', '已暂停'),
            ('completed', '已完成'),
            ('processing', '处理中'),
        ],
        default='idle'
    )
    audio_file = models.FileField(upload_to='audio/meetings/%Y/%m/%d/', null=True, blank=True)
    audio_duration = models.FloatField(null=True, blank=True)
    summary = models.JSONField(null=True, blank=True)
    notes = models.TextField(blank=True)
    notes_html = models.TextField(blank=True)
    language = models.CharField(max_length=10, default='auto')
    folder_path = models.CharField(max_length=500, blank=True)

    class Meta:
        ordering = ['-created_at']
        db_table = 'meetings'

    def __str__(self):
        return self.title


class TranscriptSegment(BaseModel):
    """转录片段"""
    meeting = models.ForeignKey(Meeting, on_delete=models.CASCADE, related_name='transcripts')
    text = models.TextField()
    speaker = models.CharField(max_length=100, blank=True)
    audio_start_time = models.FloatField(null=True, blank=True)
    audio_end_time = models.FloatField(null=True, blank=True)
    duration = models.FloatField(null=True, blank=True)
    is_final = models.BooleanField(default=False)
    # verbose_json 模式下 ASR 返回的每个字/词的时间戳数据
    words = models.JSONField(null=True, blank=True, default=list)

    class Meta:
        ordering = ['audio_start_time']
        db_table = 'transcript_segments'

    def __str__(self):
        return f"{self.meeting.title} - {self.audio_start_time}s"


class SummaryProcess(BaseModel):
    """摘要处理状态"""
    meeting = models.OneToOneField(Meeting, on_delete=models.CASCADE, related_name='summary_process')
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
    result = models.JSONField(null=True, blank=True)
    error = models.TextField(blank=True)
    chunk_count = models.IntegerField(default=0)
    processing_time = models.FloatField(null=True, blank=True)
    metadata = models.JSONField(null=True, blank=True)
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'summary_processes'


class MeetingExport(BaseModel):
    """会议导出记录"""
    meeting = models.ForeignKey(Meeting, on_delete=models.CASCADE, related_name='exports')
    file_path = models.CharField(max_length=500)
    export_format = models.CharField(
        max_length=20,
        choices=[
            ('txt', '纯文本'),
            ('md', 'Markdown'),
            ('json', 'JSON'),
        ]
    )

    class Meta:
        db_table = 'meeting_exports'
