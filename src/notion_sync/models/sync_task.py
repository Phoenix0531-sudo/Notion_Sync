"""
同步任务数据模型
"""

import json
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum


class TaskStatus(Enum):
    """任务状态"""
    CREATED = "created"          # 已创建
    RUNNING = "running"          # 运行中
    COMPLETED = "completed"      # 已完成
    FAILED = "failed"           # 失败
    PAUSED = "paused"           # 暂停


class SyncDirection(Enum):
    """同步方向"""
    NOTION_TO_LOCAL = "notion_to_local"    # Notion 到本地
    LOCAL_TO_NOTION = "local_to_notion"    # 本地到 Notion
    BIDIRECTIONAL = "bidirectional"       # 双向同步


@dataclass
class NotionSource:
    """Notion 源配置"""
    source_type: str  # "page" 或 "database"
    source_id: str    # 页面或数据库 ID
    source_title: str # 页面或数据库标题
    include_children: bool = True  # 是否包含子页面
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'NotionSource':
        return cls(**data)


@dataclass
class LocalTarget:
    """本地目标配置"""
    folder_path: str              # 本地文件夹路径
    file_format: str = "markdown" # 文件格式：markdown, html, txt
    preserve_structure: bool = True # 保持文件夹结构
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LocalTarget':
        return cls(**data)


@dataclass
class SyncOptions:
    """同步选项"""
    auto_sync: bool = False           # 自动同步
    sync_interval: int = 3600         # 同步间隔（秒）
    overwrite_existing: bool = True   # 覆盖已存在文件
    backup_before_sync: bool = False  # 同步前备份
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SyncOptions':
        return cls(**data)


@dataclass
class SyncStats:
    """同步统计"""
    total_files: int = 0
    successful_files: int = 0
    failed_files: int = 0
    last_sync_time: Optional[str] = None
    last_sync_duration: float = 0.0  # 秒
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SyncStats':
        return cls(**data)


class SyncTask:
    """同步任务"""
    
    def __init__(self, 
                 name: str,
                 notion_source: NotionSource,
                 local_target: LocalTarget,
                 sync_direction: SyncDirection = SyncDirection.NOTION_TO_LOCAL,
                 sync_options: Optional[SyncOptions] = None,
                 task_id: Optional[str] = None):
        
        self.task_id = task_id or str(uuid.uuid4())
        self.name = name
        self.notion_source = notion_source
        self.local_target = local_target
        self.sync_direction = sync_direction
        self.sync_options = sync_options or SyncOptions()
        
        # 状态信息
        self.status = TaskStatus.CREATED
        self.created_time = datetime.now().isoformat()
        self.last_modified = datetime.now().isoformat()
        self.error_message = ""
        
        # 统计信息
        self.stats = SyncStats()
    
    def update_status(self, status: TaskStatus, error_message: str = ""):
        """更新任务状态"""
        self.status = status
        self.last_modified = datetime.now().isoformat()
        self.error_message = error_message
    
    def update_stats(self, stats: SyncStats):
        """更新统计信息"""
        self.stats = stats
        self.last_modified = datetime.now().isoformat()
    
    def get_display_name(self) -> str:
        """获取显示名称"""
        return f"{self.name} ({self.notion_source.source_title})"
    
    def get_status_display(self) -> str:
        """获取状态显示文本"""
        status_map = {
            TaskStatus.CREATED: "已创建",
            TaskStatus.RUNNING: "运行中",
            TaskStatus.COMPLETED: "已完成",
            TaskStatus.FAILED: "失败",
            TaskStatus.PAUSED: "暂停"
        }
        return status_map.get(self.status, "未知")
    
    def get_direction_display(self) -> str:
        """获取同步方向显示文本"""
        direction_map = {
            SyncDirection.NOTION_TO_LOCAL: "Notion → 本地",
            SyncDirection.LOCAL_TO_NOTION: "本地 → Notion",
            SyncDirection.BIDIRECTIONAL: "双向同步"
        }
        return direction_map.get(self.sync_direction, "未知")
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "task_id": self.task_id,
            "name": self.name,
            "notion_source": self.notion_source.to_dict(),
            "local_target": self.local_target.to_dict(),
            "sync_direction": self.sync_direction.value,
            "sync_options": self.sync_options.to_dict(),
            "status": self.status.value,
            "created_time": self.created_time,
            "last_modified": self.last_modified,
            "error_message": self.error_message,
            "stats": self.stats.to_dict()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SyncTask':
        """从字典创建任务"""
        task = cls(
            name=data["name"],
            notion_source=NotionSource.from_dict(data["notion_source"]),
            local_target=LocalTarget.from_dict(data["local_target"]),
            sync_direction=SyncDirection(data["sync_direction"]),
            sync_options=SyncOptions.from_dict(data["sync_options"]),
            task_id=data["task_id"]
        )
        
        task.status = TaskStatus(data["status"])
        task.created_time = data["created_time"]
        task.last_modified = data["last_modified"]
        task.error_message = data.get("error_message", "")
        task.stats = SyncStats.from_dict(data.get("stats", {}))
        
        return task
    
    def to_json(self) -> str:
        """转换为 JSON 字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'SyncTask':
        """从 JSON 字符串创建任务"""
        data = json.loads(json_str)
        return cls.from_dict(data)
