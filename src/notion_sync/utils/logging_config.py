"""
Notion 同步应用程序的日志配置。
"""

import logging
import logging.handlers
import os
from pathlib import Path
from PySide6.QtCore import QDir

from notion_sync import APP_IDENTIFIER


def setup_logging(log_level: str = "INFO") -> None:
    """设置应用程序日志配置。"""

    # 创建日志目录
    logs_dir = Path(QDir.homePath()) / f".{APP_IDENTIFIER}" / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    # 日志文件路径
    log_file = logs_dir / "notion_sync.log"

    # 创建格式化器
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # 根日志器配置
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # 清除现有处理器
    root_logger.handlers.clear()

    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # 带轮转的文件处理器
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    # 设置特定日志器级别
    logging.getLogger("notion_sync").setLevel(logging.DEBUG)
    logging.getLogger("PySide6").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)


class LoggerMixin:
    """为任何类添加日志功能的混入类。"""

    @property
    def logger(self) -> logging.Logger:
        """获取此类的日志器。"""
        return logging.getLogger(f"{self.__class__.__module__}.{self.__class__.__name__}")


def get_logger(name: str) -> logging.Logger:
    """获取指定名称的日志器。"""
    return logging.getLogger(name)
