"""
Notion 同步应用程序的配置管理。
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional
from PySide6.QtCore import QSettings, QDir

from notion_sync import APP_IDENTIFIER, DEFAULT_CONFIG


class ConfigManager:
    """管理应用程序配置和设置。"""

    def __init__(self):
        """初始化配置管理器。"""
        self.settings = QSettings()
        self.config_dir = Path(QDir.homePath()) / f".{APP_IDENTIFIER}"
        self.config_file = self.config_dir / "config.json"
        self._config_cache: Optional[Dict[str, Any]] = None

        # 确保配置目录存在
        self.config_dir.mkdir(parents=True, exist_ok=True)

        # 加载或创建默认配置
        self._load_config()

    def _load_config(self) -> None:
        """从文件加载配置或创建默认配置。"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self._config_cache = json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                print(f"加载配置错误: {e}。使用默认配置。")
                self._config_cache = DEFAULT_CONFIG.copy()
        else:
            self._config_cache = DEFAULT_CONFIG.copy()
            self._save_config()

    def _save_config(self) -> None:
        """将配置保存到文件。"""
        if self._config_cache is not None:
            try:
                with open(self.config_file, 'w', encoding='utf-8') as f:
                    json.dump(self._config_cache, f, indent=2)
            except IOError as e:
                print(f"保存配置错误: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值。"""
        if self._config_cache is None:
            self._load_config()

        return self._config_cache.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """设置配置值。"""
        if self._config_cache is None:
            self._load_config()

        self._config_cache[key] = value
        self._save_config()

    def get_all(self) -> Dict[str, Any]:
        """获取所有配置值。"""
        if self._config_cache is None:
            self._load_config()

        return self._config_cache.copy()

    def update(self, config_dict: Dict[str, Any]) -> None:
        """更新多个配置值。"""
        if self._config_cache is None:
            self._load_config()

        self._config_cache.update(config_dict)
        self._save_config()

    def reset_to_defaults(self) -> None:
        """重置配置为默认值。"""
        self._config_cache = DEFAULT_CONFIG.copy()
        self._save_config()

    # Qt 设置集成用于 UI 状态
    def get_window_geometry(self) -> bytes:
        """获取保存的窗口几何信息。"""
        return self.settings.value("window/geometry", b"")

    def set_window_geometry(self, geometry: bytes) -> None:
        """保存窗口几何信息。"""
        self.settings.setValue("window/geometry", geometry)

    def get_window_state(self) -> bytes:
        """获取保存的窗口状态。"""
        return self.settings.value("window/state", b"")

    def set_window_state(self, state: bytes) -> None:
        """保存窗口状态。"""
        self.settings.setValue("window/state", state)

    def get_splitter_state(self, name: str) -> bytes:
        """获取保存的分割器状态。"""
        return self.settings.value(f"splitters/{name}", b"")

    def set_splitter_state(self, name: str, state: bytes) -> None:
        """保存分割器状态。"""
        self.settings.setValue(f"splitters/{name}", state)
