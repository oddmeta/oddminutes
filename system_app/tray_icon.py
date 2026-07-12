"""
系统托盘图标功能
"""
import os
import threading
import logging
from typing import Callable, Optional

try:
    import pystray
    from PIL import Image, ImageDraw
    HAS_PYSTRAY = True
except ImportError:
    HAS_PYSTRAY = False

logger = logging.getLogger(__name__)


class TrayIconManager:
    """系统托盘图标管理器"""

    def __init__(self):
        self.icon: Optional[pystray.Icon] = None
        self._running = False
        self._on_new_meeting: Optional[Callable] = None
        self._on_start_recording: Optional[Callable] = None
        self._on_stop_recording: Optional[Callable] = None
        self._on_pause_recording: Optional[Callable] = None
        self._on_resume_recording: Optional[Callable] = None
        self._on_show_window: Optional[Callable] = None
        self._on_exit: Optional[Callable] = None
        self._recording = False
        self._paused = False

    def set_callbacks(self, on_new_meeting=None, on_start_recording=None,
                      on_stop_recording=None, on_pause_recording=None,
                      on_resume_recording=None, on_show_window=None, on_exit=None):
        """设置回调函数"""
        self._on_new_meeting = on_new_meeting
        self._on_start_recording = on_start_recording
        self._on_stop_recording = on_stop_recording
        self._on_pause_recording = on_pause_recording
        self._on_resume_recording = on_resume_recording
        self._on_show_window = on_show_window
        self._on_exit = on_exit

    def _create_icon_image(self):
        """创建托盘图标，优先从favicon.ico加载"""
        project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        favicon_path = os.path.join(project_dir, 'static', 'favicon.ico')
        
        if os.path.exists(favicon_path):
            try:
                img = Image.open(favicon_path)
                if img.format == 'ICO':
                    img = img.resize((64, 64), Image.LANCZOS)
                    return img
            except Exception as e:
                logger.warning(f'加载favicon.ico失败: {e}')
        
        width = 64
        height = 64
        image = Image.new('RGB', (width, height), color='white')
        dc = ImageDraw.Draw(image)

        dc.ellipse([16, 8, 48, 40], fill='black')
        dc.rectangle([28, 40, 36, 52], fill='black')
        dc.arc([12, 20, 52, 52], 0, 180, fill='black', width=3)

        return image

    def _create_menu(self):
        """创建菜单，根据状态动态显示"""
        menu_items = []

        menu_items.append(pystray.MenuItem("新会议", self._on_clicked))

        if self._recording and not self._paused:
            menu_items.append(pystray.MenuItem("暂停录音", self._on_clicked))
            menu_items.append(pystray.MenuItem("停止录音", self._on_clicked))
        elif self._recording and self._paused:
            menu_items.append(pystray.MenuItem("继续录音", self._on_clicked))
            menu_items.append(pystray.MenuItem("停止录音", self._on_clicked))
        else:
            menu_items.append(pystray.MenuItem("开始录音", self._on_clicked))

        menu_items.append(pystray.MenuItem("显示主窗口", self._on_clicked))
        menu_items.append(pystray.MenuItem("退出", self._on_clicked))

        return pystray.Menu(*menu_items)

    def _on_clicked(self, icon, item):
        """处理菜单点击"""
        item_text = str(item)
        if item_text == "新会议" and self._on_new_meeting:
            self._on_new_meeting()
        elif item_text == "开始录音" and self._on_start_recording:
            self._on_start_recording()
        elif item_text == "停止录音" and self._on_stop_recording:
            self._on_stop_recording()
        elif item_text == "暂停录音" and self._on_pause_recording:
            self._on_pause_recording()
        elif item_text == "继续录音" and self._on_resume_recording:
            self._on_resume_recording()
        elif item_text == "显示主窗口" and self._on_show_window:
            self._on_show_window()
        elif item_text == "退出":
            icon.stop()
            if self._on_exit:
                self._on_exit()

    def start(self):
        """启动托盘图标"""
        if not HAS_PYSTRAY:
            logger.warning("pystray not installed, tray icon not available")
            return False

        if self._running:
            return True

        try:
            self.icon = pystray.Icon(
                "open_minutes",
                self._create_icon_image(),
                "小奥会议纪要",
                self._create_menu(),
            )

            self._running = True
            self.icon.run_detached()
            return True

        except Exception as e:
            logger.error(f"Failed to start tray icon: {e}")
            return False

    def stop(self):
        """停止托盘图标"""
        if self.icon:
            self.icon.stop()
        self._running = False

    def update_tooltip(self, text: str):
        """更新托盘提示文本"""
        if self.icon:
            self.icon.title = text

    def update_recording_state(self, recording: bool, paused: bool = False):
        """更新录音状态，同步菜单文字和图标"""
        self._recording = recording
        self._paused = paused
        
        if self.icon:
            try:
                self.icon.menu = self._create_menu()
            except Exception as e:
                logger.error(f"Failed to update menu: {e}")


_tray_instance: Optional[TrayIconManager] = None


def get_tray_manager() -> TrayIconManager:
    """获取托盘管理器实例"""
    global _tray_instance
    if _tray_instance is None:
        _tray_instance = TrayIconManager()
    return _tray_instance