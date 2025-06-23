"""
Authentication utilities for Notion API integration.
"""

import json
import secrets
import hashlib
import base64
from typing import Optional, Dict, Any
from urllib.parse import urlencode, parse_qs, urlparse
import keyring
from cryptography.fernet import Fernet
from PySide6.QtCore import QObject, Signal

from notion_sync import APP_IDENTIFIER
from notion_sync.utils.logging_config import LoggerMixin


class AuthManager(QObject, LoggerMixin):
    """Manages OAuth 2.0 authentication with Notion."""
    
    # Authentication signals
    auth_started = Signal()
    auth_completed = Signal(bool)  # success
    auth_error = Signal(str)
    token_refreshed = Signal()
    
    def __init__(self, client_id: str, client_secret: str, redirect_uri: str):
        """Initialize the auth manager."""
        super().__init__()
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.auth_base_url = "https://api.notion.com/v1/oauth/authorize"
        self.token_url = "https://api.notion.com/v1/oauth/token"
        
        # Generate encryption key for token storage
        self._encryption_key = self._get_or_create_encryption_key()
        self._cipher = Fernet(self._encryption_key)
        
        # Current session
        self._access_token: Optional[str] = None
        self._refresh_token: Optional[str] = None
        self._token_expires_at: Optional[float] = None
        self._workspace_info: Optional[Dict[str, Any]] = None
    
    def _get_or_create_encryption_key(self) -> bytes:
        """Get or create encryption key for secure token storage."""
        key_name = f"{APP_IDENTIFIER}_encryption_key"
        
        try:
            # Try to get existing key
            key_str = keyring.get_password("system", key_name)
            if key_str:
                return key_str.encode()
        except Exception as e:
            self.logger.warning(f"Could not retrieve encryption key: {e}")
        
        # Generate new key
        key = Fernet.generate_key()
        try:
            keyring.set_password("system", key_name, key.decode())
        except Exception as e:
            self.logger.warning(f"Could not store encryption key: {e}")
        
        return key
    
    def generate_auth_url(self) -> tuple:
        """Generate OAuth authorization URL and state parameter."""
        # Generate state parameter for CSRF protection
        state = secrets.token_urlsafe(32)
        
        # Generate code challenge for PKCE
        code_verifier = secrets.token_urlsafe(32)
        code_challenge = base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode()).digest()
        ).decode().rstrip('=')
        
        # Store code verifier securely
        self._store_code_verifier(state, code_verifier)
        
        params = {
            'client_id': self.client_id,
            'response_type': 'code',
            'redirect_uri': self.redirect_uri,
            'state': state,
            'code_challenge': code_challenge,
            'code_challenge_method': 'S256'
        }
        
        auth_url = f"{self.auth_base_url}?{urlencode(params)}"
        return auth_url, state
    
    def _store_code_verifier(self, state: str, code_verifier: str) -> None:
        """Store code verifier securely."""
        try:
            encrypted_verifier = self._cipher.encrypt(code_verifier.encode())
            keyring.set_password(APP_IDENTIFIER, f"code_verifier_{state}", 
                               base64.b64encode(encrypted_verifier).decode())
        except Exception as e:
            self.logger.error(f"Failed to store code verifier: {e}")
    
    def _get_code_verifier(self, state: str) -> Optional[str]:
        """Retrieve and decrypt code verifier."""
        try:
            encrypted_data = keyring.get_password(APP_IDENTIFIER, f"code_verifier_{state}")
            if encrypted_data:
                encrypted_verifier = base64.b64decode(encrypted_data.encode())
                code_verifier = self._cipher.decrypt(encrypted_verifier).decode()
                # Clean up
                keyring.delete_password(APP_IDENTIFIER, f"code_verifier_{state}")
                return code_verifier
        except Exception as e:
            self.logger.error(f"Failed to retrieve code verifier: {e}")
        return None
    
    async def exchange_code_for_token(self, authorization_code: str, state: str) -> bool:
        """Exchange authorization code for access token."""
        import aiohttp
        
        self.auth_started.emit()
        
        try:
            code_verifier = self._get_code_verifier(state)
            if not code_verifier:
                raise ValueError("Code verifier not found")
            
            data = {
                'grant_type': 'authorization_code',
                'code': authorization_code,
                'redirect_uri': self.redirect_uri,
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'code_verifier': code_verifier
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(self.token_url, data=data) as response:
                    if response.status == 200:
                        token_data = await response.json()
                        await self._store_tokens(token_data)
                        self.auth_completed.emit(True)
                        self.logger.info("Authentication successful")
                        return True
                    else:
                        error_data = await response.json()
                        error_msg = error_data.get('error_description', 'Authentication failed')
                        self.auth_error.emit(error_msg)
                        self.logger.error(f"Token exchange failed: {error_msg}")
                        return False
        
        except Exception as e:
            error_msg = f"Authentication error: {str(e)}"
            self.auth_error.emit(error_msg)
            self.logger.error(error_msg, exc_info=True)
            return False
    
    async def _store_tokens(self, token_data: Dict[str, Any]) -> None:
        """Store tokens securely."""
        import time
        
        self._access_token = token_data.get('access_token')
        self._refresh_token = token_data.get('refresh_token')
        
        # Calculate expiration time
        expires_in = token_data.get('expires_in', 3600)
        self._token_expires_at = time.time() + expires_in
        
        # Store workspace info
        self._workspace_info = token_data.get('workspace', {})
        
        # Encrypt and store tokens
        try:
            token_info = {
                'access_token': self._access_token,
                'refresh_token': self._refresh_token,
                'expires_at': self._token_expires_at,
                'workspace': self._workspace_info
            }
            
            encrypted_data = self._cipher.encrypt(json.dumps(token_info).encode())
            keyring.set_password(APP_IDENTIFIER, "notion_tokens", 
                               base64.b64encode(encrypted_data).decode())
            
        except Exception as e:
            self.logger.error(f"Failed to store tokens: {e}")
    
    def load_stored_tokens(self) -> bool:
        """Load previously stored tokens."""
        try:
            encrypted_data = keyring.get_password(APP_IDENTIFIER, "notion_tokens")
            if not encrypted_data:
                return False
            
            decrypted_data = self._cipher.decrypt(base64.b64decode(encrypted_data.encode()))
            token_info = json.loads(decrypted_data.decode())
            
            self._access_token = token_info.get('access_token')
            self._refresh_token = token_info.get('refresh_token')
            self._token_expires_at = token_info.get('expires_at')
            self._workspace_info = token_info.get('workspace', {})
            
            return self._access_token is not None
            
        except Exception as e:
            self.logger.error(f"Failed to load stored tokens: {e}")
            return False
    
    def clear_stored_tokens(self) -> None:
        """Clear stored authentication tokens."""
        try:
            keyring.delete_password(APP_IDENTIFIER, "notion_tokens")
        except Exception as e:
            self.logger.warning(f"Failed to clear tokens: {e}")
        
        self._access_token = None
        self._refresh_token = None
        self._token_expires_at = None
        self._workspace_info = None
    
    @property
    def is_authenticated(self) -> bool:
        """Check if user is currently authenticated."""
        return self._access_token is not None
    
    @property
    def access_token(self) -> Optional[str]:
        """Get the current access token."""
        return self._access_token
    
    @property
    def workspace_info(self) -> Optional[Dict[str, Any]]:
        """Get workspace information."""
        return self._workspace_info
    
    def is_token_expired(self) -> bool:
        """Check if the access token is expired."""
        import time
        if not self._token_expires_at:
            return True
        return time.time() >= self._token_expires_at - 300  # 5 minute buffer
    
    async def refresh_access_token(self) -> bool:
        """Refresh the access token using refresh token."""
        if not self._refresh_token:
            return False
        
        import aiohttp
        
        try:
            data = {
                'grant_type': 'refresh_token',
                'refresh_token': self._refresh_token,
                'client_id': self.client_id,
                'client_secret': self.client_secret
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(self.token_url, data=data) as response:
                    if response.status == 200:
                        token_data = await response.json()
                        await self._store_tokens(token_data)
                        self.token_refreshed.emit()
                        self.logger.info("Token refreshed successfully")
                        return True
                    else:
                        self.logger.error("Token refresh failed")
                        return False
        
        except Exception as e:
            self.logger.error(f"Token refresh error: {e}")
            return False
