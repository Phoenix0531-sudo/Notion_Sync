"""
冲突解决对话框。
"""

from typing import Optional, Dict, Any
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QTextEdit, QRadioButton, QButtonGroup, QGroupBox,
    QScrollArea, QWidget
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from notion_sync.models.sync_engine import ConflictResolution


class ConflictDialog(QDialog):
    """冲突解决对话框。"""
    
    resolution_selected = Signal(str)  # resolution type
    
    def __init__(self, conflict_data: Dict[str, Any], parent: Optional[QWidget] = None):
        """初始化冲突对话框。"""
        super().__init__(parent)
        self.conflict_data = conflict_data
        self.selected_resolution = ConflictResolution.ASK_USER
        
        self._setup_ui()
        self._load_conflict_data()
    
    def _setup_ui(self) -> None:
        """设置对话框 UI。"""
        self.setWindowTitle("同步冲突")
        self.setModal(True)
        self.setMinimumSize(600, 500)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)
        
        # 标题
        title_label = QLabel("检测到同步冲突")
        title_label.setFont(QFont("SF Pro Display", 18, QFont.Weight.Bold))
        title_label.setStyleSheet("color: #FF3B30; margin-bottom: 8px;")
        layout.addWidget(title_label)
        
        # 描述
        desc_label = QLabel("本地文件和 Notion 内容都已修改，请选择如何解决此冲突：")
        desc_label.setFont(QFont("SF Pro Display", 14))
        desc_label.setStyleSheet("color: #1D1D1F; margin-bottom: 16px;")
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)
        
        # 冲突详情
        details_frame = self._create_conflict_details()
        layout.addWidget(details_frame)
        
        # 解决选项
        resolution_frame = self._create_resolution_options()
        layout.addWidget(resolution_frame)
        
        # 按钮
        button_layout = QHBoxLayout()
        
        cancel_button = QPushButton("取消")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)
        
        button_layout.addStretch()
        
        apply_button = QPushButton("应用解决方案")
        apply_button.setStyleSheet("""
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
        """)
        apply_button.clicked.connect(self._apply_resolution)
        button_layout.addWidget(apply_button)
        
        layout.addLayout(button_layout)
    
    def _create_conflict_details(self) -> QFrame:
        """创建冲突详情面板。"""
        frame = QFrame()
        frame.setFrameStyle(QFrame.StyledPanel)
        frame.setStyleSheet("""
        QFrame {
            background-color: #F8F9FA;
            border: 1px solid #E5E5E7;
            border-radius: 8px;
            padding: 16px;
        }
        """)
        
        layout = QVBoxLayout(frame)
        layout.setSpacing(12)
        
        # 文件路径
        path_label = QLabel("文件路径:")
        path_label.setFont(QFont("SF Pro Display", 12, QFont.Weight.Medium))
        layout.addWidget(path_label)
        
        self.path_value = QLabel()
        self.path_value.setStyleSheet("color: #3C3C43; font-family: monospace;")
        layout.addWidget(self.path_value)
        
        # 分割线
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet("color: #D1D1D6;")
        layout.addWidget(separator)
        
        # 内容比较
        compare_layout = QHBoxLayout()
        
        # 本地内容
        local_group = QGroupBox("本地文件")
        local_layout = QVBoxLayout(local_group)
        
        self.local_info = QLabel()
        self.local_info.setStyleSheet("color: #8E8E93; font-size: 12px;")
        local_layout.addWidget(self.local_info)
        
        self.local_content = QTextEdit()
        self.local_content.setMaximumHeight(150)
        self.local_content.setReadOnly(True)
        local_layout.addWidget(self.local_content)
        
        compare_layout.addWidget(local_group)
        
        # Notion 内容
        notion_group = QGroupBox("Notion 内容")
        notion_layout = QVBoxLayout(notion_group)
        
        self.notion_info = QLabel()
        self.notion_info.setStyleSheet("color: #8E8E93; font-size: 12px;")
        notion_layout.addWidget(self.notion_info)
        
        self.notion_content = QTextEdit()
        self.notion_content.setMaximumHeight(150)
        self.notion_content.setReadOnly(True)
        notion_layout.addWidget(self.notion_content)
        
        compare_layout.addWidget(notion_group)
        
        layout.addLayout(compare_layout)
        
        return frame
    
    def _create_resolution_options(self) -> QFrame:
        """创建解决选项面板。"""
        frame = QFrame()
        frame.setFrameStyle(QFrame.StyledPanel)
        frame.setStyleSheet("""
        QFrame {
            background-color: #FFFFFF;
            border: 1px solid #E5E5E7;
            border-radius: 8px;
            padding: 16px;
        }
        """)
        
        layout = QVBoxLayout(frame)
        layout.setSpacing(12)
        
        # 标题
        title_label = QLabel("解决方案:")
        title_label.setFont(QFont("SF Pro Display", 14, QFont.Weight.Medium))
        layout.addWidget(title_label)
        
        # 单选按钮组
        self.resolution_group = QButtonGroup()
        
        # 本地文件优先
        self.local_wins_radio = QRadioButton("使用本地文件（覆盖 Notion 内容）")
        self.local_wins_radio.setStyleSheet("font-size: 13px; padding: 4px;")
        self.resolution_group.addButton(self.local_wins_radio, 0)
        layout.addWidget(self.local_wins_radio)
        
        local_desc = QLabel("将本地文件的内容上传到 Notion，覆盖现有内容")
        local_desc.setStyleSheet("color: #8E8E93; font-size: 11px; margin-left: 20px; margin-bottom: 8px;")
        layout.addWidget(local_desc)
        
        # Notion 内容优先
        self.notion_wins_radio = QRadioButton("使用 Notion 内容（覆盖本地文件）")
        self.notion_wins_radio.setStyleSheet("font-size: 13px; padding: 4px;")
        self.resolution_group.addButton(self.notion_wins_radio, 1)
        layout.addWidget(self.notion_wins_radio)
        
        notion_desc = QLabel("将 Notion 内容下载到本地，覆盖现有文件")
        notion_desc.setStyleSheet("color: #8E8E93; font-size: 11px; margin-left: 20px; margin-bottom: 8px;")
        layout.addWidget(notion_desc)
        
        # 保留两个版本
        self.create_both_radio = QRadioButton("保留两个版本")
        self.create_both_radio.setStyleSheet("font-size: 13px; padding: 4px;")
        self.resolution_group.addButton(self.create_both_radio, 2)
        layout.addWidget(self.create_both_radio)
        
        both_desc = QLabel("创建带时间戳的副本，保留两个版本")
        both_desc.setStyleSheet("color: #8E8E93; font-size: 11px; margin-left: 20px; margin-bottom: 8px;")
        layout.addWidget(both_desc)
        
        # 跳过此文件
        self.skip_radio = QRadioButton("跳过此文件")
        self.skip_radio.setStyleSheet("font-size: 13px; padding: 4px;")
        self.resolution_group.addButton(self.skip_radio, 3)
        layout.addWidget(self.skip_radio)
        
        skip_desc = QLabel("暂时跳过此文件，不进行同步")
        skip_desc.setStyleSheet("color: #8E8E93; font-size: 11px; margin-left: 20px;")
        layout.addWidget(skip_desc)
        
        # 默认选择本地文件优先
        self.local_wins_radio.setChecked(True)
        
        return frame
    
    def _load_conflict_data(self) -> None:
        """加载冲突数据到界面。"""
        # 设置文件路径
        local_path = self.conflict_data.get("local_path", "")
        self.path_value.setText(local_path)
        
        # 加载本地文件信息
        try:
            from pathlib import Path
            local_file = Path(local_path)
            if local_file.exists():
                stat = local_file.stat()
                modified_time = stat.st_mtime
                file_size = stat.st_size
                
                from datetime import datetime
                modified_str = datetime.fromtimestamp(modified_time).strftime("%Y-%m-%d %H:%M:%S")
                size_str = self._format_file_size(file_size)
                
                self.local_info.setText(f"修改时间: {modified_str} | 大小: {size_str}")
                
                # 读取文件内容（限制长度）
                try:
                    with open(local_file, 'r', encoding='utf-8') as f:
                        content = f.read(1000)  # 只读取前1000个字符
                        if len(content) == 1000:
                            content += "..."
                        self.local_content.setPlainText(content)
                except:
                    self.local_content.setPlainText("无法读取文件内容")
            else:
                self.local_info.setText("文件不存在")
                self.local_content.setPlainText("文件已被删除")
        except Exception as e:
            self.local_info.setText(f"读取失败: {str(e)}")
        
        # 加载 Notion 信息（这里需要从冲突数据中获取）
        notion_id = self.conflict_data.get("notion_id", "")
        self.notion_info.setText(f"Notion ID: {notion_id}")
        self.notion_content.setPlainText("Notion 内容预览...")
    
    def _format_file_size(self, size_bytes: int) -> str:
        """格式化文件大小。"""
        if size_bytes == 0:
            return "0 B"
        
        size_names = ["B", "KB", "MB", "GB"]
        import math
        i = int(math.floor(math.log(size_bytes, 1024)))
        p = math.pow(1024, i)
        s = round(size_bytes / p, 2)
        return f"{s} {size_names[i]}"
    
    def _apply_resolution(self) -> None:
        """应用选择的解决方案。"""
        checked_id = self.resolution_group.checkedId()
        
        if checked_id == 0:
            self.selected_resolution = ConflictResolution.LOCAL_WINS
        elif checked_id == 1:
            self.selected_resolution = ConflictResolution.NOTION_WINS
        elif checked_id == 2:
            self.selected_resolution = ConflictResolution.CREATE_BOTH
        else:
            self.selected_resolution = ConflictResolution.SKIP
        
        self.resolution_selected.emit(self.selected_resolution.value)
        self.accept()
    
    def get_resolution(self) -> ConflictResolution:
        """获取选择的解决方案。"""
        return self.selected_resolution
