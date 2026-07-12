"""
OddASR 客户端（OpenAI 兼容 API）
调用 OddASR 的 OpenAI 兼容接口进行语音识别
接口格式参考 OpenAI Audio Transcriptions API
"""
import logging
import io
import requests
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def _load_oddasr_from_env():
    """动态从 .env 文件读取 OddASR 地址"""
    env_file = Path(__file__).resolve().parent.parent / '.env'
    host = '127.0.0.1'
    port = '9002'
    if env_file.exists():
        for line in env_file.read_text(encoding='utf-8').splitlines():
            if line.startswith('ODDASR_HOST='):
                host = line.split('=', 1)[1].strip().strip('"').strip("'")
            elif line.startswith('ODDASR_PORT='):
                port = line.split('=', 1)[1].strip().strip('"').strip("'")
    return host, port


class OddASRClient:
    """OddASR OpenAI 兼容 API 客户端"""

    def __init__(self, host=None, port=None):
        if host is None or port is None:
            env_host, env_port = _load_oddasr_from_env()
        self.host = host or env_host
        self.port = port or env_port
        self.base_url = f"http://{self.host}:{self.port}"
        self.transcriptions_url = f"{self.base_url}/v1/audio/transcriptions"

    def transcribe_file(self, audio_path: str, language: str = 'auto', response_format: str = 'verbose_json') -> dict:
        """
        文件转录 API (OpenAI 兼容格式)
        POST /v1/audio/transcriptions
        Form-data: file=@path/to/audio.wav; model=whisper-1; language=zh
        """
        try:
            with open(audio_path, 'rb') as f:
                files = {'file': ('audio.wav', f, 'audio/wav')}
                data = {
                    'model': 'whisper-1',
                    'response_format': response_format,
                }
                if language and language != 'auto':
                    data['language'] = language

                # 请求 word-level 时间戳（OpenAI 兼容参数）
                data['timestamp_granularities[]'] = 'word'

                logger.info(f"Sending transcription request to {self.transcriptions_url}")
                response = requests.post(
                    self.transcriptions_url,
                    files=files,
                    data=data,
                    timeout=300
                )
                response.raise_for_status()

                result = response.json()

                logger.info(f"Raw response from OddASR: {result}")
                
                text = result.get('text', '')
                segments = result.get('segments', [])
                word_count = sum(len(seg.get('words', [])) for seg in segments)
                logger.info(f"Transcription completed: {len(text)} chars, {len(segments)} segments, {word_count} words")
                return result

        except requests.exceptions.ConnectionError:
            logger.error(f"Cannot connect to OddASR server at {self.base_url}")
            return {'error': '无法连接到 OddASR 服务，请确认服务已启动'}
        except requests.exceptions.Timeout:
            logger.error("Transcription request timed out")
            return {'error': '转录请求超时'}
        except Exception as e:
            logger.error(f"Transcription error: {e}")
            return {'error': str(e)}

    def transcribe_bytes(self, audio_bytes: bytes, language: str = 'auto', response_format: str = 'verbose_json') -> dict:
        """
        使用音频字节数据进行转录 (OpenAI 兼容格式)
        """
        try:
            files = {'file': ('audio.wav', io.BytesIO(audio_bytes), 'audio/wav')}
            data = {
                'model': 'whisper-1',
                'response_format': response_format,
            }
            if language and language != 'auto':
                data['language'] = language

            # 请求 word-level 时间戳（OpenAI 兼容参数）
            data['timestamp_granularities[]'] = 'word'

            response = requests.post(
                self.transcriptions_url,
                files=files,
                data=data,
                timeout=300
            )
            response.raise_for_status()

            return response.json()

        except requests.exceptions.ConnectionError:
            logger.error(f"Cannot connect to OddASR server at {self.base_url}")
            return {'error': '无法连接到 OddASR 服务'}
        except Exception as e:
            logger.error(f"Transcription error: {e}")
            return {'error': str(e)}

    def health_check(self) -> bool:
        """检查 OddASR 服务是否可用"""
        try:
            response = requests.get(f"{self.base_url}/v1/models", timeout=5)
            return response.status_code == 200
        except:
            return False

    def get_models(self) -> list:
        """获取可用的模型列表"""
        try:
            response = requests.get(f"{self.base_url}/v1/models", timeout=10)
            if response.status_code == 200:
                data = response.json()
                # OpenAI 兼容格式: {"data": [{"id": "model-name"}, ...]}
                models = data.get('data', [])
                return [m.get('id', '') for m in models if m.get('id')]
        except Exception as e:
            logger.error(f"Error getting models: {e}")
        return []


def get_oddasr_client() -> OddASRClient:
    """获取 OddASR 客户端实例（每次调用都会重新读取配置）"""
    return OddASRClient()
