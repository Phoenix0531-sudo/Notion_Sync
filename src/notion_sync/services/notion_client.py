"""
Notion API 客户端 - 实现与 Notion API 的交互。
"""

import requests
import json
from typing import Dict, List, Optional, Any
from datetime import datetime
import time

from PySide6.QtCore import QObject, Signal
from notion_sync.utils.logging_config import LoggerMixin
from notion_sync.utils.smart_cache import get_notion_cache, get_global_cache


class NotionPage:
    """Notion 页面类。"""
    
    def __init__(self, data: Dict):
        self.id = data.get("id", "")
        self.title = self._extract_title(data)
        self.created_time = data.get("created_time", "")
        self.last_edited_time = data.get("last_edited_time", "")
        self.url = data.get("url", "")
        self.parent = data.get("parent", {})
        self.properties = data.get("properties", {})
        self.archived = data.get("archived", False)
    
    def _extract_title(self, data: Dict) -> str:
        """提取页面标题。"""
        properties = data.get("properties", {})
        
        # 查找标题属性
        for prop_name, prop_data in properties.items():
            if prop_data.get("type") == "title":
                title_array = prop_data.get("title", [])
                if title_array:
                    return title_array[0].get("plain_text", "无标题页面")
        
        return "无标题页面"
    
    def to_dict(self) -> Dict:
        """转换为字典。"""
        return {
            "id": self.id,
            "title": self.title,
            "created_time": self.created_time,
            "last_edited_time": self.last_edited_time,
            "url": self.url,
            "archived": self.archived
        }


class NotionDatabase:
    """Notion 数据库类。"""
    
    def __init__(self, data: Dict):
        self.id = data.get("id", "")
        self.title = self._extract_title(data)
        self.created_time = data.get("created_time", "")
        self.last_edited_time = data.get("last_edited_time", "")
        self.url = data.get("url", "")
        self.properties = data.get("properties", {})
        self.archived = data.get("archived", False)
    
    def _extract_title(self, data: Dict) -> str:
        """提取数据库标题。"""
        title_array = data.get("title", [])
        if title_array:
            return title_array[0].get("plain_text", "无标题数据库")
        return "无标题数据库"
    
    def to_dict(self) -> Dict:
        """转换为字典。"""
        return {
            "id": self.id,
            "title": self.title,
            "created_time": self.created_time,
            "last_edited_time": self.last_edited_time,
            "url": self.url,
            "archived": self.archived
        }


class NotionClient(QObject, LoggerMixin):
    """Notion API 客户端。"""
    
    # 信号
    connection_changed = Signal(bool)  # 连接状态变化
    workspace_loaded = Signal(dict)    # 工作区加载完成
    
    def __init__(self):
        super().__init__()
        self.api_token = ""
        self.base_url = "https://api.notion.com/v1"
        self.headers = {
            "Authorization": "",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28"
        }
        self.connected = False
        self.workspace_info = {}
        self.rate_limit_delay = 0.5  # 速率限制延迟（秒）

        # 初始化缓存
        self.notion_cache = get_notion_cache()
        self.global_cache = get_global_cache()
    
    def set_api_token(self, token: str) -> bool:
        """设置 API 令牌。"""
        if not token or len(token.strip()) < 10:
            self.logger.error("无效的 API 令牌格式")
            return False

        self.api_token = token.strip()
        self.headers["Authorization"] = f"Bearer {self.api_token}"
        
        # 测试连接
        return self.test_connection()
    
    def test_connection(self) -> bool:
        """测试连接。"""
        try:
            self.logger.info(f"测试连接到 Notion，令牌长度: {len(self.api_token)}")
            response = self._make_request("GET", "/users/me")

            if response and response.get("object") == "user":
                self.connected = True
                self.connection_changed.emit(True)
                self.logger.info("成功连接到 Notion")
                return True
            else:
                self.connected = False
                self.connection_changed.emit(False)
                if response:
                    self.logger.error(f"连接到 Notion 失败，响应: {response}")
                else:
                    self.logger.error("连接到 Notion 失败，无响应")
                return False
        except Exception as e:
            self.connected = False
            self.connection_changed.emit(False)
            self.logger.error(f"连接测试失败: {e}")
            return False
    
    def disconnect(self):
        """断开连接。"""
        self.api_token = ""
        self.headers["Authorization"] = ""
        self.connected = False
        self.workspace_info = {}
        self.connection_changed.emit(False)
        self.logger.info("已断开与 Notion 的连接")

    def clear_cache(self):
        """清除缓存"""
        workspace_id = f"workspace_{hash(self.api_token)}"
        self.notion_cache.invalidate_workspace(workspace_id)
        self.logger.info("已清除 Notion 缓存")

    def get_page_content(self, page_id: str) -> dict:
        """获取页面内容"""
        if not self.connected:
            raise Exception("未连接到 Notion")

        try:
            # 检查缓存
            cached_content = self.notion_cache.get_page_data(page_id)
            if cached_content:
                self.logger.info(f"从缓存获取页面内容: {page_id}")
                return cached_content

            # 获取页面块内容
            url = f"/blocks/{page_id}/children"
            response = self._make_request("GET", url)

            if response:
                # 缓存内容
                self.notion_cache.set_page_data(page_id, response)
                self.logger.info(f"获取页面内容成功: {page_id}")
                return response
            else:
                raise Exception("获取页面内容失败")

        except Exception as e:
            self.logger.error(f"获取页面内容失败 {page_id}: {e}")
            raise e

    def get_database_content(self, database_id: str) -> dict:
        """获取数据库内容"""
        if not self.connected:
            raise Exception("未连接到 Notion")

        try:
            # 检查缓存
            cached_content = self.notion_cache.get_database_data(database_id)
            if cached_content:
                self.logger.info(f"从缓存获取数据库内容: {database_id}")
                return cached_content

            # 获取数据库页面
            url = f"/databases/{database_id}/query"
            response = self._make_request("POST", url, {})

            if response:
                # 缓存内容
                self.notion_cache.set_database_data(database_id, response)
                self.logger.info(f"获取数据库内容成功: {database_id}")
                return response
            else:
                raise Exception("获取数据库内容失败")

        except Exception as e:
            self.logger.error(f"获取数据库内容失败 {database_id}: {e}")
            raise e
    
    def load_workspace(self) -> Dict:
        """加载工作区信息。"""
        if not self.connected:
            return {}

        # 尝试从缓存获取
        workspace_id = f"workspace_{hash(self.api_token)}"
        cached_workspace = self.notion_cache.get_workspace_data(workspace_id)

        if cached_workspace:
            self.logger.info("从缓存加载工作区信息")
            self.workspace_info = cached_workspace
            self.workspace_loaded.emit(self.workspace_info)
            return self.workspace_info

        try:
            # 获取用户信息
            user_info = self._make_request("GET", "/users/me")

            # 获取页面列表
            pages = self.list_pages()

            # 获取数据库列表
            databases = self.list_databases()

            self.workspace_info = {
                "user": user_info,
                "pages": pages,
                "databases": databases,
                "page_count": len(pages),
                "database_count": len(databases),
                "name": user_info.get("name", "未知工作区") if user_info else "未知工作区",
                "owner": user_info.get("name", "未知") if user_info else "未知"
            }

            # 缓存工作区信息
            self.notion_cache.set_workspace_data(workspace_id, self.workspace_info)

            self.workspace_loaded.emit(self.workspace_info)
            return self.workspace_info

        except Exception as e:
            self.logger.error(f"加载工作区失败: {e}")
            return {}
    
    def list_pages(self, page_size: int = 100) -> List[NotionPage]:
        """列出所有页面。"""
        if not self.connected:
            return []
        
        try:
            all_pages = []
            has_more = True
            next_cursor = None
            
            while has_more:
                params = {"page_size": page_size}
                if next_cursor:
                    params["start_cursor"] = next_cursor
                
                response = self._make_request("POST", "/search", {
                    "filter": {"property": "object", "value": "page"},
                    **params
                })
                
                if not response:
                    break
                
                pages_data = response.get("results", [])
                for page_data in pages_data:
                    all_pages.append(NotionPage(page_data))
                
                has_more = response.get("has_more", False)
                next_cursor = response.get("next_cursor")
                
                # 速率限制
                time.sleep(self.rate_limit_delay)
            
            self.logger.info(f"获取到 {len(all_pages)} 个页面")
            return all_pages
            
        except Exception as e:
            self.logger.error(f"获取页面列表失败: {e}")
            return []
    
    def list_databases(self, page_size: int = 100) -> List[NotionDatabase]:
        """列出所有数据库。"""
        if not self.connected:
            return []
        
        try:
            all_databases = []
            has_more = True
            next_cursor = None
            
            while has_more:
                params = {"page_size": page_size}
                if next_cursor:
                    params["start_cursor"] = next_cursor
                
                response = self._make_request("POST", "/search", {
                    "filter": {"property": "object", "value": "database"},
                    **params
                })
                
                if not response:
                    break
                
                databases_data = response.get("results", [])
                for db_data in databases_data:
                    all_databases.append(NotionDatabase(db_data))
                
                has_more = response.get("has_more", False)
                next_cursor = response.get("next_cursor")
                
                # 速率限制
                time.sleep(self.rate_limit_delay)
            
            self.logger.info(f"获取到 {len(all_databases)} 个数据库")
            return all_databases
            
        except Exception as e:
            self.logger.error(f"获取数据库列表失败: {e}")
            return []
    

    
    def create_page(self, parent_id: str, title: str, content: str = "") -> Optional[str]:
        """创建新页面。"""
        if not self.connected:
            return None
        
        try:
            page_data = {
                "parent": {"page_id": parent_id},
                "properties": {
                    "title": {
                        "title": [{"text": {"content": title}}]
                    }
                }
            }
            
            if content:
                page_data["children"] = [
                    {
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [{"text": {"content": content}}]
                        }
                    }
                ]
            
            response = self._make_request("POST", "/pages", page_data)
            if response:
                self.logger.info(f"创建页面成功: {title}")
                return response.get("id")
            
        except Exception as e:
            self.logger.error(f"创建页面失败: {e}")
        
        return None
    
    def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Optional[Dict]:
        """发送 API 请求。"""
        url = f"{self.base_url}{endpoint}"
        
        try:
            if method == "GET":
                response = requests.get(url, headers=self.headers, timeout=30)
            elif method == "POST":
                response = requests.post(url, headers=self.headers, json=data, timeout=30)
            elif method == "PATCH":
                response = requests.patch(url, headers=self.headers, json=data, timeout=30)
            else:
                self.logger.error(f"不支持的请求方法: {method}")
                return None
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 429:
                # 速率限制，等待后重试
                self.logger.warning("触发速率限制，等待重试")
                time.sleep(2)
                return self._make_request(method, endpoint, data)
            else:
                error_text = response.text
                self.logger.error(f"API 请求失败: {method} {endpoint}")
                self.logger.error(f"状态码: {response.status_code}")
                self.logger.error(f"响应内容: {error_text}")

                # 特殊处理认证错误
                if response.status_code == 401:
                    self.logger.error("认证失败，请检查 API 令牌是否正确")
                elif response.status_code == 403:
                    self.logger.error("权限不足，请检查 API 令牌权限")

                return None
                
        except requests.exceptions.Timeout:
            self.logger.error("请求超时")
            return None
        except requests.exceptions.RequestException as e:
            self.logger.error(f"请求异常: {e}")
            return None
        except Exception as e:
            self.logger.error(f"未知错误: {e}")
            return None
