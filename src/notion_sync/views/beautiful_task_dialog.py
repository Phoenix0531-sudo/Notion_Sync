"""
美观的新建任务对话框
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QCheckBox, QLineEdit, QFileDialog,
    QMessageBox, QGridLayout
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QPainter, QColor, QBrush, QPen


class BeautifulTaskDialog(QWidget):
    """美观的新建任务对话框"""
    
    task_created = Signal(dict)
    
    def __init__(self, notion_workspace_data: dict, parent=None):
        super().__init__(parent)
        self.notion_workspace_data = notion_workspace_data
        self.selected_local_folder = ""
        self.selected_items = []
        self._setup_ui()
        self._apply_beautiful_theme()
    
    def _setup_ui(self):
        """设置美观的UI"""
        self.setWindowTitle("创建新同步任务")
        self.setFixedSize(1100, 750)
        
        # 设置窗口属性
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(0)
        
        # 创建主容器
        self.main_container = QFrame()
        self.main_container.setObjectName("mainContainer")
        container_layout = QVBoxLayout(self.main_container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)
        
        # 顶部标题区域
        self._create_title_section(container_layout)
        
        # 内容区域
        self._create_content_section(container_layout)
        
        # 底部按钮区域
        self._create_button_section(container_layout)
        
        main_layout.addWidget(self.main_container)
    
    def _create_title_section(self, parent_layout):
        """创建标题区域"""
        title_frame = QFrame()
        title_frame.setObjectName("titleFrame")
        title_frame.setFixedHeight(120)

        title_layout = QHBoxLayout(title_frame)
        title_layout.setContentsMargins(40, 35, 40, 35)
        
        # 左侧图标和文字
        left_layout = QHBoxLayout()
        
        # 图标
        icon_label = QLabel("🎯")
        icon_label.setFont(QFont("Arial", 32))
        left_layout.addWidget(icon_label)
        
        # 标题文字
        text_layout = QVBoxLayout()
        text_layout.setSpacing(8)

        title_label = QLabel("创建同步任务")
        title_label.setObjectName("titleLabel")
        title_label.setFont(QFont("Microsoft YaHei", 22, QFont.Weight.Bold))
        title_label.setMinimumHeight(35)
        text_layout.addWidget(title_label)

        subtitle_label = QLabel("选择 Notion 内容并配置本地保存位置")
        subtitle_label.setObjectName("subtitleLabel")
        subtitle_label.setFont(QFont("Microsoft YaHei", 13))
        subtitle_label.setMinimumHeight(25)
        text_layout.addWidget(subtitle_label)
        
        left_layout.addLayout(text_layout)
        title_layout.addLayout(left_layout)
        
        title_layout.addStretch()
        
        # 关闭按钮
        close_btn = QPushButton("×")
        close_btn.setObjectName("closeButton")
        close_btn.setFixedSize(40, 40)
        close_btn.clicked.connect(self.close)
        title_layout.addWidget(close_btn)
        
        parent_layout.addWidget(title_frame)
    
    def _create_content_section(self, parent_layout):
        """创建内容区域"""
        content_frame = QFrame()
        content_frame.setObjectName("contentFrame")
        
        content_layout = QHBoxLayout(content_frame)
        content_layout.setContentsMargins(40, 30, 40, 30)
        content_layout.setSpacing(40)
        
        # 左侧：Notion 内容选择
        self._create_notion_section(content_layout)
        
        # 右侧：任务配置
        self._create_config_section(content_layout)
        
        parent_layout.addWidget(content_frame)
    
    def _create_notion_section(self, parent_layout):
        """创建 Notion 内容选择区域"""
        notion_frame = QFrame()
        notion_frame.setObjectName("sectionFrame")
        notion_frame.setFixedWidth(480)
        
        layout = QVBoxLayout(notion_frame)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)
        
        # 标题
        title_label = QLabel("📚 选择 Notion 内容")
        title_label.setObjectName("sectionTitle")
        title_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        layout.addWidget(title_label)
        
        # 说明
        desc_label = QLabel("选择要同步的页面或数据库")
        desc_label.setObjectName("sectionDesc")
        desc_label.setFont(QFont("Arial", 12))
        layout.addWidget(desc_label)
        
        # 滚动区域
        scroll_area = QScrollArea()
        scroll_area.setObjectName("scrollArea")
        scroll_area.setWidgetResizable(True)
        scroll_area.setFixedHeight(350)
        
        # 内容容器
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setSpacing(15)
        scroll_layout.setContentsMargins(10, 10, 10, 10)
        
        # 添加 Notion 项目
        self._populate_notion_items(scroll_layout)
        
        scroll_area.setWidget(scroll_widget)
        layout.addWidget(scroll_area)
        
        parent_layout.addWidget(notion_frame)
    
    def _create_config_section(self, parent_layout):
        """创建配置区域"""
        config_frame = QFrame()
        config_frame.setObjectName("sectionFrame")
        config_frame.setFixedWidth(480)
        
        layout = QVBoxLayout(config_frame)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)
        
        # 标题
        title_label = QLabel("⚙️ 任务配置")
        title_label.setObjectName("sectionTitle")
        title_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        layout.addWidget(title_label)
        
        # 任务名称
        name_label = QLabel("任务名称")
        name_label.setObjectName("fieldLabel")
        name_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        layout.addWidget(name_label)
        
        self.task_name_input = QLineEdit()
        self.task_name_input.setObjectName("textInput")
        self.task_name_input.setPlaceholderText("输入任务名称...")
        self.task_name_input.setFixedHeight(45)
        self.task_name_input.textChanged.connect(self._update_create_button)
        layout.addWidget(self.task_name_input)
        
        # 本地文件夹
        folder_label = QLabel("保存位置")
        folder_label.setObjectName("fieldLabel")
        folder_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        layout.addWidget(folder_label)
        
        folder_layout = QHBoxLayout()
        folder_layout.setSpacing(10)
        
        self.folder_display = QLabel("点击选择文件夹...")
        self.folder_display.setObjectName("folderDisplay")
        self.folder_display.setFixedHeight(45)
        folder_layout.addWidget(self.folder_display)
        
        self.select_folder_btn = QPushButton("📁")
        self.select_folder_btn.setObjectName("iconButton")
        self.select_folder_btn.setFixedSize(45, 45)
        self.select_folder_btn.clicked.connect(self._select_folder)
        folder_layout.addWidget(self.select_folder_btn)
        
        layout.addLayout(folder_layout)
        
        # 选项
        options_label = QLabel("同步选项")
        options_label.setObjectName("fieldLabel")
        options_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        layout.addWidget(options_label)
        
        self.include_children_check = QCheckBox("包含子页面")
        self.include_children_check.setObjectName("checkBox")
        self.include_children_check.setChecked(True)
        layout.addWidget(self.include_children_check)
        
        self.auto_sync_check = QCheckBox("启用自动同步")
        self.auto_sync_check.setObjectName("checkBox")
        layout.addWidget(self.auto_sync_check)
        
        layout.addStretch()
        
        # 选择状态
        self.selection_status = QLabel("请选择内容和文件夹")
        self.selection_status.setObjectName("statusLabel")
        self.selection_status.setFont(QFont("Arial", 12))
        layout.addWidget(self.selection_status)
        
        parent_layout.addWidget(config_frame)
    
    def _create_button_section(self, parent_layout):
        """创建按钮区域"""
        button_frame = QFrame()
        button_frame.setObjectName("buttonFrame")
        button_frame.setFixedHeight(80)
        
        button_layout = QHBoxLayout(button_frame)
        button_layout.setContentsMargins(40, 20, 40, 20)
        
        button_layout.addStretch()
        
        # 取消按钮
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.setObjectName("cancelButton")
        self.cancel_btn.setFixedSize(100, 40)
        self.cancel_btn.clicked.connect(self.close)
        button_layout.addWidget(self.cancel_btn)
        
        # 创建按钮
        self.create_btn = QPushButton("创建任务")
        self.create_btn.setObjectName("createButton")
        self.create_btn.setFixedSize(120, 40)
        self.create_btn.clicked.connect(self._create_task)
        self.create_btn.setEnabled(False)
        button_layout.addWidget(self.create_btn)
        
        parent_layout.addWidget(button_frame)
    
    def _populate_notion_items(self, parent_layout):
        """填充 Notion 项目"""
        # 添加页面
        pages = self.notion_workspace_data.get("pages", [])
        if pages:
            page_label = QLabel(f"📄 页面 ({len(pages)} 个)")
            page_label.setObjectName("categoryLabel")
            page_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
            parent_layout.addWidget(page_label)
            
            for page in pages:
                self._add_notion_item(parent_layout, page, "page")
        
        # 添加数据库
        databases = self.notion_workspace_data.get("databases", [])
        if databases:
            db_label = QLabel(f"🗃️ 数据库 ({len(databases)} 个)")
            db_label.setObjectName("categoryLabel")
            db_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
            parent_layout.addWidget(db_label)
            
            for db in databases:
                self._add_notion_item(parent_layout, db, "database")
    
    def _add_notion_item(self, parent_layout, item, item_type):
        """添加 Notion 项目"""
        item_frame = QFrame()
        item_frame.setObjectName("itemFrame")
        item_frame.setFixedHeight(80)

        item_layout = QHBoxLayout(item_frame)
        item_layout.setContentsMargins(20, 20, 20, 20)
        item_layout.setSpacing(15)
        
        # 复选框
        checkbox = QCheckBox()
        checkbox.setObjectName("itemCheckBox")
        
        # 处理不同类型的 item 对象
        if hasattr(item, 'title'):
            item_data = {
                "id": item.id,
                "title": item.title,
                "url": getattr(item, 'url', ''),
                "created_time": getattr(item, 'created_time', ''),
                "last_edited_time": getattr(item, 'last_edited_time', '')
            }
            title = item.title
        elif isinstance(item, dict):
            item_data = item
            title = item.get("title", "无标题")
        else:
            item_data = {"id": str(item), "title": "无标题"}
            title = "无标题"
        
        checkbox.setProperty("item_data", item_data)
        checkbox.setProperty("item_type", item_type)
        checkbox.stateChanged.connect(self._on_item_selection_changed)
        item_layout.addWidget(checkbox)
        
        # 图标
        icon = "📄" if item_type == "page" else "🗃️"
        icon_label = QLabel(icon)
        icon_label.setFont(QFont("Arial", 16))
        item_layout.addWidget(icon_label)
        
        # 标题
        title_label = QLabel(title)
        title_label.setObjectName("itemTitle")
        title_label.setFont(QFont("Arial", 12))
        item_layout.addWidget(title_label)
        
        item_layout.addStretch()
        
        parent_layout.addWidget(item_frame)
    
    def _select_folder(self):
        """选择文件夹"""
        folder = QFileDialog.getExistingDirectory(self, "选择保存文件夹")
        if folder:
            self.selected_local_folder = folder
            self.folder_display.setText(folder)
            self.folder_display.setObjectName("folderDisplaySelected")
            self.folder_display.setStyleSheet(self.folder_display.styleSheet())  # 重新应用样式
            self._update_create_button()
    
    def _on_item_selection_changed(self):
        """项目选择改变"""
        self.selected_items = []
        
        # 遍历所有复选框
        for checkbox in self.findChildren(QCheckBox):
            if checkbox.objectName() == "itemCheckBox" and checkbox.isChecked():
                item_data = checkbox.property("item_data")
                item_type = checkbox.property("item_type")
                if item_data:
                    self.selected_items.append({
                        "data": item_data,
                        "type": item_type
                    })
        
        self._update_create_button()
        self._update_status()
    
    def _update_create_button(self):
        """更新创建按钮状态"""
        has_name = bool(self.task_name_input.text().strip())
        has_folder = bool(self.selected_local_folder)
        has_items = len(self.selected_items) > 0
        
        self.create_btn.setEnabled(has_name and has_folder and has_items)
    
    def _update_status(self):
        """更新状态显示"""
        if self.selected_items:
            self.selection_status.setText(f"✅ 已选择 {len(self.selected_items)} 个项目")
            self.selection_status.setObjectName("statusLabelSuccess")
        else:
            self.selection_status.setText("请选择要同步的内容")
            self.selection_status.setObjectName("statusLabel")
        
        # 重新应用样式
        self.selection_status.setStyleSheet(self.selection_status.styleSheet())
    
    def _create_task(self):
        """创建任务"""
        task_name = self.task_name_input.text().strip()
        if not task_name or not self.selected_local_folder or not self.selected_items:
            QMessageBox.warning(self, "错误", "请完成所有必填项！")
            return
        
        task_config = {
            "name": task_name,
            "local_folder": self.selected_local_folder,
            "notion_items": self.selected_items,
            "include_children": self.include_children_check.isChecked(),
            "auto_sync": self.auto_sync_check.isChecked()
        }
        
        self.task_created.emit(task_config)
        self.close()
    
    def paintEvent(self, event):
        """绘制圆角背景"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 绘制阴影
        shadow_rect = self.rect().adjusted(5, 5, -5, -5)
        painter.setBrush(QBrush(QColor(0, 0, 0, 30)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(shadow_rect, 15, 15)
        
        # 绘制主背景
        main_rect = self.rect().adjusted(0, 0, -10, -10)
        painter.setBrush(QBrush(QColor(255, 255, 255)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(main_rect, 15, 15)

    def _apply_beautiful_theme(self):
        """应用美观主题"""
        self.setStyleSheet("""
        /* 主容器 */
        QFrame#mainContainer {
            background-color: white;
            border-radius: 15px;
        }

        /* 标题区域 */
        QFrame#titleFrame {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 #667eea, stop:1 #764ba2);
            border-top-left-radius: 15px;
            border-top-right-radius: 15px;
        }

        QLabel#titleLabel {
            color: white;
            padding: 8px 0px;
            line-height: 1.4;
        }

        QLabel#subtitleLabel {
            color: rgba(255, 255, 255, 0.8);
            padding: 5px 0px;
            line-height: 1.3;
        }

        QPushButton#closeButton {
            background-color: rgba(255, 255, 255, 0.2);
            border: none;
            border-radius: 20px;
            color: white;
            font-size: 18px;
            font-weight: bold;
        }

        QPushButton#closeButton:hover {
            background-color: rgba(255, 255, 255, 0.3);
        }

        /* 内容区域 */
        QFrame#contentFrame {
            background-color: #f8f9fa;
        }

        QFrame#sectionFrame {
            background-color: white;
            border: 1px solid #e9ecef;
            border-radius: 12px;
        }

        QLabel#sectionTitle {
            color: #2c3e50;
        }

        QLabel#sectionDesc {
            color: #6c757d;
        }

        /* 滚动区域 */
        QScrollArea#scrollArea {
            border: none;
            background-color: transparent;
        }

        QScrollArea#scrollArea QScrollBar:vertical {
            background-color: #f1f3f4;
            width: 8px;
            border-radius: 4px;
        }

        QScrollArea#scrollArea QScrollBar::handle:vertical {
            background-color: #c1c8cd;
            border-radius: 4px;
            min-height: 20px;
        }

        QScrollArea#scrollArea QScrollBar::handle:vertical:hover {
            background-color: #a8b2b9;
        }

        /* 项目框架 */
        QFrame#itemFrame {
            background-color: #f8f9fa;
            border: 1px solid #e9ecef;
            border-radius: 8px;
            margin: 5px;
            min-height: 80px;
            padding: 10px;
        }

        QFrame#itemFrame:hover {
            background-color: #e3f2fd;
            border-color: #2196f3;
        }

        QLabel#itemTitle {
            color: #2c3e50;
            padding: 10px 8px;
            font-size: 14px;
            line-height: 1.6;
            min-height: 40px;
        }

        QLabel#categoryLabel {
            color: #495057;
            margin: 20px 0px 15px 0px;
            padding: 12px 0px;
            font-weight: bold;
            font-size: 15px;
            min-height: 30px;
        }

        /* 复选框 */
        QCheckBox#itemCheckBox::indicator {
            width: 18px;
            height: 18px;
            border-radius: 9px;
            border: 2px solid #ced4da;
            background-color: white;
        }

        QCheckBox#itemCheckBox::indicator:checked {
            background-color: #007bff;
            border-color: #007bff;
            image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTIiIGhlaWdodD0iOSIgdmlld0JveD0iMCAwIDEyIDkiIGZpbGw9Im5vbmUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+CjxwYXRoIGQ9Ik0xIDQuNUw0LjUgOEwxMSAxIiBzdHJva2U9IndoaXRlIiBzdHJva2Utd2lkdGg9IjIiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIgc3Ryb2tlLWxpbmVqb2luPSJyb3VuZCIvPgo8L3N2Zz4K);
        }

        QCheckBox#itemCheckBox::indicator:hover {
            border-color: #007bff;
        }

        QCheckBox#checkBox {
            color: #495057;
            font-size: 13px;
        }

        QCheckBox#checkBox::indicator {
            width: 16px;
            height: 16px;
            border-radius: 3px;
            border: 2px solid #ced4da;
            background-color: white;
        }

        QCheckBox#checkBox::indicator:checked {
            background-color: #28a745;
            border-color: #28a745;
        }

        /* 输入框 */
        QLineEdit#textInput {
            border: 2px solid #e9ecef;
            border-radius: 8px;
            padding: 12px 16px;
            font-size: 14px;
            background-color: white;
            color: #495057;
        }

        QLineEdit#textInput:focus {
            border-color: #007bff;
            outline: none;
        }

        /* 文件夹显示 */
        QLabel#folderDisplay {
            border: 2px dashed #ced4da;
            border-radius: 8px;
            padding: 12px 16px;
            background-color: #f8f9fa;
            color: #6c757d;
            font-size: 14px;
        }

        QLabel#folderDisplaySelected {
            border: 2px solid #28a745;
            background-color: #d4edda;
            color: #155724;
            font-weight: 500;
        }

        /* 字段标签 */
        QLabel#fieldLabel {
            color: #495057;
            margin-bottom: 8px;
        }

        /* 状态标签 */
        QLabel#statusLabel {
            color: #6c757d;
            font-style: italic;
        }

        QLabel#statusLabelSuccess {
            color: #28a745;
            font-weight: 500;
        }

        /* 图标按钮 */
        QPushButton#iconButton {
            background-color: #007bff;
            border: none;
            border-radius: 8px;
            color: white;
            font-size: 16px;
        }

        QPushButton#iconButton:hover {
            background-color: #0056b3;
        }

        /* 底部按钮区域 */
        QFrame#buttonFrame {
            background-color: white;
            border-top: 1px solid #e9ecef;
            border-bottom-left-radius: 15px;
            border-bottom-right-radius: 15px;
        }

        QPushButton#cancelButton {
            background-color: #6c757d;
            color: white;
            border: none;
            border-radius: 20px;
            font-size: 14px;
            font-weight: 500;
        }

        QPushButton#cancelButton:hover {
            background-color: #5a6268;
        }

        QPushButton#createButton {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #28a745, stop:1 #20c997);
            color: white;
            border: none;
            border-radius: 20px;
            font-size: 14px;
            font-weight: 600;
        }

        QPushButton#createButton:hover {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #218838, stop:1 #1ea085);
        }

        QPushButton#createButton:disabled {
            background-color: #adb5bd;
        }
        """)
