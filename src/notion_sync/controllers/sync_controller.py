"""
同步控制器，协调同步引擎和用户界面。
"""

import asyncio
from typing import Dict, Any, Optional
from PySide6.QtCore import QObject, Signal, QTimer

from notion_sync.controllers.base import SyncController
from notion_sync.models.sync_engine import SyncEngine, ConflictResolution
from notion_sync.models.notion_client import NotionClient
from notion_sync.models.file_system import FileManager
from notion_sync.models.database import DatabaseManager
from notion_sync.views.conflict_dialog import ConflictDialog


class MainSyncController(SyncController):
    """主同步控制器。"""
    
    # 同步状态信号
    sync_status_changed = Signal(str)
    sync_progress_updated = Signal(int, str)
    conflict_resolution_needed = Signal(dict)
    
    def __init__(self, notion_client: NotionClient, file_manager: FileManager,
                 database_manager: DatabaseManager, parent: Optional[QObject] = None):
        """初始化同步控制器。"""
        super().__init__(parent)
        
        # 核心组件
        self.notion_client = notion_client
        self.file_manager = file_manager
        self.database_manager = database_manager
        
        # 同步引擎
        self.sync_engine = SyncEngine(
            notion_client, file_manager, database_manager, self
        )
        
        # 自动同步定时器
        self.auto_sync_timer = QTimer()
        self.auto_sync_timer.timeout.connect(self._auto_sync)
        
        # 同步配置
        self.auto_sync_enabled = False
        self.sync_interval = 300  # 5分钟
        
        # 当前冲突对话框
        self.current_conflict_dialog: Optional[ConflictDialog] = None
        
        # 设置连接
        self._setup_connections()
    
    def _setup_connections(self) -> None:
        """设置信号连接。"""
        # 同步引擎信号
        self.sync_engine.sync_started.connect(self._on_sync_started)
        self.sync_engine.sync_finished.connect(self._on_sync_finished)
        self.sync_engine.sync_progress.connect(self._on_sync_progress)
        self.sync_engine.conflict_detected.connect(self._on_conflict_detected)
        self.sync_engine.error_occurred.connect(self._on_sync_error)
        
        # 文件管理器信号
        self.file_manager.file_changed.connect(self._on_file_changed)
    
    async def start_sync(self, sync_type: str = "bidirectional", **kwargs) -> bool:
        """启动同步操作。"""
        if self.sync_in_progress:
            self.logger.warning("同步已在进行中")
            return False
        
        try:
            self._start_sync(sync_type)
            
            if sync_type == "bidirectional":
                success = await self.sync_engine.sync()
            elif sync_type == "local_to_notion":
                success = await self._sync_local_to_notion(**kwargs)
            elif sync_type == "notion_to_local":
                success = await self._sync_notion_to_local(**kwargs)
            else:
                raise ValueError(f"未知的同步类型: {sync_type}")
            
            self._finish_sync(success)
            return success
            
        except Exception as e:
            self.logger.error(f"同步失败: {e}", exc_info=True)
            self._finish_sync(False)
            return False
    
    async def _sync_local_to_notion(self, **kwargs) -> bool:
        """执行本地到 Notion 的同步。"""
        selected_files = kwargs.get("selected_files", [])
        notion_target = kwargs.get("notion_target", {})
        
        if not selected_files:
            self.sync_status_changed.emit("没有选择要上传的文件")
            return False
        
        if not notion_target:
            self.sync_status_changed.emit("没有选择 Notion 目标")
            return False
        
        total_files = len(selected_files)
        uploaded_files = 0
        
        for i, file_path in enumerate(selected_files):
            try:
                # 更新进度
                progress = int((i / total_files) * 100)
                self.sync_progress_updated.emit(progress, f"上传文件: {file_path}")
                
                # 执行上传
                success = await self._upload_file_to_notion(file_path, notion_target)
                
                if success:
                    uploaded_files += 1
                    # 创建或更新同步记录
                    await self._create_sync_record(file_path, notion_target)
                
            except Exception as e:
                self.logger.error(f"上传文件失败 {file_path}: {e}")
        
        # 完成进度
        self.sync_progress_updated.emit(100, f"上传完成: {uploaded_files}/{total_files}")
        return uploaded_files == total_files
    
    async def _sync_notion_to_local(self, **kwargs) -> bool:
        """执行 Notion 到本地的同步。"""
        selected_items = kwargs.get("selected_items", [])
        export_settings = kwargs.get("export_settings", {})
        
        if not selected_items:
            self.sync_status_changed.emit("没有选择要导出的内容")
            return False
        
        destination = export_settings.get("destination")
        if not destination:
            self.sync_status_changed.emit("没有选择导出目标")
            return False
        
        total_items = len(selected_items)
        exported_items = 0
        
        for i, item in enumerate(selected_items):
            try:
                # 更新进度
                progress = int((i / total_items) * 100)
                self.sync_progress_updated.emit(progress, f"导出: {item.get('title', 'Unknown')}")
                
                # 执行导出
                success = await self._export_notion_item(item, export_settings)
                
                if success:
                    exported_items += 1
                
            except Exception as e:
                self.logger.error(f"导出失败 {item}: {e}")
        
        # 完成进度
        self.sync_progress_updated.emit(100, f"导出完成: {exported_items}/{total_items}")
        return exported_items == total_items
    
    async def _upload_file_to_notion(self, file_path: str, notion_target: Dict[str, Any]) -> bool:
        """上传文件到 Notion。"""
        try:
            from pathlib import Path
            
            file_info = self.file_manager.get_file_info(Path(file_path))
            if not file_info:
                return False
            
            # 根据文件类型选择上传方式
            if file_info.suffix == '.md':
                return await self._upload_markdown_to_notion(file_info, notion_target)
            elif file_info.suffix in ['.png', '.jpg', '.jpeg', '.gif']:
                return await self._upload_image_to_notion(file_info, notion_target)
            else:
                return await self._upload_generic_file_to_notion(file_info, notion_target)
                
        except Exception as e:
            self.logger.error(f"上传文件失败: {e}")
            return False
    
    async def _upload_markdown_to_notion(self, file_info, notion_target: Dict[str, Any]) -> bool:
        """上传 Markdown 文件到 Notion。"""
        # 读取 Markdown 内容
        content = file_info.read_content()
        metadata = file_info.read_metadata()
        
        # 转换为 Notion 块
        blocks = self._convert_markdown_to_notion_blocks(content)
        
        # 创建页面属性
        properties = {
            "title": {
                "title": [{"text": {"content": metadata.get("title", file_info.stem)}}]
            }
        }
        
        # 创建页面
        parent = {"page_id": notion_target["id"]} if notion_target["type"] == "page" else {"database_id": notion_target["id"]}
        
        page = await self.notion_client.create_page(parent, properties, blocks)
        return page is not None
    
    async def _upload_image_to_notion(self, file_info, notion_target: Dict[str, Any]) -> bool:
        """上传图片到 Notion。"""
        # 这里需要实现图片上传逻辑
        # Notion API 需要先上传到外部服务，然后引用 URL
        self.logger.info(f"上传图片: {file_info.path}")
        return True
    
    async def _upload_generic_file_to_notion(self, file_info, notion_target: Dict[str, Any]) -> bool:
        """上传通用文件到 Notion。"""
        # 这里需要实现通用文件上传逻辑
        self.logger.info(f"上传文件: {file_info.path}")
        return True
    
    def _convert_markdown_to_notion_blocks(self, markdown_content: str) -> list:
        """将 Markdown 内容转换为 Notion 块。"""
        # 简单的 Markdown 到 Notion 块转换
        # 这里需要更完整的实现
        blocks = []
        
        lines = markdown_content.split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            if line.startswith('# '):
                # 一级标题
                blocks.append({
                    "object": "block",
                    "type": "heading_1",
                    "heading_1": {
                        "rich_text": [{"type": "text", "text": {"content": line[2:]}}]
                    }
                })
            elif line.startswith('## '):
                # 二级标题
                blocks.append({
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {
                        "rich_text": [{"type": "text", "text": {"content": line[3:]}}]
                    }
                })
            else:
                # 普通段落
                blocks.append({
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{"type": "text", "text": {"content": line}}]
                    }
                })
        
        return blocks
    
    async def _export_notion_item(self, item: Dict[str, Any], export_settings: Dict[str, Any]) -> bool:
        """导出 Notion 项目到本地。"""
        try:
            item_type = item.get("type")
            item_id = item.get("id")
            
            if item_type == "page":
                return await self._export_notion_page(item_id, export_settings)
            elif item_type == "database":
                return await self._export_notion_database(item_id, export_settings)
            else:
                return False
                
        except Exception as e:
            self.logger.error(f"导出 Notion 项目失败: {e}")
            return False
    
    async def _export_notion_page(self, page_id: str, export_settings: Dict[str, Any]) -> bool:
        """导出 Notion 页面。"""
        # 获取页面信息
        page = await self.notion_client.get_page(page_id)
        if not page:
            return False
        
        # 获取页面内容
        blocks = await self.notion_client.get_page_content(page_id)
        
        # 转换为指定格式
        export_format = export_settings.get("format", "markdown")
        if export_format == "markdown":
            content = self._convert_notion_blocks_to_markdown(blocks)
            file_extension = ".md"
        elif export_format == "html":
            content = self._convert_notion_blocks_to_html(blocks)
            file_extension = ".html"
        else:
            content = str(blocks)
            file_extension = ".json"
        
        # 保存文件
        from pathlib import Path
        destination = Path(export_settings["destination"])
        page_title = self._get_page_title(page)
        file_path = destination / f"{page_title}{file_extension}"
        
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        except Exception as e:
            self.logger.error(f"保存文件失败: {e}")
            return False
    
    async def _export_notion_database(self, database_id: str, export_settings: Dict[str, Any]) -> bool:
        """导出 Notion 数据库。"""
        # 这里需要实现数据库导出逻辑
        self.logger.info(f"导出数据库: {database_id}")
        return True
    
    def _convert_notion_blocks_to_markdown(self, blocks: list) -> str:
        """将 Notion 块转换为 Markdown。"""
        # 简单的 Notion 块到 Markdown 转换
        markdown_lines = []
        
        for block in blocks:
            block_type = block.get("type")
            
            if block_type == "heading_1":
                text = self._extract_rich_text(block.get("heading_1", {}).get("rich_text", []))
                markdown_lines.append(f"# {text}")
            elif block_type == "heading_2":
                text = self._extract_rich_text(block.get("heading_2", {}).get("rich_text", []))
                markdown_lines.append(f"## {text}")
            elif block_type == "paragraph":
                text = self._extract_rich_text(block.get("paragraph", {}).get("rich_text", []))
                markdown_lines.append(text)
            
            markdown_lines.append("")  # 空行
        
        return "\n".join(markdown_lines)
    
    def _convert_notion_blocks_to_html(self, blocks: list) -> str:
        """将 Notion 块转换为 HTML。"""
        # 简单的 Notion 块到 HTML 转换
        html_parts = ["<!DOCTYPE html><html><body>"]
        
        for block in blocks:
            block_type = block.get("type")
            
            if block_type == "heading_1":
                text = self._extract_rich_text(block.get("heading_1", {}).get("rich_text", []))
                html_parts.append(f"<h1>{text}</h1>")
            elif block_type == "heading_2":
                text = self._extract_rich_text(block.get("heading_2", {}).get("rich_text", []))
                html_parts.append(f"<h2>{text}</h2>")
            elif block_type == "paragraph":
                text = self._extract_rich_text(block.get("paragraph", {}).get("rich_text", []))
                html_parts.append(f"<p>{text}</p>")
        
        html_parts.append("</body></html>")
        return "\n".join(html_parts)
    
    def _extract_rich_text(self, rich_text_array: list) -> str:
        """从富文本数组中提取纯文本。"""
        return "".join([rt.get("plain_text", "") for rt in rich_text_array])
    
    def _get_page_title(self, page: dict) -> str:
        """获取页面标题。"""
        properties = page.get("properties", {})
        for prop_name, prop_data in properties.items():
            if prop_data.get("type") == "title":
                title_array = prop_data.get("title", [])
                return "".join([t.get("plain_text", "") for t in title_array])
        return "Untitled"
    
    async def _create_sync_record(self, local_path: str, notion_target: Dict[str, Any]) -> None:
        """创建同步记录。"""
        self.database_manager.create_sync_record(
            local_path=local_path,
            notion_id=notion_target["id"],
            notion_type=notion_target["type"],
            sync_direction="bidirectional"
        )
    
    def _on_sync_started(self) -> None:
        """处理同步开始事件。"""
        self.sync_status_changed.emit("同步开始")
    
    def _on_sync_finished(self, sync_type: str, success: bool) -> None:
        """处理同步完成事件。"""
        status = "同步完成" if success else "同步失败"
        self.sync_status_changed.emit(status)
    
    def _on_sync_progress(self, sync_type: str, percentage: int, message: str) -> None:
        """处理同步进度事件。"""
        self.sync_progress_updated.emit(percentage, message)
    
    def _on_conflict_detected(self, conflict_data: dict) -> None:
        """处理冲突检测事件。"""
        # 显示冲突解决对话框
        self.current_conflict_dialog = ConflictDialog(conflict_data)
        self.current_conflict_dialog.resolution_selected.connect(
            lambda resolution: self._resolve_conflict(conflict_data, resolution)
        )
        self.current_conflict_dialog.show()
    
    def _resolve_conflict(self, conflict_data: dict, resolution: str) -> None:
        """解决冲突。"""
        operation = conflict_data.get("operation")
        if operation:
            resolution_enum = ConflictResolution(resolution)
            self.sync_engine.set_conflict_resolution(operation, resolution_enum)
    
    def _on_sync_error(self, error: str) -> None:
        """处理同步错误事件。"""
        self.sync_status_changed.emit(f"同步错误: {error}")
    
    def _on_file_changed(self, file_path: str, change_type: str) -> None:
        """处理文件变更事件。"""
        if self.auto_sync_enabled and not self.sync_in_progress:
            # 延迟触发自动同步，避免频繁同步
            self.auto_sync_timer.start(5000)  # 5秒后触发
    
    def _auto_sync(self) -> None:
        """自动同步。"""
        self.auto_sync_timer.stop()
        if not self.sync_in_progress:
            asyncio.create_task(self.start_sync("bidirectional"))
    
    def set_auto_sync(self, enabled: bool, interval: int = 300) -> None:
        """设置自动同步。"""
        self.auto_sync_enabled = enabled
        self.sync_interval = interval
        
        if enabled:
            self.auto_sync_timer.start(interval * 1000)
        else:
            self.auto_sync_timer.stop()
    
    def get_sync_statistics(self) -> Dict[str, int]:
        """获取同步统计信息。"""
        return self.sync_engine.get_sync_statistics()
