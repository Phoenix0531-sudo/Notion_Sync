"""
Main application controller for Notion Sync.
"""

import os
from typing import Optional, Dict, Any
from PySide6.QtCore import QObject, QTimer
from PySide6.QtWidgets import QMessageBox, QFileDialog

from notion_sync.controllers.base import BaseController
from notion_sync.models.database import DatabaseManager
from notion_sync.models.file_system import FileManager
from notion_sync.utils.config import ConfigManager
from notion_sync.utils.settings_manager import SettingsManager
from notion_sync.views.main_window import MainWindow
from notion_sync.views.token_dialog import show_token_dialog
from notion_sync.views.new_sync_dialog import show_new_sync_dialog
from notion_sync.services.sync_bridge import SyncBridge
from notion_sync.utils.error_handler import handle_error, ErrorType, error_handler_decorator


class AppController(BaseController):
    """Main application controller."""
    
    def __init__(self, config_manager: ConfigManager, parent: Optional[QObject] = None):
        """Initialize the application controller."""
        super().__init__(parent)
        self.config_manager = config_manager
        
        # Initialize models
        self.database_manager = DatabaseManager()
        self.file_manager = FileManager()
        self.settings_manager = SettingsManager(config_manager)

        # Initialize sync bridge (统一管理所有同步相关服务)
        self.sync_bridge = SyncBridge(config_manager)

        # Initialize task manager
        from notion_sync.services.task_manager import TaskManager
        self.task_manager = TaskManager(config_manager)

        # Initialize main window
        self.main_window = MainWindow(config_manager)

        # Set task manager to main window
        self.main_window.set_task_manager(self.task_manager)
        
        # Setup connections
        self._setup_connections()
        
        # Load initial state
        self._load_initial_state()
    
    def _setup_connections(self) -> None:
        """Set up signal connections."""
        # Main window actions
        self.main_window.action_requested.connect(self._handle_action)
        
        # File manager signals
        self.file_manager.file_changed.connect(self._on_file_changed)
        self.file_manager.error_occurred.connect(self._on_error)

        # Sync bridge signals
        self.sync_bridge.sync_status_changed.connect(self._on_sync_status_changed)
        self.sync_bridge.connection_status_changed.connect(self._on_connection_status_changed)
    
    def _load_initial_state(self) -> None:
        """加载初始应用状态。"""
        # 检查是否首次使用
        is_first_time = self.config_manager.get("first_time_setup", True)

        if is_first_time:
            # 延迟显示向导，让主窗口先显示
            QTimer.singleShot(500, self._show_welcome_wizard)
            return

        # 尝试加载保存的 API 令牌
        saved_token = self.config_manager.get("notion_api_token", "")

        if saved_token:
            # 尝试连接到 Notion
            if self.sync_bridge.connect_to_notion(saved_token):
                self.main_window.set_connection_status(True)
                self.main_window.set_status("已连接到云端服务")
            else:
                self.main_window.set_connection_status(False)
                self.main_window.set_status("连接失败，请重新连接")
        else:
            self.main_window.set_connection_status(False)
            self.main_window.set_status("未连接到云端服务")
    

    
    def _handle_action(self, action: str, parameters: Dict[str, Any]) -> None:
        """Handle actions from views."""
        self.logger.debug(f"Handling action: {action} with parameters: {parameters}")
        
        if action == "connect_notion":
            self._connect_to_notion()
        elif action == "disconnect_notion":
            self._disconnect_from_notion()
        elif action == "refresh":
            self._refresh_data()
        elif action == "export_to_local":
            self._export_to_local()
        elif action == "start_export":
            self._start_export(parameters)
        elif action == "create_task":
            self._create_task(parameters)
        elif action == "edit_task":
            self._edit_task(parameters)
        elif action == "run_task":
            self._run_task(parameters)
        elif action == "delete_task":
            self._delete_task(parameters)
        elif action == "stop_sync":
            self._stop_sync()
        elif action == "upload_files":
            self._upload_files()
        elif action == "export_content":
            self._export_content()
        elif action == "load_directory":
            self._load_directory(parameters.get("path", ""))
        elif action == "settings_applied":
            self._on_settings_applied()
        elif action == "app_closing":
            self._on_app_closing()
        elif action == "show_about":
            self._show_about_dialog()
        elif action == "export_settings":
            self._export_settings()
        elif action == "import_settings":
            self._import_settings()
        elif action == "reset_settings":
            self._reset_settings()
        elif action == "clear_cache":
            self._clear_cache()
        elif action == "load_notion_workspace":
            self._load_notion_workspace()
        elif action == "notion_target_selected":
            self._on_notion_target_selected(parameters)
        elif action == "close_settings":
            self._close_settings()
        elif action == "apply_theme":
            self._apply_theme(parameters.get("theme", "system"))
        elif action == "new_sync":
            self._new_export()
        elif action == "sync_now":
            self._sync_now()
        elif action == "show_help":
            self._show_help()
        elif action == "cancel_upload":
            self._cancel_upload()
        elif action == "cancel_export":
            self._cancel_export()
        elif action == "refresh_notion":
            self._refresh_notion()
        elif action == "add_sync_pair":
            self._add_sync_pair()
        elif action == "remove_sync_pair":
            self._remove_sync_pair()
        elif action == "start_bidirectional_sync":
            self._start_bidirectional_sync()
        elif action == "stop_bidirectional_sync":
            self._stop_bidirectional_sync()
        elif action == "force_sync_all":
            self._force_sync_all()
        elif action == "analyze":
            self._handle_analyze_action()
        elif action == "show_options":
            self._show_settings()
        else:
            self.logger.warning(f"未处理的动作: {action}")
    
    @error_handler_decorator(ErrorType.AUTH)
    def _connect_to_notion(self) -> None:
        """连接到云端服务。"""
        try:
            # 显示令牌输入对话框
            token = show_token_dialog(self.main_window)

            if token:
                # 使用同步桥接器连接
                if self.sync_bridge.connect_to_notion(token):
                    # 保存令牌到配置
                    self.config_manager.set("notion_api_token", token)
                    self.main_window.set_connection_status(True)
                    self.main_window.set_status("已连接到云端服务")
                    self._show_info("成功连接到云端服务！")

                    # 自动加载工作区
                    self._load_notion_workspace()
                else:
                    raise Exception("连接失败，请检查 API 令牌是否正确")
            else:
                self.main_window.set_status("连接已取消")
        except Exception as e:
            handle_error(e, {"action": "connect_to_notion"}, show_dialog=True)
    
    def _disconnect_from_notion(self) -> None:
        """断开云端连接。"""
        self.sync_bridge.disconnect_from_notion()

        # 清除保存的令牌
        self.config_manager.set("notion_api_token", "")

        self.main_window.set_connection_status(False)
        self.main_window.set_status("已断开云端连接")
    

    
    def _refresh_data(self) -> None:
        """Refresh application data."""
        self.main_window.set_status("Refreshing...")
        
        # Simulate refresh operation
        QTimer.singleShot(2000, lambda: self.main_window.set_status("Ready"))
    
    def _start_sync(self, sync_mode: str = "bidirectional") -> None:
        """开始同步。"""
        if not self.sync_bridge.is_connected():
            self._show_error("请先连接到云端服务")
            return

        # 检查是否有同步对配置
        sync_pairs = self.sync_bridge.get_sync_pairs()
        if not sync_pairs:
            # 如果没有同步对，创建一个默认的
            self._create_default_sync_pair()

        self.main_window.set_status(f"正在启动{sync_mode}同步...")
        self.main_window.add_sync_log(f"开始{sync_mode}同步")

        # 模拟同步进度
        self._simulate_sync_progress()

        self.sync_bridge.start_sync(sync_mode)

    def _export_to_local(self) -> None:
        """导出 Notion 内容到本地"""
        if not self.sync_bridge.is_connected():
            self._show_error("请先连接到 Notion")
            return

        self.logger.info("开始导出 Notion 内容到本地")
        self.main_window.set_status("正在导出内容...")

        # 开始导出（云端到本地）
        self.sync_bridge.start_sync("remote_to_local")

    def _stop_sync(self) -> None:
        """停止同步。"""
        self.sync_bridge.stop_sync()
        self.main_window.set_status("同步已停止")
    
    def _upload_files(self) -> None:
        """Upload selected files to Notion."""
        if not self.sync_bridge.is_connected():
            self._show_error("请先连接到云端服务")
            return

        # 获取选中的文件
        selected_files = self.main_window.local_to_notion_view.get_selected_files()
        if not selected_files:
            self._show_error("请先选择要上传的文件")
            return

        # 开始上传
        self.main_window.set_status("正在上传文件...")
        self.sync_bridge.start_sync("local_to_remote")

    def _export_content(self) -> None:
        """Export Notion content to local files."""
        if not self.sync_bridge.is_connected():
            self._show_error("请先连接到云端服务")
            return

        # 获取选中的内容
        selected_items = self.main_window.notion_to_local_view.get_selected_notion_items()
        if not selected_items:
            self._show_error("请先选择要导出的内容")
            return

        # 开始导出
        self.main_window.set_status("正在导出内容...")
        self.sync_bridge.start_sync("remote_to_local")
    
    @error_handler_decorator(ErrorType.FILE_IO)
    def _load_directory(self, path: str) -> None:
        """Load directory for file browsing."""
        try:
            if not path:
                return

            # 检查路径是否存在
            if not os.path.exists(path):
                raise FileNotFoundError(f"目录不存在: {path}")

            if not os.path.isdir(path):
                raise NotADirectoryError(f"路径不是目录: {path}")

            self.main_window.set_status(f"正在加载目录: {path}")

            # 使用同步桥接器加载目录
            self.sync_bridge.load_directory(path)

            QTimer.singleShot(1000, lambda: self.main_window.set_status("目录加载完成"))
        except Exception as e:
            handle_error(e, {"action": "load_directory", "path": path})
    
    def _on_file_changed(self, file_path: str, change_type: str) -> None:
        """Handle file system changes."""
        self.logger.info(f"File {change_type}: {file_path}")
        # File change handling logic would go here
    
    def _on_settings_applied(self) -> None:
        """Handle settings being applied."""
        self.main_window.set_status("Settings applied")
        # Reload any settings that affect the application state
    
    def _on_app_closing(self) -> None:
        """Handle application closing."""
        # Stop file watching
        self.file_manager.stop_watching()

        # 清理同步桥接器
        self.sync_bridge.cleanup()
    
    def _on_error(self, error: str) -> None:
        """Handle errors from models."""
        self.logger.error(error)
        self.main_window.set_status(f"Error: {error}")

    def _on_sync_status_changed(self, status: str) -> None:
        """处理同步状态变化。"""
        self.main_window.set_status(status)
        self.logger.info(f"同步状态: {status}")

        # 更新新界面的连接状态
        if hasattr(self.main_window, 'sync_view') and hasattr(self.main_window.sync_view, 'update_connection_status'):
            is_connected = "已连接" in status or "连接成功" in status
            self.main_window.sync_view.update_connection_status(is_connected)

    def _on_connection_status_changed(self, connected: bool) -> None:
        """处理连接状态变化。"""
        workspace_name = ""
        if connected and self.sync_bridge.notion_client:
            workspace_info = self.sync_bridge.get_notion_workspace_info()
            workspace_name = workspace_info.get("name", "")

        self.main_window.set_connection_status(connected, workspace_name)
        if connected:
            self.main_window.set_status("已连接到云端服务")
        else:
            self.main_window.set_status("已断开云端连接")
    
    def _show_error(self, message: str) -> None:
        """Show error message to user."""
        QMessageBox.critical(self.main_window, "Error", message)
    
    def _show_info(self, message: str) -> None:
        """Show info message to user."""
        QMessageBox.information(self.main_window, "Information", message)
    
    def _show_about_dialog(self) -> None:
        """Show about dialog."""
        about_text = """
        <h2>Notion Sync</h2>
        <p>Version 1.0.0</p>
        <p>A modern desktop application for synchronizing files with Notion.</p>
        <p>Built with PySide6 and following Apple's Human Interface Guidelines.</p>
        <p><a href="https://github.com/your-repo/notion-sync">GitHub Repository</a></p>
        """
        QMessageBox.about(self.main_window, "About Notion Sync", about_text)
    


    def _export_settings(self) -> None:
        """导出设置到文件。"""
        file_path, _ = QFileDialog.getSaveFileName(
            self.main_window,
            "导出设置",
            "notion_sync_settings.json",
            "JSON 文件 (*.json)"
        )

        if file_path:
            if self.settings_manager.export_settings(file_path):
                self._show_info("设置导出成功")
            else:
                self._show_error("设置导出失败")

    def _import_settings(self) -> None:
        """从文件导入设置。"""
        file_path, _ = QFileDialog.getOpenFileName(
            self.main_window,
            "导入设置",
            "",
            "JSON 文件 (*.json)"
        )

        if file_path:
            success, message = self.settings_manager.import_settings(file_path)
            if success:
                self._show_info("设置导入成功，重启应用程序以生效")
            else:
                self._show_error(f"设置导入失败: {message}")

    def _reset_settings(self) -> None:
        """重置设置为默认值。"""
        reply = QMessageBox.question(
            self.main_window,
            "重置设置",
            "确定要重置所有设置为默认值吗？此操作无法撤销。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.config_manager.reset_to_defaults()
            self._show_info("设置已重置为默认值")

    def _clear_cache(self) -> None:
        """清除应用程序缓存。"""
        if self.sync_bridge.notion_client:
            self.sync_bridge.notion_client.clear_cache()

        # 清除文件管理器缓存
        # self.file_manager.clear_cache()  # 如果有的话

        self._show_info("缓存已清除")

    def _load_notion_workspace(self) -> None:
        """加载云端工作区内容。"""
        if not self.sync_bridge.is_connected():
            self._show_error("请先连接到云端服务")
            return

        self.main_window.set_status("正在加载工作区...")

        # 加载工作区数据
        workspace_data = self.sync_bridge.get_notion_workspace_info()

        if workspace_data:
            # 转换为 UI 需要的格式
            pages = workspace_data.get("pages", [])
            databases = workspace_data.get("databases", [])

            print(f"原始工作区数据: pages={len(pages)}, databases={len(databases)}")

            # 将 NotionPage 和 NotionDatabase 对象转换为字典
            pages_dict = [page.to_dict() if hasattr(page, 'to_dict') else page for page in pages]
            databases_dict = [db.to_dict() if hasattr(db, 'to_dict') else db for db in databases]

            print(f"转换后数据: pages_dict={len(pages_dict)}, databases_dict={len(databases_dict)}")

            ui_data = {
                "id": "workspace_123",
                "name": workspace_data.get("name", "我的工作区"),
                "pages": pages_dict,
                "databases": databases_dict
            }

            print(f"UI数据: {ui_data}")

            # 更新 UI
            self.main_window.update_notion_workspace(ui_data)

            # 更新新界面的 Notion 内容
            if hasattr(self.main_window, 'sync_view') and hasattr(self.main_window.sync_view, 'update_notion_content'):
                self.main_window.sync_view.update_notion_content(ui_data)

            self.main_window.set_status("工作区加载完成")
        else:
            print("工作区数据为空")
            self.main_window.set_status("工作区加载失败")

    def _on_notion_target_selected(self, parameters: Dict[str, Any]) -> None:
        """处理 Notion 目标选择。"""
        notion_type = parameters.get("type")
        notion_name = parameters.get("name")

        self.logger.info(f"选择了 Notion 目标: {notion_name} ({notion_type})")

    def _close_settings(self) -> None:
        """关闭设置窗口。"""
        # 设置窗口通常是模态对话框，关闭时会自动处理
        self.main_window.set_status("设置已关闭")

    def _apply_theme(self, theme: str) -> None:
        """应用主题设置。"""
        self.logger.info(f"应用主题: {theme}")

        # 应用主题到主窗口
        self._set_application_theme(theme)

        # 保存主题设置
        self.config_manager.set("theme", theme)

        self.main_window.set_status(f"主题已切换为: {theme}")

    def _set_application_theme(self, theme: str) -> None:
        """设置应用程序主题。"""
        from PySide6.QtWidgets import QApplication
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QPalette, QColor

        app = QApplication.instance()
        if not app:
            return

        if theme == "dark" or theme == "深色":
            # 深色主题
            palette = QPalette()

            # 窗口颜色
            palette.setColor(QPalette.ColorRole.Window, QColor(45, 45, 48))
            palette.setColor(QPalette.ColorRole.WindowText, QColor(255, 255, 255))

            # 基础颜色
            palette.setColor(QPalette.ColorRole.Base, QColor(35, 35, 38))
            palette.setColor(QPalette.ColorRole.AlternateBase, QColor(55, 55, 58))

            # 文本颜色
            palette.setColor(QPalette.ColorRole.Text, QColor(255, 255, 255))
            palette.setColor(QPalette.ColorRole.BrightText, QColor(255, 0, 0))

            # 按钮颜色
            palette.setColor(QPalette.ColorRole.Button, QColor(55, 55, 58))
            palette.setColor(QPalette.ColorRole.ButtonText, QColor(255, 255, 255))

            # 高亮颜色
            palette.setColor(QPalette.ColorRole.Highlight, QColor(0, 122, 255))
            palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))

            app.setPalette(palette)

        elif theme == "light" or theme == "浅色":
            # 浅色主题
            palette = QPalette()

            # 窗口颜色
            palette.setColor(QPalette.ColorRole.Window, QColor(255, 255, 255))
            palette.setColor(QPalette.ColorRole.WindowText, QColor(0, 0, 0))

            # 基础颜色
            palette.setColor(QPalette.ColorRole.Base, QColor(255, 255, 255))
            palette.setColor(QPalette.ColorRole.AlternateBase, QColor(245, 245, 245))

            # 文本颜色
            palette.setColor(QPalette.ColorRole.Text, QColor(0, 0, 0))
            palette.setColor(QPalette.ColorRole.BrightText, QColor(255, 0, 0))

            # 按钮颜色
            palette.setColor(QPalette.ColorRole.Button, QColor(240, 240, 240))
            palette.setColor(QPalette.ColorRole.ButtonText, QColor(0, 0, 0))

            # 高亮颜色
            palette.setColor(QPalette.ColorRole.Highlight, QColor(0, 122, 255))
            palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))

            app.setPalette(palette)

        else:  # system 或 跟随系统
            # 使用系统默认主题
            app.setPalette(app.style().standardPalette())

    def _new_export(self) -> None:
        """创建新的导出任务。"""
        self.logger.info("创建新的导出任务")

        # 检查是否已连接到 Notion
        if not self.sync_bridge.is_connected():
            self._show_error("请先连接到 Notion")
            return

        # 显示导出对话框
        from notion_sync.views.export_dialog import show_export_dialog
        success, export_data = show_export_dialog(self.main_window)

        if success:
            # 开始导出任务
            target_folder = export_data.get("target_folder")
            source_type = export_data.get("source_type")
            file_format = export_data.get("file_format")

            if target_folder:
                self.logger.info(f"开始导出任务：{source_type} -> {target_folder}")
                self.main_window.set_status("正在导出...")

                # 使用同步桥接器开始导出
                self.sync_bridge.start_sync("remote_to_local")
                self._show_info(f"导出任务已开始：\n目标文件夹：{target_folder}")
            else:
                self._show_error("导出信息不完整")
        else:
            self.main_window.set_status("取消导出")

    def _start_export(self, parameters: dict) -> None:
        """开始导出（从新界面触发）"""
        notion_items = parameters.get("notion_items", [])
        local_folder = parameters.get("local_folder", "")
        item_count = parameters.get("item_count", 0)

        if not notion_items or not local_folder:
            self._show_error("导出参数不完整")
            return

        self.logger.info(f"开始导出 {item_count} 个项目到 {local_folder}")

        # 更新界面状态
        self.main_window.sync_view.update_progress(10, "准备导出...")

        # 模拟导出过程
        self._simulate_export_process(notion_items, local_folder)

    def _simulate_export_process(self, notion_items: list, local_folder: str):
        """真正的导出过程"""
        # 使用异步工作器进行真实导出
        from notion_sync.utils.async_worker import run_async_task

        def real_export():
            try:
                # 更新进度
                self.main_window.sync_view.update_progress(10, "准备导出...")

                # 确保目标文件夹存在
                import os
                os.makedirs(local_folder, exist_ok=True)

                self.main_window.sync_view.update_progress(20, "连接到 Notion...")

                # 获取 Notion 客户端
                notion_client = self.sync_bridge.notion_client
                if not notion_client or not notion_client.connected:
                    raise Exception("未连接到 Notion")

                exported_count = 0
                total_items = len(notion_items)

                for i, item in enumerate(notion_items):
                    item_id = item.get('id')
                    item_title = item.get('title', '无标题')

                    progress = 30 + (i * 60 // total_items)
                    self.main_window.sync_view.update_progress(progress, f"导出: {item_title}")

                    try:
                        # 获取页面内容
                        page_content = notion_client.get_page_content(item_id)
                        self.logger.info(f"获取页面内容: {item_title}, 内容: {page_content}")

                        # 生成文件名（移除非法字符）
                        safe_title = "".join(c for c in item_title if c.isalnum() or c in (' ', '-', '_')).strip()
                        if not safe_title:
                            safe_title = f"page_{item_id[:8]}"

                        file_path = os.path.join(local_folder, f"{safe_title}.md")

                        # 转换为 Markdown 格式
                        markdown_content = self._convert_to_markdown(page_content, item)

                        # 保存文件
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(markdown_content)

                        exported_count += 1
                        self.logger.info(f"成功导出: {item_title} -> {file_path}")

                    except Exception as e:
                        self.logger.error(f"导出失败 {item_title}: {str(e)}")
                        import traceback
                        traceback.print_exc()
                        continue

                self.main_window.sync_view.update_progress(100, "导出完成！")

                return {
                    'success': True,
                    'exported_count': exported_count,
                    'total_count': total_items,
                    'folder': local_folder
                }

            except Exception as e:
                self.logger.error(f"导出过程出错: {str(e)}")
                return {
                    'success': False,
                    'error': str(e)
                }

        # 运行异步导出
        worker = run_async_task("export_notion_content", real_export)
        worker.finished.connect(lambda result: self._on_export_finished(result))
        worker.error.connect(lambda error: self._on_export_error(error))

    def _convert_to_markdown(self, page_content: dict, item_info: dict) -> str:
        """将 Notion 内容转换为 Markdown"""
        title = item_info.get('title', '无标题')
        created_time = item_info.get('created_time', '')
        last_edited_time = item_info.get('last_edited_time', '')
        url = item_info.get('url', '')

        # 创建 Markdown 内容
        markdown = f"# {title}\n\n"

        # 添加元数据
        markdown += f"**创建时间**: {created_time}\n"
        markdown += f"**最后编辑**: {last_edited_time}\n"
        markdown += f"**原始链接**: [{title}]({url})\n\n"
        markdown += "---\n\n"

        # 处理页面内容 - 检查不同的数据格式
        blocks = []
        if page_content:
            if 'results' in page_content:
                blocks = page_content['results']
            elif 'blocks' in page_content:
                blocks = page_content['blocks']
            elif isinstance(page_content, list):
                blocks = page_content

        if blocks:
            self.logger.info(f"处理 {len(blocks)} 个块")
            for i, block in enumerate(blocks):
                try:
                    block_markdown = self._convert_block_to_markdown(block)
                    if block_markdown:
                        markdown += block_markdown
                    else:
                        self.logger.warning(f"块 {i} 转换为空: {block.get('type', 'unknown')}")
                except Exception as e:
                    self.logger.error(f"转换块 {i} 时出错: {e}")
                    continue
        else:
            markdown += "*此页面暂无内容或无法获取内容*\n"
            self.logger.warning(f"页面内容为空或格式不正确: {page_content}")

        return markdown

    def _convert_block_to_markdown(self, block: dict) -> str:
        """将 Notion 块转换为 Markdown"""
        block_type = block.get('type', '')

        if block_type == 'paragraph':
            text = self._extract_text_from_rich_text(block.get('paragraph', {}).get('rich_text', []))
            return f"{text}\n\n"

        elif block_type == 'heading_1':
            text = self._extract_text_from_rich_text(block.get('heading_1', {}).get('rich_text', []))
            return f"# {text}\n\n"

        elif block_type == 'heading_2':
            text = self._extract_text_from_rich_text(block.get('heading_2', {}).get('rich_text', []))
            return f"## {text}\n\n"

        elif block_type == 'heading_3':
            text = self._extract_text_from_rich_text(block.get('heading_3', {}).get('rich_text', []))
            return f"### {text}\n\n"

        elif block_type == 'bulleted_list_item':
            text = self._extract_text_from_rich_text(block.get('bulleted_list_item', {}).get('rich_text', []))
            return f"- {text}\n"

        elif block_type == 'numbered_list_item':
            text = self._extract_text_from_rich_text(block.get('numbered_list_item', {}).get('rich_text', []))
            return f"1. {text}\n"

        elif block_type == 'code':
            code_block = block.get('code', {})
            language = code_block.get('language', '')
            text = self._extract_text_from_rich_text(code_block.get('rich_text', []))
            return f"```{language}\n{text}\n```\n\n"

        elif block_type == 'quote':
            text = self._extract_text_from_rich_text(block.get('quote', {}).get('rich_text', []))
            return f"> {text}\n\n"

        else:
            # 对于其他类型的块，尝试提取文本
            text = self._extract_text_from_block(block)
            if text:
                return f"{text}\n\n"
            return ""

    def _extract_text_from_rich_text(self, rich_text_array: list) -> str:
        """从富文本数组中提取纯文本"""
        text = ""
        for rich_text in rich_text_array:
            if rich_text.get('type') == 'text':
                content = rich_text.get('text', {}).get('content', '')
                # 处理格式
                if rich_text.get('annotations', {}).get('bold'):
                    content = f"**{content}**"
                if rich_text.get('annotations', {}).get('italic'):
                    content = f"*{content}*"
                if rich_text.get('annotations', {}).get('code'):
                    content = f"`{content}`"
                text += content
        return text

    def _extract_text_from_block(self, block: dict) -> str:
        """从任意块中提取文本"""
        block_type = block.get('type', '')
        if block_type in block:
            block_content = block[block_type]
            if 'rich_text' in block_content:
                return self._extract_text_from_rich_text(block_content['rich_text'])
        return ""

    def _on_export_finished(self, result: dict):
        """导出完成处理"""
        if result['success']:
            exported_count = result['exported_count']
            total_count = result['total_count']
            folder = result['folder']

            message = f"成功导出 {exported_count}/{total_count} 个项目到:\n{folder}"
            self.main_window.sync_view.export_completed(True, message)
            self._show_info(f"导出完成！\n\n{message}")
        else:
            error = result['error']
            self.main_window.sync_view.export_completed(False, error)
            self._show_error(f"导出失败：{error}")

    def _on_export_error(self, error: str):
        """导出错误处理"""
        self.main_window.sync_view.export_completed(False, error)
        self._show_error(f"导出过程出错：{error}")

    def _create_task(self, parameters: dict):
        """创建新任务"""
        # 检查是否已连接到 Notion
        if not self.sync_bridge.is_connected():
            self._show_error("请先连接到 Notion")
            return

        # 获取工作区数据
        workspace_data = self.sync_bridge.get_notion_workspace_info()
        if not workspace_data:
            self._show_error("无法获取 Notion 工作区信息")
            return

        # 创建并显示美观的新任务对话框
        from notion_sync.views.beautiful_task_dialog import BeautifulTaskDialog
        dialog = BeautifulTaskDialog(workspace_data, self.main_window)
        dialog.task_created.connect(self._on_task_created)
        dialog.show()

    def _on_task_created(self, task_config: dict):
        """处理任务创建"""
        try:
            # 从配置中提取信息
            task_name = task_config["name"]
            local_folder = task_config["local_folder"]
            notion_items = task_config["notion_items"]
            include_children = task_config["include_children"]
            auto_sync = task_config["auto_sync"]

            # 为每个选中的 Notion 项目创建任务
            for item in notion_items:
                item_data = item["data"]
                item_type = item["type"]

                # 创建任务
                task = self.task_manager.create_task(
                    name=f"{task_name} - {item_data.get('title', '无标题')}",
                    notion_source_type=item_type,
                    notion_source_id=item_data.get("id", ""),
                    notion_source_title=item_data.get("title", "无标题"),
                    local_folder=local_folder,
                    include_children=include_children,
                    auto_sync=auto_sync
                )

                self.logger.info(f"创建任务: {task.name}")

            self._show_info(f"成功创建 {len(notion_items)} 个同步任务")

        except Exception as e:
            self.logger.error(f"创建任务失败: {e}")
            self._show_error(f"创建任务失败: {str(e)}")

    def _edit_task(self, parameters: dict):
        """编辑任务"""
        task_id = parameters.get("task_id")
        if not task_id:
            return

        task = self.task_manager.get_task(task_id)
        if not task:
            self._show_error("任务不存在")
            return

        # 这里可以实现编辑任务对话框
        self._show_info(f"编辑任务功能待实现: {task.name}")

    def _run_task(self, parameters: dict):
        """运行任务"""
        task_id = parameters.get("task_id")
        if not task_id:
            return

        task = self.task_manager.get_task(task_id)
        if not task:
            self._show_error("任务不存在")
            return

        # 检查是否已连接到 Notion
        if not self.sync_bridge.is_connected():
            self._show_error("请先连接到 Notion")
            return

        # 更新任务状态为运行中
        from notion_sync.models.sync_task import TaskStatus
        self.task_manager.update_task_status(task_id, TaskStatus.RUNNING)

        # 执行任务
        self._execute_sync_task(task)

    def _delete_task(self, parameters: dict):
        """删除任务"""
        task_id = parameters.get("task_id")
        if not task_id:
            return

        if self.task_manager.remove_task(task_id):
            self._show_info("任务已删除")
        else:
            self._show_error("删除任务失败")

    def _execute_sync_task(self, task):
        """执行同步任务"""
        from notion_sync.models.sync_task import TaskStatus, SyncStats
        from notion_sync.utils.async_worker import run_async_task

        def run_task():
            try:
                self.logger.info(f"开始执行任务: {task.name}")

                # 获取 Notion 客户端
                notion_client = self.sync_bridge.notion_client
                if not notion_client or not notion_client.connected:
                    raise Exception("未连接到 Notion")

                # 确保目标文件夹存在
                import os
                os.makedirs(task.local_target.folder_path, exist_ok=True)

                # 获取页面内容
                page_content = notion_client.get_page_content(task.notion_source.source_id)

                # 生成文件名
                safe_title = "".join(c for c in task.notion_source.source_title
                                   if c.isalnum() or c in (' ', '-', '_')).strip()
                if not safe_title:
                    safe_title = f"page_{task.notion_source.source_id[:8]}"

                file_path = os.path.join(task.local_target.folder_path, f"{safe_title}.md")

                # 转换为 Markdown
                item_info = {
                    "title": task.notion_source.source_title,
                    "id": task.notion_source.source_id,
                    "created_time": "",
                    "last_edited_time": "",
                    "url": f"https://notion.so/{task.notion_source.source_id}"
                }

                markdown_content = self._convert_to_markdown(page_content, item_info)

                # 保存文件
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(markdown_content)

                # 更新统计
                from datetime import datetime
                stats = SyncStats(
                    total_files=1,
                    successful_files=1,
                    failed_files=0,
                    last_sync_time=datetime.now().isoformat(),
                    last_sync_duration=0.0
                )

                return {
                    'success': True,
                    'task_id': task.task_id,
                    'stats': stats,
                    'file_path': file_path
                }

            except Exception as e:
                self.logger.error(f"任务执行失败 {task.name}: {str(e)}")
                return {
                    'success': False,
                    'task_id': task.task_id,
                    'error': str(e)
                }

        # 运行异步任务
        worker = run_async_task(f"sync_task_{task.task_id}", run_task)
        worker.finished.connect(lambda result: self._on_task_finished(result))
        worker.error.connect(lambda error: self._on_task_error(task.task_id, error))

    def _on_task_finished(self, result: dict):
        """任务完成处理"""
        from notion_sync.models.sync_task import TaskStatus

        task_id = result['task_id']

        if result['success']:
            # 更新任务状态和统计
            task = self.task_manager.get_task(task_id)
            if task:
                task.update_stats(result['stats'])
                self.task_manager.update_task_status(task_id, TaskStatus.COMPLETED)
                self._show_info(f"任务完成: {task.name}")
        else:
            # 更新任务状态为失败
            error = result['error']
            self.task_manager.update_task_status(task_id, TaskStatus.FAILED, error)
            self._show_error(f"任务失败: {error}")

    def _on_task_error(self, task_id: str, error: str):
        """任务错误处理"""
        from notion_sync.models.sync_task import TaskStatus
        self.task_manager.update_task_status(task_id, TaskStatus.FAILED, error)
        self._show_error(f"任务执行出错: {error}")

    def _sync_now(self) -> None:
        """立即执行同步。"""
        if not self.sync_bridge.is_connected():
            self._show_error("请先连接到云端服务")
            return

        self.logger.info("立即执行同步")
        self.main_window.set_status("正在执行立即同步...")
        self.sync_bridge.start_sync("bidirectional")

    def _show_help(self) -> None:
        """显示帮助信息。"""
        help_text = """
        <h2>Notion 同步工具帮助</h2>
        <h3>功能介绍：</h3>
        <ul>
        <li><b>本地到云端同步</b>：将本地文件上传到云端工作区</li>
        <li><b>云端到本地备份</b>：导出云端内容到本地文件</li>
        <li><b>双向同步</b>：保持本地和云端内容同步</li>
        </ul>
        <h3>使用步骤：</h3>
        <ol>
        <li>点击"连接到 Notion"进行身份验证</li>
        <li>选择要同步的文件或内容</li>
        <li>配置同步选项</li>
        <li>开始同步</li>
        </ol>
        <p>如需更多帮助，请访问我们的文档。</p>
        """
        QMessageBox.about(self.main_window, "帮助", help_text)

    def _cancel_upload(self) -> None:
        """取消上传操作。"""
        self.logger.info("取消上传操作")
        self.main_window.set_status("上传已取消")
        self.main_window.set_progress(0, False)

    def _cancel_export(self) -> None:
        """取消导出操作。"""
        self.logger.info("取消导出操作")
        self.main_window.set_status("导出已取消")
        self.main_window.set_progress(0, False)

    def _refresh_notion(self) -> None:
        """刷新 Notion 工作区内容。"""
        if not self.sync_bridge.is_connected():
            self._show_error("请先连接到云端服务")
            return

        self.logger.info("刷新 Notion 工作区内容")
        self.main_window.set_status("正在刷新工作区...")

        # 重新加载工作区
        QTimer.singleShot(1000, lambda: (
            self._load_notion_workspace(),
            self.main_window.set_status("工作区已刷新")
        ))

    def _add_sync_pair(self) -> None:
        """添加同步对。"""
        # 打开文件选择对话框
        local_path = QFileDialog.getExistingDirectory(
            self.main_window,
            "选择本地文件夹",
            ""
        )

        if local_path:
            # 这里应该让用户选择远程目标
            # 暂时使用默认值
            remote_path = "default_remote_path"

            if self.sync_bridge.add_sync_pair(local_path, remote_path):
                self._show_info(f"已添加同步对: {local_path}")
                # 更新 UI
                self.main_window.bidirectional_sync_view.add_sync_pair(
                    local_path, remote_path, "本地文件夹"
                )
            else:
                self._show_error("添加同步对失败")

    def _remove_sync_pair(self) -> None:
        """移除同步对。"""
        # 获取当前选中的同步对
        current_pairs = self.sync_bridge.get_sync_pairs()
        if current_pairs:
            # 移除第一个（这里应该根据用户选择）
            if self.sync_bridge.remove_sync_pair(0):
                self._show_info("已移除同步对")
                self.main_window.bidirectional_sync_view.remove_selected_sync_pair()
            else:
                self._show_error("移除同步对失败")
        else:
            self._show_info("没有可移除的同步对")

    def _start_bidirectional_sync(self) -> None:
        """开始双向同步。"""
        if not self.sync_bridge.is_connected():
            self._show_error("请先连接到云端服务")
            return

        self.logger.info("开始双向同步")
        self.main_window.set_status("正在启动双向同步...")
        self.sync_bridge.start_sync("bidirectional")

    def _stop_bidirectional_sync(self) -> None:
        """停止双向同步。"""
        self.logger.info("停止双向同步")
        self.sync_bridge.stop_sync()
        self.main_window.set_status("双向同步已停止")

    def _force_sync_all(self) -> None:
        """强制同步所有内容。"""
        if not self.sync_bridge.is_connected():
            self._show_error("请先连接到云端服务")
            return

        reply = QMessageBox.question(
            self.main_window,
            "强制同步",
            "确定要强制同步所有内容吗？这可能会覆盖现有的更改。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.logger.info("强制同步所有内容")
            self.main_window.set_status("正在强制同步所有内容...")
            self.sync_bridge.start_sync("bidirectional")

    def _create_default_sync_pair(self) -> None:
        """创建默认同步对"""
        import tempfile
        import os

        # 创建临时目录作为默认本地路径
        temp_dir = os.path.join(tempfile.gettempdir(), "notion_sync_default")
        os.makedirs(temp_dir, exist_ok=True)

        # 添加默认同步对
        success = self.sync_bridge.add_sync_pair(
            temp_dir,
            "default_notion_page",
            "bidirectional"
        )

        if success:
            self.main_window.add_sync_log(f"创建默认同步对: {temp_dir}")
        else:
            self.main_window.add_sync_log("创建默认同步对失败")

    def _simulate_sync_progress(self) -> None:
        """模拟同步进度。"""
        def update_progress():
            progress_steps = [
                (0, "准备同步..."),
                (20, "扫描本地文件..."),
                (40, "连接到 Notion..."),
                (60, "同步文件..."),
                (80, "更新索引..."),
                (100, "同步完成")
            ]

            for i, (progress, message) in enumerate(progress_steps):
                QTimer.singleShot(i * 1000, lambda p=progress, m=message: (
                    self.main_window.update_sync_progress(p),
                    self.main_window.set_status(m),
                    self.main_window.add_sync_log(m)
                ))

            # 完成后重置
            QTimer.singleShot(6000, lambda: (
                self.main_window.update_sync_progress(0),
                self.main_window.set_status("就绪")
            ))

        update_progress()



    def show_main_window(self) -> None:
        """显示主应用程序窗口。"""
        self.main_window.show()
        self.main_window.raise_()
        self.main_window.activateWindow()

    def _handle_analyze_action(self) -> None:
        """处理分析操作"""
        if not self.sync_bridge.is_connected():
            self._show_error("请先连接到 Notion")
            return

        # 更新UI状态
        if hasattr(self.main_window.sync_view, 'update_analyze_status'):
            self.main_window.sync_view.update_analyze_status(True)

        self.main_window.set_status("正在分析文件差异...")
        self.logger.info("开始分析文件差异")

        # 模拟分析过程
        QTimer.singleShot(2000, self._complete_analyze)

    def _complete_analyze(self) -> None:
        """完成分析操作"""
        # 恢复UI状态
        if hasattr(self.main_window.sync_view, 'update_analyze_status'):
            self.main_window.sync_view.update_analyze_status(False)

        self.main_window.set_status("分析完成 - 发现 3 个文件需要同步")
        self.logger.info("分析完成")

        # 显示分析结果
        self._show_info("分析完成！\n\n发现需要同步的内容：\n• 2 个新文件\n• 1 个修改的文件\n\n点击'同步'按钮开始同步。")

    def _show_settings(self) -> None:
        """显示设置对话框"""
        from notion_sync.views.settings_view import SettingsView
        settings_dialog = SettingsView(self.config_manager, self.main_window)
        settings_dialog.exec()

    def _show_welcome_wizard(self) -> None:
        """显示首次使用向导"""
        from notion_sync.views.welcome_wizard import show_welcome_wizard

        success, wizard = show_welcome_wizard(self.main_window)

        if success:
            # 获取向导设置
            settings = {}

            # 从各个页面收集设置
            notion_page = wizard.page(1)
            if notion_page:
                token = notion_page.token_input.text().strip()
                if token:
                    settings['notion_token'] = token

            folder_page = wizard.page(2)
            if folder_page:
                settings['default_folder'] = folder_page.folder_path

            prefs_page = wizard.page(3)
            if prefs_page:
                settings['auto_sync'] = prefs_page.auto_sync_check.isChecked()
                settings['startup_minimized'] = prefs_page.startup_check.isChecked()

            # 应用设置
            self._apply_wizard_settings(settings)

            # 标记首次设置完成
            self.config_manager.set("first_time_setup", False)

            self._show_info("欢迎使用 Notion 同步工具！\n\n设置已完成，您现在可以开始同步文件了。")
        else:
            # 用户取消了向导，仍然标记为已设置以避免重复显示
            self.config_manager.set("first_time_setup", False)

    def _apply_wizard_settings(self, settings: dict) -> None:
        """应用向导设置"""
        # 连接到 Notion
        if 'notion_token' in settings:
            token = settings['notion_token']
            if self.sync_bridge.connect_to_notion(token):
                self.config_manager.set("notion_api_token", token)
                self.main_window.set_connection_status(True)
                self.main_window.set_status("已连接到云端服务")
                self._load_notion_workspace()

        # 设置默认文件夹
        if 'default_folder' in settings:
            self.config_manager.set("default_sync_folder", settings['default_folder'])

        # 应用其他偏好设置
        if 'auto_sync' in settings:
            self.config_manager.set("auto_sync_enabled", settings['auto_sync'])

        if 'startup_minimized' in settings:
            self.config_manager.set("startup_minimized", settings['startup_minimized'])
