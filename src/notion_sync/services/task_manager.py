"""
同步任务管理器
"""

import json
import os
from typing import List, Optional, Dict, Any
from pathlib import Path
from PySide6.QtCore import QObject, Signal

from notion_sync.models.sync_task import SyncTask, TaskStatus
from notion_sync.utils.config import ConfigManager


class TaskManager(QObject):
    """同步任务管理器"""
    
    # 信号
    task_added = Signal(SyncTask)
    task_updated = Signal(SyncTask)
    task_removed = Signal(str)  # task_id
    task_status_changed = Signal(str, TaskStatus)  # task_id, status
    
    def __init__(self, config_manager: ConfigManager):
        super().__init__()
        self.config_manager = config_manager
        self.tasks: Dict[str, SyncTask] = {}
        
        # 任务存储文件
        self.tasks_file = Path(config_manager.config_dir) / "sync_tasks.json"
        
        # 加载已保存的任务
        self._load_tasks()
    
    def create_task(self, 
                   name: str,
                   notion_source_type: str,
                   notion_source_id: str,
                   notion_source_title: str,
                   local_folder: str,
                   include_children: bool = True,
                   auto_sync: bool = False) -> SyncTask:
        """创建新的同步任务"""
        from notion_sync.models.sync_task import NotionSource, LocalTarget, SyncDirection, SyncOptions
        
        # 创建 Notion 源配置
        notion_source = NotionSource(
            source_type=notion_source_type,
            source_id=notion_source_id,
            source_title=notion_source_title,
            include_children=include_children
        )
        
        # 创建本地目标配置
        local_target = LocalTarget(
            folder_path=local_folder,
            file_format="markdown",
            preserve_structure=True
        )
        
        # 创建同步选项
        sync_options = SyncOptions(
            auto_sync=auto_sync,
            sync_interval=3600,
            overwrite_existing=True,
            backup_before_sync=False
        )
        
        # 创建任务
        task = SyncTask(
            name=name,
            notion_source=notion_source,
            local_target=local_target,
            sync_direction=SyncDirection.NOTION_TO_LOCAL,
            sync_options=sync_options
        )
        
        # 添加到管理器
        self.add_task(task)
        
        return task
    
    def add_task(self, task: SyncTask):
        """添加任务"""
        self.tasks[task.task_id] = task
        self._save_tasks()
        self.task_added.emit(task)
    
    def remove_task(self, task_id: str) -> bool:
        """删除任务"""
        if task_id in self.tasks:
            del self.tasks[task_id]
            self._save_tasks()
            self.task_removed.emit(task_id)
            return True
        return False
    
    def update_task(self, task: SyncTask):
        """更新任务"""
        if task.task_id in self.tasks:
            self.tasks[task.task_id] = task
            self._save_tasks()
            self.task_updated.emit(task)
    
    def get_task(self, task_id: str) -> Optional[SyncTask]:
        """获取任务"""
        return self.tasks.get(task_id)
    
    def get_all_tasks(self) -> List[SyncTask]:
        """获取所有任务"""
        return list(self.tasks.values())
    
    def get_tasks_by_status(self, status: TaskStatus) -> List[SyncTask]:
        """根据状态获取任务"""
        return [task for task in self.tasks.values() if task.status == status]
    
    def update_task_status(self, task_id: str, status: TaskStatus, error_message: str = ""):
        """更新任务状态"""
        if task_id in self.tasks:
            task = self.tasks[task_id]
            task.update_status(status, error_message)
            self._save_tasks()
            self.task_status_changed.emit(task_id, status)
            self.task_updated.emit(task)
    
    def get_running_tasks(self) -> List[SyncTask]:
        """获取正在运行的任务"""
        return self.get_tasks_by_status(TaskStatus.RUNNING)
    
    def get_failed_tasks(self) -> List[SyncTask]:
        """获取失败的任务"""
        return self.get_tasks_by_status(TaskStatus.FAILED)
    
    def get_auto_sync_tasks(self) -> List[SyncTask]:
        """获取启用自动同步的任务"""
        return [task for task in self.tasks.values() if task.sync_options.auto_sync]
    
    def _load_tasks(self):
        """加载任务"""
        if not self.tasks_file.exists():
            return
        
        try:
            with open(self.tasks_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            for task_data in data.get("tasks", []):
                try:
                    task = SyncTask.from_dict(task_data)
                    self.tasks[task.task_id] = task
                except Exception as e:
                    print(f"加载任务失败: {e}")
                    continue
            
            print(f"加载了 {len(self.tasks)} 个同步任务")
            
        except Exception as e:
            print(f"加载任务文件失败: {e}")
    
    def _save_tasks(self):
        """保存任务"""
        try:
            # 确保目录存在
            self.tasks_file.parent.mkdir(parents=True, exist_ok=True)
            
            # 准备数据
            data = {
                "version": "1.0",
                "tasks": [task.to_dict() for task in self.tasks.values()]
            }
            
            # 保存到文件
            with open(self.tasks_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
        except Exception as e:
            print(f"保存任务文件失败: {e}")
    
    def export_tasks(self, file_path: str) -> bool:
        """导出任务配置"""
        try:
            data = {
                "version": "1.0",
                "export_time": str(Path().cwd()),
                "tasks": [task.to_dict() for task in self.tasks.values()]
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            return True
        except Exception as e:
            print(f"导出任务失败: {e}")
            return False
    
    def import_tasks(self, file_path: str) -> bool:
        """导入任务配置"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            imported_count = 0
            for task_data in data.get("tasks", []):
                try:
                    task = SyncTask.from_dict(task_data)
                    # 生成新的 ID 避免冲突
                    import uuid
                    task.task_id = str(uuid.uuid4())
                    self.add_task(task)
                    imported_count += 1
                except Exception as e:
                    print(f"导入任务失败: {e}")
                    continue
            
            print(f"成功导入 {imported_count} 个任务")
            return True
            
        except Exception as e:
            print(f"导入任务文件失败: {e}")
            return False
    
    def clear_all_tasks(self):
        """清除所有任务"""
        task_ids = list(self.tasks.keys())
        self.tasks.clear()
        self._save_tasks()
        
        for task_id in task_ids:
            self.task_removed.emit(task_id)
    
    def get_task_count(self) -> int:
        """获取任务总数"""
        return len(self.tasks)
    
    def get_status_summary(self) -> Dict[str, int]:
        """获取状态统计"""
        summary = {}
        for status in TaskStatus:
            summary[status.value] = len(self.get_tasks_by_status(status))
        return summary
