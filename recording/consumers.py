import json
import asyncio
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .audio_recorder import get_recorder
from .models import RecordingSession


class LevelConsumer(AsyncWebsocketConsumer):
    """WebSocket 消费者，用于实时推送音频电平和录音状态"""

    async def connect(self):
        await self.accept()
        self.running = True
        self._last_status = None
        self.task = asyncio.create_task(self.send_levels())
        print(f"[WS] 客户端已连接: {self.channel_name}")

    async def disconnect(self, close_code):
        self.running = False
        if self.task:
            self.task.cancel()
        print(f"[WS] 客户端已断开: {self.channel_name}, close_code={close_code}")

    @database_sync_to_async
    def _get_current_meeting_id(self):
        session = RecordingSession.objects.filter(status='recording').first()
        return str(session.meeting.id) if session else None

    async def send_levels(self):
        """定期发送电平数据和录音状态"""
        while self.running:
            try:
                recorder = get_recorder()
                level = recorder.current_level
                agc = recorder.agc_status

                current_status = recorder.status
                meeting_id = await self._get_current_meeting_id()

                payload = {
                    'mic_level': round(float(level.mic_level), 4),
                    'system_level': round(float(level.system_level), 4),
                    'mixed_level': round(float(level.mixed_level), 4),
                    'peak_mic': round(float(level.peak_mic), 4),
                    'peak_system': round(float(level.peak_system), 4),
                    'status': current_status,
                    'recording': current_status == 'recording',
                    'meeting_id': meeting_id,
                    'duration': float(recorder._total_duration) if hasattr(recorder, '_total_duration') else 0.0,
                    'agc': {
                        'enabled': agc['enabled'],
                        'mic_gain': round(float(agc['mic_gain']), 2),
                        'system_gain': round(float(agc['system_gain']), 2),
                        'target_rms': int(agc['target_rms']),
                    },
                }

                if current_status != self._last_status:
                    print(f"[WS] 状态变化: {self._last_status} -> {current_status}, meeting_id={meeting_id}")
                    self._last_status = current_status

                await self.send(text_data=json.dumps(payload))

                await asyncio.sleep(0.1)
            except Exception as e:
                print(f"[WS] 发送数据失败: {e}")
                await asyncio.sleep(0.5)

    async def receive(self, text_data):
        """接收客户端消息"""
        data = json.loads(text_data)
        action = data.get('action')

        if action == 'ping':
            await self.send(text_data=json.dumps({'type': 'pong'}))
        elif action == 'get_status':
            recorder = get_recorder()
            meeting_id = await self._get_current_meeting_id()
            print(f"[WS] 收到 get_status 请求, status={recorder.status}, meeting_id={meeting_id}")
            await self.send(text_data=json.dumps({
                'type': 'status',
                'status': recorder.status,
                'recording': recorder.status == 'recording',
                'meeting_id': meeting_id,
            }))
