"""
任务管理主界面
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QToolBar, QFrame, QProgressBar, QMenu
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QFont, QAction, QIcon

from notion_sync.models.sync_task import SyncTask, TaskStatus
from notion_sync.services.task_manager import TaskManager
from notion_sync.resources.icons import get_icon


class TaskManagerView(QWidget):
    """任务管理主界面"""
    
    # 信号
    create_task_requested = Signal()
    edit_task_requested = Signal(str)  # task_id
    run_task_requested = Signal(str)   # task_id
    delete_task_requested = Signal(str) # task_id
    
    def __init__(self, task_manager: TaskManager, parent=None):
        super().__init__(parent)
        self.task_manager = task_manager
        self._setup_ui()
        self._apply_dark_theme()
        self._setup_connections()
        self._refresh_task_list()
    
    def _setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # 顶部标题和工具栏
        self._create_header(layout)
        
        # 任务统计
        self._create_stats_panel(layout)
        
        # 任务列表
        self._create_task_table(layout)
        
        # 底部操作栏
        self._create_bottom_panel(layout)
    
    def _create_header(self, parent_layout):
        """创建顶部标题和工具栏"""
        header_frame = QFrame()
        header_frame.setFrameStyle(QFrame.Shape.Box)
        header_layout = QVBoxLayout(header_frame)
        
        # 主标题
        title_label = QLabel("📋 同步任务管理")
        title_label.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(title_label)
        
        # 说明文字
        desc_label = QLabel("管理您的 Notion 同步任务 - 创建、配置和执行多个同步任务")
        desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc_label.setStyleSheet("color: #888888; font-size: 14px;")
        header_layout.addWidget(desc_label)
        
        # 工具栏
        toolbar_layout = QHBoxLayout()
        
        self.create_task_btn = QPushButton("➕ 创建新任务")
        self.create_task_btn.setMinimumHeight(40)
        self.create_task_btn.clicked.connect(self.create_task_requested.emit)
        toolbar_layout.addWidget(self.create_task_btn)
        
        self.refresh_btn = QPushButton("🔄 刷新")
        self.refresh_btn.clicked.connect(self._refresh_task_list)
        toolbar_layout.addWidget(self.refresh_btn)
        
        toolbar_layout.addStretch()
        
        self.import_btn = QPushButton("📥 导入任务")
        self.import_btn.clicked.connect(self._import_tasks)
        toolbar_layout.addWidget(self.import_btn)
        
        self.export_btn = QPushButton("📤 导出任务")
        self.export_btn.clicked.connect(self._export_tasks)
        toolbar_layout.addWidget(self.export_btn)
        
        header_layout.addLayout(toolbar_layout)
        parent_layout.addWidget(header_frame)
    
    def _create_stats_panel(self, parent_layout):
        """创建统计面板"""
        stats_frame = QFrame()
        stats_frame.setFrameStyle(QFrame.Shape.Box)
        stats_layout = QHBoxLayout(stats_frame)
        
        # 总任务数
        self.total_tasks_label = QLabel("📊 总任务: 0")
        self.total_tasks_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        stats_layout.addWidget(self.total_tasks_label)
        
        stats_layout.addStretch()
        
        # 运行中任务
        self.running_tasks_label = QLabel("🔄 运行中: 0")
        self.running_tasks_label.setStyleSheet("color: #4A90E2;")
        stats_layout.addWidget(self.running_tasks_label)
        
        stats_layout.addStretch()
        
        # 已完成任务
        self.completed_tasks_label = QLabel("✅ 已完成: 0")
        self.completed_tasks_label.setStyleSheet("color: #4CAF50;")
        stats_layout.addWidget(self.completed_tasks_label)
        
        stats_layout.addStretch()
        
        # 失败任务
        self.failed_tasks_label = QLabel("❌ 失败: 0")
        self.failed_tasks_label.setStyleSheet("color: #FF6B6B;")
        stats_layout.addWidget(self.failed_tasks_label)
        
        parent_layout.addWidget(stats_frame)
    
    def _create_task_table(self, parent_layout):
        """创建任务表格"""
        self.task_table = QTableWidget()
        self.task_table.setColumnCount(7)
        self.task_table.setHorizontalHeaderLabels([
            "任务名称", "Notion 源", "本地文件夹", "状态", "最后同步", "操作", "详情"
        ])
        
        # 设置表格属性
        self.task_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.task_table.setAlternatingRowColors(True)
        self.task_table.setSortingEnabled(True)
        
        # 设置列宽
        header = self.task_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)  # 任务名称
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)  # Notion 源
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)  # 本地文件夹
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)  # 状态
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)  # 最后同步
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)  # 操作
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)  # 详情
        
        parent_layout.addWidget(self.task_table)
    
    def _create_bottom_panel(self, parent_layout):
        """创建底部面板"""
        bottom_frame = QFrame()
        bottom_frame.setFrameStyle(QFrame.Shape.Box)
        bottom_layout = QVBoxLayout(bottom_frame)
        
        # 全局操作按钮
        actions_layout = QHBoxLayout()
        
        self.run_all_btn = QPushButton("🚀 运行所有任务")
        self.run_all_btn.clicked.connect(self._run_all_tasks)
        actions_layout.addWidget(self.run_all_btn)
        
        self.stop_all_btn = QPushButton("⏹️ 停止所有任务")
        self.stop_all_btn.clicked.connect(self._stop_all_tasks)
        actions_layout.addWidget(self.stop_all_btn)
        
        actions_layout.addStretch()
        
        self.clear_completed_btn = QPushButton("🗑️ 清理已完成")
        self.clear_completed_btn.clicked.connect(self._clear_completed_tasks)
        actions_layout.addWidget(self.clear_completed_btn)
        
        bottom_layout.addLayout(actions_layout)
        
        # 状态栏
        self.status_label = QLabel("💡 提示：创建新任务开始同步您的 Notion 内容")
        self.status_label.setStyleSheet("color: #4A90E2; font-weight: bold; padding: 10px;")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        bottom_layout.addWidget(self.status_label)
        
        parent_layout.addWidget(bottom_frame)
    
    def _apply_dark_theme(self):
        """应用暗黑主题"""
        dark_style = """
        QWidget {
            background-color: #2b2b2b;
            color: #ffffff;
        }
        
        QFrame {
            background-color: #3c3c3c;
            border: 1px solid #555555;
            border-radius: 8px;
        }
        
        QLabel {
            color: #ffffff;
        }
        
        QPushButton {
            background-color: #007AFF;
            color: white;
            border: none;
            border-radius: 6px;
            padding: 10px 20px;
            font-weight: 500;
            font-size: 14px;
        }
        
        QPushButton:hover {
            background-color: #0056CC;
        }
        
        QPushButton:pressed {
            background-color: #004499;
        }
        
        QPushButton:disabled {
            background-color: #555555;
            color: #888888;
        }
        
        QTableWidget {
            background-color: #2b2b2b;
            border: 1px solid #555555;
            border-radius: 4px;
            color: #ffffff;
            gridline-color: #444444;
        }
        
        QTableWidget::item {
            padding: 8px;
            border-bottom: 1px solid #444444;
        }
        
        QTableWidget::item:selected {
            background-color: #007AFF;
            color: white;
        }
        
        QTableWidget::item:hover {
            background-color: #4c4c4c;
        }
        
        QHeaderView::section {
            background-color: #3c3c3c;
            color: #ffffff;
            padding: 8px;
            border: 1px solid #555555;
            font-weight: bold;
        }
        """
        self.setStyleSheet(dark_style)
    
    def _setup_connections(self):
        """设置信号连接"""
        # 连接任务管理器信号
        self.task_manager.task_added.connect(self._on_task_added)
        self.task_manager.task_updated.connect(self._on_task_updated)
        self.task_manager.task_removed.connect(self._on_task_removed)
        self.task_manager.task_status_changed.connect(self._on_task_status_changed)
    
    def _refresh_task_list(self):
        """刷新任务列表"""
        tasks = self.task_manager.get_all_tasks()
        
        # 清空表格
        self.task_table.setRowCount(0)
        
        # 添加任务行
        for task in tasks:
            self._add_task_row(task)
        
        # 更新统计
        self._update_stats()
    
    def _add_task_row(self, task: SyncTask):
        """添加任务行"""
        row = self.task_table.rowCount()
        self.task_table.insertRow(row)
        
        # 任务名称
        name_item = QTableWidgetItem(task.name)
        name_item.setData(Qt.ItemDataRole.UserRole, task.task_id)
        self.task_table.setItem(row, 0, name_item)
        
        # Notion 源
        source_text = f"{task.notion_source.source_title} ({task.notion_source.source_type})"
        self.task_table.setItem(row, 1, QTableWidgetItem(source_text))
        
        # 本地文件夹
        self.task_table.setItem(row, 2, QTableWidgetItem(task.local_target.folder_path))
        
        # 状态
        status_item = QTableWidgetItem(task.get_status_display())
        status_item.setData(Qt.ItemDataRole.UserRole, task.status.value)
        self.task_table.setItem(row, 3, status_item)
        
        # 最后同步时间
        last_sync = task.stats.last_sync_time or "从未同步"
        self.task_table.setItem(row, 4, QTableWidgetItem(last_sync))
        
        # 操作按钮
        self._create_action_buttons(row, task)
        
        # 详情按钮
        details_btn = QPushButton("📊 详情")
        details_btn.clicked.connect(lambda: self._show_task_details(task.task_id))
        self.task_table.setCellWidget(row, 6, details_btn)
    
    def _create_action_buttons(self, row: int, task: SyncTask):
        """创建操作按钮"""
        actions_widget = QWidget()
        actions_layout = QHBoxLayout(actions_widget)
        actions_layout.setContentsMargins(5, 5, 5, 5)
        
        # 运行按钮
        if task.status in [TaskStatus.CREATED, TaskStatus.COMPLETED, TaskStatus.FAILED]:
            run_btn = QPushButton("▶️")
            run_btn.setToolTip("运行任务")
            run_btn.clicked.connect(lambda: self.run_task_requested.emit(task.task_id))
            actions_layout.addWidget(run_btn)
        
        # 编辑按钮
        edit_btn = QPushButton("✏️")
        edit_btn.setToolTip("编辑任务")
        edit_btn.clicked.connect(lambda: self.edit_task_requested.emit(task.task_id))
        actions_layout.addWidget(edit_btn)
        
        # 删除按钮
        delete_btn = QPushButton("🗑️")
        delete_btn.setToolTip("删除任务")
        delete_btn.clicked.connect(lambda: self._confirm_delete_task(task.task_id))
        actions_layout.addWidget(delete_btn)
        
        self.task_table.setCellWidget(row, 5, actions_widget)
    
    def _update_stats(self):
        """更新统计信息"""
        summary = self.task_manager.get_status_summary()
        total = self.task_manager.get_task_count()
        
        self.total_tasks_label.setText(f"📊 总任务: {total}")
        self.running_tasks_label.setText(f"🔄 运行中: {summary.get('running', 0)}")
        self.completed_tasks_label.setText(f"✅ 已完成: {summary.get('completed', 0)}")
        self.failed_tasks_label.setText(f"❌ 失败: {summary.get('failed', 0)}")
    
    def _on_task_added(self, task: SyncTask):
        """任务添加事件"""
        self._refresh_task_list()
        self.status_label.setText(f"✅ 已添加新任务: {task.name}")
    
    def _on_task_updated(self, task: SyncTask):
        """任务更新事件"""
        self._refresh_task_list()
    
    def _on_task_removed(self, task_id: str):
        """任务删除事件"""
        self._refresh_task_list()
        self.status_label.setText("🗑️ 任务已删除")
    
    def _on_task_status_changed(self, task_id: str, status: TaskStatus):
        """任务状态改变事件"""
        self._refresh_task_list()
    
    def _confirm_delete_task(self, task_id: str):
        """确认删除任务"""
        task = self.task_manager.get_task(task_id)
        if not task:
            return
        
        reply = QMessageBox.question(
            self,
            "确认删除",
            f"确定要删除任务 '{task.name}' 吗？\n\n此操作无法撤销。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.delete_task_requested.emit(task_id)
    
    def _show_task_details(self, task_id: str):
        """显示任务详情"""
        task = self.task_manager.get_task(task_id)
        if not task:
            return
        
        # 这里可以打开任务详情对话框
        details_text = f"""
任务详情：{task.name}

Notion 源：
- 类型：{task.notion_source.source_type}
- 标题：{task.notion_source.source_title}
- ID：{task.notion_source.source_id}

本地目标：
- 文件夹：{task.local_target.folder_path}
- 格式：{task.local_target.file_format}

同步统计：
- 总文件：{task.stats.total_files}
- 成功：{task.stats.successful_files}
- 失败：{task.stats.failed_files}
- 最后同步：{task.stats.last_sync_time or '从未同步'}

创建时间：{task.created_time}
最后修改：{task.last_modified}
        """
        
        QMessageBox.information(self, "任务详情", details_text)
    
    def _run_all_tasks(self):
        """运行所有任务"""
        tasks = self.task_manager.get_all_tasks()
        for task in tasks:
            if task.status in [TaskStatus.CREATED, TaskStatus.COMPLETED, TaskStatus.FAILED]:
                self.run_task_requested.emit(task.task_id)
    
    def _stop_all_tasks(self):
        """停止所有任务"""
        # 这里实现停止逻辑
        self.status_label.setText("⏹️ 正在停止所有任务...")
    
    def _clear_completed_tasks(self):
        """清理已完成任务"""
        completed_tasks = self.task_manager.get_tasks_by_status(TaskStatus.COMPLETED)
        if not completed_tasks:
            QMessageBox.information(self, "提示", "没有已完成的任务需要清理。")
            return
        
        reply = QMessageBox.question(
            self,
            "确认清理",
            f"确定要清理 {len(completed_tasks)} 个已完成的任务吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            for task in completed_tasks:
                self.task_manager.remove_task(task.task_id)
    
    def _import_tasks(self):
        """导入任务"""
        from PySide6.QtWidgets import QFileDialog
        
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "导入任务配置",
            "",
            "JSON 文件 (*.json)"
        )
        
        if file_path:
            if self.task_manager.import_tasks(file_path):
                QMessageBox.information(self, "成功", "任务配置导入成功！")
            else:
                QMessageBox.warning(self, "失败", "任务配置导入失败！")
    
    def _export_tasks(self):
        """导出任务"""
        from PySide6.QtWidgets import QFileDialog
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "导出任务配置",
            "sync_tasks.json",
            "JSON 文件 (*.json)"
        )
        
        if file_path:
            if self.task_manager.export_tasks(file_path):
                QMessageBox.information(self, "成功", "任务配置导出成功！")
            else:
                QMessageBox.warning(self, "失败", "任务配置导出失败！")


class CreateTaskDialog(QWidget):
    """创建新任务对话框 - 现代化设计"""

    task_created = Signal(dict)  # 任务配置数据

    def __init__(self, notion_workspace_data: dict, parent=None):
        super().__init__(parent)
        self.notion_workspace_data = notion_workspace_data
        self.selected_local_folder = ""
        self.selected_items = []
        self._setup_ui()
        self._apply_modern_theme()

    def _setup_ui(self):
        """设置现代化UI"""
        self.setWindowTitle("创建新同步任务")
        self.setMinimumSize(1000, 700)
        self.setMaximumSize(1200, 800)

        # 设置窗口属性
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.WindowCloseButtonHint)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 顶部标题栏
        self._create_header(main_layout)

        # 主要内容区域
        self._create_main_content(main_layout)

        # 底部操作栏
        self._create_footer(main_layout)

    def _create_header(self, parent_layout):
        """创建顶部标题栏"""
        header = QFrame()
        header.setFixedHeight(80)
        header.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #667eea, stop:1 #764ba2);
                border: none;
                border-radius: 0px;
            }
        """)

        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(30, 20, 30, 20)

        # 图标和标题
        icon_label = QLabel("🚀")
        icon_label.setFont(QFont("Arial", 24))
        header_layout.addWidget(icon_label)

        title_layout = QVBoxLayout()
        title_layout.setSpacing(2)

        title_label = QLabel("创建新的同步任务")
        title_label.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        title_label.setStyleSheet("color: white;")
        title_layout.addWidget(title_label)

        subtitle_label = QLabel("选择 Notion 内容并配置本地保存位置")
        subtitle_label.setFont(QFont("Arial", 12))
        subtitle_label.setStyleSheet("color: rgba(255, 255, 255, 0.8);")
        title_layout.addWidget(subtitle_label)

        header_layout.addLayout(title_layout)
        header_layout.addStretch()

        # 关闭按钮
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(30, 30)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.2);
                border: none;
                border-radius: 15px;
                color: white;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.3);
            }
        """)
        close_btn.clicked.connect(self.close)
        header_layout.addWidget(close_btn)

        parent_layout.addWidget(header)

    def _create_main_content(self, parent_layout):
        """创建主要内容区域"""
        content_widget = QWidget()
        content_widget.setStyleSheet("background-color: #f8f9fa;")

        content_layout = QHBoxLayout(content_widget)
        content_layout.setContentsMargins(30, 30, 30, 30)
        content_layout.setSpacing(30)

        # 左侧：Notion 内容选择
        self._create_notion_panel(content_layout)

        # 右侧：任务配置
        self._create_config_panel(content_layout)

        parent_layout.addWidget(content_widget)

    def _create_footer(self, parent_layout):
        """创建底部操作栏"""
        footer = QFrame()
        footer.setFixedHeight(80)
        footer.setStyleSheet("""
            QFrame {
                background-color: white;
                border-top: 1px solid #e9ecef;
            }
        """)

        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(30, 20, 30, 20)

        # 进度指示
        self.progress_label = QLabel("步骤 1/3：选择 Notion 内容")
        self.progress_label.setFont(QFont("Arial", 12))
        self.progress_label.setStyleSheet("color: #6c757d;")
        footer_layout.addWidget(self.progress_label)

        footer_layout.addStretch()

        # 按钮组
        button_layout = QHBoxLayout()
        button_layout.setSpacing(15)

        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.setFixedSize(100, 40)
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
                border: none;
                border-radius: 20px;
                font-size: 14px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #5a6268;
            }
        """)
        self.cancel_btn.clicked.connect(self.close)
        button_layout.addWidget(self.cancel_btn)

        self.create_btn = QPushButton("创建任务")
        self.create_btn.setFixedSize(120, 40)
        self.create_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #28a745, stop:1 #20c997);
                color: white;
                border: none;
                border-radius: 20px;
                font-size: 14px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #218838, stop:1 #1ea085);
            }
            QPushButton:disabled {
                background-color: #adb5bd;
            }
        """)
        self.create_btn.clicked.connect(self._create_task)
        self.create_btn.setEnabled(False)
        button_layout.addWidget(self.create_btn)

        footer_layout.addLayout(button_layout)

        parent_layout.addWidget(footer)

    def _create_notion_selection(self, parent_layout):
        """创建 Notion 内容选择区域"""
        notion_frame = QFrame()
        notion_frame.setFrameStyle(QFrame.Shape.Box)
        notion_layout = QVBoxLayout(notion_frame)

        # 标题
        title_label = QLabel("📄 选择 Notion 内容")
        title_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        notion_layout.addWidget(title_label)

        # Notion 内容树
        self.notion_tree = QTableWidget()
        self.notion_tree.setColumnCount(3)
        self.notion_tree.setHorizontalHeaderLabels(["选择", "名称", "类型"])
        self.notion_tree.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)

        # 填充 Notion 内容
        self._populate_notion_content()

        notion_layout.addWidget(self.notion_tree)

        parent_layout.addWidget(notion_frame)

    def _create_task_config(self, parent_layout):
        """创建任务配置区域"""
        config_frame = QFrame()
        config_frame.setFrameStyle(QFrame.Shape.Box)
        config_layout = QVBoxLayout(config_frame)

        # 标题
        title_label = QLabel("⚙️ 任务配置")
        title_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        config_layout.addWidget(title_label)

        # 任务名称
        from PySide6.QtWidgets import QLineEdit
        name_label = QLabel("任务名称：")
        config_layout.addWidget(name_label)

        self.task_name_input = QLineEdit()
        self.task_name_input.setPlaceholderText("输入任务名称...")
        config_layout.addWidget(self.task_name_input)

        # 本地文件夹选择
        folder_label = QLabel("本地保存文件夹：")
        config_layout.addWidget(folder_label)

        folder_layout = QHBoxLayout()
        self.folder_display = QLabel("未选择文件夹")
        self.folder_display.setStyleSheet("""
            padding: 10px;
            border: 1px solid #555555;
            border-radius: 4px;
            background-color: #3c3c3c;
        """)
        folder_layout.addWidget(self.folder_display)

        self.select_folder_btn = QPushButton("📂 选择")
        self.select_folder_btn.clicked.connect(self._select_folder)
        folder_layout.addWidget(self.select_folder_btn)

        config_layout.addLayout(folder_layout)

        # 同步选项
        options_label = QLabel("同步选项：")
        config_layout.addWidget(options_label)

        from PySide6.QtWidgets import QCheckBox
        self.include_children_check = QCheckBox("包含子页面")
        self.include_children_check.setChecked(True)
        config_layout.addWidget(self.include_children_check)

        self.auto_sync_check = QCheckBox("启用自动同步")
        config_layout.addWidget(self.auto_sync_check)

        config_layout.addStretch()

        parent_layout.addWidget(config_frame)

    def _create_buttons(self, parent_layout):
        """创建底部按钮"""
        button_layout = QHBoxLayout()

        button_layout.addStretch()

        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self.close)
        button_layout.addWidget(self.cancel_btn)

        self.create_btn = QPushButton("创建任务")
        self.create_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50 !important;
                color: white !important;
                font-weight: bold;
                padding: 12px 24px;
            }
            QPushButton:hover {
                background-color: #45A049 !important;
            }
        """)
        self.create_btn.clicked.connect(self._create_task)
        button_layout.addWidget(self.create_btn)

        parent_layout.addLayout(button_layout)

    def _populate_notion_content(self):
        """填充 Notion 内容"""
        self.notion_tree.setRowCount(0)

        # 添加页面
        pages = self.notion_workspace_data.get("pages", [])
        for page in pages:
            self._add_notion_item(page, "page")

        # 添加数据库
        databases = self.notion_workspace_data.get("databases", [])
        for db in databases:
            self._add_notion_item(db, "database")

    def _add_notion_item(self, item, item_type: str):
        """添加 Notion 项目到表格"""
        row = self.notion_tree.rowCount()
        self.notion_tree.insertRow(row)

        # 选择框
        from PySide6.QtWidgets import QCheckBox
        checkbox = QCheckBox()

        # 处理不同类型的 item 对象
        if hasattr(item, 'title'):
            # NotionPage 或 NotionDatabase 对象
            item_data = {
                "id": item.id,
                "title": item.title,
                "url": getattr(item, 'url', ''),
                "created_time": getattr(item, 'created_time', ''),
                "last_edited_time": getattr(item, 'last_edited_time', '')
            }
            title = item.title
        elif isinstance(item, dict):
            # 字典对象
            item_data = item
            title = item.get("title", "无标题")
        else:
            # 其他情况
            item_data = {"id": str(item), "title": "无标题"}
            title = "无标题"

        checkbox.setProperty("item_data", item_data)
        checkbox.setProperty("item_type", item_type)
        self.notion_tree.setCellWidget(row, 0, checkbox)

        # 名称
        self.notion_tree.setItem(row, 1, QTableWidgetItem(title))

        # 类型
        type_text = "📄 页面" if item_type == "page" else "🗃️ 数据库"
        self.notion_tree.setItem(row, 2, QTableWidgetItem(type_text))

    def _select_folder(self):
        """选择本地文件夹"""
        from PySide6.QtWidgets import QFileDialog

        folder = QFileDialog.getExistingDirectory(self, "选择保存文件夹")
        if folder:
            self.selected_local_folder = folder
            self.folder_display.setText(folder)
            self.folder_display.setStyleSheet("""
                padding: 10px;
                border: 1px solid #4CAF50;
                border-radius: 4px;
                background-color: #3c3c3c;
                color: #4CAF50;
            """)

    def _create_task(self):
        """创建任务"""
        # 验证输入
        task_name = self.task_name_input.text().strip()
        if not task_name:
            QMessageBox.warning(self, "错误", "请输入任务名称！")
            return

        if not self.selected_local_folder:
            QMessageBox.warning(self, "错误", "请选择本地文件夹！")
            return

        # 获取选中的 Notion 项目
        selected_items = []
        for row in range(self.notion_tree.rowCount()):
            checkbox = self.notion_tree.cellWidget(row, 0)
            if checkbox.isChecked():
                item_data = checkbox.property("item_data")
                item_type = checkbox.property("item_type")
                selected_items.append({
                    "data": item_data,
                    "type": item_type
                })

        if not selected_items:
            QMessageBox.warning(self, "错误", "请至少选择一个 Notion 项目！")
            return

        # 创建任务配置
        task_config = {
            "name": task_name,
            "local_folder": self.selected_local_folder,
            "notion_items": selected_items,
            "include_children": self.include_children_check.isChecked(),
            "auto_sync": self.auto_sync_check.isChecked()
        }

        # 发送信号
        self.task_created.emit(task_config)
        self.close()

    def _apply_dark_theme(self):
        """应用暗黑主题"""
        dark_style = """
        QWidget {
            background-color: #2b2b2b;
            color: #ffffff;
        }

        QFrame {
            background-color: #3c3c3c;
            border: 1px solid #555555;
            border-radius: 8px;
        }

        QLabel {
            color: #ffffff;
        }

        QPushButton {
            background-color: #007AFF;
            color: white;
            border: none;
            border-radius: 6px;
            padding: 10px 20px;
            font-weight: 500;
            font-size: 14px;
        }

        QPushButton:hover {
            background-color: #0056CC;
        }

        QLineEdit {
            background-color: #3c3c3c;
            border: 1px solid #555555;
            border-radius: 4px;
            padding: 8px;
            color: #ffffff;
        }

        QTableWidget {
            background-color: #2b2b2b;
            border: 1px solid #555555;
            border-radius: 4px;
            color: #ffffff;
            gridline-color: #444444;
        }

        QTableWidget::item {
            padding: 8px;
            border-bottom: 1px solid #444444;
        }

        QCheckBox {
            color: #ffffff;
        }

        QCheckBox::indicator {
            width: 18px;
            height: 18px;
        }

        QCheckBox::indicator:unchecked {
            border: 2px solid #555555;
            background-color: #3c3c3c;
            border-radius: 3px;
        }

        QCheckBox::indicator:checked {
            border: 2px solid #007AFF;
            background-color: #007AFF;
            border-radius: 3px;
        }
        """
        self.setStyleSheet(dark_style)
