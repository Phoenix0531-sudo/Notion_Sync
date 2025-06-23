"""
错误处理和报告系统
"""

import sys
import traceback
import logging
from typing import Optional, Dict, Any, Callable
from datetime import datetime
from pathlib import Path
from PySide6.QtWidgets import QMessageBox, QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTextEdit
from PySide6.QtCore import QObject, Signal, Qt
from PySide6.QtGui import QFont


class ErrorType:
    """错误类型常量"""
    NETWORK = "network"
    AUTH = "authentication"
    FILE_IO = "file_io"
    PERMISSION = "permission"
    VALIDATION = "validation"
    UNKNOWN = "unknown"
    NOTION_API = "notion_api"
    SYNC = "sync"


class AppError(Exception):
    """应用程序自定义错误"""
    
    def __init__(self, message: str, error_type: str = ErrorType.UNKNOWN, 
                 details: Optional[Dict] = None, original_error: Optional[Exception] = None):
        super().__init__(message)
        self.message = message
        self.error_type = error_type
        self.details = details or {}
        self.original_error = original_error
        self.timestamp = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'message': self.message,
            'error_type': self.error_type,
            'details': self.details,
            'timestamp': self.timestamp.isoformat(),
            'original_error': str(self.original_error) if self.original_error else None
        }


class ErrorReportDialog(QDialog):
    """错误报告对话框"""
    
    def __init__(self, error: AppError, parent=None):
        super().__init__(parent)
        self.error = error
        self.setWindowTitle("错误报告")
        self.setMinimumSize(500, 400)
        self._setup_ui()
    
    def _setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        
        # 错误图标和标题
        header_layout = QHBoxLayout()
        
        # 错误图标
        icon_label = QLabel("⚠️")
        icon_label.setFont(QFont("Arial", 24))
        header_layout.addWidget(icon_label)
        
        # 错误标题
        title_label = QLabel(f"发生了 {self._get_error_type_name()} 错误")
        title_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        layout.addLayout(header_layout)
        
        # 错误消息
        message_label = QLabel(self.error.message)
        message_label.setWordWrap(True)
        message_label.setStyleSheet("color: #D32F2F; padding: 10px; background: #FFEBEE; border-radius: 4px;")
        layout.addWidget(message_label)
        
        # 建议解决方案
        suggestion = self._get_suggestion()
        if suggestion:
            suggestion_label = QLabel(f"💡 建议：{suggestion}")
            suggestion_label.setWordWrap(True)
            suggestion_label.setStyleSheet("color: #1976D2; padding: 10px; background: #E3F2FD; border-radius: 4px;")
            layout.addWidget(suggestion_label)
        
        # 详细信息（可展开）
        details_label = QLabel("详细信息:")
        details_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        layout.addWidget(details_label)
        
        self.details_text = QTextEdit()
        self.details_text.setMaximumHeight(150)
        self.details_text.setPlainText(self._format_details())
        self.details_text.setStyleSheet("background: #F5F5F5; border: 1px solid #E0E0E0;")
        layout.addWidget(self.details_text)
        
        # 按钮
        button_layout = QHBoxLayout()
        
        copy_btn = QPushButton("复制错误信息")
        copy_btn.clicked.connect(self._copy_error_info)
        button_layout.addWidget(copy_btn)
        
        button_layout.addStretch()
        
        ok_btn = QPushButton("确定")
        ok_btn.clicked.connect(self.accept)
        ok_btn.setDefault(True)
        button_layout.addWidget(ok_btn)
        
        layout.addLayout(button_layout)
    
    def _get_error_type_name(self) -> str:
        """获取错误类型名称"""
        type_names = {
            ErrorType.NETWORK: "网络连接",
            ErrorType.AUTH: "身份验证",
            ErrorType.FILE_IO: "文件操作",
            ErrorType.PERMISSION: "权限",
            ErrorType.VALIDATION: "数据验证",
            ErrorType.NOTION_API: "Notion API",
            ErrorType.SYNC: "同步",
            ErrorType.UNKNOWN: "未知"
        }
        return type_names.get(self.error.error_type, "未知")
    
    def _get_suggestion(self) -> Optional[str]:
        """获取解决建议"""
        suggestions = {
            ErrorType.NETWORK: "请检查网络连接，确保能够访问互联网",
            ErrorType.AUTH: "请检查 Notion API 令牌是否正确，或重新获取令牌",
            ErrorType.FILE_IO: "请检查文件路径是否存在，以及是否有足够的磁盘空间",
            ErrorType.PERMISSION: "请检查文件和文件夹的访问权限",
            ErrorType.VALIDATION: "请检查输入的数据格式是否正确",
            ErrorType.NOTION_API: "请稍后重试，或检查 Notion 服务状态",
            ErrorType.SYNC: "请检查同步配置，或尝试重新连接"
        }
        return suggestions.get(self.error.error_type)
    
    def _format_details(self) -> str:
        """格式化详细信息"""
        details = [
            f"错误类型: {self.error.error_type}",
            f"发生时间: {self.error.timestamp.strftime('%Y-%m-%d %H:%M:%S')}",
            f"错误消息: {self.error.message}"
        ]
        
        if self.error.details:
            details.append("附加信息:")
            for key, value in self.error.details.items():
                details.append(f"  {key}: {value}")
        
        if self.error.original_error:
            details.append(f"原始错误: {self.error.original_error}")
            details.append("堆栈跟踪:")
            details.append(traceback.format_exc())
        
        return "\n".join(details)
    
    def _copy_error_info(self):
        """复制错误信息到剪贴板"""
        from PySide6.QtWidgets import QApplication
        clipboard = QApplication.clipboard()
        clipboard.setText(self._format_details())
        
        # 显示复制成功提示
        QMessageBox.information(self, "复制成功", "错误信息已复制到剪贴板")


class ErrorHandler(QObject):
    """错误处理器"""
    
    error_occurred = Signal(AppError)
    
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.error_log_file = Path.home() / ".notion_sync" / "error.log"
        self.error_log_file.parent.mkdir(exist_ok=True)
        
        # 设置错误日志
        self._setup_error_logging()
    
    def _setup_error_logging(self):
        """设置错误日志"""
        error_handler = logging.FileHandler(self.error_log_file, encoding='utf-8')
        error_handler.setLevel(logging.ERROR)
        
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        error_handler.setFormatter(formatter)
        
        # 添加到根日志器
        logging.getLogger().addHandler(error_handler)
    
    def handle_error(self, error: Exception, context: Optional[Dict] = None, 
                    show_dialog: bool = True) -> AppError:
        """处理错误"""
        # 转换为 AppError
        if isinstance(error, AppError):
            app_error = error
        else:
            app_error = self._convert_to_app_error(error, context)
        
        # 记录错误
        self._log_error(app_error)
        
        # 发送信号
        self.error_occurred.emit(app_error)
        
        # 显示错误对话框
        if show_dialog:
            self._show_error_dialog(app_error)
        
        return app_error
    
    def _convert_to_app_error(self, error: Exception, context: Optional[Dict] = None) -> AppError:
        """转换为应用程序错误"""
        error_type = self._determine_error_type(error)
        message = self._get_user_friendly_message(error, error_type)
        
        return AppError(
            message=message,
            error_type=error_type,
            details=context or {},
            original_error=error
        )
    
    def _determine_error_type(self, error: Exception) -> str:
        """确定错误类型"""
        error_name = type(error).__name__
        error_message = str(error).lower()
        
        if "network" in error_message or "connection" in error_message:
            return ErrorType.NETWORK
        elif "permission" in error_message or "access" in error_message:
            return ErrorType.PERMISSION
        elif "file" in error_message or "directory" in error_message:
            return ErrorType.FILE_IO
        elif "auth" in error_message or "token" in error_message:
            return ErrorType.AUTH
        elif "notion" in error_message or "api" in error_message:
            return ErrorType.NOTION_API
        elif "sync" in error_message:
            return ErrorType.SYNC
        else:
            return ErrorType.UNKNOWN
    
    def _get_user_friendly_message(self, error: Exception, error_type: str) -> str:
        """获取用户友好的错误消息"""
        friendly_messages = {
            ErrorType.NETWORK: "网络连接失败，请检查网络设置",
            ErrorType.AUTH: "身份验证失败，请检查 API 令牌",
            ErrorType.FILE_IO: "文件操作失败，请检查文件路径和权限",
            ErrorType.PERMISSION: "权限不足，请检查文件和文件夹权限",
            ErrorType.NOTION_API: "Notion API 调用失败，请稍后重试",
            ErrorType.SYNC: "同步操作失败，请检查配置",
            ErrorType.VALIDATION: "数据验证失败，请检查输入",
        }
        
        return friendly_messages.get(error_type, f"发生未知错误: {str(error)}")
    
    def _log_error(self, error: AppError):
        """记录错误到日志"""
        self.logger.error(f"[{error.error_type}] {error.message}")
        if error.details:
            self.logger.error(f"详细信息: {error.details}")
        if error.original_error:
            self.logger.error(f"原始错误: {error.original_error}")
            self.logger.error(f"堆栈跟踪: {traceback.format_exc()}")
    
    def _show_error_dialog(self, error: AppError):
        """显示错误对话框"""
        try:
            from PySide6.QtWidgets import QApplication
            app = QApplication.instance()
            if app:
                dialog = ErrorReportDialog(error)
                dialog.exec()
        except Exception as e:
            # 如果显示对话框失败，至少打印错误
            print(f"显示错误对话框失败: {e}")
            print(f"原始错误: {error.message}")


# 全局错误处理器实例
_global_error_handler = None


def get_error_handler() -> ErrorHandler:
    """获取全局错误处理器"""
    global _global_error_handler
    if _global_error_handler is None:
        _global_error_handler = ErrorHandler()
    return _global_error_handler


def handle_error(error: Exception, context: Optional[Dict] = None, 
                show_dialog: bool = True) -> AppError:
    """处理错误的便捷函数"""
    return get_error_handler().handle_error(error, context, show_dialog)


def error_handler_decorator(error_type: str = ErrorType.UNKNOWN, 
                          show_dialog: bool = True):
    """错误处理装饰器"""
    def decorator(func: Callable):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                context = {
                    'function': func.__name__,
                    'args': str(args),
                    'kwargs': str(kwargs)
                }
                handle_error(e, context, show_dialog)
                return None
        return wrapper
    return decorator
