import json
import os
from django.conf import settings
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.utils import timezone

from meetings.models import Meeting
from core.audio_utils import convert_audio_to_mp3
from .models import RecordingSession, AudioDevice
from .audio_recorder import get_recorder, reset_recorder, AudioLevel

@api_view(['GET'])
def get_devices(request):
    """获取音频设备列表"""
    recorder = get_recorder()
    devices = recorder.get_devices()

    # 同步到数据库
    for dev in devices:
        device_type = 'microphone' if dev['type'] == 'input' else 'system'
        AudioDevice.objects.update_or_create(
            device_id=str(dev['id']),
            device_type=device_type,
            defaults={
                'name': dev['name'],
                'channels': dev['channels'],
                'sample_rate': dev['sample_rate'],
            }
        )

    return Response({
        'microphones': [d for d in devices if d['type'] == 'input'],
        'system_devices': [d for d in devices if d['type'] == 'output'],
    })


@api_view(['POST'])
def start_recording(request):
    """开始录音"""
    meeting_id = request.data.get('meeting_id')
    mic_device_id = request.data.get('mic_device_id')
    system_device_id = request.data.get('system_device_id')
    enable_system_audio = request.data.get('enable_system_audio', False)

    meeting = get_object_or_404(Meeting, id=meeting_id)

    recorder = get_recorder()
    if recorder.status == 'recording':
        return Response({'error': '已经在录音中'}, status=status.HTTP_400_BAD_REQUEST)

    success = recorder.start(
        mic_device_id=mic_device_id,
        system_device_id=system_device_id,
        enable_system_audio=enable_system_audio,
    )

    if not success:
        return Response(
            {'error': f'启动录音失败: {recorder._error_message}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    # 更新会议和录音会话状态
    meeting.status = 'recording'
    meeting.save()

    session, _ = RecordingSession.objects.update_or_create(
        meeting=meeting,
        defaults={
            'status': 'recording',
            'mic_device': str(mic_device_id) if mic_device_id else '',
            'system_device': str(system_device_id) if system_device_id else '',
        }
    )

    return Response({
        'status': 'recording',
        'meeting_id': str(meeting.id),
        'session_id': str(session.id),
    })


@api_view(['POST'])
def pause_recording(request):
    """暂停录音"""
    meeting_id = request.data.get('meeting_id')
    meeting = get_object_or_404(Meeting, id=meeting_id)

    recorder = get_recorder()
    recorder.pause()

    meeting.status = 'paused'
    meeting.save()

    session = get_object_or_404(RecordingSession, meeting=meeting)
    session.status = 'paused'
    session.save()

    return Response({'status': 'paused'})


@api_view(['POST'])
def resume_recording(request):
    """恢复录音"""
    meeting_id = request.data.get('meeting_id')
    meeting = get_object_or_404(Meeting, id=meeting_id)

    recorder = get_recorder()
    recorder.resume()

    meeting.status = 'recording'
    meeting.save()

    session = get_object_or_404(RecordingSession, meeting=meeting)
    session.status = 'recording'
    session.save()

    return Response({'status': 'recording'})


@api_view(['POST'])
def stop_recording(request):
    """停止录音"""
    meeting_id = request.data.get('meeting_id')
    meeting = get_object_or_404(Meeting, id=meeting_id)

    recorder = get_recorder()
    audio_data = recorder.stop()
    total_duration = recorder._total_duration

    # 先更新状态，让前端尽快获取到状态变化
    meeting.status = 'completed'
    meeting.save()

    session = get_object_or_404(RecordingSession, meeting=meeting)
    session.status = 'stopped'
    session.total_duration = total_duration
    session.save()

    reset_recorder()

    # 保存音频文件（在状态更新之后）
    if audio_data:
        filename = f"meeting_{meeting.id}_{int(timezone.now().timestamp())}.wav"
        rel_path = os.path.join('audio', 'meetings', filename)
        filepath = str(settings.MEDIA_ROOT / rel_path)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        with open(filepath, 'wb') as f:
            f.write(audio_data)

        meeting.audio_file.name = rel_path
        meeting.audio_duration = total_duration
        meeting.save()

        # 在后台线程中转换为 MP3，不阻塞响应
        import threading
        threading.Thread(target=convert_audio_to_mp3, args=(meeting,), daemon=True).start()

    return Response({
        'status': 'stopped',
        'duration': total_duration,
        'audio_file': meeting.audio_file.url if meeting.audio_file else None,
    })


@api_view(['GET'])
def get_level(request):
    """获取当前音频电平"""
    recorder = get_recorder()
    level = recorder.current_level
    agc = recorder.agc_status

    return Response({
        'mic_level': round(level.mic_level, 4),
        'system_level': round(level.system_level, 4),
        'mixed_level': round(level.mixed_level, 4),
        'peak_mic': round(level.peak_mic, 4),
        'peak_system': round(level.peak_system, 4),
        'agc': agc,
    })


@api_view(['POST'])
def start_monitoring(request):
    """开始预监听（只显示电平，不录音）"""
    recorder = get_recorder()
    
    mic_device_id = request.data.get('mic_device_id')
    system_device_id = request.data.get('system_device_id')
    enable_system_audio = request.data.get('enable_system_audio', False)
    
    recorder.start_monitoring(mic_device_id, system_device_id, enable_system_audio)
    
    return Response({'status': 'monitoring started'})


@api_view(['POST'])
def stop_monitoring(request):
    """停止预监听"""
    recorder = get_recorder()
    recorder.stop_monitoring()
    return Response({'status': 'monitoring stopped'})


@api_view(['GET'])
def get_recording_status(request):
    """获取录音状态"""
    recorder = get_recorder()
    
    meeting_id = None
    if recorder.status == 'recording':
        session = RecordingSession.objects.filter(status='recording').first()
        if session:
            meeting_id = str(session.meeting.id)
    else:
        active_meeting = Meeting.objects.filter(
            status__in=['idle', 'paused', 'processing']
        ).first()
        if active_meeting:
            meeting_id = str(active_meeting.id)
    
    return Response({
        'status': recorder.status,
        'recording': recorder.status == 'recording',
        'meeting_id': meeting_id,
        'duration': recorder._total_duration if hasattr(recorder, '_total_duration') else 0,
    })
