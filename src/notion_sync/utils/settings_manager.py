"""
设置管理工具，用于导入导出和验证设置。
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Tuple, Optional, List
from datetime import datetime

from notion_sync.utils.config import ConfigManager
from notion_sync.utils.logging_config import LoggerMixin
from notion_sync import DEFAULT_CONFIG


class SettingsManager(LoggerMixin):
    """设置管理器，处理设置的导入导出和验证。"""
    
    def __init__(self, config_manager: ConfigManager):
        """初始化设置管理器。"""
        self.config_manager = config_manager
    
    def export_settings(self, file_path: str, include_sensitive: bool = False) -> bool:
        """导出设置到文件。"""
        try:
            settings = self.config_manager.get_all()
            
            # 如果不包含敏感信息，则移除敏感字段
            if not include_sensitive:
                settings = self._remove_sensitive_data(settings)
            
            # 添加导出元数据
            export_data = {
                "metadata": {
                    "export_time": datetime.now().isoformat(),
                    "app_version": "1.0.0",
                    "include_sensitive": include_sensitive
                },
                "settings": settings
            }
            
            # 写入文件
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"设置已导出到: {file_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"导出设置失败: {e}")
            return False
    
    def import_settings(self, file_path: str, merge: bool = True) -> Tuple[bool, str]:
        """从文件导入设置。"""
        try:
            if not os.path.exists(file_path):
                return False, "文件不存在"
            
            # 读取文件
            with open(file_path, 'r', encoding='utf-8') as f:
                import_data = json.load(f)
            
            # 验证文件格式
            if not self._validate_import_data(import_data):
                return False, "无效的设置文件格式"
            
            settings = import_data.get("settings", {})
            
            # 验证设置
            is_valid, error_msg = self._validate_settings(settings)
            if not is_valid:
                return False, f"设置验证失败: {error_msg}"
            
            # 应用设置
            if merge:
                # 合并模式：只更新存在的设置
                for key, value in settings.items():
                    if key in DEFAULT_CONFIG:
                        self.config_manager.set(key, value)
            else:
                # 替换模式：重置为默认值后应用所有设置
                self.config_manager.reset_to_defaults()
                self.config_manager.update(settings)
            
            self.logger.info(f"设置已从 {file_path} 导入")
            return True, "设置导入成功"
            
        except json.JSONDecodeError:
            return False, "文件格式错误，不是有效的 JSON 文件"
        except Exception as e:
            self.logger.error(f"导入设置失败: {e}")
            return False, f"导入失败: {str(e)}"
    
    def _remove_sensitive_data(self, settings: Dict[str, Any]) -> Dict[str, Any]:
        """移除敏感数据。"""
        sensitive_keys = [
            "notion_client_id",
            "notion_client_secret",
            "auth_tokens",
            "api_keys"
        ]
        
        filtered_settings = {}
        for key, value in settings.items():
            if key not in sensitive_keys:
                filtered_settings[key] = value
        
        return filtered_settings
    
    def _validate_import_data(self, data: Dict[str, Any]) -> bool:
        """验证导入数据的格式。"""
        if not isinstance(data, dict):
            return False
        
        if "settings" not in data:
            return False
        
        if not isinstance(data["settings"], dict):
            return False
        
        return True
    
    def _validate_settings(self, settings: Dict[str, Any]) -> Tuple[bool, str]:
        """验证设置的有效性。"""
        try:
            # 检查数据类型
            for key, value in settings.items():
                if key in DEFAULT_CONFIG:
                    expected_type = type(DEFAULT_CONFIG[key])
                    if not isinstance(value, expected_type):
                        return False, f"设置 '{key}' 的类型不正确，期望 {expected_type.__name__}"
            
            # 检查特定设置的值范围
            if "sync_interval" in settings:
                if settings["sync_interval"] < 60:
                    return False, "同步间隔不能少于60秒"
            
            if "max_file_size" in settings:
                if settings["max_file_size"] < 1024 * 1024:  # 1MB
                    return False, "最大文件大小不能少于1MB"
                if settings["max_file_size"] > 1024 * 1024 * 1024:  # 1GB
                    return False, "最大文件大小不能超过1GB"
            
            if "max_concurrent_uploads" in settings:
                if settings["max_concurrent_uploads"] < 1 or settings["max_concurrent_uploads"] > 10:
                    return False, "并发上传数必须在1-10之间"
            
            if "retry_attempts" in settings:
                if settings["retry_attempts"] < 1 or settings["retry_attempts"] > 10:
                    return False, "重试次数必须在1-10之间"
            
            # 检查路径设置
            if "backup_location" in settings:
                backup_path = settings["backup_location"]
                if backup_path:
                    try:
                        path = Path(backup_path)
                        if not path.parent.exists():
                            return False, f"备份位置的父目录不存在: {backup_path}"
                    except Exception:
                        return False, f"备份位置路径无效: {backup_path}"
            
            return True, ""
            
        except Exception as e:
            return False, f"验证过程中出错: {str(e)}"
    
    def create_backup(self) -> Optional[str]:
        """创建当前设置的备份。"""
        try:
            from notion_sync import APP_IDENTIFIER
            from PySide6.QtCore import QDir
            
            # 创建备份目录
            backup_dir = Path(QDir.homePath()) / f".{APP_IDENTIFIER}" / "backups"
            backup_dir.mkdir(parents=True, exist_ok=True)
            
            # 生成备份文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = backup_dir / f"settings_backup_{timestamp}.json"
            
            # 导出设置
            if self.export_settings(str(backup_file), include_sensitive=False):
                self.logger.info(f"设置备份已创建: {backup_file}")
                return str(backup_file)
            else:
                return None
                
        except Exception as e:
            self.logger.error(f"创建备份失败: {e}")
            return None
    
    def restore_from_backup(self, backup_file: str) -> Tuple[bool, str]:
        """从备份文件恢复设置。"""
        return self.import_settings(backup_file, merge=False)
    
    def get_backup_list(self) -> List[Dict[str, Any]]:
        """获取可用备份列表。"""
        try:
            from notion_sync import APP_IDENTIFIER
            from PySide6.QtCore import QDir
            
            backup_dir = Path(QDir.homePath()) / f".{APP_IDENTIFIER}" / "backups"
            
            if not backup_dir.exists():
                return []
            
            backups = []
            for backup_file in backup_dir.glob("settings_backup_*.json"):
                try:
                    stat = backup_file.stat()
                    backups.append({
                        "file": str(backup_file),
                        "name": backup_file.name,
                        "created_time": datetime.fromtimestamp(stat.st_ctime),
                        "size": stat.st_size
                    })
                except Exception:
                    continue
            
            # 按创建时间排序
            backups.sort(key=lambda x: x["created_time"], reverse=True)
            return backups
            
        except Exception as e:
            self.logger.error(f"获取备份列表失败: {e}")
            return []
    
    def cleanup_old_backups(self, keep_count: int = 10) -> None:
        """清理旧的备份文件。"""
        try:
            backups = self.get_backup_list()
            
            if len(backups) > keep_count:
                # 删除多余的备份
                for backup in backups[keep_count:]:
                    try:
                        os.remove(backup["file"])
                        self.logger.info(f"已删除旧备份: {backup['name']}")
                    except Exception as e:
                        self.logger.warning(f"删除备份失败 {backup['name']}: {e}")
                        
        except Exception as e:
            self.logger.error(f"清理备份失败: {e}")
    
    def get_settings_summary(self) -> Dict[str, Any]:
        """获取设置摘要信息。"""
        settings = self.config_manager.get_all()
        
        return {
            "total_settings": len(settings),
            "auto_sync_enabled": settings.get("auto_sync", False),
            "sync_interval_minutes": settings.get("sync_interval", 300) // 60,
            "max_file_size_mb": settings.get("max_file_size", 50 * 1024 * 1024) // (1024 * 1024),
            "backup_location": settings.get("backup_location", ""),
            "theme": settings.get("dark_mode", "system"),
            "log_level": settings.get("log_level", "INFO")
        }
    
    def validate_current_settings(self) -> Tuple[bool, List[str]]:
        """验证当前设置并返回问题列表。"""
        settings = self.config_manager.get_all()
        issues = []
        
        # 检查备份位置
        backup_location = settings.get("backup_location", "")
        if backup_location:
            try:
                path = Path(backup_location)
                if not path.parent.exists():
                    issues.append(f"备份位置的父目录不存在: {backup_location}")
            except Exception:
                issues.append(f"备份位置路径无效: {backup_location}")
        
        # 检查同步间隔
        sync_interval = settings.get("sync_interval", 300)
        if sync_interval < 60:
            issues.append("同步间隔过短，建议至少60秒")
        
        # 检查文件大小限制
        max_file_size = settings.get("max_file_size", 50 * 1024 * 1024)
        if max_file_size > 100 * 1024 * 1024:  # 100MB
            issues.append("最大文件大小设置过大，可能影响性能")
        
        return len(issues) == 0, issues
