import json
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.db.models import Q
from django.utils import timezone
from datetime import timedelta

from .models import Meeting, TranscriptSegment, SummaryProcess
from .serializers import (
    MeetingListSerializer, MeetingDetailSerializer,
    MeetingCreateSerializer, MeetingUpdateSerializer,
    TranscriptSegmentSerializer
)


@api_view(['GET', 'POST'])
def meeting_list(request):
    """获取会议列表或创建新会议"""
    if request.method == 'GET':
        meetings = Meeting.objects.all()
        status_filter = request.query_params.get('status')
        if status_filter:
            meetings = meetings.filter(status=status_filter)
        serializer = MeetingListSerializer(meetings, many=True)
        return Response(serializer.data)

    elif request.method == 'POST':
        active_meetings = Meeting.objects.filter(
            status__in=['idle', 'recording', 'paused', 'processing']
        ).exists()
        if active_meetings:
            return Response(
                {'error': '请先完成或删除当前未完成的会议，再创建新会议'},
                status=status.HTTP_409_CONFLICT
            )
        
        serializer = MeetingCreateSerializer(data=request.data)
        if serializer.is_valid():
            meeting = serializer.save()
            return Response(MeetingDetailSerializer(meeting).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT', 'PATCH', 'DELETE'])
def meeting_detail(request, pk):
    """获取、更新或删除单个会议"""
    meeting = get_object_or_404(Meeting, pk=pk)

    if request.method == 'GET':
        serializer = MeetingDetailSerializer(meeting)
        return Response(serializer.data)

    elif request.method in ['PUT', 'PATCH']:
        serializer = MeetingUpdateSerializer(meeting, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(MeetingDetailSerializer(meeting).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == 'DELETE':
        meeting.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['POST'])
def search_meetings(request):
    """搜索会议转录内容"""
    query = request.data.get('query', '').strip()
    if not query:
        return Response([])

    # 搜索转录片段
    segments = TranscriptSegment.objects.filter(
        Q(text__icontains=query)
    ).select_related('meeting')[:50]

    results = []
    seen_meetings = set()

    for segment in segments:
        meeting = segment.meeting
        if meeting.id in seen_meetings:
            continue
        seen_meetings.add(meeting.id)

        text = segment.text
        match_index = text.lower().find(query.lower())
        start = max(0, match_index - 50)
        end = min(len(text), match_index + len(query) + 50)
        context = text[start:end]
        if start > 0:
            context = '...' + context
        if end < len(text):
            context = context + '...'

        results.append({
            'id': str(meeting.id),
            'title': meeting.title,
            'match_context': context,
            'timestamp': segment.created_at,
        })

    return Response(results)


@api_view(['POST'])
def export_meeting(request, pk):
    """导出会议记录"""
    meeting = get_object_or_404(Meeting, pk=pk)
    export_format = request.data.get('format', 'md')

    if export_format == 'txt':
        content = _export_txt(meeting)
        ext = 'txt'
    elif export_format == 'json':
        content = _export_json(meeting)
        ext = 'json'
    else:
        content = _export_markdown(meeting)
        ext = 'md'

    from django.http import HttpResponse
    response = HttpResponse(content, content_type='text/plain; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="{meeting.title}.{ext}"'
    return response


def _export_txt(meeting):
    lines = [
        f"会议标题: {meeting.title}",
        f"创建时间: {meeting.created_at}",
        f"时长: {meeting.audio_duration or 0}秒",
        "=" * 50,
        "",
        "转录内容:",
        "-" * 50,
    ]
    for seg in meeting.transcripts.all():
        lines.append(f"[{seg.audio_start_time:.1f}s] {seg.speaker or '未知'}: {seg.text}")

    lines.extend(["", "=" * 50, "", "笔记:", meeting.notes or "无"])
    return "\n".join(lines)


def _export_markdown(meeting):
    lines = [
        f"# {meeting.title}",
        f"",
        f"- 创建时间: {meeting.created_at}",
        f"- 时长: {meeting.audio_duration or 0}秒",
        f"",
        "## 转录内容",
        "",
    ]
    for seg in meeting.transcripts.all():
        lines.append(f"**[{seg.audio_start_time:.1f}s]** {seg.speaker or '未知'}: {seg.text}")
        lines.append("")

    lines.extend(["", "## 笔记", "", meeting.notes or "无"])

    if meeting.summary:
        lines.extend(["", "## AI 摘要", ""])
        if isinstance(meeting.summary, dict):
            for key, value in meeting.summary.items():
                lines.append(f"### {key}")
                if isinstance(value, list):
                    for item in value:
                        lines.append(f"- {item}")
                else:
                    lines.append(str(value))
                lines.append("")

    return "\n".join(lines)


def _export_json(meeting):
    data = {
        'title': meeting.title,
        'created_at': str(meeting.created_at),
        'duration': meeting.audio_duration,
        'transcripts': [
            {
                'text': seg.text,
                'speaker': seg.speaker,
                'start': seg.audio_start_time,
                'end': seg.audio_end_time,
            }
            for seg in meeting.transcripts.all()
        ],
        'notes': meeting.notes,
        'summary': meeting.summary,
    }
    return json.dumps(data, ensure_ascii=False, indent=2)


@api_view(['POST'])
def cleanup_old_meetings(request):
    """清理旧的会议数据"""
    from django.conf import settings
    days = settings.AUTO_CLEANUP_DAYS
    cutoff = timezone.now() - timedelta(days=days)

    old_meetings = Meeting.objects.filter(created_at__lt=cutoff)
    count = old_meetings.count()
    old_meetings.delete()

    return Response({'deleted': count, 'days': days})


@api_view(['PATCH'])
def transcript_segment_update(request, pk):
    """更新单个转录片段的文本或发言人"""
    segment = get_object_or_404(TranscriptSegment, pk=pk)

    text = request.data.get('text')
    speaker = request.data.get('speaker')
    changed = False

    if text is not None:
        stripped = text.strip()
        if not stripped:
            return Response({'error': '文本内容不能为空'}, status=status.HTTP_400_BAD_REQUEST)
        if segment.text != stripped:
            segment.text = stripped
            segment.words = []  # 字级时间戳失效，降级为段级联动
            changed = True

    if speaker is not None:
        if segment.speaker != speaker:
            segment.speaker = speaker
            changed = True

    if changed:
        segment.save()

    serializer = TranscriptSegmentSerializer(segment)
    return Response(serializer.data)
