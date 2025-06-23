"""
Settings view for the Notion Sync application.
"""

from typing import Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QGroupBox, QTabWidget, QFormLayout, QLineEdit,
    QSpinBox, QCheckBox, QComboBox, QFileDialog, QTextEdit,
    QScrollArea
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from notion_sync.views.base import BaseView
from notion_sync.utils.config import ConfigManager
from notion_sync.utils.i18n import tr, get_language_manager
from notion_sync.resources.icons import get_icon
from notion_sync.utils.smart_cache import get_cache_stats, clear_all_caches


class SettingsView(BaseView):
    """Settings and preferences view."""
    
    def __init__(self, config_manager: ConfigManager, parent: Optional[QWidget] = None):
        """Initialize the settings view."""
        self.config_manager = config_manager
        super().__init__(parent)

        # 应用暗黑主题
        self._apply_dark_theme()
    
    def _setup_ui(self) -> None:
        """Set up the settings UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(24)
        
        # 标题
        self.header_label = QLabel(tr("settings_title"))
        self.header_label.setFont(QFont("SF Pro Display", 24, QFont.Weight.Bold))
        self.header_label.setStyleSheet("color: #1D1D1F; margin-bottom: 8px;")
        layout.addWidget(self.header_label)

        self.description_label = QLabel(tr("settings_description"))
        self.description_label.setFont(QFont("SF Pro Display", 14))
        self.description_label.setStyleSheet("color: #8E8E93; margin-bottom: 16px;")
        layout.addWidget(self.description_label)
        
        # Create scroll area for settings
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameStyle(QFrame.Shape.NoFrame)
        
        # Settings content widget
        settings_widget = QWidget()
        settings_layout = QVBoxLayout(settings_widget)
        settings_layout.setSpacing(24)
        
        # Create settings tabs
        self.tab_widget = QTabWidget()
        settings_layout.addWidget(self.tab_widget)
        
        # Add settings tabs
        self._create_general_tab()
        self._create_sync_tab()
        self._create_notion_tab()
        self._create_advanced_tab()
        
        scroll_area.setWidget(settings_widget)
        layout.addWidget(scroll_area)
        
        # Action buttons
        button_panel = self._create_action_buttons()
        layout.addWidget(button_panel)
        
        # Load current settings
        self._load_settings()

        # 连接语言变更信号
        language_manager = get_language_manager()
        language_manager.language_changed.connect(self._on_language_changed)
    
    def _create_general_tab(self) -> None:
        """Create the general settings tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(16)
        
        # 外观设置
        appearance_group = QGroupBox(tr("settings_appearance"))
        appearance_layout = QFormLayout(appearance_group)

        # Language selection
        self.language_combo = QComboBox()
        language_manager = get_language_manager()
        supported_languages = language_manager.get_supported_languages()

        for code, name in supported_languages.items():
            self.language_combo.addItem(name, code)

        # Set current language
        current_language = language_manager.get_current_language()
        for i in range(self.language_combo.count()):
            if self.language_combo.itemData(i) == current_language:
                self.language_combo.setCurrentIndex(i)
                break

        # Connect language change signal
        self.language_combo.currentIndexChanged.connect(self._on_language_combo_changed)
        appearance_layout.addRow(tr("general_language") + ":", self.language_combo)

        # Theme selection
        self.theme_combo = QComboBox()
        self.theme_combo.addItems([tr("theme_system"), tr("theme_light"), tr("theme_dark")])
        self.theme_combo.currentTextChanged.connect(self._on_theme_changed)
        appearance_layout.addRow(tr("general_theme") + ":", self.theme_combo)

        layout.addWidget(appearance_group)
        
        # 文件处理设置
        files_group = QGroupBox(tr("settings_file_handling"))
        files_layout = QFormLayout(files_group)

        self.max_file_size = QSpinBox()
        self.max_file_size.setRange(1, 1000)
        self.max_file_size.setValue(50)
        self.max_file_size.setSuffix(tr("unit_mb"))
        files_layout.addRow(tr("file_max_size") + ":", self.max_file_size)

        self.backup_location = QLineEdit()
        self.backup_browse = QPushButton(tr("btn_browse"))
        self.backup_browse.clicked.connect(self._browse_backup_location)
        backup_layout = QHBoxLayout()
        backup_layout.addWidget(self.backup_location)
        backup_layout.addWidget(self.backup_browse)
        files_layout.addRow(tr("file_backup_location") + ":", backup_layout)

        layout.addWidget(files_group)

        # 启动设置
        startup_group = QGroupBox(tr("settings_startup"))
        startup_layout = QVBoxLayout(startup_group)

        self.start_minimized = QCheckBox(tr("startup_minimized"))
        startup_layout.addWidget(self.start_minimized)

        self.auto_connect = QCheckBox(tr("startup_auto_connect"))
        startup_layout.addWidget(self.auto_connect)

        layout.addWidget(startup_group)

        layout.addStretch()
        self.tab_widget.addTab(tab, tr("tab_general"))
    
    def _create_sync_tab(self) -> None:
        """创建同步设置标签页。"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(16)

        # 同步行为
        sync_group = QGroupBox(tr("settings_sync_behavior"))
        sync_layout = QFormLayout(sync_group)

        self.auto_sync = QCheckBox(tr("sync_enable_auto"))
        sync_layout.addRow(self.auto_sync)

        self.sync_interval = QSpinBox()
        self.sync_interval.setRange(1, 60)
        self.sync_interval.setValue(5)
        self.sync_interval.setSuffix(tr("unit_minutes"))
        sync_layout.addRow(tr("sync_interval_label") + ":", self.sync_interval)

        self.watch_file_changes = QCheckBox(tr("sync_watch_files"))
        sync_layout.addRow(self.watch_file_changes)

        layout.addWidget(sync_group)

        # 冲突解决
        conflict_group = QGroupBox(tr("settings_conflict_resolution"))
        conflict_layout = QFormLayout(conflict_group)

        self.conflict_strategy = QComboBox()
        self.conflict_strategy.addItems([
            tr("conflict_ask"),
            tr("conflict_local_wins"),
            tr("conflict_notion_wins"),
            tr("conflict_create_both")
        ])
        conflict_layout.addRow(tr("conflict_default_strategy") + ":", self.conflict_strategy)

        self.backup_conflicts = QCheckBox(tr("conflict_backup_files"))
        conflict_layout.addRow(self.backup_conflicts)

        layout.addWidget(conflict_group)

        # 性能
        performance_group = QGroupBox(tr("settings_performance"))
        performance_layout = QFormLayout(performance_group)

        self.concurrent_uploads = QSpinBox()
        self.concurrent_uploads.setRange(1, 10)
        self.concurrent_uploads.setValue(3)
        performance_layout.addRow(tr("performance_concurrent") + ":", self.concurrent_uploads)

        self.retry_attempts = QSpinBox()
        self.retry_attempts.setRange(1, 10)
        self.retry_attempts.setValue(3)
        performance_layout.addRow(tr("performance_retry") + ":", self.retry_attempts)

        layout.addWidget(performance_group)

        layout.addStretch()
        self.tab_widget.addTab(tab, tr("tab_sync"))
    
    def _create_notion_tab(self) -> None:
        """创建 Notion 设置标签页。"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(16)

        # 连接状态
        connection_group = QGroupBox(tr("settings_connection"))
        connection_layout = QVBoxLayout(connection_group)

        status_layout = QHBoxLayout()
        self.connection_status = QLabel(tr("connection_not_connected"))
        self.connection_status.setStyleSheet("color: #FF3B30; font-weight: 500;")
        status_layout.addWidget(self.connection_status)
        status_layout.addStretch()

        self.connect_button = QPushButton(tr("btn_connect"))
        self.connect_button.clicked.connect(lambda: self.action_requested.emit("connect_notion", {}))
        status_layout.addWidget(self.connect_button)

        connection_layout.addLayout(status_layout)

        # 工作区信息
        self.workspace_info = QTextEdit()
        self.workspace_info.setMaximumHeight(100)
        self.workspace_info.setReadOnly(True)
        self.workspace_info.setPlainText(tr("connection_workspace_info"))
        connection_layout.addWidget(self.workspace_info)

        layout.addWidget(connection_group)

        # API 设置
        api_group = QGroupBox(tr("settings_api"))
        api_layout = QFormLayout(api_group)

        self.rate_limit = QSpinBox()
        self.rate_limit.setRange(1, 10)
        self.rate_limit.setValue(3)
        self.rate_limit.setSuffix(tr("unit_req_per_sec"))
        api_layout.addRow(tr("api_rate_limit") + ":", self.rate_limit)

        self.request_timeout = QSpinBox()
        self.request_timeout.setRange(5, 120)
        self.request_timeout.setValue(30)
        self.request_timeout.setSuffix(tr("unit_seconds"))
        api_layout.addRow(tr("api_timeout") + ":", self.request_timeout)

        layout.addWidget(api_group)

        # 导出设置
        export_group = QGroupBox(tr("settings_export"))
        export_layout = QFormLayout(export_group)

        self.default_export_format = QComboBox()
        self.default_export_format.addItems([
            tr("format_markdown"),
            tr("format_html"),
            tr("format_json"),
            tr("format_pdf")
        ])
        export_layout.addRow(tr("export_default_format") + ":", self.default_export_format)

        self.include_metadata = QCheckBox(tr("export_include_metadata"))
        self.include_metadata.setChecked(True)
        export_layout.addRow(self.include_metadata)

        layout.addWidget(export_group)

        layout.addStretch()
        self.tab_widget.addTab(tab, tr("tab_notion"))
    
    def _create_advanced_tab(self) -> None:
        """创建高级设置标签页。"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(16)

        # 日志
        logging_group = QGroupBox(tr("settings_logging"))
        logging_layout = QFormLayout(logging_group)

        self.log_level = QComboBox()
        self.log_level.addItems([
            tr("log_debug"),
            tr("log_info"),
            tr("log_warning"),
            tr("log_error")
        ])
        self.log_level.setCurrentText(tr("log_info"))
        logging_layout.addRow(tr("logging_level") + ":", self.log_level)

        self.enable_file_logging = QCheckBox(tr("logging_enable_file"))
        self.enable_file_logging.setChecked(True)
        logging_layout.addRow(self.enable_file_logging)

        layout.addWidget(logging_group)

        # 缓存设置
        cache_group = QGroupBox(tr("settings_cache"))
        cache_layout = QFormLayout(cache_group)

        self.cache_size = QSpinBox()
        self.cache_size.setRange(10, 1000)
        self.cache_size.setValue(100)
        self.cache_size.setSuffix(tr("unit_mb"))
        cache_layout.addRow(tr("cache_size_label") + ":", self.cache_size)

        self.cache_ttl = QSpinBox()
        self.cache_ttl.setRange(1, 60)
        self.cache_ttl.setValue(5)
        self.cache_ttl.setSuffix(tr("unit_minutes"))
        cache_layout.addRow(tr("cache_ttl_label") + ":", self.cache_ttl)

        # 缓存统计信息
        self.cache_stats_label = QLabel("缓存统计: 加载中...")
        cache_layout.addRow("缓存状态:", self.cache_stats_label)

        self.clear_cache_button = QPushButton(tr("cache_clear"))
        self.clear_cache_button.setIcon(get_icon('warning'))
        self.clear_cache_button.clicked.connect(self._clear_cache)
        cache_layout.addRow(self.clear_cache_button)

        # 更新缓存统计
        self._update_cache_stats()

        layout.addWidget(cache_group)

        # 数据管理
        data_group = QGroupBox(tr("settings_data_management"))
        data_layout = QVBoxLayout(data_group)

        self.export_settings_button = QPushButton(tr("data_export_settings"))
        self.export_settings_button.clicked.connect(lambda: self.action_requested.emit("export_settings", {}))
        data_layout.addWidget(self.export_settings_button)

        self.import_settings_button = QPushButton(tr("data_import_settings"))
        self.import_settings_button.clicked.connect(lambda: self.action_requested.emit("import_settings", {}))
        data_layout.addWidget(self.import_settings_button)

        self.reset_settings_button = QPushButton(tr("data_reset_defaults"))
        self.reset_settings_button.setStyleSheet("QPushButton { color: #FF3B30; }")
        self.reset_settings_button.clicked.connect(lambda: self.action_requested.emit("reset_settings", {}))
        data_layout.addWidget(self.reset_settings_button)

        layout.addWidget(data_group)

        layout.addStretch()
        self.tab_widget.addTab(tab, tr("tab_advanced"))
    
    def _create_action_buttons(self) -> QWidget:
        """创建操作按钮面板。"""
        panel = QFrame()
        panel.setFrameStyle(QFrame.Shape.StyledPanel)
        panel.setStyleSheet("background-color: #F8F9FA; border: 1px solid #E5E5E7; border-radius: 8px;")

        layout = QHBoxLayout(panel)
        layout.setContentsMargins(16, 16, 16, 16)

        # 重置按钮
        self.reset_button = QPushButton(tr("btn_reset"))
        self.reset_button.clicked.connect(self._load_settings)
        layout.addWidget(self.reset_button)

        layout.addStretch()

        # 应用和确定按钮
        self.apply_button = QPushButton(tr("btn_apply"))
        self.apply_button.clicked.connect(self._apply_settings)
        layout.addWidget(self.apply_button)

        self.ok_button = QPushButton(tr("btn_ok"))
        self.ok_button.setStyleSheet("""
        QPushButton {
            background-color: #007AFF;
            color: white;
            border: none;
            border-radius: 6px;
            padding: 8px 16px;
            font-weight: 500;
        }
        QPushButton:hover {
            background-color: #0056CC;
        }
        """)
        self.ok_button.clicked.connect(self._save_and_close)
        layout.addWidget(self.ok_button)

        return panel
    
    def _browse_backup_location(self) -> None:
        """浏览备份位置。"""
        directory = QFileDialog.getExistingDirectory(self, tr("file_select_folder"))
        if directory:
            self.backup_location.setText(directory)

    def _on_language_combo_changed(self, index: int) -> None:
        """处理语言选择变更。"""
        language_code = self.language_combo.itemData(index)
        if language_code:
            language_manager = get_language_manager()
            language_manager.set_language(language_code)

            # 保存语言设置
            self.config_manager.set("language", language_code)

    def _on_theme_changed(self, theme_text: str) -> None:
        """处理主题变更事件。"""
        # 将显示文本映射到主题代码
        theme_map = {
            tr("theme_system"): "system",
            tr("theme_light"): "light",
            tr("theme_dark"): "dark",
            "跟随系统": "system",
            "浅色": "light",
            "深色": "dark",
            "Follow System": "system",
            "Light": "light",
            "Dark": "dark"
        }

        theme_code = theme_map.get(theme_text, "system")

        # 发送主题应用动作
        self.action_requested.emit("apply_theme", {"theme": theme_code})

        # 保存主题设置
        self.config_manager.set("theme", theme_code)

    def _on_language_changed(self, language_code: str) -> None:
        """处理语言变更事件。"""
        # 更新所有界面文本
        self._update_ui_texts()

    def _update_ui_texts(self) -> None:
        """更新界面文本。"""
        # 更新标题和描述
        self.header_label.setText(tr("settings_title"))
        self.description_label.setText(tr("settings_description"))

        # 更新标签页标题
        self.tab_widget.setTabText(0, tr("tab_general"))
        self.tab_widget.setTabText(1, tr("tab_sync"))
        self.tab_widget.setTabText(2, tr("tab_notion"))
        self.tab_widget.setTabText(3, tr("tab_advanced"))

        # 更新按钮文本
        self.backup_browse.setText(tr("btn_browse"))
        self.connect_button.setText(tr("btn_connect") if self.connection_status.text() == tr("connection_not_connected") else tr("btn_disconnect"))
        self.clear_cache_button.setText(tr("cache_clear"))
        self.export_settings_button.setText(tr("data_export_settings"))
        self.import_settings_button.setText(tr("data_import_settings"))
        self.reset_settings_button.setText(tr("data_reset_defaults"))
        self.reset_button.setText(tr("btn_reset"))
        self.apply_button.setText(tr("btn_apply"))
        self.ok_button.setText(tr("btn_ok"))

        # 更新复选框文本
        self.start_minimized.setText(tr("startup_minimized"))
        self.auto_connect.setText(tr("startup_auto_connect"))
        self.auto_sync.setText(tr("sync_enable_auto"))
        self.watch_file_changes.setText(tr("sync_watch_files"))
        self.backup_conflicts.setText(tr("conflict_backup_files"))
        self.include_metadata.setText(tr("export_include_metadata"))
        self.enable_file_logging.setText(tr("logging_enable_file"))

        # 更新下拉框选项
        current_conflict = self.conflict_strategy.currentIndex()
        self.conflict_strategy.clear()
        self.conflict_strategy.addItems([
            tr("conflict_ask"),
            tr("conflict_local_wins"),
            tr("conflict_notion_wins"),
            tr("conflict_create_both")
        ])
        self.conflict_strategy.setCurrentIndex(current_conflict)

        # 更新主题选项
        current_theme = self.theme_combo.currentIndex()
        self.theme_combo.clear()
        self.theme_combo.addItems([tr("theme_system"), tr("theme_light"), tr("theme_dark")])
        self.theme_combo.setCurrentIndex(current_theme)

        # 更新单位后缀
        self.max_file_size.setSuffix(tr("unit_mb"))
        self.sync_interval.setSuffix(tr("unit_minutes"))
        self.rate_limit.setSuffix(tr("unit_req_per_sec"))
        self.request_timeout.setSuffix(tr("unit_seconds"))
        self.cache_size.setSuffix(tr("unit_mb"))
        self.cache_ttl.setSuffix(tr("unit_minutes"))

        # 更新状态文本
        if self.connection_status.text() in ["Not connected", "未连接"]:
            self.connection_status.setText(tr("connection_not_connected"))
        if self.workspace_info.toPlainText() in ["Connect to Notion to see workspace information", "连接到 Notion 以查看工作区信息"]:
            self.workspace_info.setPlainText(tr("connection_workspace_info"))
    
    def _load_settings(self) -> None:
        """从配置管理器加载设置。"""
        # 通用设置
        self.theme_combo.setCurrentText(self.config_manager.get("dark_mode", "system").title())
        self.max_file_size.setValue(self.config_manager.get("max_file_size", 50 * 1024 * 1024) // (1024 * 1024))
        self.backup_location.setText(self.config_manager.get("backup_location", ""))
        self.start_minimized.setChecked(self.config_manager.get("start_minimized", False))
        self.auto_connect.setChecked(self.config_manager.get("auto_connect", False))

        # 同步设置
        self.auto_sync.setChecked(self.config_manager.get("auto_sync", False))
        self.sync_interval.setValue(self.config_manager.get("sync_interval", 300) // 60)
        self.watch_file_changes.setChecked(self.config_manager.get("watch_file_changes", True))

        # 导出设置（简化版）
        export_format = self.config_manager.get("export_format", "markdown")
        format_map = {
            "markdown": 0,
            "html": 1,
            "pdf": 2
        }
        # 这里需要有对应的控件，暂时注释掉
        # self.export_format.setCurrentIndex(format_map.get(export_format, 0))

        # 性能设置
        self.concurrent_uploads.setValue(self.config_manager.get("max_concurrent_uploads", 3))
        self.retry_attempts.setValue(self.config_manager.get("retry_attempts", 3))

        # Notion 设置
        self.rate_limit.setValue(self.config_manager.get("notion_api_rate_limit", 3))
        self.request_timeout.setValue(self.config_manager.get("request_timeout", 30))
        self.default_export_format.setCurrentText(self.config_manager.get("export_format", "Markdown"))
        self.include_metadata.setChecked(self.config_manager.get("include_metadata", True))

        # 高级设置
        self.log_level.setCurrentText(self.config_manager.get("log_level", "INFO"))
        self.enable_file_logging.setChecked(self.config_manager.get("enable_file_logging", True))
        self.cache_size.setValue(self.config_manager.get("cache_size", 100))
        self.cache_ttl.setValue(self.config_manager.get("cache_ttl", 5))
    
    def _apply_settings(self) -> None:
        """应用当前设置。"""
        # 通用设置
        self.config_manager.set("dark_mode", self.theme_combo.currentText().lower())
        self.config_manager.set("max_file_size", self.max_file_size.value() * 1024 * 1024)
        self.config_manager.set("backup_location", self.backup_location.text())
        self.config_manager.set("start_minimized", self.start_minimized.isChecked())
        self.config_manager.set("auto_connect", self.auto_connect.isChecked())

        # 同步设置
        self.config_manager.set("auto_sync", self.auto_sync.isChecked())
        self.config_manager.set("sync_interval", self.sync_interval.value() * 60)
        self.config_manager.set("watch_file_changes", self.watch_file_changes.isChecked())

        # 冲突解决设置
        strategy_map = {
            0: "ask_me_each_time",
            1: "local_wins",
            2: "notion_wins",
            3: "create_both"
        }
        self.config_manager.set("conflict_resolution",
                               strategy_map.get(self.conflict_strategy.currentIndex(), "ask_me_each_time"))
        self.config_manager.set("backup_conflicts", self.backup_conflicts.isChecked())

        # 性能设置
        self.config_manager.set("max_concurrent_uploads", self.concurrent_uploads.value())
        self.config_manager.set("retry_attempts", self.retry_attempts.value())

        # Notion 设置
        self.config_manager.set("notion_api_rate_limit", self.rate_limit.value())
        self.config_manager.set("request_timeout", self.request_timeout.value())
        self.config_manager.set("export_format", self.default_export_format.currentText().lower())
        self.config_manager.set("include_metadata", self.include_metadata.isChecked())

        # 高级设置
        self.config_manager.set("log_level", self.log_level.currentText())
        self.config_manager.set("enable_file_logging", self.enable_file_logging.isChecked())
        self.config_manager.set("cache_size", self.cache_size.value())
        self.config_manager.set("cache_ttl", self.cache_ttl.value())

        # 发出设置已应用的信号
        self.action_requested.emit("settings_applied", self._get_applied_settings())
    
    def _save_and_close(self) -> None:
        """保存设置并关闭。"""
        self._apply_settings()
        self.action_requested.emit("close_settings", {})

    def _get_applied_settings(self) -> dict:
        """获取已应用的设置字典。"""
        return {
            "theme": self.theme_combo.currentText().lower(),
            "auto_sync": self.auto_sync.isChecked(),
            "sync_interval": self.sync_interval.value() * 60,
            "watch_file_changes": self.watch_file_changes.isChecked(),
            "conflict_resolution": self.conflict_strategy.currentIndex(),
            "log_level": self.log_level.currentText()
        }

    def update_connection_status(self, connected: bool, workspace_info: dict = None) -> None:
        """更新连接状态显示。"""
        if connected:
            self.connection_status.setText("已连接")
            self.connection_status.setStyleSheet("color: #34C759; font-weight: 500;")
            self.connect_button.setText("断开连接")

            if workspace_info:
                info_text = f"工作区: {workspace_info.get('name', 'Unknown')}\n"
                info_text += f"所有者: {workspace_info.get('owner', 'Unknown')}\n"
                info_text += f"页面数: {workspace_info.get('page_count', 0)}\n"
                info_text += f"数据库数: {workspace_info.get('database_count', 0)}"
                self.workspace_info.setPlainText(info_text)
        else:
            self.connection_status.setText("未连接")
            self.connection_status.setStyleSheet("color: #FF3B30; font-weight: 500;")
            self.connect_button.setText("连接到 Notion")
            self.workspace_info.setPlainText("连接到 Notion 以查看工作区信息")

    def validate_settings(self) -> tuple[bool, str]:
        """验证设置的有效性。"""
        # 检查备份位置
        backup_path = self.backup_location.text().strip()
        if backup_path:
            from pathlib import Path
            try:
                path = Path(backup_path)
                if not path.parent.exists():
                    return False, "备份位置的父目录不存在"
            except Exception:
                return False, "备份位置路径无效"

        # 检查同步间隔
        if self.sync_interval.value() < 1:
            return False, "同步间隔必须至少为1分钟"

        # 检查文件大小限制
        if self.max_file_size.value() < 1:
            return False, "最大文件大小必须至少为1MB"

        # 检查并发上传数
        if self.concurrent_uploads.value() < 1:
            return False, "并发上传数必须至少为1"

        return True, ""

    def reset_to_defaults(self) -> None:
        """重置所有设置为默认值。"""
        from notion_sync import DEFAULT_CONFIG

        # 重置配置管理器
        self.config_manager.reset_to_defaults()

        # 重新加载设置到界面
        self._load_settings()

        # 发出重置信号
        self.action_requested.emit("settings_reset", {})

    def _clear_cache(self) -> None:
        """清除缓存"""
        try:
            clear_all_caches()
            self._update_cache_stats()
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.information(self, "缓存清除", "缓存已成功清除！")
        except Exception as e:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "清除失败", f"清除缓存时发生错误：{str(e)}")

    def _update_cache_stats(self) -> None:
        """更新缓存统计信息"""
        try:
            stats = get_cache_stats()
            stats_text = f"命中率: {stats.get('hit_rate', 0):.1%}, 大小: {stats.get('cache_size', 0)}/{stats.get('max_size', 0)}"
            self.cache_stats_label.setText(stats_text)
        except Exception:
            self.cache_stats_label.setText("缓存统计: 不可用")

    def _test_connection(self) -> None:
        """测试 Notion 连接"""
        self.action_requested.emit("test_notion_connection", {})

    def _export_settings(self) -> None:
        """导出设置"""
        from PySide6.QtWidgets import QFileDialog
        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出设置", "notion_sync_settings.json", "JSON Files (*.json)"
        )
        if file_path:
            self.action_requested.emit("export_settings", {"file_path": file_path})

    def _import_settings(self) -> None:
        """导入设置"""
        from PySide6.QtWidgets import QFileDialog
        file_path, _ = QFileDialog.getOpenFileName(
            self, "导入设置", "", "JSON Files (*.json)"
        )
        if file_path:
            self.action_requested.emit("import_settings", {"file_path": file_path})

    def _open_log_folder(self) -> None:
        """打开日志文件夹"""
        import os
        import subprocess
        import platform

        log_dir = os.path.expanduser("~/.notion_sync/logs")
        if not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)

        # 根据操作系统打开文件夹
        if platform.system() == "Windows":
            os.startfile(log_dir)
        elif platform.system() == "Darwin":  # macOS
            subprocess.run(["open", log_dir])
        else:  # Linux
            subprocess.run(["xdg-open", log_dir])

    def _apply_dark_theme(self) -> None:
        """应用暗黑主题样式"""
        dark_style = """
        QWidget {
            background-color: #2b2b2b;
            color: #ffffff;
        }

        QTabWidget::pane {
            border: 1px solid #555555;
            background-color: #2b2b2b;
        }

        QTabWidget::tab-bar {
            alignment: left;
        }

        QTabBar::tab {
            background-color: #3c3c3c;
            color: #ffffff;
            border: 1px solid #555555;
            padding: 8px 16px;
            margin-right: 2px;
        }

        QTabBar::tab:selected {
            background-color: #007AFF;
            color: white;
        }

        QTabBar::tab:hover {
            background-color: #4c4c4c;
        }

        QLabel {
            color: #ffffff !important;
            background-color: transparent;
        }

        QLineEdit {
            background-color: #3c3c3c;
            border: 1px solid #555555;
            border-radius: 4px;
            padding: 8px;
            color: #ffffff !important;
            font-size: 14px;
        }

        QLineEdit:focus {
            border: 2px solid #007AFF;
        }

        QPushButton {
            background-color: #007AFF !important;
            color: white !important;
            border: none;
            border-radius: 6px;
            padding: 8px 16px;
            font-weight: 500;
            font-size: 14px;
        }

        QPushButton:hover {
            background-color: #0056CC !important;
        }

        QPushButton:pressed {
            background-color: #004499 !important;
        }

        QPushButton:disabled {
            background-color: #555555 !important;
            color: #888888 !important;
        }

        QCheckBox {
            color: #ffffff !important;
            spacing: 8px;
        }

        QCheckBox::indicator {
            width: 18px;
            height: 18px;
            border-radius: 3px;
            border: 2px solid #555555;
            background-color: #3c3c3c;
        }

        QCheckBox::indicator:checked {
            background-color: #007AFF;
            border-color: #007AFF;
        }

        QComboBox {
            background-color: #3c3c3c;
            border: 1px solid #555555;
            border-radius: 4px;
            padding: 8px;
            color: #ffffff !important;
            font-size: 14px;
        }

        QComboBox:focus {
            border: 2px solid #007AFF;
        }

        QComboBox::drop-down {
            border: none;
            background-color: #3c3c3c;
        }

        QComboBox::down-arrow {
            image: none;
            border-left: 5px solid transparent;
            border-right: 5px solid transparent;
            border-top: 5px solid #ffffff;
        }

        QComboBox QAbstractItemView {
            background-color: #3c3c3c;
            border: 1px solid #555555;
            color: #ffffff;
            selection-background-color: #007AFF;
        }

        QSpinBox {
            background-color: #3c3c3c;
            border: 1px solid #555555;
            border-radius: 4px;
            padding: 8px;
            color: #ffffff !important;
            font-size: 14px;
        }

        QSpinBox:focus {
            border: 2px solid #007AFF;
        }

        QGroupBox {
            color: #ffffff !important;
            border: 1px solid #555555;
            border-radius: 4px;
            margin-top: 10px;
            padding-top: 10px;
            background-color: #2b2b2b;
        }

        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px 0 5px;
            color: #ffffff !important;
            background-color: #2b2b2b;
        }

        QTextEdit {
            background-color: #3c3c3c;
            border: 1px solid #555555;
            border-radius: 4px;
            color: #ffffff !important;
            font-size: 14px;
            padding: 8px;
        }

        QScrollArea {
            background-color: #2b2b2b;
            border: none;
        }

        QFrame {
            background-color: #2b2b2b;
            color: #ffffff;
        }
        """
        self.setStyleSheet(dark_style)
