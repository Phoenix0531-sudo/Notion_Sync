"""
Notion 工作区选择对话框。
"""

from typing import Optional, Dict, Any, List
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTreeWidget, QTreeWidgetItem, QLineEdit, QProgressBar,
    QMessageBox, QWidget
)
from PySide6.QtCore import Qt, Signal, QThread
from PySide6.QtGui import QFont, QIcon

from notion_sync.utils.i18n import tr
from notion_sync.utils.logging_config import LoggerMixin


class WorkspaceLoader(QThread, LoggerMixin):
    """工作区加载线程。"""
    
    # 信号
    workspace_loaded = Signal(dict)
    loading_progress = Signal(int, str)
    loading_error = Signal(str)
    
    def __init__(self, notion_client):
        super().__init__()
        self.notion_client = notion_client
    
    def run(self):
        """加载工作区数据。"""
        try:
            self.loading_progress.emit(10, "正在连接到 Notion...")
            
            if not self.notion_client or not self.notion_client.connected:
                self.loading_error.emit("未连接到 Notion")
                return
            
            self.loading_progress.emit(30, "正在获取页面列表...")
            pages = self.notion_client.list_pages()
            
            self.loading_progress.emit(60, "正在获取数据库列表...")
            databases = self.notion_client.list_databases()
            
            self.loading_progress.emit(90, "正在整理数据...")
            
            workspace_data = {
                "pages": [page.to_dict() for page in pages],
                "databases": [db.to_dict() for db in databases]
            }
            
            self.loading_progress.emit(100, "加载完成")
            self.workspace_loaded.emit(workspace_data)
            
        except Exception as e:
            self.logger.error(f"加载工作区失败: {e}")
            self.loading_error.emit(f"加载工作区失败: {str(e)}")


class NotionWorkspaceDialog(QDialog, LoggerMixin):
    """Notion 工作区选择对话框。"""
    
    # 信号
    path_selected = Signal(str, str)  # path, page_id
    
    def __init__(self, notion_client, parent=None):
        super().__init__(parent)
        self.notion_client = notion_client
        self.selected_path = ""
        self.selected_page_id = ""
        
        self.setWindowTitle("选择 Notion 工作区路径")
        self.setModal(True)
        self.setMinimumSize(500, 600)
        self.resize(600, 700)
        
        self._setup_ui()
        self._load_workspace()
    
    def _setup_ui(self):
        """设置界面。"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)
        
        # 标题
        title_label = QLabel("选择 Notion 工作区路径")
        title_label.setFont(QFont("SF Pro Display", 18, QFont.Weight.Bold))
        title_label.setStyleSheet("color: #1D1D1F; margin-bottom: 8px;")
        layout.addWidget(title_label)
        
        # 说明
        desc_label = QLabel("选择要同步的 Notion 页面或数据库")
        desc_label.setFont(QFont("SF Pro Display", 14))
        desc_label.setStyleSheet("color: #8E8E93;")
        layout.addWidget(desc_label)
        
        # 搜索框
        search_layout = QHBoxLayout()
        search_label = QLabel("搜索:")
        search_label.setFont(QFont("SF Pro Display", 14))
        search_layout.addWidget(search_label)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("输入页面或数据库名称...")
        self.search_input.setStyleSheet(self._get_input_style())
        self.search_input.textChanged.connect(self._filter_items)
        search_layout.addWidget(self.search_input)
        layout.addLayout(search_layout)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # 工作区树
        self.workspace_tree = QTreeWidget()
        self.workspace_tree.setHeaderLabels(["名称", "类型", "路径"])
        self.workspace_tree.setStyleSheet(self._get_tree_style())
        self.workspace_tree.itemClicked.connect(self._on_item_clicked)
        self.workspace_tree.itemDoubleClicked.connect(self._on_item_double_clicked)
        layout.addWidget(self.workspace_tree)
        
        # 选中路径显示
        path_layout = QVBoxLayout()
        path_label = QLabel("选中的路径:")
        path_label.setFont(QFont("SF Pro Display", 14, QFont.Weight.Medium))
        path_layout.addWidget(path_label)
        
        self.selected_path_label = QLabel("未选择")
        self.selected_path_label.setStyleSheet("""
        QLabel {
            background-color: #F2F2F7;
            border: 1px solid #E5E5E7;
            border-radius: 6px;
            padding: 8px 12px;
            font-family: 'SF Mono', monospace;
            font-size: 13px;
        }
        """)
        path_layout.addWidget(self.selected_path_label)
        layout.addLayout(path_layout)
        
        # 按钮
        button_layout = QHBoxLayout()
        
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.setStyleSheet(self._get_secondary_button_style())
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)
        
        button_layout.addStretch()
        
        self.select_btn = QPushButton("选择")
        self.select_btn.setStyleSheet(self._get_primary_button_style())
        self.select_btn.setEnabled(False)
        self.select_btn.clicked.connect(self._on_select_clicked)
        button_layout.addWidget(self.select_btn)
        
        layout.addLayout(button_layout)
    
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
        """
    
    def _get_tree_style(self) -> str:
        """获取树形控件样式。"""
        return """
        QTreeWidget {
            border: 2px solid #E5E5E7;
            border-radius: 8px;
            background-color: white;
            font-size: 14px;
        }
        QTreeWidget::item {
            padding: 8px;
            border-bottom: 1px solid #F2F2F7;
        }
        QTreeWidget::item:selected {
            background-color: #007AFF;
            color: white;
        }
        QTreeWidget::item:hover {
            background-color: #F2F2F7;
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
        """
    
    def _load_workspace(self):
        """加载工作区数据。"""
        self.progress_bar.setVisible(True)
        self.workspace_tree.setEnabled(False)
        
        # 创建加载线程
        self.loader = WorkspaceLoader(self.notion_client)
        self.loader.workspace_loaded.connect(self._on_workspace_loaded)
        self.loader.loading_progress.connect(self._on_loading_progress)
        self.loader.loading_error.connect(self._on_loading_error)
        self.loader.start()
    
    def _on_workspace_loaded(self, workspace_data: Dict[str, Any]):
        """工作区加载完成。"""
        self.progress_bar.setVisible(False)
        self.workspace_tree.setEnabled(True)
        
        # 清空树
        self.workspace_tree.clear()
        
        # 添加页面
        if workspace_data.get("pages"):
            pages_root = QTreeWidgetItem(self.workspace_tree, ["📄 页面", "分类", "/"])
            pages_root.setExpanded(True)
            
            for page_data in workspace_data["pages"]:
                page_item = QTreeWidgetItem(pages_root, [
                    page_data.get("title", "无标题"),
                    "页面",
                    f"/pages/{page_data.get('id', '')}"
                ])
                page_item.setData(0, Qt.ItemDataRole.UserRole, {
                    "type": "page",
                    "id": page_data.get("id", ""),
                    "title": page_data.get("title", "无标题")
                })
        
        # 添加数据库
        if workspace_data.get("databases"):
            databases_root = QTreeWidgetItem(self.workspace_tree, ["🗃️ 数据库", "分类", "/"])
            databases_root.setExpanded(True)
            
            for db_data in workspace_data["databases"]:
                db_item = QTreeWidgetItem(databases_root, [
                    db_data.get("title", "无标题"),
                    "数据库",
                    f"/databases/{db_data.get('id', '')}"
                ])
                db_item.setData(0, Qt.ItemDataRole.UserRole, {
                    "type": "database",
                    "id": db_data.get("id", ""),
                    "title": db_data.get("title", "无标题")
                })
    
    def _on_loading_progress(self, percentage: int, message: str):
        """更新加载进度。"""
        self.progress_bar.setValue(percentage)
        self.progress_bar.setFormat(f"{message} ({percentage}%)")
    
    def _on_loading_error(self, error: str):
        """处理加载错误。"""
        self.progress_bar.setVisible(False)
        self.workspace_tree.setEnabled(True)
        QMessageBox.critical(self, "加载失败", f"无法加载工作区数据:\n{error}")
    
    def _filter_items(self, text: str):
        """过滤项目。"""
        # 简单的搜索过滤
        for i in range(self.workspace_tree.topLevelItemCount()):
            top_item = self.workspace_tree.topLevelItem(i)
            self._filter_item_recursive(top_item, text.lower())
    
    def _filter_item_recursive(self, item: QTreeWidgetItem, filter_text: str):
        """递归过滤项目。"""
        if not filter_text:
            item.setHidden(False)
            for i in range(item.childCount()):
                self._filter_item_recursive(item.child(i), filter_text)
            return
        
        # 检查当前项目是否匹配
        matches = filter_text in item.text(0).lower()
        
        # 检查子项目
        child_matches = False
        for i in range(item.childCount()):
            child_item = item.child(i)
            self._filter_item_recursive(child_item, filter_text)
            if not child_item.isHidden():
                child_matches = True
        
        # 如果当前项目或子项目匹配，显示当前项目
        item.setHidden(not (matches or child_matches))
    
    def _on_item_clicked(self, item: QTreeWidgetItem, column: int):
        """项目点击处理。"""
        item_data = item.data(0, Qt.ItemDataRole.UserRole)
        if item_data and isinstance(item_data, dict):
            self.selected_path = item.text(2)
            self.selected_page_id = item_data.get("id", "")
            self.selected_path_label.setText(self.selected_path)
            self.select_btn.setEnabled(True)
        else:
            self.selected_path = ""
            self.selected_page_id = ""
            self.selected_path_label.setText("未选择")
            self.select_btn.setEnabled(False)
    
    def _on_item_double_clicked(self, item: QTreeWidgetItem, column: int):
        """项目双击处理。"""
        self._on_item_clicked(item, column)
        if self.selected_path:
            self._on_select_clicked()
    
    def _on_select_clicked(self):
        """选择按钮点击处理。"""
        if self.selected_path and self.selected_page_id:
            self.path_selected.emit(self.selected_path, self.selected_page_id)
            self.accept()


def show_notion_workspace_dialog(notion_client, parent=None) -> Optional[tuple]:
    """显示 Notion 工作区选择对话框。"""
    dialog = NotionWorkspaceDialog(notion_client, parent)
    
    selected_path = None
    selected_page_id = None
    
    def on_path_selected(path: str, page_id: str):
        nonlocal selected_path, selected_page_id
        selected_path = path
        selected_page_id = page_id
    
    dialog.path_selected.connect(on_path_selected)
    
    if dialog.exec() == QDialog.DialogCode.Accepted:
        return (selected_path, selected_page_id)
    return None
