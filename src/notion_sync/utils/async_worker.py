"""
异步工作器 - 处理耗时操作避免界面卡顿
"""

import asyncio
import threading
from typing import Any, Callable, Optional, Dict
from PySide6.QtCore import QObject, Signal, QThread, QTimer
from PySide6.QtWidgets import QApplication


class AsyncWorker(QObject):
    """异步工作器 - 在后台线程执行耗时操作"""
    
    # 信号
    started = Signal()
    finished = Signal(object)  # 完成信号，携带结果
    error = Signal(str)  # 错误信号
    progress = Signal(int, str)  # 进度信号 (百分比, 消息)
    
    def __init__(self, func: Callable, *args, **kwargs):
        super().__init__()
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self.is_cancelled = False
        
    def run(self):
        """执行工作"""
        try:
            self.started.emit()
            result = self.func(*self.args, **self.kwargs)
            if not self.is_cancelled:
                self.finished.emit(result)
        except Exception as e:
            if not self.is_cancelled:
                self.error.emit(str(e))
    
    def cancel(self):
        """取消工作"""
        self.is_cancelled = True


class AsyncTaskManager(QObject):
    """异步任务管理器"""
    
    def __init__(self):
        super().__init__()
        self.workers = {}
        self.threads = {}
    
    def run_async(self, task_id: str, func: Callable, *args, **kwargs) -> AsyncWorker:
        """异步运行任务"""
        # 如果任务已存在，先取消
        if task_id in self.workers:
            self.cancel_task(task_id)
        
        # 创建工作器和线程
        worker = AsyncWorker(func, *args, **kwargs)
        thread = QThread()
        
        # 移动工作器到线程
        worker.moveToThread(thread)
        
        # 连接信号
        thread.started.connect(worker.run)
        worker.finished.connect(thread.quit)
        worker.error.connect(thread.quit)
        thread.finished.connect(lambda: self._cleanup_task(task_id))
        
        # 保存引用
        self.workers[task_id] = worker
        self.threads[task_id] = thread
        
        # 启动线程
        thread.start()
        
        return worker
    
    def cancel_task(self, task_id: str):
        """取消任务"""
        if task_id in self.workers:
            self.workers[task_id].cancel()
            if task_id in self.threads:
                self.threads[task_id].quit()
                self.threads[task_id].wait()
    
    def _cleanup_task(self, task_id: str):
        """清理任务"""
        if task_id in self.workers:
            del self.workers[task_id]
        if task_id in self.threads:
            del self.threads[task_id]
    
    def cancel_all(self):
        """取消所有任务"""
        for task_id in list(self.workers.keys()):
            self.cancel_task(task_id)


class LoadingIndicator(QObject):
    """加载指示器"""
    
    def __init__(self, parent_widget):
        super().__init__()
        self.parent_widget = parent_widget
        self.is_loading = False
        self.timer = QTimer()
        self.timer.timeout.connect(self._update_cursor)
        self.dots = 0
        
    def start_loading(self, message: str = "加载中"):
        """开始加载动画"""
        if self.is_loading:
            return
            
        self.is_loading = True
        self.message = message
        self.dots = 0
        
        # 设置等待光标
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        
        # 启动动画定时器
        self.timer.start(500)  # 每500ms更新一次
        
        # 更新状态
        self._update_status()
    
    def stop_loading(self):
        """停止加载动画"""
        if not self.is_loading:
            return
            
        self.is_loading = False
        self.timer.stop()
        
        # 恢复光标
        QApplication.restoreOverrideCursor()
    
    def _update_cursor(self):
        """更新光标动画"""
        self.dots = (self.dots + 1) % 4
        self._update_status()
    
    def _update_status(self):
        """更新状态显示"""
        if hasattr(self.parent_widget, 'set_status'):
            dots_str = "." * self.dots
            self.parent_widget.set_status(f"{self.message}{dots_str}")


class ProgressiveLoader:
    """渐进式加载器 - 分批加载大量数据"""
    
    def __init__(self, data_source: Callable, batch_size: int = 50):
        self.data_source = data_source
        self.batch_size = batch_size
        self.current_batch = 0
        self.total_items = 0
        self.loaded_items = []
        
    def load_next_batch(self) -> tuple[list, bool]:
        """加载下一批数据"""
        start_index = self.current_batch * self.batch_size
        end_index = start_index + self.batch_size
        
        try:
            # 获取数据
            batch_data = self.data_source(start_index, end_index)
            
            if not batch_data:
                return [], True  # 没有更多数据
            
            self.loaded_items.extend(batch_data)
            self.current_batch += 1
            
            # 检查是否还有更多数据
            has_more = len(batch_data) == self.batch_size
            
            return batch_data, not has_more
            
        except Exception as e:
            raise Exception(f"加载数据失败: {str(e)}")
    
    def reset(self):
        """重置加载器"""
        self.current_batch = 0
        self.loaded_items = []


class CacheManager:
    """缓存管理器"""
    
    def __init__(self, max_size: int = 1000):
        self.cache = {}
        self.access_order = []
        self.max_size = max_size
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        if key in self.cache:
            # 更新访问顺序
            self.access_order.remove(key)
            self.access_order.append(key)
            return self.cache[key]
        return None
    
    def set(self, key: str, value: Any):
        """设置缓存"""
        if key in self.cache:
            # 更新现有缓存
            self.access_order.remove(key)
        elif len(self.cache) >= self.max_size:
            # 移除最久未使用的缓存
            oldest_key = self.access_order.pop(0)
            del self.cache[oldest_key]
        
        self.cache[key] = value
        self.access_order.append(key)
    
    def clear(self):
        """清除所有缓存"""
        self.cache.clear()
        self.access_order.clear()
    
    def remove(self, key: str):
        """移除特定缓存"""
        if key in self.cache:
            del self.cache[key]
            self.access_order.remove(key)


class SmartFileLoader:
    """智能文件加载器 - 优化大文件列表加载"""
    
    def __init__(self, cache_manager: CacheManager):
        self.cache = cache_manager
        self.loading_tasks = {}
    
    def load_directory_async(self, path: str, callback: Callable):
        """异步加载目录"""
        # 检查缓存
        cached_result = self.cache.get(f"dir:{path}")
        if cached_result:
            callback(cached_result)
            return
        
        # 异步加载
        def load_directory():
            import os
            try:
                files = []
                for root, dirs, filenames in os.walk(path):
                    for filename in filenames:
                        file_path = os.path.join(root, filename)
                        file_info = {
                            'name': filename,
                            'path': file_path,
                            'size': os.path.getsize(file_path),
                            'modified': os.path.getmtime(file_path)
                        }
                        files.append(file_info)
                
                # 缓存结果
                self.cache.set(f"dir:{path}", files)
                return files
                
            except Exception as e:
                raise Exception(f"加载目录失败: {str(e)}")
        
        # 使用异步任务管理器
        task_manager = AsyncTaskManager()
        worker = task_manager.run_async(f"load_dir_{path}", load_directory)
        
        worker.finished.connect(callback)
        worker.error.connect(lambda error: callback([]))
        
        return worker


# 全局实例
task_manager = AsyncTaskManager()
cache_manager = CacheManager()
file_loader = SmartFileLoader(cache_manager)


def run_async_task(task_id: str, func: Callable, *args, **kwargs) -> AsyncWorker:
    """运行异步任务的便捷函数"""
    return task_manager.run_async(task_id, func, *args, **kwargs)


def cancel_task(task_id: str):
    """取消任务的便捷函数"""
    task_manager.cancel_task(task_id)


def get_cache(key: str) -> Optional[Any]:
    """获取缓存的便捷函数"""
    return cache_manager.get(key)


def set_cache(key: str, value: Any):
    """设置缓存的便捷函数"""
    cache_manager.set(key, value)
