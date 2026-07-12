"""
全局快捷键支持
"""
import logging
import threading
from typing import Callable, Optional

try:
    import keyboard
    HAS_KEYBOARD = True
except ImportError:
    HAS_KEYBOARD = False

logger = logging.getLogger(__name__)


class ShortcutManager:
    """全局快捷键管理器"""

    DEFAULT_SHORTCUTS = {
        'toggle_record': 'ctrl+shift+r',
        'show_window': 'ctrl+shift+m',
        'pause_record': 'ctrl+shift+p',
    }

    def __init__(self):
        self._handlers = {}
        self._registered = False
        self._lock = threading.Lock()

    def register_handler(self, action: str, callback: Callable):
        """注册快捷键处理函数"""
        self._handlers[action] = callback

    def unregister_handler(self, action: str):
        """注销快捷键处理函数"""
        if action in self._handlers:
            del self._handlers[action]

    def start(self, shortcuts: Optional[dict] = None):
        """启动快捷键监听"""
        if not HAS_KEYBOARD:
            logger.warning("keyboard module not installed, shortcuts not available")
            return False

        with self._lock:
            if self._registered:
                return True

            shortcut_map = shortcuts or self.DEFAULT_SHORTCUTS

            try:
                for action, hotkey in shortcut_map.items():
                    if action in self._handlers:
                        keyboard.add_hotkey(hotkey, self._handlers[action])

                self._registered = True
                logger.info("Global shortcuts registered")
                return True

            except Exception as e:
                logger.error(f"Failed to register shortcuts: {e}")
                return False

    def stop(self):
        """停止快捷键监听"""
        if not HAS_KEYBOARD:
            return

        with self._lock:
            if self._registered:
                try:
                    keyboard.unhook_all()
                    self._registered = False
                    logger.info("Global shortcuts unregistered")
                except Exception as e:
                    logger.error(f"Error unregistering shortcuts: {e}")


# 全局实例
_shortcut_instance: Optional[ShortcutManager] = None


def get_shortcut_manager() -> ShortcutManager:
    """获取快捷键管理器实例"""
    global _shortcut_instance
    if _shortcut_instance is None:
        _shortcut_instance = ShortcutManager()
    return _shortcut_instance
