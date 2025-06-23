"""
双向同步引擎实现。
"""

import asyncio
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum

from notion_sync.models.base import SyncableModel
from notion_sync.models.notion_client import NotionClient
from notion_sync.models.file_system import FileManager, FileInfo
from notion_sync.models.database import DatabaseManager, SyncRecord


class ConflictType(Enum):
    """冲突类型枚举。"""
    NO_CONFLICT = "no_conflict"
    LOCAL_NEWER = "local_newer"
    NOTION_NEWER = "notion_newer"
    BOTH_MODIFIED = "both_modified"
    LOCAL_DELETED = "local_deleted"
    NOTION_DELETED = "notion_deleted"


class ConflictResolution(Enum):
    """冲突解决策略枚举。"""
    ASK_USER = "ask_user"
    LOCAL_WINS = "local_wins"
    NOTION_WINS = "notion_wins"
    CREATE_BOTH = "create_both"
    SKIP = "skip"


class SyncOperation:
    """同步操作数据类。"""
    
    def __init__(self, operation_type: str, local_path: str, notion_id: str,
                 direction: str, conflict_type: ConflictType = ConflictType.NO_CONFLICT):
        self.operation_type = operation_type  # create, update, delete
        self.local_path = local_path
        self.notion_id = notion_id
        self.direction = direction  # local_to_notion, notion_to_local, bidirectional
        self.conflict_type = conflict_type
        self.resolution: Optional[ConflictResolution] = None
        self.status = "pending"  # pending, in_progress, completed, failed
        self.error_message: Optional[str] = None


class SyncEngine(SyncableModel):
    """双向同步引擎。"""
    
    def __init__(self, notion_client: NotionClient, file_manager: FileManager,
                 database_manager: DatabaseManager, parent=None):
        """初始化同步引擎。"""
        super().__init__(parent)
        self.notion_client = notion_client
        self.file_manager = file_manager
        self.database_manager = database_manager
        
        # 同步配置
        self.default_resolution = ConflictResolution.ASK_USER
        self.max_concurrent_operations = 3
        self.retry_attempts = 3
        
        # 当前同步状态
        self._sync_operations: List[SyncOperation] = []
        self._current_operation_index = 0
    
    async def sync(self) -> bool:
        """执行同步操作。"""
        try:
            self._set_sync_state(True)
            self.logger.info("开始双向同步")
            
            # 获取所有同步记录
            sync_records = self.database_manager.get_all_sync_records()
            
            if not sync_records:
                self.logger.info("没有配置的同步对")
                return True
            
            # 分析每个同步对的状态
            total_operations = 0
            for record in sync_records:
                operations = await self._analyze_sync_record(record)
                self._sync_operations.extend(operations)
                total_operations += len(operations)
            
            if not self._sync_operations:
                self.logger.info("没有需要同步的内容")
                return True
            
            # 处理冲突
            await self._resolve_conflicts()
            
            # 执行同步操作
            success = await self._execute_sync_operations()
            
            self.logger.info(f"同步完成，成功: {success}")
            return success
            
        except Exception as e:
            self.logger.error(f"同步失败: {e}", exc_info=True)
            self._set_error(f"同步失败: {str(e)}")
            return False
        finally:
            self._set_sync_state(False)
    
    async def _analyze_sync_record(self, record: SyncRecord) -> List[SyncOperation]:
        """分析同步记录，确定需要的操作。"""
        operations = []
        
        try:
            # 获取本地文件信息
            local_path = Path(record.local_path)
            local_exists = local_path.exists()
            local_modified = None
            local_checksum = None
            
            if local_exists:
                file_info = FileInfo(local_path)
                local_modified = file_info.modified_time
                local_checksum = file_info.get_checksum()
            
            # 获取 Notion 内容信息
            notion_exists = False
            notion_modified = None
            notion_checksum = None
            
            if record.notion_type == "page":
                notion_page = await self.notion_client.get_page(record.notion_id)
                if notion_page:
                    notion_exists = True
                    notion_modified = datetime.fromisoformat(
                        notion_page["last_edited_time"].replace("Z", "+00:00")
                    )
                    # 计算 Notion 内容的校验和
                    notion_checksum = await self._get_notion_content_checksum(record.notion_id)
            
            # 确定冲突类型
            conflict_type = self._detect_conflict(
                local_exists, local_modified, local_checksum,
                notion_exists, notion_modified, notion_checksum,
                record
            )
            
            # 根据冲突类型创建操作
            operation = self._create_sync_operation(record, conflict_type)
            if operation:
                operations.append(operation)
        
        except Exception as e:
            self.logger.error(f"分析同步记录失败 {record.local_path}: {e}")
        
        return operations
    
    def _detect_conflict(self, local_exists: bool, local_modified: Optional[datetime],
                        local_checksum: Optional[str], notion_exists: bool,
                        notion_modified: Optional[datetime], notion_checksum: Optional[str],
                        record: SyncRecord) -> ConflictType:
        """检测冲突类型。"""
        
        # 如果没有上次同步时间，认为是首次同步
        if not record.last_sync_time:
            if local_exists and notion_exists:
                return ConflictType.BOTH_MODIFIED
            elif local_exists:
                return ConflictType.LOCAL_NEWER
            elif notion_exists:
                return ConflictType.NOTION_NEWER
            else:
                return ConflictType.NO_CONFLICT
        
        # 检查是否有删除
        if not local_exists and not notion_exists:
            return ConflictType.NO_CONFLICT
        elif not local_exists:
            return ConflictType.LOCAL_DELETED
        elif not notion_exists:
            return ConflictType.NOTION_DELETED
        
        # 检查内容是否变更
        local_changed = (local_modified and local_modified > record.last_sync_time) or \
                       (local_checksum != record.local_checksum)
        notion_changed = (notion_modified and notion_modified > record.last_sync_time) or \
                        (notion_checksum != record.notion_checksum)
        
        if local_changed and notion_changed:
            return ConflictType.BOTH_MODIFIED
        elif local_changed:
            return ConflictType.LOCAL_NEWER
        elif notion_changed:
            return ConflictType.NOTION_NEWER
        else:
            return ConflictType.NO_CONFLICT
    
    def _create_sync_operation(self, record: SyncRecord, conflict_type: ConflictType) -> Optional[SyncOperation]:
        """根据冲突类型创建同步操作。"""
        
        if conflict_type == ConflictType.NO_CONFLICT:
            return None
        
        # 确定操作类型和方向
        if conflict_type == ConflictType.LOCAL_NEWER:
            operation_type = "update"
            direction = "local_to_notion"
        elif conflict_type == ConflictType.NOTION_NEWER:
            operation_type = "update"
            direction = "notion_to_local"
        elif conflict_type == ConflictType.LOCAL_DELETED:
            operation_type = "delete"
            direction = "local_to_notion"
        elif conflict_type == ConflictType.NOTION_DELETED:
            operation_type = "delete"
            direction = "notion_to_local"
        else:  # BOTH_MODIFIED
            operation_type = "update"
            direction = "bidirectional"
        
        return SyncOperation(
            operation_type=operation_type,
            local_path=record.local_path,
            notion_id=record.notion_id,
            direction=direction,
            conflict_type=conflict_type
        )
    
    async def _resolve_conflicts(self) -> None:
        """解决冲突。"""
        for operation in self._sync_operations:
            if operation.conflict_type == ConflictType.BOTH_MODIFIED:
                # 发出冲突检测信号，让 UI 处理
                conflict_data = {
                    "local_path": operation.local_path,
                    "notion_id": operation.notion_id,
                    "conflict_type": operation.conflict_type.value,
                    "operation": operation
                }
                self.conflict_detected.emit(conflict_data)
                
                # 如果没有用户选择，使用默认策略
                if operation.resolution is None:
                    operation.resolution = self.default_resolution
    
    async def _execute_sync_operations(self) -> bool:
        """执行同步操作。"""
        total_operations = len(self._sync_operations)
        completed_operations = 0
        
        # 使用信号量限制并发操作数
        semaphore = asyncio.Semaphore(self.max_concurrent_operations)
        
        async def execute_operation(operation: SyncOperation) -> bool:
            async with semaphore:
                return await self._execute_single_operation(operation)
        
        # 并发执行操作
        tasks = [execute_operation(op) for op in self._sync_operations]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 统计结果
        success_count = sum(1 for result in results if result is True)
        
        # 更新进度
        self._emit_progress(100, f"同步完成: {success_count}/{total_operations} 成功")
        
        return success_count == total_operations
    
    async def _execute_single_operation(self, operation: SyncOperation) -> bool:
        """执行单个同步操作。"""
        try:
            operation.status = "in_progress"
            
            if operation.direction == "local_to_notion":
                success = await self._sync_local_to_notion(operation)
            elif operation.direction == "notion_to_local":
                success = await self._sync_notion_to_local(operation)
            else:  # bidirectional conflict
                success = await self._handle_bidirectional_conflict(operation)
            
            operation.status = "completed" if success else "failed"
            return success
            
        except Exception as e:
            operation.status = "failed"
            operation.error_message = str(e)
            self.logger.error(f"执行同步操作失败: {e}")
            return False
    
    async def _sync_local_to_notion(self, operation: SyncOperation) -> bool:
        """同步本地文件到 Notion。"""
        # 实现本地到 Notion 的同步逻辑
        # 这里需要根据具体的文件类型和 Notion API 来实现
        self.logger.info(f"同步本地文件到 Notion: {operation.local_path}")
        return True
    
    async def _sync_notion_to_local(self, operation: SyncOperation) -> bool:
        """同步 Notion 内容到本地。"""
        # 实现 Notion 到本地的同步逻辑
        self.logger.info(f"同步 Notion 内容到本地: {operation.notion_id}")
        return True
    
    async def _handle_bidirectional_conflict(self, operation: SyncOperation) -> bool:
        """处理双向冲突。"""
        if operation.resolution == ConflictResolution.LOCAL_WINS:
            return await self._sync_local_to_notion(operation)
        elif operation.resolution == ConflictResolution.NOTION_WINS:
            return await self._sync_notion_to_local(operation)
        elif operation.resolution == ConflictResolution.CREATE_BOTH:
            # 创建两个版本
            local_success = await self._sync_local_to_notion(operation)
            notion_success = await self._sync_notion_to_local(operation)
            return local_success and notion_success
        else:  # SKIP
            return True
    
    async def _get_notion_content_checksum(self, notion_id: str) -> str:
        """获取 Notion 内容的校验和。"""
        try:
            # 获取页面内容
            blocks = await self.notion_client.get_page_content(notion_id)
            
            # 将内容转换为字符串并计算校验和
            content_str = str(blocks)
            return hashlib.md5(content_str.encode()).hexdigest()
        except Exception as e:
            self.logger.error(f"获取 Notion 内容校验和失败: {e}")
            return ""
    
    def set_conflict_resolution(self, operation: SyncOperation, resolution: ConflictResolution) -> None:
        """设置冲突解决策略。"""
        operation.resolution = resolution
    
    def get_sync_statistics(self) -> Dict[str, int]:
        """获取同步统计信息。"""
        stats = {
            "total": len(self._sync_operations),
            "pending": 0,
            "in_progress": 0,
            "completed": 0,
            "failed": 0
        }
        
        for operation in self._sync_operations:
            stats[operation.status] += 1
        
        return stats
