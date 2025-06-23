"""
新建同步对话框。
"""

from typing import Optional
from pathlib import Path
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QComboBox, QFileDialog, QGroupBox,
    QCheckBox, QFrame, QWidget, QScrollArea
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from notion_sync.utils.i18n import tr
from notion_sync.views.notion_workspace_dialog import show_notion_workspace_dialog


class NewSyncDialog(QDialog):
    """新建同步对话框。"""

    # 信号
    sync_created = Signal(dict)  # 同步配置创建完成

    def __init__(self, notion_client=None, parent=None):
        super().__init__(parent)
        self.notion_client = notion_client
        self.setWindowTitle(tr("new_sync_title"))
        self.setModal(True)
        self.setMinimumSize(520, 600)
        self.setMaximumSize(700, 800)
        self.resize(580, 650)

        self._setup_ui()
    
    def _setup_ui(self):
        """设置界面。"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(24)

        # 标题区域
        title_widget = self._create_title_section()
        layout.addWidget(title_widget)

        # 滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setSpacing(20)

        # 基本设置
        basic_group = self._create_basic_settings()
        content_layout.addWidget(basic_group)

        # 路径设置
        path_group = self._create_path_settings()
        content_layout.addWidget(path_group)

        # 同步选项
        options_group = self._create_sync_options()
        content_layout.addWidget(options_group)

        # 文件过滤
        filter_group = self._create_file_filter()
        content_layout.addWidget(filter_group)

        scroll_area.setWidget(content_widget)
        layout.addWidget(scroll_area)

        # 按钮区域
        button_widget = self._create_button_section()
        layout.addWidget(button_widget)

    def _create_title_section(self) -> QWidget:
        """创建标题区域。"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        title_label = QLabel(tr("new_sync_title"))
        title_label.setFont(QFont("SF Pro Display", 20, QFont.Weight.Bold))
        title_label.setStyleSheet("color: #1D1D1F;")
        layout.addWidget(title_label)

        desc_label = QLabel(tr("new_sync_desc"))
        desc_label.setFont(QFont("SF Pro Display", 14))
        desc_label.setStyleSheet("color: #8E8E93;")
        layout.addWidget(desc_label)

        return widget

    def _create_basic_settings(self) -> QGroupBox:
        """创建基本设置组。"""
        group = QGroupBox(tr("basic_settings"))
        group.setFont(QFont("SF Pro Display", 16, QFont.Weight.Medium))
        layout = QVBoxLayout(group)
        layout.setSpacing(16)

        # 同步名称
        name_layout = QVBoxLayout()
        name_label = QLabel(tr("sync_name"))
        name_label.setFont(QFont("SF Pro Display", 14, QFont.Weight.Medium))
        name_layout.addWidget(name_label)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText(tr("sync_name_placeholder"))
        self.name_input.setMinimumHeight(36)
        self.name_input.setStyleSheet(self._get_input_style())
        name_layout.addWidget(self.name_input)
        layout.addLayout(name_layout)

        # 同步类型
        type_layout = QVBoxLayout()
        type_label = QLabel(tr("sync_type"))
        type_label.setFont(QFont("SF Pro Display", 14, QFont.Weight.Medium))
        type_layout.addWidget(type_label)

        self.sync_type = QComboBox()
        self.sync_type.addItems([
            tr("sync_type_bidirectional"),
            tr("sync_type_local_to_remote"),
            tr("sync_type_remote_to_local")
        ])
        self.sync_type.setMinimumHeight(36)
        self.sync_type.setStyleSheet(self._get_combo_style())
        self.sync_type.currentIndexChanged.connect(self._on_sync_type_changed)
        type_layout.addWidget(self.sync_type)

        # 类型说明
        self.type_desc = QLabel(tr("sync_type_desc_bidirectional"))
        self.type_desc.setFont(QFont("SF Pro Display", 12))
        self.type_desc.setStyleSheet("color: #8E8E93; margin-top: 4px;")
        type_layout.addWidget(self.type_desc)
        layout.addLayout(type_layout)

        return group

    def _create_path_settings(self) -> QGroupBox:
        """创建路径设置组。"""
        group = QGroupBox(tr("path_settings"))
        group.setFont(QFont("SF Pro Display", 16, QFont.Weight.Medium))
        layout = QVBoxLayout(group)
        layout.setSpacing(16)

        # 本地路径
        local_layout = QVBoxLayout()
        local_label = QLabel(tr("local_path"))
        local_label.setFont(QFont("SF Pro Display", 14, QFont.Weight.Medium))
        local_layout.addWidget(local_label)

        local_input_layout = QHBoxLayout()
        self.local_path = QLineEdit()
        self.local_path.setPlaceholderText(tr("local_path_placeholder"))
        self.local_path.setMinimumHeight(36)
        self.local_path.setStyleSheet(self._get_input_style())
        local_input_layout.addWidget(self.local_path)

        self.browse_local_btn = QPushButton(tr("btn_browse"))
        self.browse_local_btn.setMinimumHeight(36)
        self.browse_local_btn.setStyleSheet(self._get_secondary_button_style())
        self.browse_local_btn.clicked.connect(self._browse_local_path)
        local_input_layout.addWidget(self.browse_local_btn)

        local_layout.addLayout(local_input_layout)
        layout.addLayout(local_layout)

        # 云端路径
        remote_layout = QVBoxLayout()
        remote_label = QLabel(tr("remote_path"))
        remote_label.setFont(QFont("SF Pro Display", 14, QFont.Weight.Medium))
        remote_layout.addWidget(remote_label)

        remote_input_layout = QHBoxLayout()
        self.remote_path = QLineEdit()
        self.remote_path.setPlaceholderText(tr("remote_path_placeholder"))
        self.remote_path.setMinimumHeight(36)
        self.remote_path.setStyleSheet(self._get_input_style())
        remote_input_layout.addWidget(self.remote_path)

        self.browse_remote_btn = QPushButton(tr("btn_select"))
        self.browse_remote_btn.setMinimumHeight(36)
        self.browse_remote_btn.setStyleSheet(self._get_secondary_button_style())
        self.browse_remote_btn.clicked.connect(self._browse_remote_path)
        remote_input_layout.addWidget(self.browse_remote_btn)

        remote_layout.addLayout(remote_input_layout)
        layout.addLayout(remote_layout)

        return group

    def _create_sync_options(self) -> QGroupBox:
        """创建同步选项组。"""
        group = QGroupBox(tr("sync_options"))
        group.setFont(QFont("SF Pro Display", 16, QFont.Weight.Medium))
        layout = QVBoxLayout(group)
        layout.setSpacing(12)

        self.auto_sync = QCheckBox(tr("enable_auto_sync"))
        self.auto_sync.setChecked(True)
        self.auto_sync.setFont(QFont("SF Pro Display", 14))
        layout.addWidget(self.auto_sync)

        self.include_hidden = QCheckBox(tr("include_hidden_files"))
        self.include_hidden.setFont(QFont("SF Pro Display", 14))
        layout.addWidget(self.include_hidden)

        self.backup_conflicts = QCheckBox(tr("backup_on_conflict"))
        self.backup_conflicts.setChecked(True)
        self.backup_conflicts.setFont(QFont("SF Pro Display", 14))
        layout.addWidget(self.backup_conflicts)

        return group

    def _create_file_filter(self) -> QGroupBox:
        """创建文件过滤组。"""
        group = QGroupBox(tr("file_filter"))
        group.setFont(QFont("SF Pro Display", 16, QFont.Weight.Medium))
        layout = QVBoxLayout(group)
        layout.setSpacing(12)

        filter_label = QLabel(tr("file_types"))
        filter_label.setFont(QFont("SF Pro Display", 14, QFont.Weight.Medium))
        layout.addWidget(filter_label)

        self.file_patterns = QLineEdit()
        self.file_patterns.setText("*.md, *.txt, *.json, *.html")
        self.file_patterns.setPlaceholderText(tr("file_types_placeholder"))
        self.file_patterns.setMinimumHeight(36)
        self.file_patterns.setStyleSheet(self._get_input_style())
        layout.addWidget(self.file_patterns)

        help_label = QLabel(tr("file_types_help"))
        help_label.setFont(QFont("SF Pro Display", 12))
        help_label.setStyleSheet("color: #8E8E93;")
        layout.addWidget(help_label)

        return group

    def _create_button_section(self) -> QWidget:
        """创建按钮区域。"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 16, 0, 0)

        self.cancel_btn = QPushButton(tr("btn_cancel"))
        self.cancel_btn.setMinimumHeight(40)
        self.cancel_btn.setStyleSheet(self._get_secondary_button_style())
        self.cancel_btn.clicked.connect(self.reject)
        layout.addWidget(self.cancel_btn)

        layout.addStretch()

        self.create_btn = QPushButton(tr("btn_create_sync"))
        self.create_btn.setMinimumHeight(40)
        self.create_btn.setStyleSheet(self._get_primary_button_style())
        self.create_btn.setDefault(True)
        self.create_btn.clicked.connect(self._on_create_clicked)
        layout.addWidget(self.create_btn)

        # 连接信号
        self.name_input.textChanged.connect(self._validate_form)
        self.local_path.textChanged.connect(self._validate_form)
        self.remote_path.textChanged.connect(self._validate_form)

        # 初始验证
        self._validate_form()

        return widget
    
    def _get_input_style(self) -> str:
        """获取输入框样式。"""
        return """
        QLineEdit {
            padding: 8px 12px;
            border: 2px solid #E5E5E7;
            border-radius: 8px;
            font-size: 14px;
            background-color: white;
        }
        QLineEdit:focus {
            border-color: #007AFF;
        }
        QLineEdit:disabled {
            background-color: #F2F2F7;
            color: #8E8E93;
        }
        """

    def _get_combo_style(self) -> str:
        """获取下拉框样式。"""
        return """
        QComboBox {
            padding: 8px 12px;
            border: 2px solid #E5E5E7;
            border-radius: 8px;
            font-size: 14px;
            background-color: white;
        }
        QComboBox:focus {
            border-color: #007AFF;
        }
        QComboBox::drop-down {
            border: none;
            width: 20px;
        }
        QComboBox::down-arrow {
            image: none;
            border-left: 5px solid transparent;
            border-right: 5px solid transparent;
            border-top: 5px solid #8E8E93;
        }
        """

    def _get_primary_button_style(self) -> str:
        """获取主要按钮样式。"""
        return """
        QPushButton {
            background-color: #34C759;
            color: white;
            border: none;
            border-radius: 8px;
            padding: 12px 24px;
            font-weight: 600;
            font-size: 14px;
        }
        QPushButton:hover {
            background-color: #28A745;
        }
        QPushButton:pressed {
            background-color: #1E7E34;
        }
        QPushButton:disabled {
            background-color: #E5E5E7;
            color: #8E8E93;
        }
        """

    def _get_secondary_button_style(self) -> str:
        """获取次要按钮样式。"""
        return """
        QPushButton {
            background-color: #F2F2F7;
            color: #1D1D1F;
            border: none;
            border-radius: 8px;
            padding: 12px 24px;
            font-weight: 500;
            font-size: 14px;
        }
        QPushButton:hover {
            background-color: #E5E5EA;
        }
        QPushButton:pressed {
            background-color: #D1D1D6;
        }
        """

    def _on_sync_type_changed(self, index: int):
        """同步类型变化处理。"""
        descriptions = [
            tr("sync_type_desc_bidirectional"),
            tr("sync_type_desc_local_to_remote"),
            tr("sync_type_desc_remote_to_local")
        ]

        if hasattr(self, 'type_desc'):
            self.type_desc.setText(descriptions[index])
    
    def _browse_local_path(self):
        """浏览本地路径。"""
        path = QFileDialog.getExistingDirectory(
            self,
            "选择本地文件夹",
            self.local_path.text() or str(Path.home())
        )
        if path:
            self.local_path.setText(path)
            
            # 自动生成同步名称
            if not self.name_input.text():
                folder_name = Path(path).name
                self.name_input.setText(f"{folder_name} 同步")
    
    def _browse_remote_path(self):
        """选择云端路径。"""
        if not self.notion_client:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(
                self,
                "未连接",
                "请先连接到 Notion 才能选择云端路径。"
            )
            return

        # 显示 Notion 工作区选择对话框
        result = show_notion_workspace_dialog(self.notion_client, self)

        if result:
            path, page_id = result
            self.remote_path.setText(path)
            # 保存页面ID用于后续同步
            self.remote_path.setProperty("page_id", page_id)
    
    def _validate_form(self):
        """验证表单。"""
        name = self.name_input.text().strip()
        local = self.local_path.text().strip()
        remote = self.remote_path.text().strip()
        
        # 检查必填字段
        is_valid = bool(name and local and remote)
        
        # 检查本地路径是否存在
        if local and not Path(local).exists():
            is_valid = False
        
        self.create_btn.setEnabled(is_valid)
    
    def _on_create_clicked(self):
        """创建按钮点击处理。"""
        sync_config = self.get_sync_config()
        if sync_config:
            self.sync_created.emit(sync_config)
            self.accept()
    
    def get_sync_config(self) -> Optional[dict]:
        """获取同步配置。"""
        name = self.name_input.text().strip()
        local_path = self.local_path.text().strip()
        remote_path = self.remote_path.text().strip()
        
        if not (name and local_path and remote_path):
            return None
        
        # 获取同步类型
        sync_types = ["bidirectional", "local_to_remote", "remote_to_local"]
        sync_type = sync_types[self.sync_type.currentIndex()]
        
        # 解析文件模式
        patterns = [p.strip() for p in self.file_patterns.text().split(",") if p.strip()]
        
        return {
            "name": name,
            "local_path": local_path,
            "remote_path": remote_path,
            "sync_type": sync_type,
            "auto_sync": self.auto_sync.isChecked(),
            "include_hidden": self.include_hidden.isChecked(),
            "backup_conflicts": self.backup_conflicts.isChecked(),
            "file_patterns": patterns,
            "enabled": True
        }


def show_new_sync_dialog(notion_client=None, parent=None) -> Optional[dict]:
    """显示新建同步对话框并返回配置。"""
    dialog = NewSyncDialog(notion_client, parent)
    if dialog.exec() == QDialog.DialogCode.Accepted:
        return dialog.get_sync_config()
    return None
