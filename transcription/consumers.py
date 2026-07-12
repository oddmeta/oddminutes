import json
import asyncio
from channels.generic.websocket import AsyncWebsocketConsumer
from .oddasr_client import get_oddasr_client


class RealtimeTranscriptionConsumer(AsyncWebsocketConsumer):
    """WebSocket 消费者，用于实时转录"""

    async def connect(self):
        await self.accept()
        self.audio_buffer = bytearray()
        self.running = True
        self.language = 'auto'

    async def disconnect(self, close_code):
        self.running = False

    async def receive(self, text_data=None, bytes_data=None):
        if bytes_data:
            # 接收音频数据
            self.audio_buffer.extend(bytes_data)

            # 每 5 秒触发一次转录
            if len(self.audio_buffer) >= 16000 * 2 * 5:  # 5 seconds of 16-bit mono
                await self._process_buffer()

        elif text_data:
            data = json.loads(text_data)
            action = data.get('action')

            if action == 'start':
                self.language = data.get('language', 'auto')
                await self.send(text_data=json.dumps({
                    'type': 'started',
                    'language': self.language,
                }))

            elif action == 'stop':
                if len(self.audio_buffer) > 0:
                    await self._process_buffer(final=True)
                await self.send(text_data=json.dumps({'type': 'stopped'}))

            elif action == 'config':
                self.language = data.get('language', 'auto')

    async def _process_buffer(self, final=False):
        """处理音频缓冲区"""
        if len(self.audio_buffer) == 0:
            return

        audio_data = bytes(self.audio_buffer)
        self.audio_buffer.clear()

        try:
            client = get_oddasr_client()
            result = await asyncio.to_thread(
                client.transcribe_bytes,
                audio_data,
                language=self.language
            )

            if 'error' not in result:
                await self.send(text_data=json.dumps({
                    'type': 'partial' if not final else 'final',
                    'text': result.get('text', ''),
                    'is_final': final,
                }))
            else:
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': result['error'],
                }))

        except Exception as e:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': str(e),
            }))
