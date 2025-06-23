"""
图标资源管理器
提供应用程序中使用的所有图标
"""

from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QPolygon
from PySide6.QtCore import Qt, QSize, QPoint
from PySide6.QtWidgets import QStyle, QApplication


class IconManager:
    """图标管理器 - 提供统一的图标访问"""
    
    _instance = None
    _icons = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, '_initialized'):
            self._initialized = True
            # 延迟创建图标，直到 QApplication 存在
            self._icons_created = False
    
    def _create_icons(self):
        """创建所有图标"""
        # 使用系统图标和自定义图标
        style = QApplication.style()
        
        # 基础操作图标
        self._icons['analyze'] = self._create_analyze_icon()
        self._icons['sync'] = self._create_sync_icon()
        self._icons['connect'] = self._create_connect_icon()
        self._icons['disconnect'] = self._create_disconnect_icon()
        self._icons['refresh'] = style.standardIcon(QStyle.StandardPixmap.SP_BrowserReload)
        self._icons['folder'] = style.standardIcon(QStyle.StandardPixmap.SP_DirIcon)
        self._icons['file'] = style.standardIcon(QStyle.StandardPixmap.SP_FileIcon)
        self._icons['settings'] = style.standardIcon(QStyle.StandardPixmap.SP_ComputerIcon)
        
        # 状态图标
        self._icons['success'] = self._create_success_icon()
        self._icons['error'] = self._create_error_icon()
        self._icons['warning'] = self._create_warning_icon()
        self._icons['info'] = self._create_info_icon()
        
        # 同步方向图标
        self._icons['sync_bidirectional'] = self._create_bidirectional_icon()
        self._icons['sync_to_notion'] = self._create_to_notion_icon()
        self._icons['sync_from_notion'] = self._create_from_notion_icon()
        
        # 文件类型图标
        self._icons['markdown'] = self._create_markdown_icon()
        self._icons['text'] = self._create_text_icon()
        self._icons['image'] = self._create_image_icon()
        
        # 应用图标
        self._icons['app'] = self._create_app_icon()
    
    def _create_analyze_icon(self) -> QIcon:
        """创建分析图标"""
        pixmap = QPixmap(16, 16)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 绘制放大镜
        painter.setPen(QColor("#4A90E2"))
        painter.setBrush(QColor("#4A90E2"))
        painter.drawEllipse(2, 2, 8, 8)
        painter.drawLine(9, 9, 14, 14)
        
        painter.end()
        return QIcon(pixmap)
    
    def _create_sync_icon(self) -> QIcon:
        """创建同步图标"""
        pixmap = QPixmap(16, 16)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 绘制双向箭头
        painter.setPen(QColor("#34C759"))
        painter.setBrush(QColor("#34C759"))
        
        # 上箭头
        painter.drawLine(8, 2, 8, 6)
        painter.drawLine(6, 4, 8, 2)
        painter.drawLine(10, 4, 8, 2)
        
        # 下箭头
        painter.drawLine(8, 10, 8, 14)
        painter.drawLine(6, 12, 8, 14)
        painter.drawLine(10, 12, 8, 14)
        
        painter.end()
        return QIcon(pixmap)
    
    def _create_connect_icon(self) -> QIcon:
        """创建连接图标"""
        pixmap = QPixmap(16, 16)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 绘制链接图标
        painter.setPen(QColor("#007AFF"))
        painter.setBrush(QColor("#007AFF"))
        
        # 绘制链条
        painter.drawEllipse(2, 2, 6, 6)
        painter.drawEllipse(8, 8, 6, 6)
        painter.drawLine(6, 6, 10, 10)
        
        painter.end()
        return QIcon(pixmap)
    
    def _create_disconnect_icon(self) -> QIcon:
        """创建断开连接图标"""
        pixmap = QPixmap(16, 16)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 绘制断开的链接
        painter.setPen(QColor("#FF3B30"))
        painter.setBrush(QColor("#FF3B30"))
        
        painter.drawEllipse(2, 2, 6, 6)
        painter.drawEllipse(8, 8, 6, 6)
        # 绘制断开的线
        painter.drawLine(6, 6, 8, 8)
        painter.drawLine(8, 10, 10, 8)
        
        painter.end()
        return QIcon(pixmap)
    
    def _create_success_icon(self) -> QIcon:
        """创建成功图标"""
        pixmap = QPixmap(16, 16)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 绘制对勾
        painter.setPen(QColor("#34C759"))
        painter.setBrush(QColor("#34C759"))
        painter.drawEllipse(1, 1, 14, 14)
        
        painter.setPen(QColor("white"))
        painter.drawLine(4, 8, 7, 11)
        painter.drawLine(7, 11, 12, 5)
        
        painter.end()
        return QIcon(pixmap)
    
    def _create_error_icon(self) -> QIcon:
        """创建错误图标"""
        pixmap = QPixmap(16, 16)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 绘制错误图标
        painter.setPen(QColor("#FF3B30"))
        painter.setBrush(QColor("#FF3B30"))
        painter.drawEllipse(1, 1, 14, 14)
        
        painter.setPen(QColor("white"))
        painter.drawLine(5, 5, 11, 11)
        painter.drawLine(5, 11, 11, 5)
        
        painter.end()
        return QIcon(pixmap)
    
    def _create_warning_icon(self) -> QIcon:
        """创建警告图标"""
        pixmap = QPixmap(16, 16)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 绘制警告三角形
        painter.setPen(QColor("#FF9500"))
        painter.setBrush(QColor("#FF9500"))

        points = [
            QPoint(8, 2),
            QPoint(14, 14),
            QPoint(2, 14)
        ]
        polygon = QPolygon(points)
        painter.drawPolygon(polygon)
        
        painter.setPen(QColor("white"))
        painter.drawLine(8, 5, 8, 10)
        painter.drawEllipse(7, 11, 2, 2)
        
        painter.end()
        return QIcon(pixmap)
    
    def _create_info_icon(self) -> QIcon:
        """创建信息图标"""
        pixmap = QPixmap(16, 16)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 绘制信息图标
        painter.setPen(QColor("#007AFF"))
        painter.setBrush(QColor("#007AFF"))
        painter.drawEllipse(1, 1, 14, 14)
        
        painter.setPen(QColor("white"))
        painter.drawEllipse(7, 4, 2, 2)
        painter.drawLine(8, 7, 8, 12)
        
        painter.end()
        return QIcon(pixmap)
    
    def _create_bidirectional_icon(self) -> QIcon:
        """创建双向同步图标"""
        pixmap = QPixmap(16, 16)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        painter.setPen(QColor("#4A90E2"))
        # 左右箭头
        painter.drawLine(2, 6, 14, 6)
        painter.drawLine(2, 10, 14, 10)
        
        # 箭头头部
        painter.drawLine(12, 4, 14, 6)
        painter.drawLine(12, 8, 14, 6)
        painter.drawLine(4, 8, 2, 10)
        painter.drawLine(4, 12, 2, 10)
        
        painter.end()
        return QIcon(pixmap)
    
    def _create_to_notion_icon(self) -> QIcon:
        """创建到Notion图标"""
        pixmap = QPixmap(16, 16)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        painter.setPen(QColor("#34C759"))
        painter.drawLine(2, 8, 14, 8)
        painter.drawLine(12, 6, 14, 8)
        painter.drawLine(12, 10, 14, 8)
        
        painter.end()
        return QIcon(pixmap)
    
    def _create_from_notion_icon(self) -> QIcon:
        """创建从Notion图标"""
        pixmap = QPixmap(16, 16)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        painter.setPen(QColor("#FF9500"))
        painter.drawLine(2, 8, 14, 8)
        painter.drawLine(4, 6, 2, 8)
        painter.drawLine(4, 10, 2, 8)
        
        painter.end()
        return QIcon(pixmap)
    
    def _create_markdown_icon(self) -> QIcon:
        """创建Markdown图标"""
        pixmap = QPixmap(16, 16)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        painter.setPen(QColor("#4A90E2"))
        painter.drawText(2, 12, "M")
        
        painter.end()
        return QIcon(pixmap)
    
    def _create_text_icon(self) -> QIcon:
        """创建文本图标"""
        pixmap = QPixmap(16, 16)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        painter.setPen(QColor("#666666"))
        painter.drawLine(3, 4, 13, 4)
        painter.drawLine(3, 7, 13, 7)
        painter.drawLine(3, 10, 10, 10)
        
        painter.end()
        return QIcon(pixmap)
    
    def _create_image_icon(self) -> QIcon:
        """创建图片图标"""
        pixmap = QPixmap(16, 16)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        painter.setPen(QColor("#FF9500"))
        painter.drawRect(2, 2, 12, 12)
        painter.drawEllipse(4, 4, 3, 3)
        painter.drawLine(6, 10, 14, 2)
        
        painter.end()
        return QIcon(pixmap)
    
    def _create_app_icon(self) -> QIcon:
        """创建应用图标"""
        pixmap = QPixmap(32, 32)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 绘制应用图标
        painter.setPen(QColor("#4A90E2"))
        painter.setBrush(QColor("#4A90E2"))
        painter.drawRoundedRect(4, 4, 24, 24, 4, 4)
        
        painter.setPen(QColor("white"))
        painter.drawText(8, 20, "NS")
        
        painter.end()
        return QIcon(pixmap)
    
    def get_icon(self, name: str) -> QIcon:
        """获取图标"""
        if not self._icons_created:
            self._create_icons()
            self._icons_created = True
        return self._icons.get(name, QIcon())
    
    def get_status_icon(self, status: str) -> QIcon:
        """根据状态获取图标"""
        if not self._icons_created:
            self._create_icons()
            self._icons_created = True
        status_map = {
            'success': 'success',
            'error': 'error',
            'warning': 'warning',
            'info': 'info',
            'connected': 'connect',
            'disconnected': 'disconnect',
            'syncing': 'sync',
            'analyzing': 'analyze'
        }
        return self.get_icon(status_map.get(status, 'info'))


# 全局图标管理器实例
icon_manager = IconManager()


def get_icon(name: str) -> QIcon:
    """获取图标的便捷函数"""
    return icon_manager.get_icon(name)


def get_status_icon(status: str) -> QIcon:
    """获取状态图标的便捷函数"""
    return icon_manager.get_status_icon(status)
