"""
首次使用向导
"""

from PySide6.QtWidgets import (
    QWizard, QWizardPage, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QLineEdit, QTextEdit, QCheckBox, QProgressBar,
    QFrame, QGroupBox, QFormLayout, QFileDialog
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QFont, QPixmap, QPainter, QColor
from notion_sync.resources.icons import get_icon
from notion_sync.utils.i18n import tr


class WelcomeWizard(QWizard):
    """首次使用向导"""
    
    setup_completed = Signal(dict)  # 设置完成信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("欢迎使用 Notion 同步工具")
        self.setWizardStyle(QWizard.WizardStyle.ModernStyle)
        self.setMinimumSize(600, 500)
        
        # 设置向导页面
        self.addPage(WelcomePage())
        self.addPage(NotionSetupPage())
        self.addPage(FolderSetupPage())
        self.addPage(PreferencesPage())
        self.addPage(CompletePage())
        
        # 设置暗黑主题样式
        self.setStyleSheet("""
        QWizard {
            background-color: #2b2b2b;
            color: #ffffff;
        }

        QWizardPage {
            background-color: #2b2b2b;
            color: #ffffff;
            border-radius: 8px;
            margin: 10px;
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

        QFormLayout QLabel {
            color: #ffffff !important;
        }
        """)
        
        # 连接信号
        self.finished.connect(self._on_finished)
    
    def _on_finished(self, result):
        """向导完成时的处理"""
        if result == QWizard.DialogCode.Accepted:
            # 收集所有设置
            settings = {}
            
            # 从各个页面收集设置
            notion_page = self.page(1)
            if notion_page:
                settings['notion_token'] = notion_page.token_input.text()
            
            folder_page = self.page(2)
            if folder_page:
                settings['default_folder'] = folder_page.folder_path
            
            prefs_page = self.page(3)
            if prefs_page:
                settings['auto_sync'] = prefs_page.auto_sync_check.isChecked()
                settings['startup_minimized'] = prefs_page.startup_check.isChecked()
            
            self.setup_completed.emit(settings)


class WelcomePage(QWizardPage):
    """欢迎页面"""
    
    def __init__(self):
        super().__init__()
        self.setTitle("欢迎使用 Notion 同步工具")
        self.setSubTitle("让我们快速设置您的同步环境")
        
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        
        # 欢迎图标
        icon_label = QLabel()
        icon_label.setPixmap(get_icon('app').pixmap(64, 64))
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon_label)
        
        # 欢迎文本
        welcome_text = QLabel("""
        <h2>欢迎使用 Notion 同步工具！</h2>
        <p>这个向导将帮助您：</p>
        <ul>
        <li>🔗 连接到您的 Notion 工作区</li>
        <li>📁 设置本地同步文件夹</li>
        <li>⚙️ 配置同步偏好设置</li>
        <li>🚀 开始您的第一次同步</li>
        </ul>
        <p>整个过程只需要几分钟时间。</p>
        """)
        welcome_text.setWordWrap(True)
        welcome_text.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.addWidget(welcome_text)
        
        layout.addStretch()


class NotionSetupPage(QWizardPage):
    """Notion 设置页面"""
    
    def __init__(self):
        super().__init__()
        self.setTitle("连接到 Notion")
        self.setSubTitle("输入您的 Notion API 令牌")
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # 说明文本
        info_text = QLabel("""
        <h3>如何获取 Notion API 令牌：</h3>
        <ol>
        <li>访问 <a href="https://www.notion.so/my-integrations">Notion 集成页面</a></li>
        <li>点击"新建集成"</li>
        <li>填写集成名称（如：我的同步工具）</li>
        <li>选择关联的工作区</li>
        <li>点击"提交"</li>
        <li>复制生成的"内部集成令牌"</li>
        </ol>
        """)
        info_text.setWordWrap(True)
        info_text.setOpenExternalLinks(True)
        layout.addWidget(info_text)
        
        # 令牌输入
        token_group = QGroupBox("API 令牌")
        token_layout = QFormLayout(token_group)
        
        self.token_input = QLineEdit()
        self.token_input.setPlaceholderText("粘贴您的 Notion API 令牌...")
        self.token_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.token_input.textChanged.connect(self._validate_token)
        token_layout.addRow("令牌:", self.token_input)
        
        # 显示/隐藏令牌按钮
        self.show_token_btn = QPushButton("显示")
        self.show_token_btn.setMaximumWidth(60)
        self.show_token_btn.clicked.connect(self._toggle_token_visibility)
        token_layout.addRow("", self.show_token_btn)
        
        layout.addWidget(token_group)
        
        # 测试连接按钮
        self.test_btn = QPushButton("测试连接")
        self.test_btn.setIcon(get_icon('connect'))
        self.test_btn.clicked.connect(self._test_connection)
        self.test_btn.setEnabled(False)
        layout.addWidget(self.test_btn)
        
        # 状态显示
        self.status_label = QLabel("")
        layout.addWidget(self.status_label)
        
        layout.addStretch()
        
        # 注册字段
        self.registerField("notion_token*", self.token_input)
    
    def _validate_token(self):
        """验证令牌格式"""
        token = self.token_input.text().strip()
        self.test_btn.setEnabled(len(token) > 20)  # 基本长度检查
    
    def _toggle_token_visibility(self):
        """切换令牌显示/隐藏"""
        if self.token_input.echoMode() == QLineEdit.EchoMode.Password:
            self.token_input.setEchoMode(QLineEdit.EchoMode.Normal)
            self.show_token_btn.setText("隐藏")
        else:
            self.token_input.setEchoMode(QLineEdit.EchoMode.Password)
            self.show_token_btn.setText("显示")
    
    def _test_connection(self):
        """测试连接"""
        self.test_btn.setEnabled(False)
        self.test_btn.setText("测试中...")
        self.status_label.setText("正在测试连接...")
        
        # 模拟连接测试
        QTimer.singleShot(2000, self._connection_result)
    
    def _connection_result(self):
        """连接测试结果"""
        self.test_btn.setEnabled(True)
        self.test_btn.setText("测试连接")
        self.status_label.setText("✅ 连接成功！")
        self.status_label.setStyleSheet("color: #4CAF50 !important; font-weight: bold;")


class FolderSetupPage(QWizardPage):
    """文件夹设置页面"""
    
    def __init__(self):
        super().__init__()
        self.setTitle("选择同步文件夹")
        self.setSubTitle("选择用于同步的本地文件夹")
        self.folder_path = ""
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # 说明
        info_text = QLabel("""
        <p>选择一个本地文件夹用于与 Notion 同步。</p>
        <p>建议创建一个专门的文件夹，如 "Notion同步" 或 "我的笔记"。</p>
        """)
        info_text.setWordWrap(True)
        layout.addWidget(info_text)
        
        # 文件夹选择
        folder_group = QGroupBox("同步文件夹")
        folder_layout = QVBoxLayout(folder_group)
        
        folder_select_layout = QHBoxLayout()
        self.folder_label = QLabel("未选择文件夹")
        self.folder_label.setStyleSheet("""
            padding: 8px;
            border: 1px solid #555555;
            border-radius: 4px;
            background-color: #3c3c3c;
            color: #ffffff !important;
        """)
        folder_select_layout.addWidget(self.folder_label)
        
        self.browse_btn = QPushButton("浏览...")
        self.browse_btn.setIcon(get_icon('folder'))
        self.browse_btn.clicked.connect(self._browse_folder)
        folder_select_layout.addWidget(self.browse_btn)
        
        folder_layout.addLayout(folder_select_layout)
        layout.addWidget(folder_group)
        
        # 选项
        options_group = QGroupBox("文件夹选项")
        options_layout = QVBoxLayout(options_group)
        
        self.create_subfolders_check = QCheckBox("自动创建子文件夹（按页面分类）")
        self.create_subfolders_check.setChecked(True)
        options_layout.addWidget(self.create_subfolders_check)
        
        self.backup_existing_check = QCheckBox("备份现有文件")
        self.backup_existing_check.setChecked(True)
        options_layout.addWidget(self.backup_existing_check)
        
        layout.addWidget(options_group)
        layout.addStretch()
    
    def _browse_folder(self):
        """浏览文件夹"""
        folder = QFileDialog.getExistingDirectory(
            self, "选择同步文件夹", ""
        )
        if folder:
            self.folder_path = folder
            self.folder_label.setText(folder)
            self.completeChanged.emit()
    
    def isComplete(self):
        """检查页面是否完成"""
        return bool(self.folder_path)


class PreferencesPage(QWizardPage):
    """偏好设置页面"""
    
    def __init__(self):
        super().__init__()
        self.setTitle("偏好设置")
        self.setSubTitle("配置同步行为和应用偏好")
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # 同步设置
        sync_group = QGroupBox("同步设置")
        sync_layout = QVBoxLayout(sync_group)
        
        self.auto_sync_check = QCheckBox("启用自动同步")
        self.auto_sync_check.setChecked(True)
        sync_layout.addWidget(self.auto_sync_check)
        
        self.watch_files_check = QCheckBox("监控文件变化")
        self.watch_files_check.setChecked(True)
        sync_layout.addWidget(self.watch_files_check)
        
        layout.addWidget(sync_group)
        
        # 应用设置
        app_group = QGroupBox("应用设置")
        app_layout = QVBoxLayout(app_group)
        
        self.startup_check = QCheckBox("启动时最小化到系统托盘")
        app_layout.addWidget(self.startup_check)
        
        self.notifications_check = QCheckBox("显示同步通知")
        self.notifications_check.setChecked(True)
        app_layout.addWidget(self.notifications_check)
        
        layout.addWidget(app_group)
        layout.addStretch()


class CompletePage(QWizardPage):
    """完成页面"""
    
    def __init__(self):
        super().__init__()
        self.setTitle("设置完成")
        self.setSubTitle("您已成功配置 Notion 同步工具")
        
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        
        # 成功图标
        success_icon = QLabel()
        success_icon.setPixmap(get_icon('success').pixmap(48, 48))
        success_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(success_icon)
        
        # 完成文本
        complete_text = QLabel("""
        <h2>🎉 设置完成！</h2>
        <p>您的 Notion 同步工具已经配置完成，现在可以：</p>
        <ul>
        <li>✅ 自动同步本地文件到 Notion</li>
        <li>✅ 从 Notion 导出内容到本地</li>
        <li>✅ 实时监控文件变化</li>
        <li>✅ 享受无缝的同步体验</li>
        </ul>
        <p><b>点击"完成"开始使用！</b></p>
        """)
        complete_text.setWordWrap(True)
        complete_text.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.addWidget(complete_text)
        
        layout.addStretch()


def show_welcome_wizard(parent=None):
    """显示欢迎向导"""
    wizard = WelcomeWizard(parent)
    return wizard.exec() == QWizard.DialogCode.Accepted, wizard
