"""
Notion 同步应用程序的主入口点。
"""

import sys
import os
import logging
from pathlib import Path
from typing import Optional

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QDir
from PySide6.QtGui import QIcon

# 将 src 目录添加到 Python 路径
src_dir = Path(__file__).parent.parent
sys.path.insert(0, str(src_dir))

from notion_sync import APP_NAME, APP_VERSION, APP_IDENTIFIER
from notion_sync.utils.config import ConfigManager
from notion_sync.utils.logging_config import setup_logging
from notion_sync.utils.i18n import get_language_manager
from notion_sync.controllers.app_controller import AppController


def setup_application() -> QApplication:
    """设置具有适当配置的 QApplication。"""
    # 启用高 DPI 缩放
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)

    # 设置应用程序元数据
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName("Notion Sync")
    app.setOrganizationDomain("notion-sync.example.com")
    app.setApplicationDisplayName(APP_NAME)

    # 设置应用程序图标
    icon_path = Path(__file__).parent / "resources" / "icons" / "app_icon.png"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    # 设置样式
    app.setStyle("Fusion")  # 使用 Fusion 样式以保持跨平台一致性

    return app


def setup_directories() -> None:
    """创建必要的应用程序目录。"""
    config_dir = QDir.homePath() + f"/.{APP_IDENTIFIER}"
    cache_dir = config_dir + "/cache"
    logs_dir = config_dir + "/logs"

    for directory in [config_dir, cache_dir, logs_dir]:
        Path(directory).mkdir(parents=True, exist_ok=True)


def main() -> int:
    """主应用程序入口点。"""
    try:
        # 设置目录
        setup_directories()

        # 设置日志
        setup_logging()
        logger = logging.getLogger(__name__)
        logger.info(f"启动 {APP_NAME} v{APP_VERSION}")

        # 创建应用程序
        app = setup_application()

        # 初始化配置
        config_manager = ConfigManager()

        # 初始化语言管理器并设置语言
        language_manager = get_language_manager()
        saved_language = config_manager.get("language", "zh_CN")
        language_manager.set_language(saved_language)

        # 创建并初始化应用控制器
        app_controller = AppController(config_manager)

        # 应用保存的主题设置
        saved_theme = config_manager.get("theme", "system")
        app_controller._apply_theme(saved_theme)

        app_controller.show_main_window()

        # 启动事件循环
        return app.exec()

    except Exception as e:
        logging.error(f"启动应用程序失败: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
