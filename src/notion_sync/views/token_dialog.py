"""
API 令牌输入对话框。
"""

from typing import Optional
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QTextEdit, QFrame
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from notion_sync.utils.i18n import tr


class TokenInputDialog(QDialog):
    """API 令牌输入对话框。"""
    
    # 信号
    token_entered = Signal(str)  # 令牌输入完成
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("connect_to_notion"))
        self.setModal(True)
        self.setFixedSize(500, 400)
        
        self._setup_ui()
    
    def _setup_ui(self):
        """设置界面。"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)
        
        # 标题
        title_label = QLabel(tr("connect_to_notion"))
        title_label.setFont(QFont("SF Pro Display", 18, QFont.Weight.Bold))
        title_label.setStyleSheet("color: #1D1D1F; margin-bottom: 8px;")
        layout.addWidget(title_label)
        
        # 说明文本
        info_text = QTextEdit()
        info_text.setReadOnly(True)
        info_text.setMaximumHeight(120)
        info_text.setHtml("""
        <p>要连接到云端服务，您需要提供 API 令牌。</p>
        <p><b>获取步骤：</b></p>
        <ol>
        <li>访问 <a href="https://www.notion.so/my-integrations">https://www.notion.so/my-integrations</a></li>
        <li>点击"新建集成"</li>
        <li>填写集成信息并创建</li>
        <li>复制生成的"内部集成令牌"</li>
        </ol>
        """)
        layout.addWidget(info_text)
        
        # 令牌输入
        token_layout = QVBoxLayout()
        token_label = QLabel("API 令牌:")
        token_label.setFont(QFont("SF Pro Display", 14, QFont.Weight.Medium))
        token_layout.addWidget(token_label)
        
        self.token_input = QLineEdit()
        self.token_input.setPlaceholderText("secret_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx")
        self.token_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.token_input.setStyleSheet("""
        QLineEdit {
            padding: 8px 12px;
            border: 2px solid #E5E5E7;
            border-radius: 6px;
            font-size: 14px;
        }
        QLineEdit:focus {
            border-color: #007AFF;
        }
        """)
        token_layout.addWidget(self.token_input)
        
        # 显示/隐藏令牌按钮
        show_hide_layout = QHBoxLayout()
        self.show_token_btn = QPushButton("显示令牌")
        self.show_token_btn.setCheckable(True)
        self.show_token_btn.clicked.connect(self._toggle_token_visibility)
        self.show_token_btn.setStyleSheet("""
        QPushButton {
            background: none;
            border: none;
            color: #007AFF;
            text-decoration: underline;
            padding: 4px;
        }
        QPushButton:hover {
            color: #0056CC;
        }
        """)
        show_hide_layout.addWidget(self.show_token_btn)
        show_hide_layout.addStretch()
        token_layout.addLayout(show_hide_layout)
        
        layout.addLayout(token_layout)
        
        # 按钮
        button_layout = QHBoxLayout()
        
        self.cancel_btn = QPushButton(tr("btn_cancel"))
        self.cancel_btn.clicked.connect(self.reject)
        self.cancel_btn.setStyleSheet("""
        QPushButton {
            background-color: #F2F2F7;
            color: #1D1D1F;
            border: none;
            border-radius: 6px;
            padding: 10px 20px;
            font-weight: 500;
        }
        QPushButton:hover {
            background-color: #E5E5EA;
        }
        """)
        button_layout.addWidget(self.cancel_btn)
        
        button_layout.addStretch()
        
        self.connect_btn = QPushButton(tr("btn_connect"))
        self.connect_btn.clicked.connect(self._on_connect_clicked)
        self.connect_btn.setDefault(True)
        self.connect_btn.setStyleSheet("""
        QPushButton {
            background-color: #007AFF;
            color: white;
            border: none;
            border-radius: 6px;
            padding: 10px 20px;
            font-weight: 500;
        }
        QPushButton:hover {
            background-color: #0056CC;
        }
        QPushButton:disabled {
            background-color: #E5E5E7;
            color: #8E8E93;
        }
        """)
        button_layout.addWidget(self.connect_btn)
        
        layout.addLayout(button_layout)
        
        # 连接信号
        self.token_input.textChanged.connect(self._on_token_changed)
        self.token_input.returnPressed.connect(self._on_connect_clicked)
        
        # 初始状态
        self._on_token_changed()
    
    def _toggle_token_visibility(self):
        """切换令牌显示/隐藏。"""
        if self.show_token_btn.isChecked():
            self.token_input.setEchoMode(QLineEdit.EchoMode.Normal)
            self.show_token_btn.setText("隐藏令牌")
        else:
            self.token_input.setEchoMode(QLineEdit.EchoMode.Password)
            self.show_token_btn.setText("显示令牌")
    
    def _on_token_changed(self):
        """令牌输入变化处理。"""
        token = self.token_input.text().strip()
        # 检查令牌格式 - Notion API 令牌通常以 "secret_" 开头，但也可能有其他格式
        # 放宽验证条件，只要不为空且长度合理即可
        is_valid = len(token) >= 10  # 最小长度检查
        self.connect_btn.setEnabled(is_valid)
    
    def _on_connect_clicked(self):
        """连接按钮点击处理。"""
        token = self.token_input.text().strip()
        if token:
            self.token_entered.emit(token)
            self.accept()
    
    def get_token(self) -> str:
        """获取输入的令牌。"""
        return self.token_input.text().strip()
    
    def set_token(self, token: str):
        """设置令牌。"""
        self.token_input.setText(token)
    
    def clear_token(self):
        """清除令牌。"""
        self.token_input.clear()


def show_token_dialog(parent=None) -> Optional[str]:
    """显示令牌输入对话框并返回令牌。"""
    dialog = TokenInputDialog(parent)
    if dialog.exec() == QDialog.DialogCode.Accepted:
        return dialog.get_token()
    return None
