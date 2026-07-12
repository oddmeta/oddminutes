import logging
import os
import subprocess

logger = logging.getLogger(__name__)


def convert_audio_to_mp3(meeting):
    if not meeting.audio_file:
        return

    audio_path = meeting.audio_file.path
    file_ext = os.path.splitext(audio_path)[1].lower()

    if file_ext == '.mp3':
        return

    try:
        mp3_path = os.path.splitext(audio_path)[0] + '.mp3'
        
        ffmpeg_cmd = [
            'ffmpeg', '-y', '-i', audio_path,
            '-codec:a', 'libmp3lame', '-q:a', '2', mp3_path
        ]
        
        startupinfo = None
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE
        
        result = subprocess.run(
            ffmpeg_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            startupinfo=startupinfo,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
            check=True
        )

        if os.path.exists(audio_path):
            os.remove(audio_path)

        rel_mp3_path = os.path.splitext(meeting.audio_file.name)[0] + '.mp3'
        meeting.audio_file.name = rel_mp3_path
        meeting.save(update_fields=['audio_file'])

    except subprocess.CalledProcessError as e:
        logger.error(f"音频转换失败 {audio_path}: {e.stderr.decode('utf-8', errors='ignore')}")
    except Exception as e:
        logger.error(f"音频转换失败 {audio_path}: {e}")
