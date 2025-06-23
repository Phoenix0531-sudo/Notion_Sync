"""
同步桥接器 - 连接 Notion API 客户端和文件同步服务。
"""

from typing import Optional, Dict, Any
from PySide6.QtCore import QObject, Signal

from notion_sync.services.notion_client import NotionClient
from notion_sync.services.file_sync_service import FileSyncService
from notion_sync.services.file_watcher import FileWatcher
from notion_sync.utils.logging_config import LoggerMixin


class SyncBridge(QObject, LoggerMixin):
    """同步桥接器 - 协调各个同步组件。"""
    
    # 信号
    sync_status_changed = Signal(str)  # 同步状态变化
    connection_status_changed = Signal(bool)  # 连接状态变化
    
    def __init__(self, config_manager):
        super().__init__()
        self.config_manager = config_manager
        
        # 初始化组件
        self.notion_client: Optional[NotionClient] = None
        self.file_sync_service = FileSyncService(config_manager)
        self.file_watcher = FileWatcher()
        
        # 连接信号
        self._setup_connections()
    
    def _setup_connections(self):
        """设置组件间的信号连接。"""
        # 文件监控信号
        self.file_watcher.file_changed.connect(self._on_file_changed)
        
        # 文件同步服务信号
        self.file_sync_service.sync_started.connect(
            lambda: self.sync_status_changed.emit("同步已启动")
        )
        self.file_sync_service.sync_completed.connect(
            lambda success, msg: self.sync_status_changed.emit(msg)
        )
        self.file_sync_service.sync_error.connect(
            lambda error: self.sync_status_changed.emit(f"同步错误: {error}")
        )
    
    def set_notion_client(self, notion_client: NotionClient):
        """设置 Notion 客户端。"""
        self.notion_client = notion_client
        
        # 将 Notion 客户端注入到文件同步服务
        self._inject_notion_client_to_sync_service()
        
        # 连接 Notion 客户端信号
        if notion_client:
            notion_client.connection_changed.connect(self.connection_status_changed.emit)
    
    def _inject_notion_client_to_sync_service(self):
        """将 Notion 客户端注入到文件同步服务。"""
        if hasattr(self.file_sync_service, '_notion_client'):
            self.file_sync_service._notion_client = self.notion_client
        
        # 为同步工作线程提供 Notion 客户端访问
        original_get_notion_client = getattr(
            self.file_sync_service.__class__, '_get_notion_client', None
        )
        
        def get_notion_client_impl(sync_service_instance):
            return self.notion_client
        
        # 动态替换方法
        self.file_sync_service._get_notion_client = lambda: self.notion_client
    
    def connect_to_notion(self, api_token: str) -> bool:
        """连接到 Notion。"""
        try:
            if not self.notion_client:
                self.notion_client = NotionClient()
                self.set_notion_client(self.notion_client)
            
            success = self.notion_client.set_api_token(api_token)
            if success:
                self.logger.info("成功连接到 Notion")
                self.sync_status_changed.emit("已连接到云端服务")
                return True
            else:
                self.logger.error("连接到 Notion 失败")
                self.sync_status_changed.emit("连接失败")
                return False
                
        except Exception as e:
            self.logger.error(f"连接到 Notion 时发生错误: {e}")
            self.sync_status_changed.emit(f"连接错误: {str(e)}")
            return False
    
    def disconnect_from_notion(self):
        """断开 Notion 连接。"""
        if self.notion_client:
            self.notion_client.disconnect()
        self.sync_status_changed.emit("已断开云端连接")
    
    def start_file_watching(self, paths: list):
        """开始文件监控。"""
        try:
            # 清除现有监控路径
            self.file_watcher.clear_watch_paths()
            
            # 添加新的监控路径
            for path in paths:
                self.file_watcher.add_watch_path(path)
            
            # 启动监控
            if self.file_watcher.start_watching():
                self.logger.info(f"开始监控 {len(paths)} 个路径")
                return True
            else:
                self.logger.error("启动文件监控失败")
                return False
                
        except Exception as e:
            self.logger.error(f"启动文件监控时发生错误: {e}")
            return False
    
    def stop_file_watching(self):
        """停止文件监控。"""
        self.file_watcher.stop_watching()
        self.logger.info("文件监控已停止")
    
    def add_sync_pair(self, local_path: str, remote_path: str, sync_mode: str = "bidirectional") -> bool:
        """添加同步对。"""
        success = self.file_sync_service.add_sync_pair(local_path, remote_path, sync_mode)
        if success:
            # 如果启用了自动同步，添加到文件监控
            self.file_watcher.add_watch_path(local_path)
            self.logger.info(f"添加同步对: {local_path} <-> {remote_path}")
        return success
    
    def remove_sync_pair(self, index: int) -> bool:
        """移除同步对。"""
        # 获取要移除的同步对信息
        sync_pairs = self.file_sync_service.get_sync_pairs()
        if 0 <= index < len(sync_pairs):
            removed_pair = sync_pairs[index]
            # 从文件监控中移除
            self.file_watcher.remove_watch_path(str(removed_pair.local_path))
        
        return self.file_sync_service.remove_sync_pair(index)
    
    def start_sync(self, sync_mode: str = "remote_to_local"):
        """开始导出（仅支持云端到本地）。"""
        if not self.notion_client or not self.notion_client.connected:
            self.sync_status_changed.emit("请先连接到 Notion")
            return False

        # 只支持云端到本地的导出
        if sync_mode != "remote_to_local":
            self.sync_status_changed.emit("仅支持从 Notion 导出到本地")
            return False

        self.sync_status_changed.emit("正在导出 Notion 内容...")
        self.file_sync_service.start_sync(sync_mode)
        return True
    
    def stop_sync(self):
        """停止同步。"""
        self.file_sync_service.stop_sync()
    
    def get_sync_pairs(self):
        """获取所有同步对。"""
        return self.file_sync_service.get_sync_pairs()
    
    def is_connected(self) -> bool:
        """检查是否已连接到 Notion。"""
        return self.notion_client and self.notion_client.connected
    
    def is_syncing(self) -> bool:
        """检查是否正在同步。"""
        return self.file_sync_service.is_syncing
    
    def _on_file_changed(self, event):
        """处理文件变化事件。"""
        self.logger.info(f"检测到文件变化: {event}")
        
        # 如果启用了自动同步，触发同步
        if self.is_connected() and not self.is_syncing():
            # 检查变化的文件是否在同步对中
            changed_file_path = str(event.path)
            sync_pairs = self.get_sync_pairs()
            
            for pair in sync_pairs:
                if changed_file_path.startswith(str(pair.local_path)):
                    self.logger.info(f"触发自动同步: {pair.local_path}")
                    self.start_sync(pair.sync_mode)
                    break
    
    def get_notion_workspace_info(self) -> Dict[str, Any]:
        """获取 Notion 工作区信息。"""
        if not self.notion_client or not self.notion_client.connected:
            return {}
        
        return self.notion_client.load_workspace()
    
    def create_remote_path_mapping(self, remote_path: str, page_id: str):
        """创建远程路径到页面ID的映射。"""
        # 这里可以维护一个路径映射表
        # 暂时存储在配置中
        mappings = self.config_manager.get("remote_path_mappings", {})
        mappings[remote_path] = page_id
        self.config_manager.set("remote_path_mappings", mappings)
        self.logger.info(f"创建路径映射: {remote_path} -> {page_id}")
    
    def resolve_remote_path(self, remote_path: str) -> Optional[str]:
        """解析远程路径为页面ID。"""
        mappings = self.config_manager.get("remote_path_mappings", {})
        return mappings.get(remote_path)
    
    def cleanup(self):
        """清理资源。"""
        self.stop_file_watching()
        self.stop_sync()
        if self.notion_client:
            self.notion_client.disconnect()
        self.logger.info("同步桥接器已清理")
