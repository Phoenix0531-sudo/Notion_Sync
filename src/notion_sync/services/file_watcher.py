"""
文件监控服务 - 监控文件系统变化。
"""

import os
import time
from pathlib import Path
from typing import Dict, List, Set, Callable, Optional
from datetime import datetime
from enum import Enum

from PySide6.QtCore import QObject, Signal, QTimer, QThread
from notion_sync.utils.logging_config import LoggerMixin


class FileChangeType(Enum):
    """文件变化类型。"""
    CREATED = "created"
    MODIFIED = "modified"
    DELETED = "deleted"
    MOVED = "moved"


class FileChangeEvent:
    """文件变化事件。"""
    
    def __init__(self, path: Path, change_type: FileChangeType, timestamp: datetime = None):
        self.path = path
        self.change_type = change_type
        self.timestamp = timestamp or datetime.now()
        self.old_path: Optional[Path] = None  # 用于移动事件
    
    def __str__(self):
        return f"FileChangeEvent({self.change_type.value}: {self.path})"


class FileWatcherWorker(QThread, LoggerMixin):
    """文件监控工作线程。"""
    
    # 信号
    file_changed = Signal(object)  # FileChangeEvent
    
    def __init__(self, watch_paths: List[Path], poll_interval: float = 1.0):
        super().__init__()
        self.watch_paths = watch_paths
        self.poll_interval = poll_interval
        self.should_stop = False
        self.file_states: Dict[Path, Dict] = {}
        self.supported_extensions = {'.md', '.txt', '.json', '.html', '.py', '.js', '.css'}
        
        # 初始化文件状态
        self._initialize_file_states()
    
    def stop(self):
        """停止监控。"""
        self.should_stop = True
    
    def run(self):
        """运行监控循环。"""
        self.logger.info(f"开始监控 {len(self.watch_paths)} 个路径")
        
        while not self.should_stop:
            try:
                self._check_for_changes()
                self.msleep(int(self.poll_interval * 1000))
            except Exception as e:
                self.logger.error(f"文件监控错误: {e}")
                self.msleep(5000)  # 错误时等待5秒
    
    def _initialize_file_states(self):
        """初始化文件状态。"""
        for watch_path in self.watch_paths:
            if watch_path.exists():
                self._scan_directory(watch_path)
    
    def _scan_directory(self, directory: Path):
        """扫描目录并记录文件状态。"""
        try:
            if directory.is_file():
                self._record_file_state(directory)
                return
            
            for item in directory.rglob("*"):
                if item.is_file() and self._should_monitor_file(item):
                    self._record_file_state(item)
                    
        except Exception as e:
            self.logger.error(f"扫描目录失败 {directory}: {e}")
    
    def _should_monitor_file(self, file_path: Path) -> bool:
        """判断是否应该监控此文件。"""
        # 检查文件扩展名
        if file_path.suffix.lower() not in self.supported_extensions:
            return False
        
        # 忽略隐藏文件和临时文件
        if file_path.name.startswith('.') or file_path.name.startswith('~'):
            return False
        
        # 忽略特定目录
        ignore_dirs = {'.git', '__pycache__', 'node_modules', '.vscode'}
        if any(part in ignore_dirs for part in file_path.parts):
            return False
        
        return True
    
    def _record_file_state(self, file_path: Path):
        """记录文件状态。"""
        try:
            stat = file_path.stat()
            self.file_states[file_path] = {
                'size': stat.st_size,
                'mtime': stat.st_mtime,
                'exists': True
            }
        except Exception as e:
            self.logger.error(f"记录文件状态失败 {file_path}: {e}")
    
    def _check_for_changes(self):
        """检查文件变化。"""
        current_files = set()
        
        # 扫描当前文件
        for watch_path in self.watch_paths:
            if not watch_path.exists():
                continue
                
            try:
                if watch_path.is_file():
                    if self._should_monitor_file(watch_path):
                        current_files.add(watch_path)
                        self._check_file_changes(watch_path)
                else:
                    for item in watch_path.rglob("*"):
                        if item.is_file() and self._should_monitor_file(item):
                            current_files.add(item)
                            self._check_file_changes(item)
            except Exception as e:
                self.logger.error(f"检查路径变化失败 {watch_path}: {e}")
        
        # 检查删除的文件
        deleted_files = set(self.file_states.keys()) - current_files
        for deleted_file in deleted_files:
            self._emit_change_event(deleted_file, FileChangeType.DELETED)
            del self.file_states[deleted_file]
    
    def _check_file_changes(self, file_path: Path):
        """检查单个文件的变化。"""
        try:
            stat = file_path.stat()
            current_state = {
                'size': stat.st_size,
                'mtime': stat.st_mtime,
                'exists': True
            }
            
            if file_path not in self.file_states:
                # 新文件
                self.file_states[file_path] = current_state
                self._emit_change_event(file_path, FileChangeType.CREATED)
            else:
                # 检查修改
                old_state = self.file_states[file_path]
                if (current_state['size'] != old_state['size'] or 
                    current_state['mtime'] != old_state['mtime']):
                    self.file_states[file_path] = current_state
                    self._emit_change_event(file_path, FileChangeType.MODIFIED)
                    
        except Exception as e:
            self.logger.error(f"检查文件变化失败 {file_path}: {e}")
    
    def _emit_change_event(self, file_path: Path, change_type: FileChangeType):
        """发送文件变化事件。"""
        event = FileChangeEvent(file_path, change_type)
        self.file_changed.emit(event)
        self.logger.debug(f"文件变化: {event}")


class FileWatcher(QObject, LoggerMixin):
    """文件监控服务。"""
    
    # 信号
    file_changed = Signal(object)  # FileChangeEvent
    
    def __init__(self):
        super().__init__()
        self.watch_paths: List[Path] = []
        self.worker: Optional[FileWatcherWorker] = None
        self.is_watching = False
        self.poll_interval = 1.0  # 轮询间隔（秒）
    
    def add_watch_path(self, path: str) -> bool:
        """添加监控路径。"""
        try:
            watch_path = Path(path)
            if not watch_path.exists():
                self.logger.error(f"路径不存在: {path}")
                return False
            
            if watch_path not in self.watch_paths:
                self.watch_paths.append(watch_path)
                self.logger.info(f"添加监控路径: {path}")
                
                # 如果正在监控，重启监控
                if self.is_watching:
                    self.restart_watching()
            
            return True
        except Exception as e:
            self.logger.error(f"添加监控路径失败: {e}")
            return False
    
    def remove_watch_path(self, path: str) -> bool:
        """移除监控路径。"""
        try:
            watch_path = Path(path)
            if watch_path in self.watch_paths:
                self.watch_paths.remove(watch_path)
                self.logger.info(f"移除监控路径: {path}")
                
                # 如果正在监控，重启监控
                if self.is_watching:
                    self.restart_watching()
            
            return True
        except Exception as e:
            self.logger.error(f"移除监控路径失败: {e}")
            return False
    
    def start_watching(self) -> bool:
        """开始监控。"""
        if self.is_watching:
            self.logger.warning("文件监控已在运行")
            return True
        
        if not self.watch_paths:
            self.logger.error("没有配置监控路径")
            return False
        
        try:
            self.worker = FileWatcherWorker(self.watch_paths, self.poll_interval)
            self.worker.file_changed.connect(self._on_file_changed)
            self.worker.start()
            
            self.is_watching = True
            self.logger.info("文件监控已启动")
            return True
            
        except Exception as e:
            self.logger.error(f"启动文件监控失败: {e}")
            return False
    
    def stop_watching(self):
        """停止监控。"""
        if not self.is_watching:
            return
        
        if self.worker:
            self.worker.stop()
            self.worker.wait(5000)  # 等待最多5秒
            self.worker = None
        
        self.is_watching = False
        self.logger.info("文件监控已停止")
    
    def restart_watching(self):
        """重启监控。"""
        self.stop_watching()
        time.sleep(0.1)  # 短暂等待
        self.start_watching()
    
    def set_poll_interval(self, interval: float):
        """设置轮询间隔。"""
        self.poll_interval = max(0.1, interval)  # 最小0.1秒
        
        if self.is_watching:
            self.restart_watching()
    
    def get_watch_paths(self) -> List[str]:
        """获取监控路径列表。"""
        return [str(path) for path in self.watch_paths]
    
    def _on_file_changed(self, event: FileChangeEvent):
        """处理文件变化事件。"""
        self.file_changed.emit(event)
        self.logger.info(f"检测到文件变化: {event}")
    
    def clear_watch_paths(self):
        """清除所有监控路径。"""
        self.stop_watching()
        self.watch_paths.clear()
        self.logger.info("已清除所有监控路径")
