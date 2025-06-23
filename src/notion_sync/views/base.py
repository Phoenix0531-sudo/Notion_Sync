"""
Base view classes for the Notion Sync application.
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QProgressBar, QFrame, QSizePolicy, QStatusBar
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QFont, QPalette

from notion_sync.utils.logging_config import LoggerMixin


class BaseView(QWidget, LoggerMixin):
    """Base view class with common functionality."""
    
    # Common signals
    action_requested = Signal(str, dict)  # action_name, parameters
    close_requested = Signal()
    
    def __init__(self, parent: Optional[QWidget] = None):
        """Initialize the base view."""
        super().__init__(parent)
        self._setup_ui()
        self._apply_styling()
    
    def _setup_ui(self) -> None:
        """Set up the user interface. Override in subclasses."""
        pass
    
    def _apply_styling(self) -> None:
        """Apply custom styling following Apple HIG."""
        # Set font
        font = QFont()
        font.setFamily("SF Pro Display")  # Fallback to system font
        font.setPointSize(13)
        self.setFont(font)
        
        # Apply custom stylesheet
        self.setStyleSheet(self._get_stylesheet())
    
    def _get_stylesheet(self) -> str:
        """Get the stylesheet for this view."""
        return """
        QWidget {
            background-color: #ffffff;
            color: #000000;
        }
        
        QWidget[darkMode="true"] {
            background-color: #1e1e1e;
            color: #ffffff;
        }
        
        QPushButton {
            background-color: #007AFF;
            color: white;
            border: none;
            border-radius: 6px;
            padding: 8px 16px;
            font-weight: 500;
        }
        
        QPushButton:hover {
            background-color: #0056CC;
        }
        
        QPushButton:pressed {
            background-color: #004499;
        }
        
        QPushButton:disabled {
            background-color: #E5E5E7;
            color: #8E8E93;
        }
        
        QLabel {
            color: #000000;
        }
        
        QLabel[darkMode="true"] {
            color: #ffffff;
        }
        """
    
    def set_dark_mode(self, enabled: bool) -> None:
        """Set dark mode styling."""
        self.setProperty("darkMode", enabled)
        for child in self.findChildren(QWidget):
            child.setProperty("darkMode", enabled)
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()


class StatusBarView(QStatusBar):
    """Status bar widget with progress and message display."""

    def __init__(self, parent: Optional[QWidget] = None):
        """Initialize the status bar."""
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the status bar UI."""
        # Status message (use the built-in showMessage functionality)
        self.showMessage("Ready")

        # Progress bar (hidden by default)
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumWidth(200)
        self.progress_bar.setMaximumHeight(16)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.hide()
        self.addPermanentWidget(self.progress_bar)

        # Connection status
        self.connection_label = QLabel("●")
        self.connection_label.setStyleSheet("color: #34C759; font-size: 16px;")
        self.connection_label.setToolTip("Connected to Notion")
        self.addPermanentWidget(self.connection_label)

        # Style the status bar
        self.setStyleSheet("""
        QStatusBar {
            background-color: #F2F2F7;
            border-top: 1px solid #D1D1D6;
            color: #8E8E93;
            font-size: 12px;
        }
        """)
    
    def set_status(self, message: str) -> None:
        """Set the status message."""
        self.showMessage(message)
    
    def set_progress(self, percentage: int, visible: bool = True) -> None:
        """Set progress bar value and visibility."""
        self.progress_bar.setValue(percentage)
        self.progress_bar.setVisible(visible)
    
    def set_connection_status(self, connected: bool) -> None:
        """Set the connection status indicator."""
        if connected:
            self.connection_label.setStyleSheet("color: #34C759; font-size: 16px;")
            self.connection_label.setToolTip("Connected to Notion")
        else:
            self.connection_label.setStyleSheet("color: #FF3B30; font-size: 16px;")
            self.connection_label.setToolTip("Disconnected from Notion")


class LoadingView(QWidget):
    """Loading overlay widget."""
    
    def __init__(self, parent: Optional[QWidget] = None):
        """Initialize the loading view."""
        super().__init__(parent)
        self._setup_ui()
        self.hide()
    
    def _setup_ui(self) -> None:
        """Set up the loading UI."""
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumWidth(300)
        self.progress_bar.setRange(0, 100)
        layout.addWidget(self.progress_bar)
        
        # Status label
        self.status_label = QLabel("Loading...")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("font-size: 14px; color: #8E8E93; margin-top: 8px;")
        layout.addWidget(self.status_label)
        
        # Style the widget
        self.setStyleSheet("""
        QWidget {
            background-color: rgba(255, 255, 255, 0.9);
        }
        """)
    
    def show_loading(self, message: str = "Loading...") -> None:
        """Show the loading overlay."""
        self.status_label.setText(message)
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
        self.show()
        self.raise_()
    
    def update_progress(self, percentage: int, message: str = "") -> None:
        """Update progress and message."""
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(percentage)
        if message:
            self.status_label.setText(message)
    
    def hide_loading(self) -> None:
        """Hide the loading overlay."""
        self.hide()


class ErrorView(QWidget):
    """Error display widget."""
    
    retry_requested = Signal()
    
    def __init__(self, parent: Optional[QWidget] = None):
        """Initialize the error view."""
        super().__init__(parent)
        self._setup_ui()
        self.hide()
    
    def _setup_ui(self) -> None:
        """Set up the error UI."""
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(16)
        
        # Error icon (using text for now)
        icon_label = QLabel("⚠️")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setStyleSheet("font-size: 48px;")
        layout.addWidget(icon_label)
        
        # Error message
        self.error_label = QLabel("An error occurred")
        self.error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.error_label.setStyleSheet("font-size: 16px; font-weight: 500; color: #FF3B30;")
        self.error_label.setWordWrap(True)
        layout.addWidget(self.error_label)
        
        # Retry button
        self.retry_button = QPushButton("Retry")
        self.retry_button.clicked.connect(self.retry_requested.emit)
        self.retry_button.setMaximumWidth(120)
        layout.addWidget(self.retry_button, alignment=Qt.AlignmentFlag.AlignCenter)
    
    def show_error(self, message: str) -> None:
        """Show an error message."""
        self.error_label.setText(message)
        self.show()
        self.raise_()
    
    def hide_error(self) -> None:
        """Hide the error view."""
        self.hide()
