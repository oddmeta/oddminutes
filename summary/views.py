import asyncio
import json
import threading
import time
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.utils import timezone

from meetings.models import Meeting, SummaryProcess
from .models import SummaryTemplate, AIModelConfig, SummaryLanguagePreference
from .ai_processor import SummaryProcessor


@api_view(['POST'])
def generate_summary(request):
    """生成会议摘要"""
    meeting_id = request.data.get('meeting_id')
    provider = request.data.get('provider', 'openai')
    model_name = request.data.get('model_name', 'Qwen3-8B')
    chunk_size = request.data.get('chunk_size', 5000)
    overlap = request.data.get('overlap', 1000)
    custom_prompt = request.data.get('custom_prompt', '')
    language = request.data.get('language', 'zh')
    template_id = request.data.get('template_id')

    meeting = get_object_or_404(Meeting, id=meeting_id)

    # 获取转录文本
    transcripts = meeting.transcripts.all().order_by('audio_start_time')
    text = " ".join([t.text for t in transcripts])

    if not text:
        return Response(
            {'error': '没有转录文本可供摘要'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # 创建或更新摘要处理记录
    process, _ = SummaryProcess.objects.update_or_create(
        meeting=meeting,
        defaults={
            'status': 'processing',
            'start_time': timezone.now(),
            'error': '',
            'result': None,
        }
    )

    def do_summary():
        try:
            processor = SummaryProcessor()
            start = time.time()

            num_chunks, all_json_data = asyncio.run(processor.process_transcript(
                text=text,
                provider=provider,
                model_name=model_name,
                chunk_size=chunk_size,
                overlap=overlap,
                custom_prompt=custom_prompt,
                language=language,
            ))

            final_summary = processor.aggregate_summaries(all_json_data)

            # 应用模板
            if template_id:
                try:
                    template = SummaryTemplate.objects.get(id=template_id)
                    template_structure = template.structure
                    # 可以在这里根据模板结构调整输出
                except SummaryTemplate.DoesNotExist:
                    pass

            meeting.summary = final_summary
            meeting.save()

            process.status = 'completed'
            process.result = final_summary
            process.chunk_count = num_chunks
            process.processing_time = time.time() - start
            process.end_time = timezone.now()
            process.save()

            processor.cleanup()

        except Exception as e:
            process.status = 'failed'
            process.error = str(e)
            process.end_time = timezone.now()
            process.save()

    thread = threading.Thread(target=do_summary, daemon=True)
    thread.start()

    return Response({
        'process_id': str(process.id),
        'status': 'processing',
    })


@api_view(['GET'])
def get_summary_status(request, meeting_id):
    """获取摘要状态"""
    meeting = get_object_or_404(Meeting, id=meeting_id)

    try:
        process = meeting.summary_process
    except SummaryProcess.DoesNotExist:
        return Response({
            'status': 'not_found',
            'meeting_id': str(meeting_id),
        })

    return Response({
        'status': process.status,
        'meeting_id': str(meeting_id),
        'meeting_name': meeting.summary.get('MeetingName') if meeting.summary else None,
        'data': process.result if process.status == 'completed' else None,
        'error': process.error if process.status == 'failed' else None,
        'start_time': process.start_time,
        'end_time': process.end_time,
    })


@api_view(['POST'])
def regenerate_summary(request):
    """重新生成摘要"""
    meeting_id = request.data.get('meeting_id')
    meeting = get_object_or_404(Meeting, id=meeting_id)

    # 清除旧摘要
    meeting.summary = None
    meeting.save()

    if hasattr(meeting, 'summary_process'):
        meeting.summary_process.delete()

    # 调用生成摘要
    return generate_summary(request)


@api_view(['GET', 'POST'])
def summary_templates(request):
    """获取或创建摘要模板"""
    if request.method == 'GET':
        templates = SummaryTemplate.objects.all()
        return Response([{
            'id': str(t.id),
            'name': t.name,
            'description': t.description,
            'structure': t.structure,
            'is_default': t.is_default,
            'is_builtin': t.is_builtin,
        } for t in templates])

    elif request.method == 'POST':
        template = SummaryTemplate.objects.create(
            name=request.data.get('name'),
            description=request.data.get('description', ''),
            structure=request.data.get('structure', {}),
        )
        return Response({
            'id': str(template.id),
            'name': template.name,
        }, status=status.HTTP_201_CREATED)


@api_view(['GET', 'POST', 'PUT', 'DELETE'])
def ai_model_config(request):
    """获取或设置 AI 模型配置"""
    if request.method == 'GET':
        configs = AIModelConfig.objects.all()
        return Response([{
            'id': str(c.id),
            'provider': c.provider,
            'model_name': c.model_name,
            'api_key': c.api_key,
            'base_url': c.base_url,
            'is_default': c.is_default,
            'extra_params': c.extra_params,
        } for c in configs])

    elif request.method == 'POST':
        config = AIModelConfig.objects.create(
            provider=request.data.get('provider'),
            model_name=request.data.get('model_name'),
            api_key=request.data.get('api_key', ''),
            base_url=request.data.get('base_url', ''),
            is_default=request.data.get('is_default', False),
            extra_params=request.data.get('extra_params', {}),
        )
        if config.is_default:
            AIModelConfig.objects.exclude(id=config.id).update(is_default=False)
        return Response({'id': str(config.id)}, status=status.HTTP_201_CREATED)

    elif request.method == 'PUT':
        config_id = request.data.get('id')
        config = get_object_or_404(AIModelConfig, id=config_id)
        config.provider = request.data.get('provider', config.provider)
        config.model_name = request.data.get('model_name', config.model_name)
        config.api_key = request.data.get('api_key', config.api_key)
        config.base_url = request.data.get('base_url', config.base_url)
        config.is_default = request.data.get('is_default', config.is_default)
        config.save()
        if config.is_default:
            AIModelConfig.objects.exclude(id=config.id).update(is_default=False)
        return Response({'id': str(config.id)})

    elif request.method == 'DELETE':
        config_id = request.data.get('id')
        config = get_object_or_404(AIModelConfig, id=config_id)
        config.delete()
        return Response({'status': 'deleted'})


@api_view(['GET', 'POST'])
def language_preferences(request):
    """获取或设置语言偏好"""
    if request.method == 'GET':
        prefs = SummaryLanguagePreference.objects.all()
        return Response([{
            'id': str(p.id),
            'language': p.language,
            'language_name': p.language_name,
            'is_default': p.is_default,
        } for p in prefs])

    elif request.method == 'POST':
        pref = SummaryLanguagePreference.objects.create(
            language=request.data.get('language'),
            language_name=request.data.get('language_name'),
            is_default=request.data.get('is_default', False),
        )
        if pref.is_default:
            SummaryLanguagePreference.objects.exclude(id=pref.id).update(is_default=False)
        return Response({'id': str(pref.id)}, status=status.HTTP_201_CREATED)


@api_view(['POST'])
def stream_summary(request):
    """流式生成摘要（通过 SSE）"""
    from django.http import StreamingHttpResponse

    meeting_id = request.data.get('meeting_id')
    meeting = get_object_or_404(Meeting, id=meeting_id)

    transcripts = meeting.transcripts.all().order_by('audio_start_time')
    text = " ".join([t.text for t in transcripts])

    provider = request.data.get('provider', 'ollama')
    model_name = request.data.get('model_name', 'llama3')
    custom_prompt = request.data.get('custom_prompt', '')
    language = request.data.get('language', 'zh')

    def generate():
        yield 'data: {"type": "start"}\n\n'

        try:
            processor = SummaryProcessor()
            num_chunks, all_json_data = asyncio.run(processor.process_transcript(
                text=text,
                provider=provider,
                model_name=model_name,
                custom_prompt=custom_prompt,
                language=language,
            ))

            for i, chunk_json in enumerate(all_json_data):
                yield f'data: {{"type": "chunk", "index": {i}, "data": {json.dumps(chunk_json, ensure_ascii=False)}}}\n\n'

            final = processor.aggregate_summaries(all_json_data)
            meeting.summary = final
            meeting.save()

            yield f'data: {{"type": "complete", "data": {json.dumps(final, ensure_ascii=False)}}}\n\n'

        except Exception as e:
            yield f'data: {{"type": "error", "message": "{str(e)}"}}\n\n'

    response = StreamingHttpResponse(generate(), content_type='text/event-stream')
    response['Cache-Control'] = 'no-cache'
    return response
