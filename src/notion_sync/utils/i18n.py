"""
国际化和本地化支持。
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional
from PySide6.QtCore import QObject, Signal

from notion_sync.utils.logging_config import LoggerMixin


class LanguageManager(QObject, LoggerMixin):
    """语言管理器，处理多语言支持。"""
    
    # 语言变更信号
    language_changed = Signal(str)
    
    def __init__(self):
        """初始化语言管理器。"""
        super().__init__()
        
        # 当前语言
        self.current_language = "zh_CN"
        
        # 语言数据
        self.translations: Dict[str, Dict[str, str]] = {}
        
        # 支持的语言
        self.supported_languages = {
            "zh_CN": "简体中文",
            "en_US": "English"
        }
        
        # 加载语言文件
        self._load_translations()
    
    def _load_translations(self) -> None:
        """加载翻译文件。"""
        try:
            # 语言文件目录
            lang_dir = Path(__file__).parent.parent / "resources" / "languages"
            
            if not lang_dir.exists():
                # 如果目录不存在，使用内置翻译
                self._load_builtin_translations()
                return
            
            # 加载每种语言的翻译文件
            for lang_code in self.supported_languages.keys():
                lang_file = lang_dir / f"{lang_code}.json"
                if lang_file.exists():
                    with open(lang_file, 'r', encoding='utf-8') as f:
                        self.translations[lang_code] = json.load(f)
                else:
                    self.logger.warning(f"语言文件不存在: {lang_file}")
            
            # 如果没有加载到任何翻译，使用内置翻译
            if not self.translations:
                self._load_builtin_translations()
                
        except Exception as e:
            self.logger.error(f"加载翻译文件失败: {e}")
            self._load_builtin_translations()
    
    def _load_builtin_translations(self) -> None:
        """加载内置翻译。"""
        # 中文翻译
        self.translations["zh_CN"] = {
            # 应用程序
            "app_title": "Notion 同步工具",
            "app_version": "版本",
            
            # 菜单
            "menu_file": "文件(&F)",
            "menu_edit": "编辑(&E)",
            "menu_view": "视图(&V)",
            "menu_sync": "同步(&S)",
            "menu_tools": "工具(&T)",
            "menu_help": "帮助(&H)",
            
            # 文件菜单
            "new_sync": "新建同步(&N)...",
            "import_settings": "导入设置(&I)...",
            "export_settings": "导出设置(&E)...",
            "quit": "退出(&Q)",
            
            # 编辑菜单
            "preferences": "偏好设置(&P)...",
            
            # 视图菜单
            "toggle_sidebar": "切换侧边栏(&S)",
            "toggle_toolbar": "切换工具栏(&T)",
            "toggle_statusbar": "切换状态栏(&B)",
            
            # 同步菜单
            "start_sync": "开始同步(&S)",
            "stop_sync": "停止同步(&T)",
            "sync_now": "立即同步(&N)",
            
            # 工具菜单
            "clear_cache": "清除缓存(&C)",
            "reset_settings": "重置设置(&R)",
            
            # 帮助菜单
            "about": "关于(&A)",
            "help": "帮助(&H)",
            
            # 侧边栏导航
            "nav_local_to_notion": "本地到 Notion",
            "nav_notion_to_local": "Notion 到本地",
            "nav_bidirectional": "双向同步",
            "nav_settings": "设置",
            
            # 工具栏
            "toolbar_start_sync": "开始同步",
            "toolbar_stop_sync": "停止同步",
            "toolbar_refresh": "刷新",
            
            # 状态栏
            "status_ready": "就绪",
            "status_connecting": "连接中...",
            "status_connected": "已连接",
            "status_disconnected": "未连接",
            "status_syncing": "同步中...",
            "status_sync_complete": "同步完成",
            "status_sync_failed": "同步失败",
            
            # 连接状态
            "connection_connected": "已连接到 Notion",
            "connection_disconnected": "未连接到 Notion",
            "connect_to_notion": "连接到云端服务",
            
            # 按钮
            "btn_connect": "连接到 Notion",
            "btn_disconnect": "断开连接",
            "btn_browse": "浏览...",
            "btn_select": "选择",
            "btn_cancel": "取消",
            "btn_ok": "确定",
            "btn_apply": "应用",
            "btn_reset": "重置",
            "btn_save": "保存",
            "btn_load": "加载",
            "btn_delete": "删除",
            "btn_add": "添加",
            "btn_remove": "移除",
            "btn_edit": "编辑",
            "btn_refresh": "刷新",
            "btn_retry": "重试",
            
            # 设置页面
            "settings_title": "设置",
            "settings_description": "配置您的 Notion 同步偏好设置",
            "settings_general": "通用",
            "settings_sync": "同步",
            "settings_advanced": "高级",
            "settings_about": "关于",
            
            # 通用设置
            "general_language": "语言",
            "general_theme": "主题",
            "general_startup": "启动选项",
            "general_auto_start": "开机自启动",
            "general_start_minimized": "启动时最小化",
            "general_auto_connect": "自动连接到 Notion",
            
            # 主题选项
            "theme_system": "跟随系统",
            "theme_light": "浅色",
            "theme_dark": "深色",
            
            # 同步设置
            "sync_auto_sync": "自动同步",
            "sync_interval": "同步间隔（分钟）",
            "sync_watch_changes": "监控文件变更",
            "sync_conflict_resolution": "冲突解决策略",
            "sync_backup_conflicts": "备份冲突文件",
            
            # 冲突解决策略
            "conflict_ask": "每次询问",
            "conflict_local_wins": "本地优先",
            "conflict_notion_wins": "Notion 优先",
            "conflict_create_both": "保留两者",
            
            # 错误消息
            "error_connection_failed": "连接失败",
            "error_sync_failed": "同步失败",
            "error_file_not_found": "文件未找到",
            "error_permission_denied": "权限被拒绝",
            "error_invalid_settings": "设置无效",
            
            # 成功消息
            "success_connected": "连接成功",
            "success_sync_complete": "同步完成",
            "success_settings_saved": "设置已保存",
            "success_settings_imported": "设置导入成功",
            "success_settings_exported": "设置导出成功",
            
            # 确认对话框
            "confirm_quit": "确定要退出吗？",
            "confirm_reset_settings": "确定要重置所有设置吗？此操作无法撤销。",
            "confirm_clear_cache": "确定要清除缓存吗？",
            "confirm_disconnect": "确定要断开连接吗？",
            
            # 文件操作
            "file_select_folder": "选择文件夹",
            "file_select_file": "选择文件",
            "file_save_as": "另存为",
            "file_open": "打开",
            
            # 进度信息
            "progress_connecting": "正在连接...",
            "progress_syncing": "正在同步...",
            "progress_uploading": "正在上传...",
            "progress_downloading": "正在下载...",
            "progress_analyzing": "正在分析...",
            "progress_complete": "完成",

            # 设置页面详细翻译
            "settings_appearance": "外观",
            "settings_file_handling": "文件处理",
            "settings_startup": "启动",
            "settings_sync_behavior": "同步行为",
            "settings_conflict_resolution": "冲突解决",
            "settings_performance": "性能",
            "settings_connection": "连接",
            "settings_api": "API 设置",
            "settings_export": "导出设置",
            "settings_logging": "日志",
            "settings_cache": "缓存",
            "settings_data_management": "数据管理",

            # 文件处理
            "file_max_size": "最大文件大小",
            "file_backup_location": "备份位置",

            # 启动选项
            "startup_minimized": "启动时最小化",
            "startup_auto_connect": "启动时自动连接到 Notion",

            # 同步行为
            "sync_enable_auto": "启用自动同步",
            "sync_interval_label": "同步间隔",
            "sync_watch_files": "监控文件变更",

            # 冲突解决
            "conflict_default_strategy": "默认策略",
            "conflict_backup_files": "备份冲突文件",

            # 性能设置
            "performance_concurrent": "并发上传数",
            "performance_retry": "重试次数",

            # 连接设置
            "connection_not_connected": "未连接",
            "connection_workspace_info": "连接到 Notion 以查看工作区信息",

            # API 设置
            "api_rate_limit": "速率限制",
            "api_timeout": "请求超时",

            # 导出设置
            "export_default_format": "默认格式",
            "export_include_metadata": "在导出中包含元数据",

            # 日志设置
            "logging_level": "日志级别",
            "logging_enable_file": "启用文件日志",

            # 缓存设置
            "cache_size_label": "缓存大小",
            "cache_ttl_label": "缓存生存时间",
            "cache_clear": "清除缓存",

            # 数据管理
            "data_export_settings": "导出设置",
            "data_import_settings": "导入设置",
            "data_reset_defaults": "重置为默认值",

            # 单位
            "unit_mb": " MB",
            "unit_minutes": " 分钟",
            "unit_seconds": " 秒",
            "unit_req_per_sec": " 请求/秒",

            # 标签页标题
            "tab_general": "通用",
            "tab_sync": "同步",
            "tab_notion": "Notion",
            "tab_advanced": "高级",

            # 同步视图
            "sync_local_to_notion": "本地到云端同步",
            "sync_local_to_notion_desc": "将本地文件和文件夹上传到您的云端工作区",
            "sync_notion_to_local": "云端到本地备份",
            "sync_notion_to_local_desc": "导出并备份您的云端工作区到本地文件",
            "sync_bidirectional": "双向同步",
            "sync_bidirectional_desc": "保持您的本地文件和云端工作区同步",

            # 文件浏览器
            "local_files": "本地文件",
            "no_directory_selected": "未选择目录",
            "file_tree_headers": ["名称", "类型", "大小", "修改时间"],
            "show_files": "显示:",
            "show_markdown": "Markdown",
            "show_images": "图片",
            "show_other": "其他",

            # Notion 目标
            "notion_destination": "Notion 目标",
            "workspace_label": "工作区:",
            "not_connected": "未连接",
            "upload_to": "上传到:",
            "select_destination": "选择目标...",
            "new_page": "新页面",
            "existing_page": "现有页面",
            "database": "数据库",
            "load_notion_content": "加载 Notion 内容",
            "options_label": "选项:",
            "preserve_structure": "保持文件夹结构",
            "overwrite_existing": "覆盖现有文件",

            # 操作按钮
            "upload_selected": "上传选中文件",
            "export_selected": "导出选中内容",
            "ready_to_upload": "准备上传",
            "ready_to_export": "准备导出",
            "upload_progress": "上传进度",
            "export_progress": "导出进度",
            "upload_complete": "上传完成",
            "export_complete": "导出完成",

            # Notion 工作区
            "notion_workspace": "Notion 工作区",
            "refresh_workspace": "刷新工作区",
            "export_options": "导出选项",
            "export_format": "导出格式:",
            "destination_folder": "目标文件夹:",
            "select_folder": "选择文件夹...",
            "include_attachments": "包含附件",
            "preserve_hierarchy": "保持页面层次结构",
            "incremental_backup": "增量备份",

            # 双向同步
            "sync_pairs": "同步对",
            "add_sync_pair": "添加同步对",
            "remove_selected": "移除选中",
            "auto_sync_label": "自动同步",
            "interval_label": "间隔:",
            "start_sync": "开始同步",
            "stop_sync": "停止同步",
            "force_sync_all": "强制同步全部",
            "sync_stopped": "同步已停止",

            # 文件类型
            "file_type_markdown": "标记文档",
            "file_type_text": "文本文件",
            "file_type_html": "网页文件",
            "file_type_json": "数据文件",
            "file_type_png": "图片文件",
            "file_type_jpeg": "图片文件",
            "file_type_gif": "动图文件",
            "file_type_webp": "图片文件",
            "file_type_other": "其他文件",
            "file_type_folder": "文件夹",
            "file_type_page": "页面",
            "file_type_database": "数据库",
            "file_type_workspace": "工作区",

            # 导出格式（完全中文）
            "format_markdown": "标记文档",
            "format_html": "网页文件",
            "format_json": "数据文件",
            "format_pdf": "便携文档",

            # 日志级别（完全中文）
            "log_debug": "调试",
            "log_info": "信息",
            "log_warning": "警告",
            "log_error": "错误",

            # 新建同步对话框
            "new_sync_title": "新建同步配置",
            "new_sync_desc": "配置本地文件夹与云端工作区之间的同步规则",
            "basic_settings": "基本设置",
            "sync_name": "同步名称",
            "sync_name_placeholder": "例如：我的文档同步",
            "sync_type": "同步类型",
            "sync_type_bidirectional": "双向同步",
            "sync_type_local_to_remote": "本地到云端",
            "sync_type_remote_to_local": "云端到本地",
            "sync_type_desc_bidirectional": "保持本地文件夹与云端工作区双向同步",
            "sync_type_desc_local_to_remote": "仅将本地文件上传到云端工作区",
            "sync_type_desc_remote_to_local": "仅从云端工作区下载内容到本地",
            "path_settings": "路径设置",
            "local_path": "本地路径",
            "local_path_placeholder": "选择本地文件夹...",
            "remote_path": "云端路径",
            "remote_path_placeholder": "例如：/我的文档",
            "sync_options": "同步选项",
            "enable_auto_sync": "启用自动同步",
            "include_hidden_files": "包含隐藏文件",
            "backup_on_conflict": "冲突时备份文件",
            "file_filter": "文件过滤",
            "file_types": "包含的文件类型",
            "file_types_placeholder": "例如：*.md, *.txt, *.docx",
            "file_types_help": "用逗号分隔多个文件类型，支持通配符",
            "btn_browse": "浏览",
            "btn_select": "选择",
            "btn_create_sync": "创建同步",

            # 状态信息
            "no_permission": "无权限访问",
            "untitled_page": "无标题页面",
            "untitled_database": "无标题数据库",
            "my_workspace": "我的工作区",
            "pages_folder": "页面",
            "databases_folder": "数据库",
            "empty_database": "空",
            "rows_count": "行",
        }
        
        # 英文翻译
        self.translations["en_US"] = {
            # 应用程序
            "app_title": "Notion Sync Tool",
            "app_version": "Version",
            
            # 菜单
            "menu_file": "&File",
            "menu_edit": "&Edit",
            "menu_view": "&View",
            "menu_sync": "&Sync",
            "menu_tools": "&Tools",
            "menu_help": "&Help",
            
            # 文件菜单
            "new_sync": "&New Sync...",
            "import_settings": "&Import Settings...",
            "export_settings": "&Export Settings...",
            "quit": "&Quit",
            
            # 编辑菜单
            "preferences": "&Preferences...",
            
            # 视图菜单
            "toggle_sidebar": "Toggle &Sidebar",
            "toggle_toolbar": "Toggle &Toolbar",
            "toggle_statusbar": "Toggle Status&bar",
            
            # 同步菜单
            "start_sync": "&Start Sync",
            "stop_sync": "S&top Sync",
            "sync_now": "Sync &Now",
            
            # 工具菜单
            "clear_cache": "&Clear Cache",
            "reset_settings": "&Reset Settings",
            
            # 帮助菜单
            "about": "&About",
            "help": "&Help",
            
            # 侧边栏导航
            "nav_local_to_notion": "Local to Notion",
            "nav_notion_to_local": "Notion to Local",
            "nav_bidirectional": "Bidirectional Sync",
            "nav_settings": "Settings",
            
            # 工具栏
            "toolbar_start_sync": "Start Sync",
            "toolbar_stop_sync": "Stop Sync",
            "toolbar_refresh": "Refresh",
            
            # 状态栏
            "status_ready": "Ready",
            "status_connecting": "Connecting...",
            "status_connected": "Connected",
            "status_disconnected": "Disconnected",
            "status_syncing": "Syncing...",
            "status_sync_complete": "Sync Complete",
            "status_sync_failed": "Sync Failed",
            
            # 连接状态
            "connection_connected": "Connected to Notion",
            "connection_disconnected": "Disconnected from Notion",
            "connect_to_notion": "Connect to Cloud Service",
            
            # 按钮
            "btn_connect": "Connect to Notion",
            "btn_disconnect": "Disconnect",
            "btn_browse": "Browse...",
            "btn_select": "Select",
            "btn_cancel": "Cancel",
            "btn_ok": "OK",
            "btn_apply": "Apply",
            "btn_reset": "Reset",
            "btn_save": "Save",
            "btn_load": "Load",
            "btn_delete": "Delete",
            "btn_add": "Add",
            "btn_remove": "Remove",
            "btn_edit": "Edit",
            "btn_refresh": "Refresh",
            "btn_retry": "Retry",
            
            # 设置页面
            "settings_title": "Settings",
            "settings_description": "Configure your Notion Sync preferences",
            "settings_general": "General",
            "settings_sync": "Sync",
            "settings_advanced": "Advanced",
            "settings_about": "About",
            
            # 通用设置
            "general_language": "Language",
            "general_theme": "Theme",
            "general_startup": "Startup Options",
            "general_auto_start": "Start with system",
            "general_start_minimized": "Start minimized",
            "general_auto_connect": "Auto connect to Notion",
            
            # 主题选项
            "theme_system": "Follow System",
            "theme_light": "Light",
            "theme_dark": "Dark",
            
            # 同步设置
            "sync_auto_sync": "Auto Sync",
            "sync_interval": "Sync Interval (minutes)",
            "sync_watch_changes": "Watch File Changes",
            "sync_conflict_resolution": "Conflict Resolution",
            "sync_backup_conflicts": "Backup Conflict Files",
            
            # 冲突解决策略
            "conflict_ask": "Ask Each Time",
            "conflict_local_wins": "Local Wins",
            "conflict_notion_wins": "Notion Wins",
            "conflict_create_both": "Keep Both",
            
            # 错误消息
            "error_connection_failed": "Connection Failed",
            "error_sync_failed": "Sync Failed",
            "error_file_not_found": "File Not Found",
            "error_permission_denied": "Permission Denied",
            "error_invalid_settings": "Invalid Settings",
            
            # 成功消息
            "success_connected": "Connected Successfully",
            "success_sync_complete": "Sync Complete",
            "success_settings_saved": "Settings Saved",
            "success_settings_imported": "Settings Imported Successfully",
            "success_settings_exported": "Settings Exported Successfully",
            
            # 确认对话框
            "confirm_quit": "Are you sure you want to quit?",
            "confirm_reset_settings": "Are you sure you want to reset all settings? This action cannot be undone.",
            "confirm_clear_cache": "Are you sure you want to clear the cache?",
            "confirm_disconnect": "Are you sure you want to disconnect?",
            
            # 文件操作
            "file_select_folder": "Select Folder",
            "file_select_file": "Select File",
            "file_save_as": "Save As",
            "file_open": "Open",
            
            # 进度信息
            "progress_connecting": "Connecting...",
            "progress_syncing": "Syncing...",
            "progress_uploading": "Uploading...",
            "progress_downloading": "Downloading...",
            "progress_analyzing": "Analyzing...",
            "progress_complete": "Complete",

            # 设置页面详细翻译
            "settings_appearance": "Appearance",
            "settings_file_handling": "File Handling",
            "settings_startup": "Startup",
            "settings_sync_behavior": "Sync Behavior",
            "settings_conflict_resolution": "Conflict Resolution",
            "settings_performance": "Performance",
            "settings_connection": "Connection",
            "settings_api": "API Settings",
            "settings_export": "Export Settings",
            "settings_logging": "Logging",
            "settings_cache": "Cache",
            "settings_data_management": "Data Management",

            # 文件处理
            "file_max_size": "Max file size",
            "file_backup_location": "Backup location",

            # 启动选项
            "startup_minimized": "Start minimized",
            "startup_auto_connect": "Auto-connect to Notion on startup",

            # 同步行为
            "sync_enable_auto": "Enable automatic synchronization",
            "sync_interval_label": "Sync interval",
            "sync_watch_files": "Watch for file changes",

            # 冲突解决
            "conflict_default_strategy": "Default strategy",
            "conflict_backup_files": "Backup conflicted files",

            # 性能设置
            "performance_concurrent": "Concurrent uploads",
            "performance_retry": "Retry attempts",

            # 连接设置
            "connection_not_connected": "Not connected",
            "connection_workspace_info": "Connect to Notion to see workspace information",

            # API 设置
            "api_rate_limit": "Rate limit",
            "api_timeout": "Request timeout",

            # 导出设置
            "export_default_format": "Default format",
            "export_include_metadata": "Include metadata in exports",

            # 日志设置
            "logging_level": "Log level",
            "logging_enable_file": "Enable file logging",

            # 缓存设置
            "cache_size_label": "Cache size",
            "cache_ttl_label": "Cache TTL",
            "cache_clear": "Clear Cache",

            # 数据管理
            "data_export_settings": "Export Settings",
            "data_import_settings": "Import Settings",
            "data_reset_defaults": "Reset to Defaults",

            # 单位
            "unit_mb": " MB",
            "unit_minutes": " minutes",
            "unit_seconds": " seconds",
            "unit_req_per_sec": " req/sec",

            # 标签页标题
            "tab_general": "General",
            "tab_sync": "Sync",
            "tab_notion": "Notion",
            "tab_advanced": "Advanced",

            # 同步视图
            "sync_local_to_notion": "Local to Notion Sync",
            "sync_local_to_notion_desc": "Upload local files and folders to your Notion workspace",
            "sync_notion_to_local": "Notion to Local Backup",
            "sync_notion_to_local_desc": "Export and backup your Notion workspace to local files",
            "sync_bidirectional": "Bidirectional Synchronization",
            "sync_bidirectional_desc": "Keep your local files and Notion workspace in sync",

            # 文件浏览器
            "local_files": "Local Files",
            "no_directory_selected": "No directory selected",
            "file_tree_headers": ["Name", "Type", "Size", "Modified"],
            "show_files": "Show:",
            "show_markdown": "Markdown",
            "show_images": "Images",
            "show_other": "Other",

            # Notion 目标
            "notion_destination": "Notion Destination",
            "workspace_label": "Workspace:",
            "not_connected": "Not connected",
            "upload_to": "Upload to:",
            "select_destination": "Select destination...",
            "new_page": "New page",
            "existing_page": "Existing page",
            "database": "Database",
            "load_notion_content": "Load Notion Content",
            "options_label": "Options:",
            "preserve_structure": "Preserve folder structure",
            "overwrite_existing": "Overwrite existing files",

            # 操作按钮
            "upload_selected": "Upload Selected Files",
            "export_selected": "Export Selected",
            "ready_to_upload": "Ready to upload",
            "ready_to_export": "Ready to export",
            "upload_progress": "Upload progress",
            "export_progress": "Export progress",
            "upload_complete": "Upload complete",
            "export_complete": "Export complete",

            # Notion 工作区
            "notion_workspace": "Notion Workspace",
            "refresh_workspace": "Refresh Workspace",
            "export_options": "Export Options",
            "export_format": "Export Format:",
            "destination_folder": "Destination:",
            "select_folder": "Select folder...",
            "include_attachments": "Include attachments",
            "preserve_hierarchy": "Preserve page hierarchy",
            "incremental_backup": "Incremental backup",

            # 双向同步
            "sync_pairs": "Sync Pairs",
            "add_sync_pair": "Add Sync Pair",
            "remove_selected": "Remove Selected",
            "auto_sync_label": "Auto-sync",
            "interval_label": "Interval:",
            "start_sync": "Start Sync",
            "stop_sync": "Stop Sync",
            "force_sync_all": "Force Sync All",
            "sync_stopped": "Sync stopped",

            # 文件类型
            "file_type_markdown": "Markdown",
            "file_type_text": "Text File",
            "file_type_html": "HTML",
            "file_type_json": "JSON",
            "file_type_png": "PNG Image",
            "file_type_jpeg": "JPEG Image",
            "file_type_gif": "GIF Image",
            "file_type_webp": "WebP Image",
            "file_type_other": "Other File",
            "file_type_folder": "Folder",
            "file_type_page": "Page",
            "file_type_database": "Database",
            "file_type_workspace": "Workspace",

            # 状态信息
            "no_permission": "No permission to access",
            "untitled_page": "Untitled Page",
            "untitled_database": "Untitled Database",
            "my_workspace": "My Workspace",
            "pages_folder": "Pages",
            "databases_folder": "Databases",
            "empty_database": "Empty",
            "rows_count": "rows",
        }
    
    def set_language(self, language_code: str) -> bool:
        """设置当前语言。"""
        if language_code not in self.supported_languages:
            self.logger.warning(f"不支持的语言: {language_code}")
            return False
        
        if language_code != self.current_language:
            self.current_language = language_code
            self.language_changed.emit(language_code)
            self.logger.info(f"语言已切换到: {self.supported_languages[language_code]}")
        
        return True
    
    def get_current_language(self) -> str:
        """获取当前语言代码。"""
        return self.current_language
    
    def get_supported_languages(self) -> Dict[str, str]:
        """获取支持的语言列表。"""
        return self.supported_languages.copy()
    
    def translate(self, key: str, default: Optional[str] = None) -> str:
        """翻译指定的键。"""
        if self.current_language in self.translations:
            translation = self.translations[self.current_language].get(key)
            if translation:
                return translation
        
        # 如果当前语言没有翻译，尝试使用英文
        if self.current_language != "en_US" and "en_US" in self.translations:
            translation = self.translations["en_US"].get(key)
            if translation:
                return translation
        
        # 如果都没有，返回默认值或键名
        return default or key
    
    def tr(self, key: str, default: Optional[str] = None) -> str:
        """翻译的简写方法。"""
        return self.translate(key, default)


# 全局语言管理器实例
_language_manager = None

def get_language_manager() -> LanguageManager:
    """获取全局语言管理器实例。"""
    global _language_manager
    if _language_manager is None:
        _language_manager = LanguageManager()
    return _language_manager

def tr(key: str, default: Optional[str] = None) -> str:
    """全局翻译函数。"""
    return get_language_manager().translate(key, default)
