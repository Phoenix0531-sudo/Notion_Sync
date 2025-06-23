"""
智能缓存系统 - 提高应用性能
"""

import json
import time
import hashlib
import os
from typing import Any, Optional, Dict, List
from pathlib import Path
from PySide6.QtCore import QObject, Signal, QTimer


class CacheEntry:
    """缓存条目"""
    
    def __init__(self, key: str, value: Any, ttl: int = 3600):
        self.key = key
        self.value = value
        self.created_at = time.time()
        self.ttl = ttl  # 生存时间（秒）
        self.access_count = 0
        self.last_accessed = time.time()
    
    def is_expired(self) -> bool:
        """检查是否过期"""
        return time.time() - self.created_at > self.ttl
    
    def access(self) -> Any:
        """访问缓存项"""
        self.access_count += 1
        self.last_accessed = time.time()
        return self.value
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'key': self.key,
            'value': self.value,
            'created_at': self.created_at,
            'ttl': self.ttl,
            'access_count': self.access_count,
            'last_accessed': self.last_accessed
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'CacheEntry':
        """从字典创建"""
        entry = cls(data['key'], data['value'], data['ttl'])
        entry.created_at = data['created_at']
        entry.access_count = data['access_count']
        entry.last_accessed = data['last_accessed']
        return entry


class SmartCache(QObject):
    """智能缓存管理器"""
    
    cache_hit = Signal(str)  # 缓存命中信号
    cache_miss = Signal(str)  # 缓存未命中信号
    cache_expired = Signal(str)  # 缓存过期信号
    
    def __init__(self, max_size: int = 1000, default_ttl: int = 3600):
        super().__init__()
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.cache: Dict[str, CacheEntry] = {}
        self.stats = {
            'hits': 0,
            'misses': 0,
            'expired': 0,
            'evictions': 0
        }
        
        # 定期清理过期缓存
        self.cleanup_timer = QTimer()
        self.cleanup_timer.timeout.connect(self._cleanup_expired)
        self.cleanup_timer.start(60000)  # 每分钟清理一次
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        if key not in self.cache:
            self.stats['misses'] += 1
            self.cache_miss.emit(key)
            return None
        
        entry = self.cache[key]
        
        if entry.is_expired():
            self.stats['expired'] += 1
            self.cache_expired.emit(key)
            del self.cache[key]
            return None
        
        self.stats['hits'] += 1
        self.cache_hit.emit(key)
        return entry.access()
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """设置缓存"""
        if ttl is None:
            ttl = self.default_ttl
        
        # 如果缓存已满，移除最少使用的项
        if len(self.cache) >= self.max_size and key not in self.cache:
            self._evict_lru()
        
        self.cache[key] = CacheEntry(key, value, ttl)
    
    def delete(self, key: str) -> bool:
        """删除缓存"""
        if key in self.cache:
            del self.cache[key]
            return True
        return False
    
    def clear(self) -> None:
        """清空缓存"""
        self.cache.clear()
        self.stats = {
            'hits': 0,
            'misses': 0,
            'expired': 0,
            'evictions': 0
        }
    
    def _evict_lru(self) -> None:
        """移除最少使用的缓存项"""
        if not self.cache:
            return
        
        # 找到最少使用的项
        lru_key = min(self.cache.keys(), 
                     key=lambda k: (self.cache[k].access_count, self.cache[k].last_accessed))
        
        del self.cache[lru_key]
        self.stats['evictions'] += 1
    
    def _cleanup_expired(self) -> None:
        """清理过期缓存"""
        expired_keys = [key for key, entry in self.cache.items() if entry.is_expired()]
        for key in expired_keys:
            del self.cache[key]
            self.stats['expired'] += 1
    
    def get_stats(self) -> dict:
        """获取缓存统计"""
        total_requests = self.stats['hits'] + self.stats['misses']
        hit_rate = self.stats['hits'] / total_requests if total_requests > 0 else 0
        
        return {
            **self.stats,
            'total_requests': total_requests,
            'hit_rate': hit_rate,
            'cache_size': len(self.cache),
            'max_size': self.max_size
        }


class PersistentCache(SmartCache):
    """持久化缓存"""
    
    def __init__(self, cache_dir: str, max_size: int = 1000, default_ttl: int = 3600):
        super().__init__(max_size, default_ttl)
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_file = self.cache_dir / "cache.json"
        
        # 加载持久化缓存
        self._load_cache()
        
        # 定期保存缓存
        self.save_timer = QTimer()
        self.save_timer.timeout.connect(self._save_cache)
        self.save_timer.start(300000)  # 每5分钟保存一次
    
    def _load_cache(self) -> None:
        """加载持久化缓存"""
        if not self.cache_file.exists():
            return

        try:
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if not content:
                    return
                data = json.loads(content)

            for entry_data in data.get('entries', []):
                try:
                    entry = CacheEntry.from_dict(entry_data)
                    if not entry.is_expired():
                        self.cache[entry.key] = entry
                except Exception as e:
                    print(f"跳过损坏的缓存条目: {e}")
                    continue

            # 加载统计信息
            if 'stats' in data:
                self.stats.update(data['stats'])

        except (json.JSONDecodeError, KeyError, IOError) as e:
            print(f"加载缓存失败: {e}")
            # 删除损坏的缓存文件
            try:
                self.cache_file.unlink()
                print("已删除损坏的缓存文件")
            except Exception:
                pass
    
    def _save_cache(self) -> None:
        """保存持久化缓存"""
        try:
            # 清理过期项
            self._cleanup_expired()

            # 只保存可序列化的缓存条目
            serializable_entries = []
            for entry in self.cache.values():
                try:
                    entry_dict = entry.to_dict()
                    # 验证可以序列化
                    json.dumps(entry_dict)
                    serializable_entries.append(entry_dict)
                except (TypeError, ValueError) as e:
                    print(f"跳过不可序列化的缓存条目 {entry.key}: {e}")
                    continue

            data = {
                'entries': serializable_entries,
                'stats': self.stats,
                'saved_at': time.time()
            }

            # 先写入临时文件，然后重命名（原子操作）
            temp_file = self.cache_file.with_suffix('.tmp')
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2, default=str)

            # 原子替换
            temp_file.replace(self.cache_file)

        except Exception as e:
            print(f"保存缓存失败: {e}")
            # 清理临时文件
            temp_file = self.cache_file.with_suffix('.tmp')
            if temp_file.exists():
                try:
                    temp_file.unlink()
                except Exception:
                    pass
    
    def close(self) -> None:
        """关闭缓存（保存数据）"""
        self._save_cache()
        self.save_timer.stop()
        self.cleanup_timer.stop()


class FileMetadataCache:
    """文件元数据缓存"""
    
    def __init__(self, cache: SmartCache):
        self.cache = cache
    
    def get_file_hash(self, file_path: str) -> Optional[str]:
        """获取文件哈希值"""
        cache_key = f"file_hash:{file_path}"
        
        # 检查文件修改时间
        try:
            stat = os.stat(file_path)
            mtime = stat.st_mtime
            size = stat.st_size
            
            # 检查缓存
            cached_data = self.cache.get(cache_key)
            if cached_data and cached_data['mtime'] == mtime and cached_data['size'] == size:
                return cached_data['hash']
            
            # 计算新的哈希值
            hash_value = self._calculate_file_hash(file_path)
            
            # 缓存结果
            self.cache.set(cache_key, {
                'hash': hash_value,
                'mtime': mtime,
                'size': size
            }, ttl=86400)  # 24小时
            
            return hash_value
            
        except (OSError, IOError):
            return None
    
    def _calculate_file_hash(self, file_path: str) -> str:
        """计算文件哈希值"""
        hash_md5 = hashlib.md5()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except (OSError, IOError):
            return ""


class NotionDataCache:
    """Notion 数据缓存"""
    
    def __init__(self, cache: SmartCache):
        self.cache = cache
    
    def get_workspace_data(self, workspace_id: str) -> Optional[dict]:
        """获取工作区数据"""
        return self.cache.get(f"notion_workspace:{workspace_id}")
    
    def set_workspace_data(self, workspace_id: str, data: dict) -> None:
        """设置工作区数据"""
        self.cache.set(f"notion_workspace:{workspace_id}", data, ttl=1800)  # 30分钟
    
    def get_page_data(self, page_id: str) -> Optional[dict]:
        """获取页面数据"""
        return self.cache.get(f"notion_page:{page_id}")
    
    def set_page_data(self, page_id: str, data: dict) -> None:
        """设置页面数据"""
        self.cache.set(f"notion_page:{page_id}", data, ttl=3600)  # 1小时
    
    def get_database_data(self, database_id: str) -> Optional[dict]:
        """获取数据库数据"""
        return self.cache.get(f"notion_database:{database_id}")
    
    def set_database_data(self, database_id: str, data: dict) -> None:
        """设置数据库数据"""
        self.cache.set(f"notion_database:{database_id}", data, ttl=1800)  # 30分钟
    
    def invalidate_workspace(self, workspace_id: str) -> None:
        """使工作区缓存失效"""
        self.cache.delete(f"notion_workspace:{workspace_id}")


# 全局缓存实例
_global_cache = None
_file_cache = None
_notion_cache = None


def get_global_cache() -> SmartCache:
    """获取全局缓存实例"""
    global _global_cache
    if _global_cache is None:
        cache_dir = os.path.expanduser("~/.notion_sync/cache")
        _global_cache = PersistentCache(cache_dir)
    return _global_cache


def get_file_cache() -> FileMetadataCache:
    """获取文件缓存实例"""
    global _file_cache
    if _file_cache is None:
        _file_cache = FileMetadataCache(get_global_cache())
    return _file_cache


def get_notion_cache() -> NotionDataCache:
    """获取 Notion 缓存实例"""
    global _notion_cache
    if _notion_cache is None:
        _notion_cache = NotionDataCache(get_global_cache())
    return _notion_cache


def clear_all_caches():
    """清空所有缓存"""
    get_global_cache().clear()


def get_cache_stats() -> dict:
    """获取缓存统计信息"""
    return get_global_cache().get_stats()
