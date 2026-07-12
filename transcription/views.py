import os
import threading
from django.conf import settings
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.utils import timezone

from meetings.models import Meeting, TranscriptSegment
from core.audio_utils import convert_audio_to_mp3
from .models import TranscriptionJob, TranscriptionConfig
from .oddasr_client import get_oddasr_client


@api_view(['POST'])
def transcribe_audio_file(request):
    """转录音频文件"""
    meeting_id = request.data.get('meeting_id')
    language = request.data.get('language', 'auto')
    model = request.data.get('model', 'default')

    meeting = get_object_or_404(Meeting, id=meeting_id)

    if not meeting.audio_file:
        return Response(
            {'error': '会议没有音频文件'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # 创建转录任务
    job = TranscriptionJob.objects.create(
        meeting=meeting,
        source='file',
        language=language,
        model=model,
        status='processing',
    )
    meeting.status = 'processing'
    meeting.save()

    # 在后台线程执行转录
    def do_transcription():
        try:
            client = get_oddasr_client()
            audio_path = str(settings.MEDIA_ROOT / meeting.audio_file.name)

            result = client.transcribe_file(audio_path, language=language)

            if 'error' in result:
                job.status = 'failed'
                job.error_message = result['error']
                job.save()
                meeting.status = 'completed'
                meeting.save()
                return

            text = result.get('text', '')
            job.result_text = text
            job.status = 'completed'
            job.save()

            # 保存转录片段
            _save_transcript_segments(meeting, text, result)
            meeting.status = 'completed'
            meeting.save()

        except Exception as e:
            job.status = 'failed'
            job.error_message = str(e)
            job.save()
            meeting.status = 'completed'
            meeting.save()

    thread = threading.Thread(target=do_transcription, daemon=True)
    thread.start()

    return Response({
        'job_id': str(job.id),
        'status': 'processing',
    })


@api_view(['POST'])
def retranscribe(request):
    """重新转录已有音频"""
    meeting_id = request.data.get('meeting_id')
    language = request.data.get('language', 'auto')
    model = request.data.get('model', 'default')

    meeting = get_object_or_404(Meeting, id=meeting_id)

    # 删除旧转录
    meeting.transcripts.all().delete()
    meeting.status = 'processing'
    meeting.save()

    job = TranscriptionJob.objects.create(
        meeting=meeting,
        source='reprocess',
        language=language,
        model=model,
        status='processing',
    )

    def do_retranscription():
        try:
            client = get_oddasr_client()
            audio_path = str(settings.MEDIA_ROOT / meeting.audio_file.name)

            result = client.transcribe_file(audio_path, language=language)

            if 'error' in result:
                job.status = 'failed'
                job.error_message = result['error']
                job.save()
                meeting.status = 'completed'
                meeting.save()
                return

            text = result.get('text', '')
            job.result_text = text
            job.status = 'completed'
            job.save()

            _save_transcript_segments(meeting, text, result)
            meeting.language = language
            meeting.status = 'completed'
            meeting.save()

        except Exception as e:
            job.status = 'failed'
            job.error_message = str(e)
            job.save()
            meeting.status = 'completed'
            meeting.save()

    thread = threading.Thread(target=do_retranscription, daemon=True)
    thread.start()

    return Response({
        'job_id': str(job.id),
        'status': 'processing',
    })


@api_view(['POST'])
def upload_and_transcribe(request):
    """上传音频文件并转录"""
    audio_file = request.FILES.get('audio')
    title = request.data.get('title', audio_file.name if audio_file else '导入的音频')
    language = request.data.get('language', 'auto')

    if not audio_file:
        return Response(
            {'error': '请上传音频文件'},
            status=status.HTTP_400_BAD_REQUEST
        )

    filename = audio_file.name.lower()
    if filename.endswith('.m4a'):
        return Response(
            {'error': '不支持导入 m4a 格式的音频文件，请选择其他格式'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # 创建会议
    meeting = Meeting.objects.create(title=title, status='processing')

    # 保存音频文件
    meeting.audio_file = audio_file
    meeting.save()

    # 如果不是 MP3 格式，自动转换为 MP3
    convert_audio_to_mp3(meeting)

    # 创建转录任务
    job = TranscriptionJob.objects.create(
        meeting=meeting,
        source='file',
        language=language,
        status='processing',
    )

    def do_transcription():
        try:
            client = get_oddasr_client()
            audio_path = str(settings.MEDIA_ROOT / meeting.audio_file.name)

            result = client.transcribe_file(audio_path, language=language)

            if 'error' in result:
                job.status = 'failed'
                job.error_message = result['error']
                job.save()
                meeting.status = 'completed'
                meeting.save()
                return

            text = result.get('text', '')
            job.result_text = text
            job.status = 'completed'
            job.save()

            _save_transcript_segments(meeting, text, result)
            meeting.status = 'completed'
            meeting.save()

        except Exception as e:
            job.status = 'failed'
            job.error_message = str(e)
            job.save()
            meeting.status = 'completed'
            meeting.save()

    thread = threading.Thread(target=do_transcription, daemon=True)
    thread.start()

    return Response({
        'meeting_id': str(meeting.id),
        'job_id': str(job.id),
        'status': 'processing',
    })


@api_view(['GET'])
def get_transcription_status(request, job_id):
    """获取转录任务状态"""
    job = get_object_or_404(TranscriptionJob, id=job_id)

    return Response({
        'job_id': str(job.id),
        'status': job.status,
        'result_text': job.result_text if job.status == 'completed' else None,
        'error': job.error_message if job.status == 'failed' else None,
        'created_at': job.created_at,
        'updated_at': job.updated_at,
    })


@api_view(['GET', 'POST'])
def transcription_config(request):
    """获取或设置转录配置"""
    config, _ = TranscriptionConfig.objects.get_or_create(
        defaults={
            'provider': 'oddasr',
            'model': 'default',
            'language': 'auto',
        }
    )

    if request.method == 'GET':
        return Response({
            'provider': config.provider,
            'model': config.model,
            'language': config.language,
            'extra_config': config.extra_config,
        })

    elif request.method == 'POST':
        config.provider = request.data.get('provider', config.provider)
        config.model = request.data.get('model', config.model)
        config.language = request.data.get('language', config.language)
        if 'extra_config' in request.data:
            config.extra_config = request.data['extra_config']
        config.save()

        return Response({
            'provider': config.provider,
            'model': config.model,
            'language': config.language,
        })


@api_view(['GET'])
def check_oddasr_status(request):
    """检查 OddASR 服务状态"""
    client = get_oddasr_client()
    is_healthy = client.health_check()

    return Response({
        'available': is_healthy,
        'url': client.base_url,
    })


def _save_transcript_segments(meeting, text: str, result: dict):
    """保存转录结果为片段"""
    segments = result.get('segments')

    if segments:
        # 使用 ASR 返回的 segments，包含每个片段的发言人和时间戳
        for seg in segments:
            segment_text = seg.get('text', '')
            spk_id = seg.get('speaker')
            # 时间戳可能为 None，用 or 0 兜底
            start_time = seg.get('start') if seg.get('start') is not None else 0
            end_time = seg.get('end') if seg.get('end') is not None else 0
            words = seg.get('words', [])

            # 跳过空文本
            if not segment_text or not segment_text.strip():
                continue

            duration = end_time - start_time

            # speaker 为 None 或缺失时兜底为 '发言人'
            if spk_id is not None:
                speaker = f'发言人 {spk_id}'
            else:
                speaker = '发言人'

            # 提取并保存 words 时间戳数据（verbose_json 模式）
            words_data = []
            if words:
                for w in words:
                    # word 时间戳缺失时用 segment 时间戳兜底
                    w_start = w.get('start')
                    w_end = w.get('end')
                    words_data.append({
                        'word': w.get('word', ''),
                        'start': w_start if w_start is not None else start_time,
                        'end': w_end if w_end is not None else end_time,
                        'probability': w.get('probability'),
                    })

            TranscriptSegment.objects.create(
                meeting=meeting,
                text=segment_text,
                speaker=speaker,
                audio_start_time=start_time,
                audio_end_time=end_time,
                duration=max(duration, 0),
                is_final=True,
                words=words_data,
            )
    else:
        # 回退：简单按句号分割（无发言人信息）
        sentences = [s.strip() for s in text.replace('?', '。').replace('!', '。').split('。') if s.strip()]

        duration_per_sentence = (meeting.audio_duration or 0) / max(len(sentences), 1)

        for i, sentence in enumerate(sentences):
            start_time = i * duration_per_sentence
            end_time = (i + 1) * duration_per_sentence

            TranscriptSegment.objects.create(
                meeting=meeting,
                text=sentence + '。',
                speaker='发言人',
                audio_start_time=start_time,
                audio_end_time=end_time,
                duration=duration_per_sentence,
                is_final=True,
                words=[],
            )
