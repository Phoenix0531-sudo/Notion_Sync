"""
Database models and operations for Notion Sync.
"""

import os
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import create_engine, Column, String, DateTime, Integer, Text, Boolean, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from PySide6.QtCore import QDir

from notion_sync import APP_IDENTIFIER
from notion_sync.utils.logging_config import LoggerMixin

Base = declarative_base()


class SyncRecord(Base):
    """Database model for sync metadata."""
    __tablename__ = 'sync_records'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    local_path = Column(String(500), nullable=False, unique=True)
    notion_id = Column(String(100), nullable=False)
    notion_type = Column(String(50), nullable=False)  # 'page' or 'database'
    sync_direction = Column(String(50), nullable=False)  # 'local_to_notion', 'notion_to_local', 'bidirectional'
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    last_sync_time = Column(DateTime, nullable=True)
    local_modified_time = Column(DateTime, nullable=True)
    notion_modified_time = Column(DateTime, nullable=True)
    
    # Content tracking
    local_checksum = Column(String(32), nullable=True)  # MD5 hash
    notion_checksum = Column(String(32), nullable=True)
    
    # Conflict management
    conflict_status = Column(String(20), default='none')  # 'none', 'detected', 'resolved'
    conflict_data = Column(JSON, nullable=True)
    
    # Sync status
    sync_status = Column(String(20), default='pending')  # 'pending', 'syncing', 'completed', 'failed'
    last_error = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    
    def __repr__(self):
        return f"<SyncRecord(local_path='{self.local_path}', notion_id='{self.notion_id}')>"


class SyncHistory(Base):
    """Database model for sync operation history."""
    __tablename__ = 'sync_history'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    sync_record_id = Column(Integer, nullable=False)
    operation_type = Column(String(50), nullable=False)  # 'upload', 'download', 'update', 'delete'
    direction = Column(String(50), nullable=False)
    
    # Operation details
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    success = Column(Boolean, default=False)
    error_message = Column(Text, nullable=True)
    
    # Change tracking
    changes_summary = Column(JSON, nullable=True)
    file_size = Column(Integer, nullable=True)
    
    def __repr__(self):
        return f"<SyncHistory(operation='{self.operation_type}', success={self.success})>"


class AppSettings(Base):
    """Database model for application settings."""
    __tablename__ = 'app_settings'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(100), nullable=False, unique=True)
    value = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<AppSettings(key='{self.key}')>"


class ConflictResolution(Base):
    """Database model for conflict resolution rules."""
    __tablename__ = 'conflict_resolutions'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    pattern = Column(String(200), nullable=False)  # File pattern or path
    resolution_strategy = Column(String(50), nullable=False)  # 'local_wins', 'notion_wins', 'manual', 'merge'
    auto_apply = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<ConflictResolution(pattern='{self.pattern}', strategy='{self.resolution_strategy}')>"


class DatabaseManager(LoggerMixin):
    """Manages database operations for the application."""
    
    def __init__(self):
        """Initialize the database manager."""
        self.db_path = self._get_database_path()
        self.engine = create_engine(f'sqlite:///{self.db_path}', echo=False)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
        # Create tables
        self._create_tables()
        
        # Initialize default settings
        self._initialize_default_settings()
    
    def _get_database_path(self) -> Path:
        """Get the database file path."""
        config_dir = Path(QDir.homePath()) / f".{APP_IDENTIFIER}"
        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir / "notion_sync.db"
    
    def _create_tables(self) -> None:
        """Create database tables."""
        try:
            Base.metadata.create_all(bind=self.engine)
            self.logger.info("Database tables created successfully")
        except Exception as e:
            self.logger.error(f"Failed to create database tables: {e}")
            raise
    
    def _initialize_default_settings(self) -> None:
        """Initialize default application settings."""
        default_settings = {
            'sync_interval': 300,
            'auto_sync': False,
            'max_file_size': 50 * 1024 * 1024,
            'export_format': 'markdown',
            'dark_mode': 'system',
            'backup_location': str(Path.home() / "Documents" / "Notion Backups"),
            'watched_directories': [],
            'conflict_resolution': 'manual'
        }
        
        with self.get_session() as session:
            for key, value in default_settings.items():
                existing = session.query(AppSettings).filter_by(key=key).first()
                if not existing:
                    setting = AppSettings(key=key, value=value)
                    session.add(setting)
            session.commit()
    
    def get_session(self) -> Session:
        """Get a database session."""
        return self.SessionLocal()
    
    # Sync Records Operations
    def create_sync_record(self, local_path: str, notion_id: str, notion_type: str,
                          sync_direction: str = 'bidirectional') -> Optional[SyncRecord]:
        """Create a new sync record."""
        try:
            with self.get_session() as session:
                record = SyncRecord(
                    local_path=local_path,
                    notion_id=notion_id,
                    notion_type=notion_type,
                    sync_direction=sync_direction
                )
                session.add(record)
                session.commit()
                session.refresh(record)
                return record
        except Exception as e:
            self.logger.error(f"Failed to create sync record: {e}")
            return None
    
    def get_sync_record(self, local_path: str) -> Optional[SyncRecord]:
        """Get sync record by local path."""
        try:
            with self.get_session() as session:
                return session.query(SyncRecord).filter_by(local_path=local_path).first()
        except Exception as e:
            self.logger.error(f"Failed to get sync record: {e}")
            return None
    
    def get_sync_record_by_notion_id(self, notion_id: str) -> Optional[SyncRecord]:
        """Get sync record by Notion ID."""
        try:
            with self.get_session() as session:
                return session.query(SyncRecord).filter_by(notion_id=notion_id).first()
        except Exception as e:
            self.logger.error(f"Failed to get sync record by notion ID: {e}")
            return None
    
    def get_all_sync_records(self) -> List[SyncRecord]:
        """Get all sync records."""
        try:
            with self.get_session() as session:
                return session.query(SyncRecord).all()
        except Exception as e:
            self.logger.error(f"Failed to get all sync records: {e}")
            return []
    
    def update_sync_record(self, record_id: int, **kwargs) -> bool:
        """Update a sync record."""
        try:
            with self.get_session() as session:
                record = session.query(SyncRecord).filter_by(id=record_id).first()
                if record:
                    for key, value in kwargs.items():
                        if hasattr(record, key):
                            setattr(record, key, value)
                    session.commit()
                    return True
                return False
        except Exception as e:
            self.logger.error(f"Failed to update sync record: {e}")
            return False
    
    def delete_sync_record(self, local_path: str) -> bool:
        """Delete a sync record."""
        try:
            with self.get_session() as session:
                record = session.query(SyncRecord).filter_by(local_path=local_path).first()
                if record:
                    session.delete(record)
                    session.commit()
                    return True
                return False
        except Exception as e:
            self.logger.error(f"Failed to delete sync record: {e}")
            return False
    
    # Sync History Operations
    def add_sync_history(self, sync_record_id: int, operation_type: str, 
                        direction: str, **kwargs) -> Optional[SyncHistory]:
        """Add a sync history entry."""
        try:
            with self.get_session() as session:
                history = SyncHistory(
                    sync_record_id=sync_record_id,
                    operation_type=operation_type,
                    direction=direction,
                    **kwargs
                )
                session.add(history)
                session.commit()
                session.refresh(history)
                return history
        except Exception as e:
            self.logger.error(f"Failed to add sync history: {e}")
            return None
    
    def get_sync_history(self, sync_record_id: int, limit: int = 50) -> List[SyncHistory]:
        """Get sync history for a record."""
        try:
            with self.get_session() as session:
                return (session.query(SyncHistory)
                       .filter_by(sync_record_id=sync_record_id)
                       .order_by(SyncHistory.started_at.desc())
                       .limit(limit)
                       .all())
        except Exception as e:
            self.logger.error(f"Failed to get sync history: {e}")
            return []
    
    # Settings Operations
    def get_setting(self, key: str, default: Any = None) -> Any:
        """Get an application setting."""
        try:
            with self.get_session() as session:
                setting = session.query(AppSettings).filter_by(key=key).first()
                return setting.value if setting else default
        except Exception as e:
            self.logger.error(f"Failed to get setting {key}: {e}")
            return default
    
    def set_setting(self, key: str, value: Any) -> bool:
        """Set an application setting."""
        try:
            with self.get_session() as session:
                setting = session.query(AppSettings).filter_by(key=key).first()
                if setting:
                    setting.value = value
                    setting.updated_at = datetime.utcnow()
                else:
                    setting = AppSettings(key=key, value=value)
                    session.add(setting)
                session.commit()
                return True
        except Exception as e:
            self.logger.error(f"Failed to set setting {key}: {e}")
            return False
    
    def get_all_settings(self) -> Dict[str, Any]:
        """Get all application settings."""
        try:
            with self.get_session() as session:
                settings = session.query(AppSettings).all()
                return {setting.key: setting.value for setting in settings}
        except Exception as e:
            self.logger.error(f"Failed to get all settings: {e}")
            return {}
    
    # Conflict Resolution Operations
    def add_conflict_resolution(self, pattern: str, strategy: str, auto_apply: bool = False) -> bool:
        """Add a conflict resolution rule."""
        try:
            with self.get_session() as session:
                rule = ConflictResolution(
                    pattern=pattern,
                    resolution_strategy=strategy,
                    auto_apply=auto_apply
                )
                session.add(rule)
                session.commit()
                return True
        except Exception as e:
            self.logger.error(f"Failed to add conflict resolution rule: {e}")
            return False
    
    def get_conflict_resolutions(self) -> List[ConflictResolution]:
        """Get all conflict resolution rules."""
        try:
            with self.get_session() as session:
                return session.query(ConflictResolution).all()
        except Exception as e:
            self.logger.error(f"Failed to get conflict resolution rules: {e}")
            return []
