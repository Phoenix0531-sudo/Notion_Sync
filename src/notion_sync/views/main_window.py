"""
Notion 同步的主应用程序窗口。
"""

from typing import Optional
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QSplitter,
    QStackedWidget, QMenuBar, QMenu, QStatusBar, QToolBar, QLabel,
    QTabWidget, QPushButton, QFrame
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QAction, QIcon, QKeySequence

from notion_sync.utils.i18n import get_language_manager, tr

from notion_sync.views.base import BaseView, StatusBarView
from notion_sync.views.settings_view import SettingsView
from notion_sync.utils.config import ConfigManager


class MainWindow(QMainWindow):
    """带侧边栏导航的主应用程序窗口。"""

    # 信号
    action_requested = Signal(str, dict)

    def __init__(self, config_manager: ConfigManager, parent: Optional[QWidget] = None):
        """初始化主窗口。"""
        super().__init__(parent)
        self.config_manager = config_manager

        # 获取语言管理器
        self.language_manager = get_language_manager()

        # 窗口属性 - 确保内容完整显示
        self.setWindowTitle(tr("app_title"))
        self.setMinimumSize(1200, 750)  # 增加最小尺寸确保内容显示
        self.resize(1300, 800)  # 增加默认尺寸

        # 初始化 UI 组件
        self._setup_ui()
        self._setup_menu_bar()
        self._setup_toolbar()
        self._setup_status_bar()
        self._setup_connections()

        # 恢复窗口状态
        self._restore_window_state()

        # 自动保存定时器
        self.auto_save_timer = QTimer()
        self.auto_save_timer.timeout.connect(self._save_window_state)
        self.auto_save_timer.start(5000)  # 每5秒保存一次

        # 连接语言变更信号
        self.language_manager.language_changed.connect(self._on_language_changed)
    
    def _setup_ui(self) -> None:
        """设置主用户界面。"""
        # 中央部件 - 使用任务管理界面
        from notion_sync.views.task_manager_view import TaskManagerView
        from notion_sync.services.task_manager import TaskManager

        # 创建任务管理器（需要从控制器传入）
        self.task_manager = None  # 将在控制器中设置
        self.sync_view = None     # 将在设置任务管理器后创建

        # 临时显示一个占位符
        placeholder = QLabel("正在初始化任务管理器...")
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder.setStyleSheet("color: #888888; font-size: 16px;")
        self.setCentralWidget(placeholder)

    def set_task_manager(self, task_manager):
        """设置任务管理器并创建界面"""
        self.task_manager = task_manager

        # 创建任务管理界面
        from notion_sync.views.task_manager_view import TaskManagerView
        self.sync_view = TaskManagerView(task_manager)

        # 连接信号
        self.sync_view.create_task_requested.connect(self._on_create_task_requested)
        self.sync_view.edit_task_requested.connect(self._on_edit_task_requested)
        self.sync_view.run_task_requested.connect(self._on_run_task_requested)
        self.sync_view.delete_task_requested.connect(self._on_delete_task_requested)

        # 设置为中央部件
        self.setCentralWidget(self.sync_view)

    def _on_create_task_requested(self):
        """处理创建任务请求"""
        self.action_requested.emit("create_task", {})

    def _on_edit_task_requested(self, task_id: str):
        """处理编辑任务请求"""
        self.action_requested.emit("edit_task", {"task_id": task_id})

    def _on_run_task_requested(self, task_id: str):
        """处理运行任务请求"""
        self.action_requested.emit("run_task", {"task_id": task_id})

    def _on_delete_task_requested(self, task_id: str):
        """处理删除任务请求"""
        self.action_requested.emit("delete_task", {"task_id": task_id})


    
    def _setup_menu_bar(self) -> None:
        """设置菜单栏。"""
        menubar = self.menuBar()

        # 文件菜单
        self.file_menu = menubar.addMenu(tr("menu_file"))

        # 新建同步动作
        self.new_sync_action = QAction(tr("new_sync"), self)
        self.new_sync_action.setShortcut(QKeySequence.StandardKey.New)
        self.new_sync_action.triggered.connect(lambda: self.action_requested.emit("new_sync", {}))
        self.file_menu.addAction(self.new_sync_action)

        self.file_menu.addSeparator()

        # 导入/导出动作
        self.import_action = QAction(tr("import_settings"), self)
        self.import_action.triggered.connect(lambda: self.action_requested.emit("import_settings", {}))
        self.file_menu.addAction(self.import_action)

        self.export_action = QAction(tr("export_settings"), self)
        self.export_action.triggered.connect(lambda: self.action_requested.emit("export_settings", {}))
        self.file_menu.addAction(self.export_action)

        self.file_menu.addSeparator()

        # 退出动作
        self.quit_action = QAction(tr("quit"), self)
        self.quit_action.setShortcut(QKeySequence.StandardKey.Quit)
        self.quit_action.triggered.connect(self.close)
        self.file_menu.addAction(self.quit_action)
        
        # 编辑菜单
        self.edit_menu = menubar.addMenu(tr("menu_edit"))

        # 偏好设置动作
        self.preferences_action = QAction(tr("preferences"), self)
        self.preferences_action.setShortcut(QKeySequence.StandardKey.Preferences)
        self.preferences_action.triggered.connect(self._show_settings)
        self.edit_menu.addAction(self.preferences_action)

        # 同步菜单
        self.sync_menu = menubar.addMenu(tr("menu_sync"))

        # 开始同步动作
        self.start_sync_action = QAction(tr("start_sync"), self)
        self.start_sync_action.setShortcut(QKeySequence("Ctrl+S"))
        self.start_sync_action.triggered.connect(lambda: self.action_requested.emit("start_sync", {}))
        self.sync_menu.addAction(self.start_sync_action)

        # 停止同步动作
        self.stop_sync_action = QAction(tr("stop_sync"), self)
        self.stop_sync_action.setShortcut(QKeySequence("Ctrl+T"))
        self.stop_sync_action.triggered.connect(lambda: self.action_requested.emit("stop_sync", {}))
        self.sync_menu.addAction(self.stop_sync_action)
        
        self.sync_menu.addSeparator()

        # 立即同步动作
        self.sync_now_action = QAction(tr("sync_now"), self)
        self.sync_now_action.triggered.connect(lambda: self.action_requested.emit("sync_now", {}))
        self.sync_menu.addAction(self.sync_now_action)

        # 连接菜单
        self.connection_menu = menubar.addMenu("连接")

        # 连接到 Notion 动作
        self.connect_action = QAction("连接到 Notion", self)
        self.connect_action.setShortcut(QKeySequence("Ctrl+N"))
        self.connect_action.triggered.connect(lambda: self.action_requested.emit("connect_notion", {}))
        self.connection_menu.addAction(self.connect_action)

        # 断开连接动作
        self.disconnect_action = QAction("断开连接", self)
        self.disconnect_action.triggered.connect(lambda: self.action_requested.emit("disconnect_notion", {}))
        self.connection_menu.addAction(self.disconnect_action)

        self.connection_menu.addSeparator()

        # 刷新工作区动作
        self.refresh_action = QAction("刷新工作区", self)
        self.refresh_action.setShortcut(QKeySequence.StandardKey.Refresh)
        self.refresh_action.triggered.connect(lambda: self.action_requested.emit("refresh_notion", {}))
        self.connection_menu.addAction(self.refresh_action)

        # 工具菜单
        self.tools_menu = menubar.addMenu(tr("menu_tools"))

        # 清除缓存动作
        self.clear_cache_action = QAction(tr("clear_cache"), self)
        self.clear_cache_action.triggered.connect(lambda: self.action_requested.emit("clear_cache", {}))
        self.tools_menu.addAction(self.clear_cache_action)

        # 重置设置动作
        self.reset_settings_action = QAction(tr("reset_settings"), self)
        self.reset_settings_action.triggered.connect(lambda: self.action_requested.emit("reset_settings", {}))
        self.tools_menu.addAction(self.reset_settings_action)

        # 帮助菜单
        self.help_menu = menubar.addMenu(tr("menu_help"))

        # 关于动作
        self.about_action = QAction(tr("about"), self)
        self.about_action.triggered.connect(lambda: self.action_requested.emit("show_about", {}))
        self.help_menu.addAction(self.about_action)

        # 帮助动作
        self.help_action = QAction(tr("help"), self)
        self.help_action.triggered.connect(lambda: self.action_requested.emit("show_help", {}))
        self.help_menu.addAction(self.help_action)
    
    def _setup_toolbar(self) -> None:
        """设置工具栏。"""
        self.toolbar = QToolBar(tr("app_title"))
        self.toolbar.setObjectName("MainToolBar")
        self.toolbar.setMovable(False)
        self.addToolBar(self.toolbar)

        # 同步动作
        self.toolbar_start_sync = QAction(tr("toolbar_start_sync"), self)
        self.toolbar_start_sync.setToolTip(tr("toolbar_start_sync"))
        self.toolbar_start_sync.triggered.connect(lambda: self.action_requested.emit("start_sync", {}))
        self.toolbar.addAction(self.toolbar_start_sync)

        self.toolbar_stop_sync = QAction(tr("toolbar_stop_sync"), self)
        self.toolbar_stop_sync.setToolTip(tr("toolbar_stop_sync"))
        self.toolbar_stop_sync.triggered.connect(lambda: self.action_requested.emit("stop_sync", {}))
        self.toolbar.addAction(self.toolbar_stop_sync)

        self.toolbar.addSeparator()

        # 刷新动作
        self.toolbar_refresh = QAction(tr("toolbar_refresh"), self)
        self.toolbar_refresh.setToolTip(tr("toolbar_refresh"))
        self.toolbar_refresh.triggered.connect(lambda: self.action_requested.emit("refresh", {}))
        self.toolbar.addAction(self.toolbar_refresh)

        self.toolbar.addSeparator()

        # 设置动作
        self.toolbar_settings = QAction(tr("settings_title"), self)
        self.toolbar_settings.setToolTip(tr("settings_title"))
        self.toolbar_settings.triggered.connect(self._show_settings)
        self.toolbar.addAction(self.toolbar_settings)
    
    def _setup_status_bar(self) -> None:
        """Set up the status bar."""
        self.status_bar = StatusBarView()
        self.setStatusBar(self.status_bar)
    
    def _setup_connections(self) -> None:
        """Set up signal connections."""
        # 同步视图的信号连接将在 set_task_manager 中设置
        pass
    
    def update_connection_status(self, connected: bool, workspace_name: str = "") -> None:
        """更新连接状态显示。"""
        self.sync_view.update_connection_status(connected, workspace_name)
    

    
    def set_status(self, message: str) -> None:
        """Set status bar message."""
        self.status_bar.set_status(message)
    
    def set_progress(self, percentage: int, visible: bool = True) -> None:
        """Set progress bar value and visibility."""
        self.status_bar.set_progress(percentage, visible)
    
    def set_connection_status(self, connected: bool, workspace_name: str = "") -> None:
        """Set connection status indicator."""
        self.status_bar.set_connection_status(connected)
        if hasattr(self.sync_view, 'update_connection_status'):
            self.sync_view.update_connection_status(connected)

    def update_notion_workspace(self, workspace_data: dict) -> None:
        """更新 Notion 工作区显示"""
        try:
            print(f"主窗口更新工作区: {workspace_data}")
            # 新界面使用 update_notion_content 方法
            if hasattr(self.sync_view, 'update_notion_content'):
                self.sync_view.update_notion_content(workspace_data)
            elif hasattr(self.sync_view, 'update_notion_workspace'):
                self.sync_view.update_notion_workspace(workspace_data)
        except Exception as e:
            print(f"主窗口更新工作区时出错: {e}")
            import traceback
            traceback.print_exc()

    def add_sync_log(self, message: str) -> None:
        """添加同步日志"""
        # GoodSync 风格界面使用状态栏显示消息
        self.sync_view.set_status(message)

    def update_sync_progress(self, percentage: int) -> None:
        """更新同步进度"""
        self.sync_view.update_progress(percentage)

    def _show_settings(self) -> None:
        """显示设置对话框"""
        from notion_sync.views.settings_view import SettingsView
        from PySide6.QtWidgets import QDialog, QVBoxLayout

        # 创建设置对话框
        settings_dialog = QDialog(self)
        settings_dialog.setWindowTitle("设置")
        settings_dialog.setModal(True)
        settings_dialog.resize(700, 600)

        # 应用暗黑主题到对话框
        settings_dialog.setStyleSheet("""
        QDialog {
            background-color: #2b2b2b;
            color: #ffffff;
        }
        """)

        layout = QVBoxLayout(settings_dialog)
        layout.setContentsMargins(0, 0, 0, 0)

        # 添加设置视图
        settings_view = SettingsView(self.config_manager)
        layout.addWidget(settings_view)

        # 显示对话框
        settings_dialog.exec()
    
    def _save_window_state(self) -> None:
        """Save window geometry and state."""
        self.config_manager.set_window_geometry(self.saveGeometry())
        self.config_manager.set_window_state(self.saveState())
    
    def _restore_window_state(self) -> None:
        """Restore window geometry and state."""
        geometry = self.config_manager.get_window_geometry()
        if geometry:
            self.restoreGeometry(geometry)
        
        state = self.config_manager.get_window_state()
        if state:
            self.restoreState(state)
        
        # 简洁界面无需恢复标签页状态
    
    def _on_language_changed(self, language_code: str) -> None:
        """处理语言变更事件。"""
        # 更新窗口标题
        self.setWindowTitle(tr("app_title"))

        # 更新菜单
        self._update_menu_texts()

        # 更新工具栏
        self._update_toolbar_texts()

        # 更新状态栏
        self.status_bar.set_status(tr("status_ready"))

    def _update_menu_texts(self) -> None:
        """更新菜单文本。"""
        # 文件菜单
        self.file_menu.setTitle(tr("menu_file"))
        self.new_sync_action.setText(tr("new_sync"))
        self.import_action.setText(tr("import_settings"))
        self.export_action.setText(tr("export_settings"))
        self.quit_action.setText(tr("quit"))

        # 编辑菜单
        self.edit_menu.setTitle(tr("menu_edit"))
        self.preferences_action.setText(tr("preferences"))

        # 连接菜单
        self.connection_menu.setTitle("连接")
        self.connect_action.setText("连接到 Notion")
        self.disconnect_action.setText("断开连接")
        self.refresh_action.setText("刷新工作区")

        # 同步菜单
        self.sync_menu.setTitle(tr("menu_sync"))
        self.start_sync_action.setText(tr("start_sync"))
        self.stop_sync_action.setText(tr("stop_sync"))
        self.sync_now_action.setText(tr("sync_now"))

        # 工具菜单
        self.tools_menu.setTitle(tr("menu_tools"))
        self.clear_cache_action.setText(tr("clear_cache"))
        self.reset_settings_action.setText(tr("reset_settings"))

        # 帮助菜单
        self.help_menu.setTitle(tr("menu_help"))
        self.about_action.setText(tr("about"))
        self.help_action.setText(tr("help"))

    def _update_toolbar_texts(self) -> None:
        """更新工具栏文本。"""
        self.toolbar_start_sync.setText(tr("toolbar_start_sync"))
        self.toolbar_start_sync.setToolTip(tr("toolbar_start_sync"))

        self.toolbar_stop_sync.setText(tr("toolbar_stop_sync"))
        self.toolbar_stop_sync.setToolTip(tr("toolbar_stop_sync"))

        self.toolbar_refresh.setText(tr("toolbar_refresh"))
        self.toolbar_refresh.setToolTip(tr("toolbar_refresh"))

        self.toolbar_settings.setText(tr("settings_title"))
        self.toolbar_settings.setToolTip(tr("settings_title"))

    def closeEvent(self, event) -> None:
        """处理窗口关闭事件。"""
        self._save_window_state()
        self.action_requested.emit("app_closing", {})
        event.accept()
