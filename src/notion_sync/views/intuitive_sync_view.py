"""
直观的同步界面 - Notion在左边，本地文件夹在右边，中间有明确的操作指引
"""

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton,
    QTreeWidget, QTreeWidgetItem, QFileDialog, QProgressBar, 
    QSplitter, QFrame, QTextEdit
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QFont
from notion_sync.resources.icons import get_icon


class IntuitiveSyncView(QWidget):
    """直观的同步界面"""
    
    action_requested = Signal(str, dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._apply_dark_theme()
        
        # 状态变量
        self.selected_notion_items = []
        self.selected_local_folder = ""
        self.is_connected = False
        
    def _setup_ui(self):
        """设置UI"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)
        
        # 顶部标题和说明
        self._create_header(main_layout)
        
        # 主要内容区域
        content_layout = QHBoxLayout()
        content_layout.setSpacing(20)
        
        # 左侧：Notion 内容
        self._create_notion_panel(content_layout)
        
        # 中间：操作区域
        self._create_action_panel(content_layout)
        
        # 右侧：本地文件夹
        self._create_local_panel(content_layout)
        
        main_layout.addLayout(content_layout)
        
        # 底部：进度和状态
        self._create_bottom_panel(main_layout)
    
    def _create_header(self, parent_layout):
        """创建顶部标题区域"""
        header_frame = QFrame()
        header_frame.setFrameStyle(QFrame.Shape.Box)
        header_layout = QVBoxLayout(header_frame)
        
        # 主标题
        title_label = QLabel("📥 Notion 内容导出")
        title_label.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(title_label)
        
        # 说明文字
        desc_label = QLabel("从 Notion 导出内容到本地文件夹 - 简单三步完成")
        desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc_label.setStyleSheet("color: #888888; font-size: 14px;")
        header_layout.addWidget(desc_label)
        
        parent_layout.addWidget(header_frame)
    
    def _create_notion_panel(self, parent_layout):
        """创建 Notion 面板"""
        notion_frame = QFrame()
        notion_frame.setFrameStyle(QFrame.Shape.Box)
        notion_frame.setMinimumWidth(300)
        layout = QVBoxLayout(notion_frame)
        
        # 步骤标题
        step_label = QLabel("1️⃣ 连接并选择 Notion 内容")
        step_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        step_label.setStyleSheet("color: #4A90E2; padding: 10px;")
        layout.addWidget(step_label)
        
        # 连接状态和按钮
        self.connection_status = QLabel("❌ 未连接到 Notion")
        self.connection_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.connection_status.setStyleSheet("color: #FF6B6B; font-weight: bold; padding: 5px;")
        layout.addWidget(self.connection_status)
        
        self.connect_btn = QPushButton("🔗 连接 Notion")
        self.connect_btn.setMinimumHeight(40)
        self.connect_btn.clicked.connect(self._connect_notion)
        layout.addWidget(self.connect_btn)
        
        # Notion 内容树
        content_label = QLabel("选择要导出的内容：")
        content_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        layout.addWidget(content_label)
        
        self.notion_tree = QTreeWidget()
        self.notion_tree.setHeaderLabel("Notion 工作区内容")
        self.notion_tree.setSelectionMode(QTreeWidget.SelectionMode.MultiSelection)
        self.notion_tree.itemSelectionChanged.connect(self._on_notion_selection_changed)
        layout.addWidget(self.notion_tree)
        
        # 刷新按钮
        self.refresh_btn = QPushButton("🔄 刷新内容")
        self.refresh_btn.clicked.connect(self._refresh_notion)
        self.refresh_btn.setEnabled(False)
        layout.addWidget(self.refresh_btn)
        
        parent_layout.addWidget(notion_frame)
    
    def _create_action_panel(self, parent_layout):
        """创建中间操作面板"""
        action_frame = QFrame()
        action_frame.setFrameStyle(QFrame.Shape.Box)
        action_frame.setMinimumWidth(200)
        action_frame.setMaximumWidth(250)
        layout = QVBoxLayout(action_frame)
        
        # 添加空间
        layout.addStretch()
        
        # 步骤指示
        step_label = QLabel("2️⃣ 开始导出")
        step_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        step_label.setStyleSheet("color: #4A90E2;")
        step_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(step_label)
        
        # 箭头指示
        arrow_label = QLabel("⬇️")
        arrow_label.setFont(QFont("Arial", 48))
        arrow_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        arrow_label.setStyleSheet("color: #4A90E2; margin: 20px;")
        layout.addWidget(arrow_label)
        
        # 主要操作按钮
        self.main_action_btn = QPushButton("🚀 开始导出")
        self.main_action_btn.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        self.main_action_btn.setMinimumHeight(80)
        self.main_action_btn.clicked.connect(self._start_export)
        self.main_action_btn.setEnabled(False)
        layout.addWidget(self.main_action_btn)
        
        # 状态显示
        self.action_status = QLabel("请完成上述步骤")
        self.action_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.action_status.setWordWrap(True)
        self.action_status.setStyleSheet("color: #888888; font-size: 12px; margin: 10px;")
        layout.addWidget(self.action_status)
        
        layout.addStretch()
        
        parent_layout.addWidget(action_frame)
    
    def _create_local_panel(self, parent_layout):
        """创建本地文件夹面板"""
        local_frame = QFrame()
        local_frame.setFrameStyle(QFrame.Shape.Box)
        local_frame.setMinimumWidth(300)
        layout = QVBoxLayout(local_frame)
        
        # 步骤标题
        step_label = QLabel("3️⃣ 选择本地保存位置")
        step_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        step_label.setStyleSheet("color: #4A90E2; padding: 10px;")
        layout.addWidget(step_label)
        
        # 文件夹显示区域
        self.folder_display = QLabel("📁 点击下方按钮选择文件夹")
        self.folder_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.folder_display.setMinimumHeight(80)
        self.folder_display.setStyleSheet("""
            border: 2px dashed #555555;
            border-radius: 8px;
            background-color: #3c3c3c;
            color: #888888;
            padding: 20px;
            margin: 10px;
        """)
        layout.addWidget(self.folder_display)
        
        # 选择文件夹按钮
        self.select_folder_btn = QPushButton("📂 选择保存文件夹")
        self.select_folder_btn.setMinimumHeight(40)
        self.select_folder_btn.clicked.connect(self._select_folder)
        layout.addWidget(self.select_folder_btn)
        
        # 文件夹预览
        preview_label = QLabel("文件夹预览：")
        preview_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        layout.addWidget(preview_label)
        
        self.folder_preview = QTreeWidget()
        self.folder_preview.setHeaderLabel("当前文件夹内容")
        self.folder_preview.setMaximumHeight(200)
        layout.addWidget(self.folder_preview)
        
        # 打开文件夹按钮
        self.open_folder_btn = QPushButton("🗂️ 打开文件夹")
        self.open_folder_btn.clicked.connect(self._open_folder)
        self.open_folder_btn.setEnabled(False)
        layout.addWidget(self.open_folder_btn)
        
        parent_layout.addWidget(local_frame)
    
    def _create_bottom_panel(self, parent_layout):
        """创建底部状态面板"""
        bottom_frame = QFrame()
        bottom_frame.setFrameStyle(QFrame.Shape.Box)
        layout = QVBoxLayout(bottom_frame)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setMinimumHeight(25)
        layout.addWidget(self.progress_bar)
        
        # 状态信息
        self.status_label = QLabel("💡 提示：请按照上方步骤操作，完成后点击开始导出")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("color: #4A90E2; font-weight: bold; padding: 10px;")
        layout.addWidget(self.status_label)
        
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
            padding: 12px 20px;
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
        
        QTreeWidget {
            background-color: #2b2b2b;
            border: 1px solid #555555;
            border-radius: 4px;
            color: #ffffff;
        }
        
        QTreeWidget::item {
            padding: 8px;
            border-bottom: 1px solid #444444;
        }
        
        QTreeWidget::item:selected {
            background-color: #007AFF;
            color: white;
        }
        
        QTreeWidget::item:hover {
            background-color: #4c4c4c;
        }
        
        QProgressBar {
            border: 1px solid #555555;
            border-radius: 4px;
            background-color: #3c3c3c;
            text-align: center;
            color: #ffffff;
        }
        
        QProgressBar::chunk {
            background-color: #4CAF50;
            border-radius: 3px;
        }
        """
        self.setStyleSheet(dark_style)
    
    def _connect_notion(self):
        """连接 Notion"""
        self.action_requested.emit("connect_notion", {})
    
    def _refresh_notion(self):
        """刷新 Notion 内容"""
        self.action_requested.emit("refresh_notion", {})
    
    def _select_folder(self):
        """选择本地文件夹"""
        folder = QFileDialog.getExistingDirectory(self, "选择导出文件夹", "")
        if folder:
            self.selected_local_folder = folder
            self.folder_display.setText(f"✅ 已选择：\n{folder}")
            self.folder_display.setStyleSheet("""
                border: 2px solid #4CAF50;
                border-radius: 8px;
                background-color: #3c3c3c;
                color: #4CAF50;
                padding: 20px;
                margin: 10px;
                font-weight: bold;
            """)
            self.open_folder_btn.setEnabled(True)
            self._update_folder_preview(folder)
            self._update_action_button()
    
    def _open_folder(self):
        """打开文件夹"""
        if self.selected_local_folder:
            import os
            import subprocess
            import platform
            
            try:
                if platform.system() == "Windows":
                    os.startfile(self.selected_local_folder)
                elif platform.system() == "Darwin":  # macOS
                    subprocess.run(["open", self.selected_local_folder])
                else:  # Linux
                    subprocess.run(["xdg-open", self.selected_local_folder])
            except Exception as e:
                self.status_label.setText(f"❌ 无法打开文件夹：{str(e)}")
    
    def _update_folder_preview(self, folder_path):
        """更新文件夹预览"""
        self.folder_preview.clear()
        try:
            import os
            items = os.listdir(folder_path)
            if not items:
                empty_item = QTreeWidgetItem(self.folder_preview, ["📂 文件夹为空"])
                return
            
            for item in items[:10]:  # 只显示前10个项目
                item_path = os.path.join(folder_path, item)
                if os.path.isdir(item_path):
                    tree_item = QTreeWidgetItem(self.folder_preview, [f"📁 {item}"])
                else:
                    tree_item = QTreeWidgetItem(self.folder_preview, [f"📄 {item}"])
            
            if len(items) > 10:
                more_item = QTreeWidgetItem(self.folder_preview, [f"... 还有 {len(items) - 10} 个项目"])
                
        except Exception as e:
            error_item = QTreeWidgetItem(self.folder_preview, [f"❌ 无法读取：{str(e)}"])
    
    def _on_notion_selection_changed(self):
        """Notion 选择改变"""
        self.selected_notion_items = self.notion_tree.selectedItems()
        self._update_action_button()
    
    def _update_action_button(self):
        """更新操作按钮状态"""
        has_notion = len(self.selected_notion_items) > 0
        has_folder = bool(self.selected_local_folder)
        is_connected = self.is_connected
        
        if is_connected and has_notion and has_folder:
            self.main_action_btn.setEnabled(True)
            self.main_action_btn.setStyleSheet("""
                QPushButton {
                    background-color: #4CAF50 !important;
                    color: white !important;
                    font-weight: bold !important;
                    font-size: 16px !important;
                }
                QPushButton:hover {
                    background-color: #45A049 !important;
                }
            """)
            self.action_status.setText(f"✅ 准备就绪！\n已选择 {len(self.selected_notion_items)} 个项目")
            self.action_status.setStyleSheet("color: #4CAF50; font-weight: bold;")
        else:
            self.main_action_btn.setEnabled(False)
            self.main_action_btn.setStyleSheet("")  # 恢复默认样式
            
            missing = []
            if not is_connected:
                missing.append("连接 Notion")
            if not has_notion:
                missing.append("选择内容")
            if not has_folder:
                missing.append("选择文件夹")
            
            self.action_status.setText(f"❌ 还需要：{' → '.join(missing)}")
            self.action_status.setStyleSheet("color: #FF6B6B;")
    
    def _start_export(self):
        """开始导出"""
        if not self.selected_notion_items or not self.selected_local_folder:
            return
        
        # 收集选中的项目
        selected_items = []
        for item in self.selected_notion_items:
            item_data = item.data(0, Qt.ItemDataRole.UserRole)
            if item_data:
                selected_items.append(item_data)
        
        export_data = {
            "notion_items": selected_items,
            "local_folder": self.selected_local_folder,
            "item_count": len(selected_items)
        }
        
        # 显示进度
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_label.setText("🚀 正在导出，请稍候...")
        self.status_label.setStyleSheet("color: #4A90E2; font-weight: bold;")
        self.main_action_btn.setEnabled(False)
        
        # 发送导出请求
        self.action_requested.emit("start_export", export_data)
    
    # 公共方法供外部调用
    def update_connection_status(self, connected: bool):
        """更新连接状态"""
        self.is_connected = connected
        if connected:
            self.connection_status.setText("✅ 已连接到 Notion")
            self.connection_status.setStyleSheet("color: #4CAF50; font-weight: bold;")
            self.connect_btn.setText("🔄 重新连接")
            self.refresh_btn.setEnabled(True)
        else:
            self.connection_status.setText("❌ 未连接到 Notion")
            self.connection_status.setStyleSheet("color: #FF6B6B; font-weight: bold;")
            self.connect_btn.setText("🔗 连接 Notion")
            self.refresh_btn.setEnabled(False)
            self.notion_tree.clear()
        
        self._update_action_button()
    
    def update_notion_content(self, workspace_data: dict):
        """更新 Notion 内容"""
        self.notion_tree.clear()
        
        # 添加页面
        pages = workspace_data.get("pages", [])
        if pages:
            pages_root = QTreeWidgetItem(self.notion_tree, [f"📄 页面 ({len(pages)} 个)"])
            pages_root.setExpanded(True)
            for page in pages:
                page_item = QTreeWidgetItem(pages_root, [page.get("title", "无标题")])
                page_item.setIcon(0, get_icon('file'))
                page_item.setData(0, Qt.ItemDataRole.UserRole, page)
        
        # 添加数据库
        databases = workspace_data.get("databases", [])
        if databases:
            db_root = QTreeWidgetItem(self.notion_tree, [f"🗃️ 数据库 ({len(databases)} 个)"])
            db_root.setExpanded(True)
            for db in databases:
                db_item = QTreeWidgetItem(db_root, [db.get("title", "无标题")])
                db_item.setIcon(0, get_icon('folder'))
                db_item.setData(0, Qt.ItemDataRole.UserRole, db)
        
        self._update_action_button()
    
    def update_progress(self, value: int, message: str = ""):
        """更新进度"""
        # 使用 QTimer 避免递归重绘
        QTimer.singleShot(0, lambda: self._update_progress_safe(value, message))

    def _update_progress_safe(self, value: int, message: str = ""):
        """安全更新进度（避免递归重绘）"""
        try:
            self.progress_bar.setValue(value)
            if message:
                self.status_label.setText(f"🔄 {message}")
        except Exception as e:
            print(f"更新进度时出错: {e}")
    
    def export_completed(self, success: bool, message: str = ""):
        """导出完成"""
        # 使用 QTimer 避免递归重绘
        QTimer.singleShot(0, lambda: self._export_completed_safe(success, message))

    def _export_completed_safe(self, success: bool, message: str = ""):
        """安全处理导出完成（避免递归重绘）"""
        try:
            self.progress_bar.setVisible(False)
            self.main_action_btn.setEnabled(True)

            if success:
                self.status_label.setText("🎉 导出完成！文件已保存到选定文件夹")
                self.status_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
            else:
                self.status_label.setText(f"❌ 导出失败：{message}")
                self.status_label.setStyleSheet("color: #FF6B6B; font-weight: bold;")

            # 5秒后恢复提示
            QTimer.singleShot(5000, self._reset_status_message)
        except Exception as e:
            print(f"处理导出完成时出错: {e}")

    def _reset_status_message(self):
        """重置状态消息"""
        try:
            self.status_label.setText("💡 提示：请按照上方步骤操作，完成后点击开始导出")
            self.status_label.setStyleSheet("color: #4A90E2; font-weight: bold;")
        except Exception as e:
            print(f"重置状态消息时出错: {e}")
