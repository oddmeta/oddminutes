"""
音频录制模块，支持麦克风录制、系统音频录制、双轨混音、实时电平监测等功能
"""
import io
import wave
import threading
import time
import logging
from dataclasses import dataclass
from typing import Callable, Optional, List
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)

try:
    import pyaudio
    HAS_PYAUDIO = True
except ImportError:
    HAS_PYAUDIO = False
    logger.info("PyAudio not installed, will use sounddevice")

try:
    import sounddevice as sd
    HAS_SOUNDDEVICE = True
except ImportError:
    HAS_SOUNDDEVICE = False
    logger.warning("sounddevice not installed")


@dataclass
class AudioLevel:
    """音频电平数据"""
    mic_level: float = 0.0
    system_level: float = 0.0
    mixed_level: float = 0.0
    peak_mic: float = 0.0
    peak_system: float = 0.0


class AudioRecorder:
    """音频录制器，支持麦克风+系统音频双轨录制和混音"""

    def __init__(self, sample_rate=16000, channels=1, chunk_duration=5):
        self.sample_rate = sample_rate
        self.channels = channels
        self.chunk_duration = chunk_duration
        self.chunk_samples = int(sample_rate * chunk_duration)

        self._recording = False
        self._monitoring = False
        self._paused = False
        self._status = 'idle'
        self._error_message = ''

        self._mic_stream = None
        self._system_stream = None

        self._mic_buffer = []
        self._system_buffer = []
        self._mixed_buffer = []

        self._record_thread = None
        self._level_thread = None
        self._checkpoint_thread = None

        self._current_level = AudioLevel()
        self._level_callback: Optional[Callable[[AudioLevel], None]] = None
        self._audio_callback: Optional[Callable[[bytes, float], None]] = None
        self._checkpoint_callback: Optional[Callable[[], None]] = None

        self._total_duration = 0.0
        self._segment_index = 0
        self._checkpoint_interval = 30
        self._last_checkpoint_time = 0

        self._lock = threading.Lock()

        # AGC (自动增益控制) 参数
        self._agc_enabled = True
        self._mic_gain = 1.0
        self._system_gain = 1.0
        self._target_rms = 8000.0
        self._agc_attack = 0.05
        self._agc_decay = 0.005
        self._max_gain = 10.0
        self._min_gain = 0.1

    @property
    def status(self) -> str:
        return self._status

    @property
    def current_level(self) -> AudioLevel:
        return self._current_level

    @property
    def agc_status(self) -> dict:
        """获取 AGC 状态"""
        return {
            'enabled': self._agc_enabled,
            'mic_gain': round(self._mic_gain, 2),
            'system_gain': round(self._system_gain, 2),
            'target_rms': int(self._target_rms),
        }

    def set_level_callback(self, callback: Callable[[AudioLevel], None]):
        """设置电平监测回调"""
        self._level_callback = callback

    def set_audio_callback(self, callback: Callable[[bytes, float], None]):
        """设置音频数据回调（用于实时转录）"""
        self._audio_callback = callback

    def set_checkpoint_callback(self, callback: Callable[[], None]):
        """设置检查点保存回调"""
        self._checkpoint_callback = callback

    def get_devices(self) -> List[dict]:
        """获取所有可用音频设备"""
        devices = []

        if HAS_SOUNDDEVICE:
            try:
                device_list = sd.query_devices()
                for i, dev in enumerate(device_list):
                    devices.append({
                        'id': i,
                        'name': dev['name'],
                        'channels': dev['max_input_channels'],
                        'sample_rate': int(dev['default_samplerate']),
                        'type': 'input' if dev['max_input_channels'] > 0 else 'output',
                    })
            except Exception as e:
                logger.error(f"Error querying devices: {e}")

        return devices

    def start_monitoring(self, mic_device_id: Optional[int] = None,
                          system_device_id: Optional[int] = None,
                          enable_system_audio: bool = False):
        """开始预监听（只打开音频流，不保存数据，用于实时电平显示）"""
        with self._lock:
            if self._recording or self._monitoring:
                return

            if not HAS_SOUNDDEVICE:
                return

            self._monitoring = True
            self._status = 'monitoring'

        try:
            if HAS_SOUNDDEVICE:
                blocksize = 1024
                sd.default.samplerate = self.sample_rate
                sd.default.channels = self.channels

                try:
                    self._mic_stream = sd.InputStream(
                        device=mic_device_id,
                        channels=self.channels,
                        samplerate=self.sample_rate,
                        blocksize=blocksize,
                        dtype='int16',
                    )
                    self._mic_stream.start()
                except Exception as e:
                    logger.error(f"Failed to open microphone stream for monitoring: {e}")
                    self._mic_stream = None

                if enable_system_audio and system_device_id is not None:
                    try:
                        self._system_stream = sd.InputStream(
                            device=system_device_id,
                            channels=self.channels,
                            samplerate=self.sample_rate,
                            blocksize=blocksize,
                            dtype='int16',
                        )
                        self._system_stream.start()
                    except Exception as e:
                        logger.warning(f"Could not open system audio device for monitoring: {e}")
                        self._system_stream = None

            self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self._monitor_thread.start()

            self._level_thread = threading.Thread(target=self._level_loop, daemon=True)
            self._level_thread.start()

            logger.info("Monitoring started")

        except Exception as e:
            self._status = 'error'
            logger.error(f"Failed to start monitoring: {e}")

    def _monitor_loop(self):
        """预监听循环：读取音频数据到缓冲区，但不保存"""
        logger.info(f"[Monitor] 预监听循环启动, mic_stream={self._mic_stream}, system_stream={self._system_stream}")
        
        while self._monitoring:
            try:
                if self._mic_stream and self._mic_stream.active:
                    try:
                        mic_data, _ = self._mic_stream.read(1024)
                        if mic_data.ndim > 1:
                            mic_data = mic_data[:, 0]
                        mic_array = mic_data.astype(np.int16)
                        if self._agc_enabled:
                            mic_array, self._mic_gain = self._apply_agc(mic_array, self._mic_gain)
                        self._mic_buffer.append(mic_array)
                        if len(self._mic_buffer) > 20:
                            self._mic_buffer = self._mic_buffer[-10:]
                        logger.debug(f"[Monitor] 读取麦克风数据: {len(mic_array)} samples, buffer_size={len(self._mic_buffer)}")
                    except sd.PortAudioError as e:
                        if e.args[0] == 'Stream is stopped':
                            break
                        logger.error(f"Mic stream error in monitor: {e}")
                else:
                    logger.debug(f"[Monitor] 麦克风流未激活: mic_stream={self._mic_stream}, active={self._mic_stream.active if self._mic_stream else 'None'}")

                if self._system_stream and self._system_stream.active:
                    try:
                        system_data, _ = self._system_stream.read(1024)
                        if system_data.ndim > 1:
                            system_data = system_data[:, 0]
                        system_array = system_data.astype(np.int16)
                        if self._agc_enabled:
                            system_array, self._system_gain = self._apply_agc(system_array, self._system_gain)
                        self._system_buffer.append(system_array)
                        if len(self._system_buffer) > 20:
                            self._system_buffer = self._system_buffer[-10:]
                        logger.debug(f"[Monitor] 读取系统音频数据: {len(system_array)} samples")
                    except sd.PortAudioError as e:
                        if e.args[0] == 'Stream is stopped':
                            break
                        logger.error(f"System stream error in monitor: {e}")

            except Exception as e:
                logger.error(f"Error in monitor loop: {e}")
                time.sleep(0.01)

    def stop_monitoring(self):
        """停止预监听"""
        self._monitoring = False
        self._status = 'idle'

        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=1)

        if self._level_thread and self._level_thread.is_alive():
            self._level_thread.join(timeout=1)

        if self._mic_stream:
            try:
                self._mic_stream.stop()
                self._mic_stream.close()
            except Exception as e:
                logger.error(f"Error closing mic stream: {e}")
            self._mic_stream = None

        if self._system_stream:
            try:
                self._system_stream.stop()
                self._system_stream.close()
            except Exception as e:
                logger.error(f"Error closing system stream: {e}")
            self._system_stream = None

        self._mic_buffer.clear()
        self._system_buffer.clear()

    def start(self, mic_device_id: Optional[int] = None,
              system_device_id: Optional[int] = None,
              enable_system_audio: bool = False):
        """开始录音"""
        with self._lock:
            if self._recording:
                self._status = 'recording'
                self._error_message = 'Already recording'
                return False

            if not HAS_SOUNDDEVICE:
                self._status = 'error'
                self._error_message = 'sounddevice not available'
                return False

            if self._monitoring:
                self._monitoring = False
                if self._monitor_thread and self._monitor_thread.is_alive():
                    self._monitor_thread.join(timeout=1)

            self._recording = True
            self._paused = False
            self._status = 'recording'
            self._total_duration = 0.0

        try:
            self._mic_buffer.clear()
            self._system_buffer.clear()
            self._mixed_buffer.clear()

            if HAS_SOUNDDEVICE:
                blocksize = 1024
                sd.default.samplerate = self.sample_rate
                sd.default.channels = self.channels

                if not self._mic_stream:
                    try:
                        self._mic_stream = sd.InputStream(
                            device=mic_device_id,
                            channels=self.channels,
                            samplerate=self.sample_rate,
                            blocksize=blocksize,
                            dtype='int16',
                        )
                        self._mic_stream.start()
                    except Exception as e:
                        logger.error(f"Failed to open microphone stream: {e}")
                        self._mic_stream = None
                else:
                    try:
                        self._mic_stream.stop()
                        self._mic_stream.close()
                    except Exception:
                        pass
                    try:
                        self._mic_stream = sd.InputStream(
                            device=mic_device_id,
                            channels=self.channels,
                            samplerate=self.sample_rate,
                            blocksize=blocksize,
                            dtype='int16',
                        )
                        self._mic_stream.start()
                    except Exception as e:
                        logger.error(f"Failed to open microphone stream: {e}")
                        self._mic_stream = None

                if enable_system_audio and system_device_id is not None:
                    if not self._system_stream:
                        try:
                            self._system_stream = sd.InputStream(
                                device=system_device_id,
                                channels=self.channels,
                                samplerate=self.sample_rate,
                                blocksize=blocksize,
                                dtype='int16',
                            )
                            self._system_stream.start()
                        except Exception as e:
                            logger.warning(f"Could not open system audio device: {e}")
                            self._system_stream = None
                    else:
                        try:
                            self._system_stream.stop()
                            self._system_stream.close()
                        except Exception:
                            pass
                        try:
                            self._system_stream = sd.InputStream(
                                device=system_device_id,
                                channels=self.channels,
                                samplerate=self.sample_rate,
                                blocksize=blocksize,
                                dtype='int16',
                            )
                            self._system_stream.start()
                        except Exception as e:
                            logger.warning(f"Could not open system audio device: {e}")
                            self._system_stream = None

            self._record_thread = threading.Thread(target=self._record_loop, daemon=True)
            self._record_thread.start()

            self._level_thread = threading.Thread(target=self._level_loop, daemon=True)
            self._level_thread.start()

            self._checkpoint_thread = threading.Thread(target=self._checkpoint_loop, daemon=True)
            self._checkpoint_thread.start()

            logger.info("Recording started")
            return True

        except Exception as e:
            self._status = 'error'
            self._error_message = str(e)
            logger.error(f"Failed to start recording: {e}")
            return False

    def pause(self):
        """暂停录音"""
        with self._lock:
            self._paused = True
            self._status = 'paused'
        logger.info("Recording paused")

    def resume(self):
        """恢复录音"""
        with self._lock:
            self._paused = False
            self._status = 'recording'
        logger.info("Recording resumed")

    def _drain_mic_stream(self):
        """读取麦克风流中剩余的缓冲数据"""
        if not self._mic_stream or not self._mic_stream.active:
            return
        try:
            while True:
                try:
                    mic_data, _ = self._mic_stream.read(1024, timeout=0.1)
                    if mic_data.ndim > 1:
                        mic_data = mic_data[:, 0]
                    mic_array = mic_data.astype(np.int16)
                    if self._agc_enabled:
                        mic_array, self._mic_gain = self._apply_agc(mic_array, self._mic_gain)
                    self._mic_buffer.append(mic_array)
                    mixed = self._mix_audio(mic_array, None)
                    self._mixed_buffer.append(mixed)
                    self._total_duration += 1024 / self.sample_rate
                except sd.PortAudioError as e:
                    if e.args[0] == 'Stream is stopped':
                        break
                    raise
                except sd.TimeoutError:
                    break
        except Exception as e:
            logger.debug(f"Error draining mic stream: {e}")

    def _drain_system_stream(self):
        """读取系统音频流中剩余的缓冲数据"""
        if not self._system_stream or not self._system_stream.active:
            return
        try:
            while True:
                try:
                    system_data, _ = self._system_stream.read(1024, timeout=0.1)
                    if system_data.ndim > 1:
                        system_data = system_data[:, 0]
                    system_array = system_data.astype(np.int16)
                    if self._agc_enabled:
                        system_array, self._system_gain = self._apply_agc(system_array, self._system_gain)
                    self._system_buffer.append(system_array)
                    mixed = self._mix_audio(None, system_array)
                    self._mixed_buffer.append(mixed)
                    self._total_duration += 1024 / self.sample_rate
                except sd.PortAudioError as e:
                    if e.args[0] == 'Stream is stopped':
                        break
                    raise
                except sd.TimeoutError:
                    break
        except Exception as e:
            logger.debug(f"Error draining system stream: {e}")

    def stop(self) -> Optional[bytes]:
        """停止录音并返回音频数据"""
        self._recording = False
        self._status = 'stopped'

        if self._record_thread and self._record_thread.is_alive():
            self._record_thread.join(timeout=2)
        if self._level_thread and self._level_thread.is_alive():
            self._level_thread.join(timeout=1)
        if self._checkpoint_thread and self._checkpoint_thread.is_alive():
            self._checkpoint_thread.join(timeout=1)

        if self._mic_stream:
            self._drain_mic_stream()
            try:
                self._mic_stream.stop()
                self._mic_stream.close()
            except Exception as e:
                logger.error(f"Error closing mic stream: {e}")
            self._mic_stream = None

        if self._system_stream:
            self._drain_system_stream()
            try:
                self._system_stream.stop()
                self._system_stream.close()
            except Exception as e:
                logger.error(f"Error closing system stream: {e}")
            self._system_stream = None

        audio_data = self._get_mixed_audio()
        logger.info(f"Recording stopped, total duration: {self._total_duration:.1f}s")
        return audio_data

    def _record_loop(self):
        """录音主循环"""
        while self._recording:
            if self._paused:
                time.sleep(0.1)
                continue

            try:
                mic_array = None
                if self._mic_stream and self._mic_stream.active:
                    try:
                        mic_data, _ = self._mic_stream.read(1024)
                        if mic_data.ndim > 1:
                            mic_data = mic_data[:, 0]
                        mic_array = mic_data.astype(np.int16)
                        if self._agc_enabled:
                            mic_array, self._mic_gain = self._apply_agc(mic_array, self._mic_gain)
                        self._mic_buffer.append(mic_array)
                    except sd.PortAudioError as e:
                        if e.args[0] == 'Stream is stopped':
                            break
                        logger.error(f"Mic stream error: {e}")

                system_array = None
                if self._system_stream and self._system_stream.active:
                    try:
                        system_data, _ = self._system_stream.read(1024)
                        if system_data.ndim > 1:
                            system_data = system_data[:, 0]
                        system_array = system_data.astype(np.int16)
                        if self._agc_enabled:
                            system_array, self._system_gain = self._apply_agc(system_array, self._system_gain)
                        self._system_buffer.append(system_array)
                    except sd.PortAudioError as e:
                        if e.args[0] == 'Stream is stopped':
                            break
                        logger.error(f"System stream error: {e}")

                mixed = self._mix_audio(mic_array, system_array)
                self._mixed_buffer.append(mixed)

                self._total_duration += 1024 / self.sample_rate

                if self._audio_callback and len(self._mixed_buffer) >= self.chunk_samples // 1024:
                    chunk = np.concatenate(self._mixed_buffer[:self.chunk_samples // 1024])
                    self._audio_callback(chunk.tobytes(), self._total_duration)
                    self._mixed_buffer = self._mixed_buffer[self.chunk_samples // 1024:]

            except Exception as e:
                logger.error(f"Error in record loop: {e}")
                time.sleep(0.01)

    def _level_loop(self):
        """电平监测循环"""
        while self._recording or self._monitoring:
            if self._paused:
                time.sleep(0.1)
                continue

            try:
                mic_level = 0.0
                system_level = 0.0
                peak_mic = 0.0
                peak_system = 0.0

                if self._mic_buffer:
                    recent_mic = np.concatenate(self._mic_buffer[-10:]) if len(self._mic_buffer) > 10 else np.concatenate(self._mic_buffer)
                    if len(recent_mic) > 0:
                        mic_level = self._calculate_rms(recent_mic)
                        peak_mic = float(np.max(np.abs(recent_mic)) / 32768.0)

                if self._system_buffer:
                    recent_sys = np.concatenate(self._system_buffer[-10:]) if len(self._system_buffer) > 10 else np.concatenate(self._system_buffer)
                    if len(recent_sys) > 0:
                        system_level = self._calculate_rms(recent_sys)
                        peak_system = float(np.max(np.abs(recent_sys)) / 32768.0)

                mixed_level = max(mic_level, system_level)

                self._current_level = AudioLevel(
                    mic_level=mic_level,
                    system_level=system_level,
                    mixed_level=mixed_level,
                    peak_mic=peak_mic,
                    peak_system=peak_system,
                )

                if self._level_callback:
                    self._level_callback(self._current_level)

            except Exception as e:
                logger.error(f"Error in level loop: {e}")

            time.sleep(0.1)

    def _checkpoint_loop(self):
        """检查点保存循环"""
        self._last_checkpoint_time = time.time()

        while self._recording:
            time.sleep(1)
            if self._paused:
                continue

            elapsed = time.time() - self._last_checkpoint_time
            if elapsed >= self._checkpoint_interval:
                self._last_checkpoint_time = time.time()
                if self._checkpoint_callback:
                    try:
                        self._checkpoint_callback()
                    except Exception as e:
                        logger.error(f"Checkpoint callback error: {e}")

    def _apply_agc(self, audio: np.ndarray, current_gain: float) -> tuple:
        """
        应用自动增益控制 (AGC)
        返回增益后的音频和更新后的增益值
        """
        if len(audio) == 0:
            return audio, current_gain

        float_audio = audio.astype(np.float32)
        rms = np.sqrt(np.mean(float_audio ** 2))

        if rms < 1.0:
            return audio, current_gain

        desired_gain = self._target_rms / rms

        if desired_gain > current_gain:
            new_gain = current_gain + (desired_gain - current_gain) * self._agc_attack
        else:
            new_gain = current_gain + (desired_gain - current_gain) * self._agc_decay

        new_gain = np.clip(new_gain, self._min_gain, self._max_gain)

        amplified = float_audio * new_gain

        amplified = np.clip(amplified, -32768, 32767)

        return amplified.astype(np.int16), new_gain

    def _mix_audio(self, mic_array: np.ndarray, system_array: Optional[np.ndarray]) -> np.ndarray:
        """混音处理，带自动压限"""
        if system_array is None:
            return mic_array
        if mic_array is None:
            return system_array

        min_len = min(len(mic_array), len(system_array))
        mic = mic_array[:min_len].astype(np.float32)
        system = system_array[:min_len].astype(np.float32)

        mixed = mic * 0.55 + system * 0.55

        threshold = 30000
        mixed = np.where(
            np.abs(mixed) > threshold,
            np.sign(mixed) * (threshold + (np.abs(mixed) - threshold) * 0.3),
            mixed
        )

        mixed = np.clip(mixed, -32768, 32767)
        return mixed.astype(np.int16)

    def _calculate_rms(self, audio: np.ndarray) -> float:
        """计算 RMS 电平 (0-1)"""
        if len(audio) == 0:
            return 0.0
        rms = np.sqrt(np.mean(audio.astype(np.float32) ** 2))
        return float(min(rms / 32768.0, 1.0))

    def _get_mixed_audio(self) -> bytes:
        """获取混音后的音频数据并编码为 WAV 格式"""
        if not self._mixed_buffer:
            return b''

        all_audio = np.concatenate(self._mixed_buffer)

        buf = io.BytesIO()
        with wave.open(buf, 'wb') as wf:
            wf.setnchannels(self.channels)
            wf.setsampwidth(2)
            wf.setframerate(self.sample_rate)
            wf.writeframes(all_audio.tobytes())

        return buf.getvalue()

    def save_to_file(self, filepath: str) -> str:
        """保存录音到文件"""
        audio_data = self._get_mixed_audio()
        if not audio_data:
            return ''

        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'wb') as f:
            f.write(audio_data)

        return filepath

    def get_checkpoints_audio(self) -> bytes:
        """获取检查点合并后的音频"""
        return self._get_mixed_audio()

    def cleanup(self):
        """清理资源"""
        self.stop()


# 全局录音器实例
_recorder_instance: Optional[AudioRecorder] = None


def get_recorder() -> AudioRecorder:
    """获取全局录音器实例"""
    global _recorder_instance
    if _recorder_instance is None:
        _recorder_instance = AudioRecorder()
    return _recorder_instance


def reset_recorder():
    """重置录音器"""
    global _recorder_instance
    if _recorder_instance:
        _recorder_instance.cleanup()
    _recorder_instance = None