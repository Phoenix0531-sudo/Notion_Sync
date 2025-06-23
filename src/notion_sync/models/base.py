"""
Notion 同步应用程序的基础模型类。
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, TypeVar, Generic
from PySide6.QtCore import QObject, Signal
from notion_sync.utils.logging_config import LoggerMixin

T = TypeVar('T')


class BaseModel(QObject, LoggerMixin):
    """具有通用功能的基础模型类。"""

    # 模型变更信号
    data_changed = Signal()
    error_occurred = Signal(str)
    operation_started = Signal(str)
    operation_finished = Signal(str)
    progress_updated = Signal(int, str)  # 进度百分比，状态消息

    def __init__(self, parent: Optional[QObject] = None):
        """初始化基础模型。"""
        super().__init__(parent)
        self._is_loading = False
        self._last_error: Optional[str] = None

    @property
    def is_loading(self) -> bool:
        """检查模型是否正在加载数据。"""
        return self._is_loading

    @property
    def last_error(self) -> Optional[str]:
        """获取最后的错误消息。"""
        return self._last_error

    def _set_loading(self, loading: bool) -> None:
        """设置加载状态。"""
        self._is_loading = loading
        if loading:
            self._last_error = None

    def _set_error(self, error: str) -> None:
        """设置错误消息。"""
        self._last_error = error
        self._is_loading = False
        self.error_occurred.emit(error)
        self.logger.error(error)

    def _emit_progress(self, percentage: int, message: str = "") -> None:
        """发出进度更新信号。"""
        self.progress_updated.emit(percentage, message)


class Repository(Generic[T], ABC):
    """数据访问的抽象仓储模式。"""

    @abstractmethod
    async def get_by_id(self, id: str) -> Optional[T]:
        """根据 ID 获取项目。"""
        pass

    @abstractmethod
    async def get_all(self) -> List[T]:
        """获取所有项目。"""
        pass

    @abstractmethod
    async def create(self, item: T) -> T:
        """创建新项目。"""
        pass

    @abstractmethod
    async def update(self, item: T) -> T:
        """更新现有项目。"""
        pass

    @abstractmethod
    async def delete(self, id: str) -> bool:
        """根据 ID 删除项目。"""
        pass


class CacheableModel(BaseModel):
    """具有缓存功能的基础模型。"""

    def __init__(self, parent: Optional[QObject] = None):
        """初始化可缓存模型。"""
        super().__init__(parent)
        self._cache: Dict[str, Any] = {}
        self._cache_ttl: Dict[str, float] = {}
        self._default_ttl = 300  # 5分钟

    def _get_from_cache(self, key: str) -> Optional[Any]:
        """如果未过期，从缓存获取值。"""
        import time

        if key not in self._cache:
            return None

        if key in self._cache_ttl:
            if time.time() > self._cache_ttl[key]:
                # 缓存已过期
                del self._cache[key]
                del self._cache_ttl[key]
                return None

        return self._cache[key]

    def _set_cache(self, key: str, value: Any, ttl: Optional[float] = None) -> None:
        """在缓存中设置带 TTL 的值。"""
        import time

        self._cache[key] = value
        if ttl is None:
            ttl = self._default_ttl
        self._cache_ttl[key] = time.time() + ttl

    def _clear_cache(self, pattern: Optional[str] = None) -> None:
        """清除匹配模式的缓存条目，如果模式为 None 则清除所有。"""
        if pattern is None:
            self._cache.clear()
            self._cache_ttl.clear()
        else:
            keys_to_remove = [key for key in self._cache.keys() if pattern in key]
            for key in keys_to_remove:
                del self._cache[key]
                if key in self._cache_ttl:
                    del self._cache_ttl[key]


class SyncableModel(BaseModel):
    """可同步项目的基础模型。"""

    # 同步相关信号
    sync_started = Signal()
    sync_finished = Signal(bool)  # 成功状态
    sync_progress = Signal(int, str)  # 百分比，消息
    conflict_detected = Signal(dict)  # 冲突数据

    def __init__(self, parent: Optional[QObject] = None):
        """初始化可同步模型。"""
        super().__init__(parent)
        self._sync_in_progress = False
        self._last_sync_time: Optional[float] = None

    @property
    def sync_in_progress(self) -> bool:
        """检查同步是否正在进行。"""
        return self._sync_in_progress

    @property
    def last_sync_time(self) -> Optional[float]:
        """获取最后同步的时间戳。"""
        return self._last_sync_time

    def _set_sync_state(self, syncing: bool) -> None:
        """设置同步状态。"""
        self._sync_in_progress = syncing
        if syncing:
            self.sync_started.emit()
        else:
            import time
            self._last_sync_time = time.time()

    @abstractmethod
    async def sync(self) -> bool:
        """执行同步。成功时返回 True。"""
        pass
