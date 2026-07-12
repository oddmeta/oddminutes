from rest_framework import serializers
from .models import Meeting, TranscriptSegment, SummaryProcess


class TranscriptSegmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = TranscriptSegment
        fields = ['id', 'text', 'speaker', 'audio_start_time', 'audio_end_time', 'duration', 'is_final', 'words', 'created_at']
        read_only_fields = ['id', 'audio_start_time', 'audio_end_time', 'duration', 'is_final', 'created_at']


class MeetingListSerializer(serializers.ModelSerializer):
    transcript_count = serializers.SerializerMethodField()
    duration_display = serializers.SerializerMethodField()

    class Meta:
        model = Meeting
        fields = ['id', 'title', 'status', 'created_at', 'updated_at', 'transcript_count', 'duration_display']

    def get_transcript_count(self, obj):
        return obj.transcripts.count()

    def get_duration_display(self, obj):
        if obj.audio_duration:
            minutes = int(obj.audio_duration // 60)
            seconds = int(obj.audio_duration % 60)
            return f"{minutes}:{seconds:02d}"
        return "0:00"


class MeetingDetailSerializer(serializers.ModelSerializer):
    transcripts = TranscriptSegmentSerializer(many=True, read_only=True)
    summary_data = serializers.SerializerMethodField()
    transcription_error = serializers.SerializerMethodField()

    class Meta:
        model = Meeting
        fields = ['id', 'title', 'status', 'created_at', 'updated_at',
                  'audio_file', 'audio_duration', 'transcripts',
                  'summary', 'notes', 'notes_html', 'language', 'summary_data', 'transcription_error']

    def get_summary_data(self, obj):
        if hasattr(obj, 'summary_process'):
            return {
                'status': obj.summary_process.status,
                'result': obj.summary_process.result,
                'error': obj.summary_process.error,
            }
        return None

    def get_transcription_error(self, obj):
        latest_job = obj.transcription_jobs.order_by('-created_at').first()
        if latest_job and latest_job.status == 'failed':
            return latest_job.error_message
        return None


class MeetingCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Meeting
        fields = ['title']


class MeetingUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Meeting
        fields = ['title', 'notes', 'notes_html']
