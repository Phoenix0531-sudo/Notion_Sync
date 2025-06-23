"""
Notion API client with rate limiting and error handling.
"""

import asyncio
import time
from typing import Dict, List, Optional, Any, Union
import aiohttp
from asyncio_throttle import Throttler

from notion_sync.models.base import BaseModel
from notion_sync.utils.auth import AuthManager


class NotionAPIError(Exception):
    """Custom exception for Notion API errors."""
    
    def __init__(self, message: str, status_code: Optional[int] = None, 
                 error_code: Optional[str] = None):
        super().__init__(message)
        self.status_code = status_code
        self.error_code = error_code


class NotionClient(BaseModel):
    """Notion API client with authentication and rate limiting."""
    
    def __init__(self, auth_manager: AuthManager, parent=None):
        """Initialize the Notion client."""
        super().__init__(parent)
        self.auth_manager = auth_manager
        self.base_url = "https://api.notion.com/v1"
        self.api_version = "2022-06-28"
        
        # Rate limiting: 3 requests per second
        self.throttler = Throttler(rate_limit=3, period=1.0)
        
        # Session for connection pooling
        self._session: Optional[aiohttp.ClientSession] = None
        
        # Cache for frequently accessed data
        self._pages_cache: Dict[str, Dict] = {}
        self._databases_cache: Dict[str, Dict] = {}
        self._cache_ttl = 300  # 5 minutes
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=30)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session
    
    async def close(self) -> None:
        """Close the HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()
    
    def _get_headers(self) -> Dict[str, str]:
        """Get headers for API requests."""
        headers = {
            "Authorization": f"Bearer {self.auth_manager.access_token}",
            "Notion-Version": self.api_version,
            "Content-Type": "application/json"
        }
        return headers
    
    async def _make_request(self, method: str, endpoint: str, 
                          data: Optional[Dict] = None, 
                          params: Optional[Dict] = None) -> Dict[str, Any]:
        """Make a rate-limited API request."""
        if not self.auth_manager.is_authenticated:
            raise NotionAPIError("Not authenticated")
        
        # Check if token needs refresh
        if self.auth_manager.is_token_expired():
            if not await self.auth_manager.refresh_access_token():
                raise NotionAPIError("Failed to refresh access token")
        
        # Apply rate limiting
        async with self.throttler:
            session = await self._get_session()
            url = f"{self.base_url}/{endpoint.lstrip('/')}"
            headers = self._get_headers()
            
            try:
                async with session.request(
                    method, url, headers=headers, json=data, params=params
                ) as response:
                    response_data = await response.json()
                    
                    if response.status >= 400:
                        error_msg = response_data.get('message', 'API request failed')
                        error_code = response_data.get('code')
                        raise NotionAPIError(error_msg, response.status, error_code)
                    
                    return response_data
            
            except aiohttp.ClientError as e:
                raise NotionAPIError(f"Network error: {str(e)}")
    
    async def get_users(self) -> List[Dict[str, Any]]:
        """Get list of users in the workspace."""
        try:
            self._set_loading(True)
            response = await self._make_request("GET", "/users")
            return response.get("results", [])
        except Exception as e:
            self._set_error(f"Failed to get users: {str(e)}")
            return []
        finally:
            self._set_loading(False)
    
    async def search(self, query: str = "", filter_type: Optional[str] = None,
                    sort_direction: str = "descending") -> List[Dict[str, Any]]:
        """Search for pages and databases."""
        try:
            self._set_loading(True)
            
            data = {
                "sort": {
                    "direction": sort_direction,
                    "timestamp": "last_edited_time"
                }
            }
            
            if query:
                data["query"] = query
            
            if filter_type:
                data["filter"] = {"property": "object", "value": filter_type}
            
            response = await self._make_request("POST", "/search", data)
            return response.get("results", [])
        
        except Exception as e:
            self._set_error(f"Search failed: {str(e)}")
            return []
        finally:
            self._set_loading(False)
    
    async def get_page(self, page_id: str, use_cache: bool = True) -> Optional[Dict[str, Any]]:
        """Get a page by ID."""
        # Check cache first
        if use_cache and page_id in self._pages_cache:
            cached_page = self._pages_cache[page_id]
            if time.time() - cached_page.get("_cached_at", 0) < self._cache_ttl:
                return cached_page
        
        try:
            response = await self._make_request("GET", f"/pages/{page_id}")
            
            # Cache the response
            if use_cache:
                response["_cached_at"] = time.time()
                self._pages_cache[page_id] = response
            
            return response
        
        except Exception as e:
            self._set_error(f"Failed to get page {page_id}: {str(e)}")
            return None
    
    async def get_database(self, database_id: str, use_cache: bool = True) -> Optional[Dict[str, Any]]:
        """Get a database by ID."""
        # Check cache first
        if use_cache and database_id in self._databases_cache:
            cached_db = self._databases_cache[database_id]
            if time.time() - cached_db.get("_cached_at", 0) < self._cache_ttl:
                return cached_db
        
        try:
            response = await self._make_request("GET", f"/databases/{database_id}")
            
            # Cache the response
            if use_cache:
                response["_cached_at"] = time.time()
                self._databases_cache[database_id] = response
            
            return response
        
        except Exception as e:
            self._set_error(f"Failed to get database {database_id}: {str(e)}")
            return None
    
    async def query_database(self, database_id: str, 
                           filter_conditions: Optional[Dict] = None,
                           sorts: Optional[List[Dict]] = None,
                           start_cursor: Optional[str] = None,
                           page_size: int = 100) -> Dict[str, Any]:
        """Query a database with filters and sorting."""
        try:
            data = {"page_size": page_size}
            
            if filter_conditions:
                data["filter"] = filter_conditions
            
            if sorts:
                data["sorts"] = sorts
            
            if start_cursor:
                data["start_cursor"] = start_cursor
            
            response = await self._make_request("POST", f"/databases/{database_id}/query", data)
            return response
        
        except Exception as e:
            self._set_error(f"Database query failed: {str(e)}")
            return {"results": [], "has_more": False}
    
    async def get_page_content(self, page_id: str) -> List[Dict[str, Any]]:
        """Get the content blocks of a page."""
        try:
            all_blocks = []
            start_cursor = None
            
            while True:
                params = {"page_size": 100}
                if start_cursor:
                    params["start_cursor"] = start_cursor
                
                response = await self._make_request("GET", f"/blocks/{page_id}/children", params=params)
                blocks = response.get("results", [])
                all_blocks.extend(blocks)
                
                if not response.get("has_more", False):
                    break
                
                start_cursor = response.get("next_cursor")
            
            return all_blocks
        
        except Exception as e:
            self._set_error(f"Failed to get page content: {str(e)}")
            return []
    
    async def create_page(self, parent: Dict[str, Any], properties: Dict[str, Any],
                         children: Optional[List[Dict]] = None) -> Optional[Dict[str, Any]]:
        """Create a new page."""
        try:
            data = {
                "parent": parent,
                "properties": properties
            }
            
            if children:
                data["children"] = children
            
            response = await self._make_request("POST", "/pages", data)
            return response
        
        except Exception as e:
            self._set_error(f"Failed to create page: {str(e)}")
            return None
    
    async def update_page(self, page_id: str, properties: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update page properties."""
        try:
            data = {"properties": properties}
            response = await self._make_request("PATCH", f"/pages/{page_id}", data)
            
            # Update cache
            if page_id in self._pages_cache:
                del self._pages_cache[page_id]
            
            return response
        
        except Exception as e:
            self._set_error(f"Failed to update page: {str(e)}")
            return None
    
    async def append_blocks(self, block_id: str, children: List[Dict[str, Any]]) -> bool:
        """Append blocks to a page or block."""
        try:
            data = {"children": children}
            await self._make_request("PATCH", f"/blocks/{block_id}/children", data)
            return True
        
        except Exception as e:
            self._set_error(f"Failed to append blocks: {str(e)}")
            return False
    
    def clear_cache(self) -> None:
        """Clear all cached data."""
        self._pages_cache.clear()
        self._databases_cache.clear()
