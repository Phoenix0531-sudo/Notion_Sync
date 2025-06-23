"""
导出对话框 - 专注于从 Notion 导出到本地
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QFileDialog, QComboBox, QCheckBox, QGroupBox,
    QFormLayout, QTextEdit, QProgressBar, QMessageBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from notion_sync.resources.icons import get_icon


class ExportDialog(QDialog):
    """导出对话框"""
    
    export_requested = Signal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("导出 Notion 内容")
        self.setMinimumSize(600, 500)
        self.setModal(True)
        
        self._setup_ui()
        self._apply_dark_theme()
        self._setup_connections()
    
    def _setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        
        # 标题
        title_label = QLabel("从 Notion 导出内容到本地")
        title_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)
        
        # 导出源设置
        source_group = QGroupBox("选择导出内容")
        source_layout = QFormLayout(source_group)
        
        # Notion 工作区选择
        self.workspace_combo = QComboBox()
        self.workspace_combo.addItems(["当前工作区", "选择特定页面", "选择数据库"])
        source_layout.addRow("导出范围:", self.workspace_combo)
        
        # 特定页面/数据库选择
        self.content_combo = QComboBox()
        self.content_combo.setEnabled(False)
        source_layout.addRow("具体内容:", self.content_combo)
        
        layout.addWidget(source_group)
        
        # 导出目标设置
        target_group = QGroupBox("选择导出位置")
        target_layout = QFormLayout(target_group)
        
        # 本地文件夹选择
        folder_layout = QHBoxLayout()
        self.folder_edit = QLineEdit()
        self.folder_edit.setPlaceholderText("选择导出到的本地文件夹...")
        folder_layout.addWidget(self.folder_edit)
        
        self.browse_btn = QPushButton("浏览")
        self.browse_btn.setIcon(get_icon('folder'))
        self.browse_btn.clicked.connect(self._browse_folder)
        folder_layout.addWidget(self.browse_btn)
        
        target_layout.addRow("本地文件夹:", folder_layout)
        
        layout.addWidget(target_group)
        
        # 导出选项
        options_group = QGroupBox("导出选项")
        options_layout = QFormLayout(options_group)
        
        # 文件格式
        self.format_combo = QComboBox()
        self.format_combo.addItems(["Markdown (.md)", "HTML (.html)", "纯文本 (.txt)"])
        options_layout.addRow("文件格式:", self.format_combo)
        
        # 包含选项
        self.include_images_check = QCheckBox("包含图片")
        self.include_images_check.setChecked(True)
        options_layout.addRow("", self.include_images_check)
        
        self.include_attachments_check = QCheckBox("包含附件")
        self.include_attachments_check.setChecked(True)
        options_layout.addRow("", self.include_attachments_check)
        
        self.preserve_structure_check = QCheckBox("保持文件夹结构")
        self.preserve_structure_check.setChecked(True)
        options_layout.addRow("", self.preserve_structure_check)
        
        layout.addWidget(options_group)
        
        # 进度显示
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        self.status_label = QLabel("")
        self.status_label.setVisible(False)
        layout.addWidget(self.status_label)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        
        self.preview_btn = QPushButton("预览")
        self.preview_btn.setIcon(get_icon('info'))
        self.preview_btn.clicked.connect(self._preview_export)
        button_layout.addWidget(self.preview_btn)
        
        button_layout.addStretch()
        
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)
        
        self.export_btn = QPushButton("开始导出")
        self.export_btn.setIcon(get_icon('download'))
        self.export_btn.setDefault(True)
        self.export_btn.clicked.connect(self._start_export)
        button_layout.addWidget(self.export_btn)
        
        layout.addLayout(button_layout)
    
    def _apply_dark_theme(self):
        """应用暗黑主题"""
        dark_style = """
        QDialog {
            background-color: #2b2b2b;
            color: #ffffff;
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
        
        QProgressBar {
            border: 1px solid #555555;
            border-radius: 4px;
            background-color: #3c3c3c;
            text-align: center;
            color: #ffffff;
        }
        
        QProgressBar::chunk {
            background-color: #007AFF;
            border-radius: 3px;
        }
        """
        self.setStyleSheet(dark_style)
    
    def _setup_connections(self):
        """设置信号连接"""
        self.workspace_combo.currentTextChanged.connect(self._on_workspace_changed)
    
    def _browse_folder(self):
        """浏览文件夹"""
        folder = QFileDialog.getExistingDirectory(self, "选择导出文件夹")
        if folder:
            self.folder_edit.setText(folder)
    
    def _on_workspace_changed(self, text):
        """工作区选择改变"""
        if text == "当前工作区":
            self.content_combo.setEnabled(False)
            self.content_combo.clear()
        else:
            self.content_combo.setEnabled(True)
            if text == "选择特定页面":
                self.content_combo.clear()
                self.content_combo.addItems(["页面 1", "页面 2", "页面 3"])  # 这里应该从 Notion 获取
            elif text == "选择数据库":
                self.content_combo.clear()
                self.content_combo.addItems(["数据库 1", "数据库 2"])  # 这里应该从 Notion 获取
    
    def _preview_export(self):
        """预览导出"""
        if not self.folder_edit.text():
            QMessageBox.warning(self, "警告", "请先选择导出文件夹")
            return
        
        # 显示预览信息
        preview_text = f"""
导出预览:

导出范围: {self.workspace_combo.currentText()}
导出位置: {self.folder_edit.text()}
文件格式: {self.format_combo.currentText()}

选项:
- 包含图片: {'是' if self.include_images_check.isChecked() else '否'}
- 包含附件: {'是' if self.include_attachments_check.isChecked() else '否'}
- 保持结构: {'是' if self.preserve_structure_check.isChecked() else '否'}

预计导出文件数量: 约 10-50 个文件
预计用时: 2-5 分钟
        """
        
        QMessageBox.information(self, "导出预览", preview_text)
    
    def _start_export(self):
        """开始导出"""
        if not self.folder_edit.text():
            QMessageBox.warning(self, "警告", "请先选择导出文件夹")
            return
        
        # 收集导出参数
        export_params = {
            "source_type": self.workspace_combo.currentText(),
            "target_folder": self.folder_edit.text(),
            "file_format": self.format_combo.currentText(),
            "include_images": self.include_images_check.isChecked(),
            "include_attachments": self.include_attachments_check.isChecked(),
            "preserve_structure": self.preserve_structure_check.isChecked()
        }
        
        # 发送导出请求信号
        self.export_requested.emit(export_params)
        
        # 显示进度
        self.progress_bar.setVisible(True)
        self.status_label.setVisible(True)
        self.status_label.setText("正在准备导出...")
        
        # 禁用按钮
        self.export_btn.setEnabled(False)
        self.cancel_btn.setText("停止")
    
    def update_progress(self, value: int, message: str = ""):
        """更新进度"""
        self.progress_bar.setValue(value)
        if message:
            self.status_label.setText(message)
    
    def export_completed(self, success: bool, message: str = ""):
        """导出完成"""
        self.progress_bar.setVisible(False)
        self.status_label.setVisible(False)
        self.export_btn.setEnabled(True)
        self.cancel_btn.setText("关闭")
        
        if success:
            QMessageBox.information(self, "导出完成", message or "导出成功完成！")
            self.accept()
        else:
            QMessageBox.warning(self, "导出失败", message or "导出过程中发生错误")


def show_export_dialog(parent=None) -> tuple[bool, dict]:
    """显示导出对话框"""
    dialog = ExportDialog(parent)
    
    export_params = {}
    
    def on_export_requested(params):
        nonlocal export_params
        export_params = params
    
    dialog.export_requested.connect(on_export_requested)
    
    result = dialog.exec()
    return result == QDialog.DialogCode.Accepted, export_params
