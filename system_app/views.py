import os
import platform
from pathlib import Path
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import SystemSettings, UpdateInfo, NotificationLog

ENV_FILE = Path(__file__).resolve().parent.parent / '.env'


def _read_env_var(key, default=''):
    """从 .env 文件读取变量"""
    if not ENV_FILE.exists():
        return default
    for line in ENV_FILE.read_text(encoding='utf-8').splitlines():
        if line.startswith(f'{key}='):
            return line.split('=', 1)[1].strip().strip('"').strip("'")
    return default


def _write_env_var(key, value):
    """写入变量到 .env 文件"""
    lines = []
    if ENV_FILE.exists():
        lines = ENV_FILE.read_text(encoding='utf-8').splitlines()

    updated = False
    new_lines = []
    for line in lines:
        if line.startswith(f'{key}='):
            new_lines.append(f'{key}={value}')
            updated = True
        else:
            new_lines.append(line)

    if not updated:
        new_lines.append(f'{key}={value}')

    ENV_FILE.write_text('\n'.join(new_lines) + '\n', encoding='utf-8')


def _get_oddasr_address():
    """从 .env 读取 OddASR 地址"""
    host = _read_env_var('ODDASR_HOST', '127.0.0.1')
    port = _read_env_var('ODDASR_PORT', '9002')
    return f"{host}:{port}"


def _set_oddasr_address(address):
    """将 OddASR 地址写入 .env"""
    try:
        host, port = address.split(':')
    except ValueError:
        host = address
        port = '9002'
    _write_env_var('ODDASR_HOST', host)
    _write_env_var('ODDASR_PORT', port)


@api_view(['GET', 'POST'])
def system_settings(request):
    """获取或更新系统设置"""
    settings_obj, _ = SystemSettings.objects.get_or_create(
        defaults={
            'auto_start': False,
            'minimize_to_tray': True,
            'enable_notifications': True,
        }
    )

    if request.method == 'GET':
        return Response({
            'auto_start': settings_obj.auto_start,
            'minimize_to_tray': settings_obj.minimize_to_tray,
            'dnd_mode': settings_obj.dnd_mode,
            'enable_notifications': settings_obj.enable_notifications,
            'enable_analytics': settings_obj.enable_analytics,
            'auto_cleanup_days': settings_obj.auto_cleanup_days,
            'global_shortcuts': settings_obj.global_shortcuts,
            'theme': settings_obj.theme,
            'onboarding_completed': settings_obj.onboarding_completed,
            'oddasr_host': _get_oddasr_address(),
        })

    elif request.method == 'POST':
        settings_obj.auto_start = request.data.get('auto_start', settings_obj.auto_start)
        settings_obj.minimize_to_tray = request.data.get('minimize_to_tray', settings_obj.minimize_to_tray)
        settings_obj.dnd_mode = request.data.get('dnd_mode', settings_obj.dnd_mode)
        settings_obj.enable_notifications = request.data.get('enable_notifications', settings_obj.enable_notifications)
        settings_obj.enable_analytics = request.data.get('enable_analytics', settings_obj.enable_analytics)
        settings_obj.auto_cleanup_days = request.data.get('auto_cleanup_days', settings_obj.auto_cleanup_days)
        settings_obj.global_shortcuts = request.data.get('global_shortcuts', settings_obj.global_shortcuts)
        settings_obj.theme = request.data.get('theme', settings_obj.theme)
        settings_obj.onboarding_completed = request.data.get('onboarding_completed', settings_obj.onboarding_completed)
        settings_obj.save()

        # 保存 OddASR 地址到 .env
        oddasr_host = request.data.get('oddasr_host')
        if oddasr_host:
            _set_oddasr_address(oddasr_host)

        return Response({'status': 'saved'})


@api_view(['GET'])
def check_updates(request):
    """检查更新"""
    update_info, _ = UpdateInfo.objects.get_or_create(
        defaults={
            'current_version': '1.0.0',
            'auto_check': True,
        }
    )

    # 这里可以实现实际的更新检查逻辑
    # 例如访问 GitHub API 或自定义更新服务器

    return Response({
        'current_version': update_info.current_version,
        'latest_version': update_info.latest_version or update_info.current_version,
        'has_update': update_info.latest_version and update_info.latest_version != update_info.current_version,
        'download_url': update_info.download_url,
        'release_notes': update_info.release_notes,
    })


@api_view(['GET'])
def get_notifications(request):
    """获取通知列表"""
    notifications = NotificationLog.objects.all()[:50]
    return Response([{
        'id': str(n.id),
        'title': n.title,
        'message': n.message,
        'type': n.notification_type,
        'is_read': n.is_read,
        'created_at': n.created_at,
    } for n in notifications])


@api_view(['POST'])
def mark_notification_read(request):
    """标记通知为已读"""
    notification_id = request.data.get('id')
    notification = get_object_or_404(NotificationLog, id=notification_id)
    notification.is_read = True
    notification.save()
    return Response({'status': 'marked'})


@api_view(['POST'])
def send_notification(request):
    """发送系统通知"""
    title = request.data.get('title', '通知')
    message = request.data.get('message', '')
    notification_type = request.data.get('type', 'info')

    # 保存通知日志
    NotificationLog.objects.create(
        title=title,
        message=message,
        notification_type=notification_type,
    )

    # 尝试发送系统通知
    try:
        if platform.system() == 'Windows':
            from win10toast import ToastNotifier
            toaster = ToastNotifier()
            toaster.show_toast(title, message, duration=5)
    except Exception as e:
        pass

    return Response({'status': 'sent'})


@api_view(['POST'])
def complete_onboarding(request):
    """完成首次启动引导"""
    settings_obj, _ = SystemSettings.objects.get_or_create()
    settings_obj.onboarding_completed = True
    settings_obj.save()
    return Response({'status': 'completed'})


@api_view(['GET'])
def system_info(request):
    """获取系统信息"""
    return Response({
        'platform': platform.system(),
        'platform_version': platform.version(),
        'python_version': platform.python_version(),
        'node': platform.node(),
    })
