"""
GoodSync 风格的同步界面
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QFileDialog, QTreeWidget, QTreeWidgetItem,
    QComboBox, QProgressBar
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QFont
from notion_sync.resources.icons import get_icon, get_status_icon
from notion_sync.utils.async_worker import run_async_task, LoadingIndicator, file_loader


class GoodSyncStyleView(QWidget):
    """GoodSync 风格的同步界面"""
    
    action_requested = Signal(str, dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._setup_connections()

        # 初始化加载指示器
        self.loading_indicator = LoadingIndicator(self)

        # 缓存数据
        self._cached_local_files = []
        self._cached_notion_data = {}
    
    def _setup_ui(self):
        """设置 GoodSync 风格界面"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 工具栏
        self._create_toolbar(layout)
        
        # 主同步区域
        self._create_main_area(layout)
        
        # 底部状态栏
        self._create_status_bar(layout)
    
    def _create_toolbar(self, layout):
        """创建工具栏 - 暗黑主题"""
        toolbar_frame = QFrame()
        toolbar_frame.setStyleSheet("""
        QFrame {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #3C3C3C, stop:1 #2D2D2D);
            border-bottom: 1px solid #1E1E1E;
            min-height: 60px;
        }
        """)
        
        toolbar_layout = QHBoxLayout(toolbar_frame)
        toolbar_layout.setContentsMargins(10, 5, 10, 5)
        toolbar_layout.setSpacing(5)
        
        # 左侧按钮组
        self._create_toolbar_buttons(toolbar_layout)
        
        # 中间弹簧
        toolbar_layout.addStretch()
        
        # 右侧连接状态
        self._create_connection_status(toolbar_layout)
        
        layout.addWidget(toolbar_frame)
    
    def _create_toolbar_buttons(self, layout):
        """创建工具栏按钮"""
        # 分析按钮
        self.analyze_btn = QPushButton("分析")
        self.analyze_btn.setIcon(get_icon('analyze'))
        self.analyze_btn.setToolTip("分析本地文件和 Notion 页面的差异，检查需要同步的内容")
        self.analyze_btn.setStyleSheet(self._get_toolbar_button_style())
        self.analyze_btn.setMinimumSize(60, 40)
        layout.addWidget(self.analyze_btn)

        # 导出按钮（云端到本地）
        self.export_btn = QPushButton("导出")
        self.export_btn.setIcon(get_icon('download'))
        self.export_btn.setToolTip("将选中的 Notion 内容导出到本地文件夹")
        self.export_btn.setStyleSheet(self._get_toolbar_button_style())
        self.export_btn.setMinimumSize(60, 40)
        layout.addWidget(self.export_btn)

        # 分隔符
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.VLine)
        separator.setStyleSheet("color: #555555;")
        layout.addWidget(separator)

        # 选项按钮
        self.options_btn = QPushButton("选项")
        self.options_btn.setIcon(get_icon('settings'))
        self.options_btn.setToolTip("打开设置和配置选项")
        self.options_btn.setStyleSheet(self._get_toolbar_button_style())
        self.options_btn.setMinimumSize(60, 40)
        layout.addWidget(self.options_btn)
    
    def _create_connection_status(self, layout):
        """创建连接状态显示"""
        # 连接状态标签
        self.connection_label = QLabel("未连接到 Notion")
        self.connection_label.setStyleSheet("""
        QLabel {
            color: #CCCCCC;
            font-size: 12px;
            padding: 5px;
        }
        """)
        layout.addWidget(self.connection_label)
        
        # 连接按钮
        self.connect_btn = QPushButton("连接")
        self.connect_btn.setIcon(get_icon('connect'))
        self.connect_btn.setToolTip("连接或断开与 Notion 的连接")
        self.connect_btn.setStyleSheet(self._get_toolbar_button_style())
        self.connect_btn.setMinimumSize(60, 40)
        layout.addWidget(self.connect_btn)
    
    def _create_main_area(self, layout):
        """创建主同步区域 - 暗黑主题的左右布局"""
        main_frame = QFrame()
        main_frame.setStyleSheet("""
        QFrame {
            background: #2D2D2D;
            border: none;
        }
        """)
        
        main_layout = QHBoxLayout(main_frame)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 左侧面板 - 本地文件
        left_panel = self._create_folder_panel("本地文件夹", True)
        main_layout.addWidget(left_panel, 1)
        
        # 中间同步控制区域
        center_panel = self._create_sync_control_panel()
        main_layout.addWidget(center_panel)
        
        # 右侧面板 - Notion
        right_panel = self._create_folder_panel("Notion 工作区", False)
        main_layout.addWidget(right_panel, 1)
        
        layout.addWidget(main_frame)
    
    def _create_folder_panel(self, title, is_local):
        """创建文件夹面板 - 暗黑主题"""
        panel = QFrame()
        panel.setStyleSheet("""
        QFrame {
            background: #1E1E1E;
            border: 1px solid #404040;
        }
        """)
        
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        
        # 标题栏
        title_frame = QFrame()
        title_frame.setStyleSheet("""
        QFrame {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #404040, stop:1 #353535);
            border: 1px solid #555555;
            min-height: 30px;
        }
        """)
        
        title_layout = QHBoxLayout(title_frame)
        title_layout.setContentsMargins(10, 5, 10, 5)
        
        title_label = QLabel(title)
        title_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        title_label.setStyleSheet("color: #FFFFFF;")
        title_layout.addWidget(title_label)
        
        title_layout.addStretch()
        
        # 选择按钮
        if is_local:
            select_btn = QPushButton("选择文件夹")
            select_btn.setIcon(get_icon('folder'))
            select_btn.setToolTip("选择要同步的本地文件夹")
            select_btn.clicked.connect(self._select_local_folder)
        else:
            select_btn = QPushButton("刷新")
            select_btn.setIcon(get_icon('refresh'))
            select_btn.setToolTip("刷新 Notion 工作区内容")
            select_btn.clicked.connect(self._refresh_notion)

        select_btn.setStyleSheet(self._get_small_button_style())
        title_layout.addWidget(select_btn)
        
        layout.addWidget(title_frame)
        
        # 文件列表
        if is_local:
            self.local_tree = QTreeWidget()
            self.local_tree.setHeaderLabel("文件")
            self.local_tree.setStyleSheet("""
            QTreeWidget {
                background: #1E1E1E;
                color: #FFFFFF;
                border: 1px solid #404040;
                selection-background-color: #4A90E2;
            }
            QTreeWidget::item {
                padding: 3px;
            }
            QTreeWidget::item:hover {
                background: #404040;
            }
            QHeaderView::section {
                background: #353535;
                color: #FFFFFF;
                border: 1px solid #555555;
                padding: 5px;
            }
            """)
            layout.addWidget(self.local_tree)
        else:
            self.notion_tree = QTreeWidget()
            self.notion_tree.setHeaderLabel("页面和数据库")
            self.notion_tree.setStyleSheet("""
            QTreeWidget {
                background: #1E1E1E;
                color: #FFFFFF;
                border: 1px solid #404040;
                selection-background-color: #4A90E2;
            }
            QTreeWidget::item {
                padding: 3px;
            }
            QTreeWidget::item:hover {
                background: #404040;
            }
            QHeaderView::section {
                background: #353535;
                color: #FFFFFF;
                border: 1px solid #555555;
                padding: 5px;
            }
            """)
            layout.addWidget(self.notion_tree)
        
        return panel
    
    def _create_sync_control_panel(self):
        """创建中间同步控制面板 - 暗黑主题"""
        panel = QFrame()
        panel.setStyleSheet("""
        QFrame {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #2D2D2D, stop:1 #252525);
            border: 1px solid #404040;
            min-width: 200px;
            max-width: 200px;
        }
        """)
        
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 20, 10, 20)
        layout.setSpacing(15)
        
        # 导出说明
        direction_label = QLabel("导出方向")
        direction_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        direction_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        direction_label.setStyleSheet("color: #FFFFFF;")
        layout.addWidget(direction_label)

        # 固定方向说明
        direction_info = QLabel("Notion → 本地")
        direction_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        direction_info.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        direction_info.setStyleSheet("""
            color: #4A90E2;
            background: #1E1E1E;
            padding: 8px;
            border: 1px solid #555555;
            border-radius: 3px;
        """)
        layout.addWidget(direction_info)
        
        layout.addStretch()
        
        # 导出箭头图标区域
        arrow_label = QLabel("⬇")
        arrow_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        arrow_label.setFont(QFont("Arial", 32))
        arrow_label.setStyleSheet("color: #4A90E2;")
        layout.addWidget(arrow_label)
        
        layout.addStretch()
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("""
        QProgressBar {
            background: #1E1E1E;
            color: #FFFFFF;
            border: 1px solid #555555;
            border-radius: 3px;
            text-align: center;
        }
        QProgressBar::chunk {
            background-color: #4A90E2;
            border-radius: 2px;
        }
        """)
        layout.addWidget(self.progress_bar)
        
        return panel
    
    def _create_status_bar(self, layout):
        """创建底部状态栏 - 暗黑主题"""
        status_frame = QFrame()
        status_frame.setStyleSheet("""
        QFrame {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #2D2D2D, stop:1 #1E1E1E);
            border-top: 1px solid #404040;
            min-height: 25px;
            max-height: 25px;
        }
        """)
        
        status_layout = QHBoxLayout(status_frame)
        status_layout.setContentsMargins(10, 3, 10, 3)
        
        self.status_label = QLabel("就绪")
        self.status_label.setStyleSheet("color: #CCCCCC; font-size: 11px;")
        status_layout.addWidget(self.status_label)
        
        status_layout.addStretch()
        
        layout.addWidget(status_frame)
    
    def _get_toolbar_button_style(self):
        """工具栏按钮样式 - 暗黑主题"""
        return """
        QPushButton {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #404040, stop:1 #353535);
            color: #FFFFFF;
            border: 1px solid #555555;
            border-radius: 3px;
            padding: 5px 10px;
            font-size: 11px;
        }
        QPushButton:hover {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #4A90E2, stop:1 #357ABD);
            border: 1px solid #4A90E2;
        }
        QPushButton:pressed {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #357ABD, stop:1 #2E6DA4);
        }
        """
    
    def _get_small_button_style(self):
        """小按钮样式 - 暗黑主题"""
        return """
        QPushButton {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #404040, stop:1 #353535);
            color: #FFFFFF;
            border: 1px solid #555555;
            border-radius: 2px;
            padding: 3px 8px;
            font-size: 10px;
        }
        QPushButton:hover {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #4A90E2, stop:1 #357ABD);
            border: 1px solid #4A90E2;
        }
        """
    
    def _setup_connections(self):
        """设置信号连接"""
        self.analyze_btn.clicked.connect(lambda: self.action_requested.emit("analyze", {}))
        self.export_btn.clicked.connect(lambda: self.action_requested.emit("export_to_local", {}))
        self.connect_btn.clicked.connect(lambda: self.action_requested.emit("connect_notion", {}))
        self.options_btn.clicked.connect(lambda: self.action_requested.emit("show_options", {}))
    
    def _select_local_folder(self):
        """选择本地文件夹"""
        folder = QFileDialog.getExistingDirectory(self, "选择本地文件夹")
        if folder:
            self._load_local_folder_async(folder)

    def _load_local_folder_async(self, folder_path: str):
        """异步加载本地文件夹"""
        # 开始加载动画
        self.loading_indicator.start_loading("正在扫描文件夹")

        # 异步加载文件列表
        def load_files():
            import os
            files = []
            try:
                for root, dirs, filenames in os.walk(folder_path):
                    # 限制扫描深度避免卡顿
                    level = root.replace(folder_path, '').count(os.sep)
                    if level >= 3:  # 最多3层深度
                        dirs[:] = []  # 不再深入子目录
                        continue

                    for filename in filenames:
                        if filename.startswith('.'):  # 跳过隐藏文件
                            continue

                        file_path = os.path.join(root, filename)
                        try:
                            file_info = {
                                'name': filename,
                                'path': file_path,
                                'size': os.path.getsize(file_path),
                                'type': self._get_file_type(filename)
                            }
                            files.append(file_info)
                        except (OSError, IOError):
                            continue  # 跳过无法访问的文件

                return files
            except Exception as e:
                raise Exception(f"扫描文件夹失败: {str(e)}")

        # 运行异步任务
        worker = run_async_task("load_local_folder", load_files)
        worker.finished.connect(lambda files: self._on_local_files_loaded(folder_path, files))
        worker.error.connect(lambda error: self._on_loading_error("加载本地文件夹失败", error))

    def _on_local_files_loaded(self, folder_path: str, files: list):
        """本地文件加载完成"""
        self.loading_indicator.stop_loading()
        self._cached_local_files = files

        # 更新UI
        self._update_local_file_tree(files)
        self.set_status(f"已加载 {len(files)} 个文件 - {folder_path}")

        # 发送信号
        self.action_requested.emit("load_directory", {"path": folder_path, "files": files})

    def _update_local_file_tree(self, files: list):
        """更新本地文件树"""
        self.local_tree.clear()

        # 按类型分组显示
        file_types = {}
        for file_info in files:
            file_type = file_info['type']
            if file_type not in file_types:
                file_types[file_type] = []
            file_types[file_type].append(file_info)

        # 添加到树形控件
        for file_type, type_files in file_types.items():
            type_item = QTreeWidgetItem(self.local_tree, [f"{file_type} ({len(type_files)})"])
            type_item.setIcon(0, get_icon(self._get_type_icon(file_type)))

            for file_info in type_files[:50]:  # 限制显示数量避免卡顿
                file_item = QTreeWidgetItem(type_item, [file_info['name']])
                file_item.setIcon(0, get_icon('file'))
                file_item.setData(0, Qt.ItemDataRole.UserRole, file_info)

    def _get_file_type(self, filename: str) -> str:
        """获取文件类型"""
        ext = filename.lower().split('.')[-1] if '.' in filename else ''

        if ext in ['md', 'markdown']:
            return 'Markdown'
        elif ext in ['txt', 'text']:
            return '文本文件'
        elif ext in ['jpg', 'jpeg', 'png', 'gif', 'bmp']:
            return '图片文件'
        elif ext in ['pdf']:
            return 'PDF文件'
        elif ext in ['doc', 'docx']:
            return 'Word文档'
        else:
            return '其他文件'

    def _get_type_icon(self, file_type: str) -> str:
        """获取文件类型图标"""
        type_icons = {
            'Markdown': 'markdown',
            '文本文件': 'text',
            '图片文件': 'image',
            'PDF文件': 'file',
            'Word文档': 'file',
            '其他文件': 'file'
        }
        return type_icons.get(file_type, 'file')
    
    def _refresh_notion(self):
        """刷新 Notion 工作区"""
        self.loading_indicator.start_loading("正在刷新 Notion 工作区")

        # 延迟发送信号，让加载动画先显示
        QTimer.singleShot(100, lambda: self.action_requested.emit("refresh_notion", {}))

    def _on_loading_error(self, title: str, error: str):
        """处理加载错误"""
        self.loading_indicator.stop_loading()
        self.set_status(f"{title}: {error}")

        # 可以在这里显示错误对话框
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.warning(self, title, f"操作失败：\n{error}")
    
    def update_connection_status(self, connected: bool, workspace_name: str = ""):
        """更新连接状态"""
        if connected:
            self.connection_label.setText(f"已连接: {workspace_name}" if workspace_name else "已连接到 Notion")
            self.connect_btn.setText("断开")
            self.connect_btn.setIcon(get_icon('disconnect'))
            self.connect_btn.setToolTip("断开与 Notion 的连接")
        else:
            self.connection_label.setText("未连接到 Notion")
            self.connect_btn.setText("连接")
            self.connect_btn.setIcon(get_icon('connect'))
            self.connect_btn.setToolTip("连接到 Notion 工作区")
    
    def update_notion_workspace(self, workspace_data: dict):
        """更新 Notion 工作区显示"""
        # 停止加载动画
        self.loading_indicator.stop_loading()

        # 缓存数据
        self._cached_notion_data = workspace_data

        # 异步更新UI避免卡顿
        QTimer.singleShot(50, lambda: self._update_notion_tree_async(workspace_data))

    def _update_notion_tree_async(self, workspace_data: dict):
        """异步更新 Notion 树形控件"""
        self.notion_tree.clear()

        pages = workspace_data.get("pages", [])
        databases = workspace_data.get("databases", [])

        # 分批添加项目避免界面卡顿
        if pages:
            pages_root = QTreeWidgetItem(self.notion_tree, [f"📄 页面 ({len(pages)})"])
            pages_root.setExpanded(True)
            pages_root.setIcon(0, get_icon('file'))

            # 分批添加页面
            self._add_items_progressively(pages_root, pages, "page")

        if databases:
            db_root = QTreeWidgetItem(self.notion_tree, [f"🗃️ 数据库 ({len(databases)})"])
            db_root.setExpanded(True)
            db_root.setIcon(0, get_icon('folder'))

            # 分批添加数据库
            self._add_items_progressively(db_root, databases, "database")

        # 更新状态
        total_items = len(pages) + len(databases)
        self.set_status(f"已加载 {total_items} 个 Notion 项目")

    def _add_items_progressively(self, parent_item: QTreeWidgetItem, items: list, item_type: str):
        """渐进式添加项目避免界面卡顿"""
        batch_size = 20  # 每批处理20个项目

        def add_batch(start_index: int):
            end_index = min(start_index + batch_size, len(items))

            for i in range(start_index, end_index):
                item = items[i]
                title = item.get("title", "无标题")

                tree_item = QTreeWidgetItem(parent_item, [title])
                tree_item.setIcon(0, get_icon('file' if item_type == 'page' else 'folder'))
                tree_item.setData(0, Qt.ItemDataRole.UserRole, item)

                # 添加工具提示
                if item.get("url"):
                    tree_item.setToolTip(0, f"点击查看: {item['url']}")

            # 如果还有更多项目，继续处理
            if end_index < len(items):
                QTimer.singleShot(10, lambda: add_batch(end_index))

        # 开始添加第一批
        if items:
            add_batch(0)
    
    def set_status(self, message: str):
        """设置状态消息"""
        self.status_label.setText(message)
    
    def update_progress(self, percentage: int):
        """更新进度"""
        if percentage > 0:
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(percentage)
            # 更新同步按钮状态
            self.sync_btn.setText("同步中...")
            self.sync_btn.setIcon(get_status_icon('syncing'))
            self.sync_btn.setEnabled(False)
        else:
            self.progress_bar.setVisible(False)
            # 恢复同步按钮状态
            self.sync_btn.setText("同步")
            self.sync_btn.setIcon(get_icon('sync'))
            self.sync_btn.setEnabled(True)

    def update_analyze_status(self, analyzing: bool):
        """更新分析状态"""
        if analyzing:
            self.analyze_btn.setText("分析中...")
            self.analyze_btn.setIcon(get_status_icon('analyzing'))
            self.analyze_btn.setEnabled(False)
        else:
            self.analyze_btn.setText("分析")
            self.analyze_btn.setIcon(get_icon('analyze'))
            self.analyze_btn.setEnabled(True)

    def show_status_message(self, message: str, status_type: str = "info"):
        """显示状态消息"""
        self.set_status(message)
        # 可以在这里添加状态图标显示
