"""
Authentication dialog for Notion OAuth flow.
"""

import webbrowser
from typing import Optional
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QTextEdit, QProgressBar, QWidget
)
from PySide6.QtCore import Qt, Signal, QTimer, QThread
from PySide6.QtGui import QFont, QPixmap, QIcon
from PySide6.QtNetwork import QTcpServer, QTcpSocket

from notion_sync.views.base import BaseView


class CallbackServer(QThread):
    """Local server to handle OAuth callback."""
    
    callback_received = Signal(str, str)  # code, state
    error_occurred = Signal(str)
    
    def __init__(self, port: int = 8080):
        """Initialize the callback server."""
        super().__init__()
        self.port = port
        self.server = None
        self.should_stop = False
    
    def run(self):
        """Run the callback server."""
        from urllib.parse import parse_qs, urlparse
        import socket
        
        try:
            # Create a simple HTTP server
            server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server_socket.bind(('localhost', self.port))
            server_socket.listen(1)
            server_socket.settimeout(1.0)  # 1 second timeout for checking should_stop
            
            while not self.should_stop:
                try:
                    client_socket, address = server_socket.accept()
                    
                    # Read the request
                    request = client_socket.recv(1024).decode('utf-8')
                    
                    # Parse the request line
                    request_line = request.split('\n')[0]
                    url_path = request_line.split(' ')[1]
                    
                    if url_path.startswith('/callback'):
                        # Parse query parameters
                        parsed_url = urlparse(url_path)
                        params = parse_qs(parsed_url.query)
                        
                        # Send success response
                        response = """HTTP/1.1 200 OK
Content-Type: text/html

<!DOCTYPE html>
<html>
<head>
    <title>Notion Sync - Authentication</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
               text-align: center; padding: 50px; background-color: #f8f9fa; }
        .container { max-width: 400px; margin: 0 auto; background: white; 
                    padding: 40px; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
        .success { color: #34C759; font-size: 24px; margin-bottom: 16px; }
        .message { color: #1D1D1F; font-size: 16px; margin-bottom: 24px; }
        .close-btn { background: #007AFF; color: white; border: none; 
                    padding: 12px 24px; border-radius: 6px; font-size: 14px; cursor: pointer; }
    </style>
</head>
<body>
    <div class="container">
        <div class="success">✓ Authentication Successful</div>
        <div class="message">You have successfully connected to Notion. You can now close this window and return to the application.</div>
        <button class="close-btn" onclick="window.close()">Close Window</button>
    </div>
</body>
</html>"""
                        
                        client_socket.send(response.encode('utf-8'))
                        client_socket.close()
                        
                        # Extract authorization code and state
                        code = params.get('code', [''])[0]
                        state = params.get('state', [''])[0]
                        error = params.get('error', [''])[0]
                        
                        if error:
                            self.error_occurred.emit(f"OAuth error: {error}")
                        elif code and state:
                            self.callback_received.emit(code, state)
                        else:
                            self.error_occurred.emit("Invalid callback parameters")
                        
                        break
                    else:
                        # Send 404 for other paths
                        response = "HTTP/1.1 404 Not Found\r\n\r\n"
                        client_socket.send(response.encode('utf-8'))
                        client_socket.close()
                
                except socket.timeout:
                    continue  # Check should_stop flag
                except Exception as e:
                    if not self.should_stop:
                        self.error_occurred.emit(f"Server error: {str(e)}")
                    break
            
            server_socket.close()
            
        except Exception as e:
            self.error_occurred.emit(f"Failed to start callback server: {str(e)}")
    
    def stop(self):
        """Stop the callback server."""
        self.should_stop = True
        self.wait(3000)  # Wait up to 3 seconds for thread to finish


class AuthDialog(QDialog):
    """Authentication dialog for Notion OAuth."""
    
    authentication_completed = Signal(bool)  # success
    
    def __init__(self, parent: Optional[QWidget] = None):
        """Initialize the authentication dialog."""
        super().__init__(parent)
        self.callback_server = None
        self.auth_url = ""
        self.state = ""
        
        self._setup_ui()
        self._setup_connections()
    
    def _setup_ui(self) -> None:
        """Set up the dialog UI."""
        self.setWindowTitle("Connect to Notion")
        self.setModal(True)
        self.setFixedSize(500, 400)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(24)
        
        # Header
        header_layout = QVBoxLayout()
        
        # Icon/Logo placeholder
        icon_label = QLabel("🔗")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setStyleSheet("font-size: 48px; margin-bottom: 16px;")
        header_layout.addWidget(icon_label)
        
        title_label = QLabel("Connect to Notion")
        title_label.setFont(QFont("SF Pro Display", 20, QFont.Weight.Bold))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("color: #1D1D1F; margin-bottom: 8px;")
        header_layout.addWidget(title_label)
        
        description_label = QLabel("Authorize Notion Sync to access your Notion workspace")
        description_label.setFont(QFont("SF Pro Display", 14))
        description_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        description_label.setStyleSheet("color: #8E8E93; margin-bottom: 16px;")
        description_label.setWordWrap(True)
        header_layout.addWidget(description_label)
        
        layout.addLayout(header_layout)
        
        # Instructions
        instructions_frame = QFrame()
        instructions_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        instructions_frame.setStyleSheet("""
        QFrame {
            background-color: #F2F2F7;
            border: 1px solid #D1D1D6;
            border-radius: 8px;
            padding: 16px;
        }
        """)
        
        instructions_layout = QVBoxLayout(instructions_frame)
        instructions_layout.setSpacing(8)
        
        instructions_title = QLabel("How to connect:")
        instructions_title.setFont(QFont("SF Pro Display", 14, QFont.Weight.Medium))
        instructions_title.setStyleSheet("color: #1D1D1F;")
        instructions_layout.addWidget(instructions_title)
        
        steps = [
            "1. Click 'Open Notion Authorization' below",
            "2. Sign in to your Notion account in the browser",
            "3. Grant permission to Notion Sync",
            "4. Return to this dialog - it will close automatically"
        ]
        
        for step in steps:
            step_label = QLabel(step)
            step_label.setFont(QFont("SF Pro Display", 12))
            step_label.setStyleSheet("color: #3C3C43; margin-left: 8px;")
            instructions_layout.addWidget(step_label)
        
        layout.addWidget(instructions_frame)
        
        # Status area
        self.status_frame = QFrame()
        self.status_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        self.status_frame.setStyleSheet("""
        QFrame {
            background-color: #FFF;
            border: 1px solid #E5E5E7;
            border-radius: 8px;
            padding: 16px;
        }
        """)
        
        status_layout = QVBoxLayout(self.status_frame)
        status_layout.setSpacing(12)
        
        self.status_label = QLabel("Ready to connect")
        self.status_label.setFont(QFont("SF Pro Display", 14))
        self.status_label.setStyleSheet("color: #1D1D1F;")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        status_layout.addWidget(self.status_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # Indeterminate
        self.progress_bar.setVisible(False)
        status_layout.addWidget(self.progress_bar)
        
        layout.addWidget(self.status_frame)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)
        
        button_layout.addStretch()
        
        self.auth_button = QPushButton("Open Notion Authorization")
        self.auth_button.setStyleSheet("""
        QPushButton {
            background-color: #007AFF;
            color: white;
            border: none;
            border-radius: 6px;
            padding: 12px 24px;
            font-weight: 500;
            font-size: 14px;
        }
        QPushButton:hover {
            background-color: #0056CC;
        }
        QPushButton:disabled {
            background-color: #E5E5E7;
            color: #8E8E93;
        }
        """)
        self.auth_button.clicked.connect(self._start_authentication)
        button_layout.addWidget(self.auth_button)
        
        layout.addLayout(button_layout)
    
    def _setup_connections(self) -> None:
        """Set up signal connections."""
        pass
    
    def start_authentication(self, auth_url: str, state: str) -> None:
        """Start the authentication process."""
        self.auth_url = auth_url
        self.state = state
        self.show()
    
    def _start_authentication(self) -> None:
        """Start the OAuth authentication flow."""
        try:
            # Start callback server
            self.callback_server = CallbackServer(8080)
            self.callback_server.callback_received.connect(self._on_callback_received)
            self.callback_server.error_occurred.connect(self._on_auth_error)
            self.callback_server.start()
            
            # Update UI
            self.status_label.setText("Starting local server...")
            self.progress_bar.setVisible(True)
            self.auth_button.setEnabled(False)
            
            # Open browser after a short delay
            QTimer.singleShot(1000, self._open_browser)
            
        except Exception as e:
            self._on_auth_error(f"Failed to start authentication: {str(e)}")
    
    def _open_browser(self) -> None:
        """Open the authorization URL in the browser."""
        try:
            webbrowser.open(self.auth_url)
            self.status_label.setText("Waiting for authorization in browser...")
        except Exception as e:
            self._on_auth_error(f"Failed to open browser: {str(e)}")
    
    def _on_callback_received(self, code: str, state: str) -> None:
        """Handle OAuth callback."""
        if state != self.state:
            self._on_auth_error("Invalid state parameter - possible CSRF attack")
            return
        
        self.status_label.setText("Authorization received, completing authentication...")
        
        # Stop the callback server
        if self.callback_server:
            self.callback_server.stop()
            self.callback_server = None
        
        # Emit success signal with the authorization code
        self.authentication_completed.emit(True)
        self.accept()
    
    def _on_auth_error(self, error: str) -> None:
        """Handle authentication error."""
        self.status_label.setText(f"Error: {error}")
        self.progress_bar.setVisible(False)
        self.auth_button.setEnabled(True)
        
        # Stop the callback server
        if self.callback_server:
            self.callback_server.stop()
            self.callback_server = None
        
        self.authentication_completed.emit(False)
    
    def closeEvent(self, event) -> None:
        """Handle dialog close event."""
        # Stop the callback server
        if self.callback_server:
            self.callback_server.stop()
            self.callback_server = None
        
        super().closeEvent(event)
    
    def reject(self) -> None:
        """Handle dialog rejection."""
        # Stop the callback server
        if self.callback_server:
            self.callback_server.stop()
            self.callback_server = None
        
        self.authentication_completed.emit(False)
        super().reject()
