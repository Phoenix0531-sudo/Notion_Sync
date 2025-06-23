"""
Notion 同步工具 - 与 Notion 同步的桌面 GUI 应用程序。

遵循苹果人机界面指南的现代化、简洁界面，
用于本地文件和 Notion 工作区之间的双向同步。
"""

__version__ = "1.0.0"
__author__ = "Your Name"
__email__ = "your.email@example.com"
__description__ = "与 Notion 同步的桌面 GUI 应用程序"

# 应用程序元数据
APP_NAME = "Notion 同步工具"
APP_VERSION = __version__
APP_IDENTIFIER = "com.example.notion-sync"

# 支持的文件格式
SUPPORTED_FORMATS = {
    "documents": [".md", ".txt", ".html", ".json"],
    "images": [".png", ".jpg", ".jpeg", ".gif", ".webp"],
    "exports": [".md", ".html", ".json", ".pdf"]
}

# 默认配置
DEFAULT_CONFIG = {
    "language": "zh_CN",  # zh_CN, en_US
    "sync_interval": 300,  # 5分钟
    "max_file_size": 50 * 1024 * 1024,  # 50MB
    "max_concurrent_uploads": 5,
    "retry_attempts": 3,
    "retry_delay": 1,
    "auto_sync": False,
    "dark_mode": "system",  # "light", "dark", "system"
    "export_format": "markdown",
    "backup_location": "~/Documents/Notion Backups"
}
