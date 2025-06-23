"""
Local file system management for Notion Sync.
"""

import os
import hashlib
import mimetypes
from pathlib import Path
from typing import Dict, List, Optional, Set, Any, Generator
from datetime import datetime
import frontmatter
import markdown

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent, FileCreatedEvent, FileDeletedEvent

from notion_sync.models.base import BaseModel
from notion_sync import SUPPORTED_FORMATS


class FileWatcher(FileSystemEventHandler):
    """File system event handler for watching file changes."""
    
    def __init__(self, file_manager: 'FileManager'):
        """Initialize the file watcher."""
        super().__init__()
        self.file_manager = file_manager
        self.supported_extensions = set()
        for format_list in SUPPORTED_FORMATS.values():
            self.supported_extensions.update(format_list)
    
    def _is_supported_file(self, file_path: str) -> bool:
        """Check if file is supported for sync."""
        return Path(file_path).suffix.lower() in self.supported_extensions
    
    def on_modified(self, event):
        """Handle file modification events."""
        if not event.is_directory and self._is_supported_file(event.src_path):
            self.file_manager.file_changed.emit(event.src_path, "modified")
    
    def on_created(self, event):
        """Handle file creation events."""
        if not event.is_directory and self._is_supported_file(event.src_path):
            self.file_manager.file_changed.emit(event.src_path, "created")
    
    def on_deleted(self, event):
        """Handle file deletion events."""
        if not event.is_directory and self._is_supported_file(event.src_path):
            self.file_manager.file_changed.emit(event.src_path, "deleted")


class FileInfo:
    """Information about a local file."""
    
    def __init__(self, path: Path):
        """Initialize file info."""
        self.path = path
        self.name = path.name
        self.stem = path.stem
        self.suffix = path.suffix.lower()
        self.size = path.stat().st_size if path.exists() else 0
        self.modified_time = datetime.fromtimestamp(path.stat().st_mtime) if path.exists() else datetime.now()
        self.created_time = datetime.fromtimestamp(path.stat().st_ctime) if path.exists() else datetime.now()
        self.is_directory = path.is_dir() if path.exists() else False
        self.mime_type = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
        self._content_cache: Optional[str] = None
        self._metadata_cache: Optional[Dict[str, Any]] = None
    
    @property
    def is_supported(self) -> bool:
        """Check if file format is supported."""
        for format_list in SUPPORTED_FORMATS.values():
            if self.suffix in format_list:
                return True
        return False
    
    @property
    def format_category(self) -> Optional[str]:
        """Get the format category (documents, images, etc.)."""
        for category, formats in SUPPORTED_FORMATS.items():
            if self.suffix in formats:
                return category
        return None
    
    def get_checksum(self) -> str:
        """Calculate file checksum."""
        if not self.path.exists() or self.is_directory:
            return ""
        
        hasher = hashlib.md5()
        with open(self.path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hasher.update(chunk)
        return hasher.hexdigest()
    
    def read_content(self) -> str:
        """Read file content as text."""
        if self._content_cache is not None:
            return self._content_cache
        
        if not self.path.exists() or self.is_directory:
            return ""
        
        try:
            if self.suffix in ['.md', '.txt', '.html', '.json']:
                with open(self.path, 'r', encoding='utf-8') as f:
                    self._content_cache = f.read()
            else:
                # For binary files, return base64 encoded content
                import base64
                with open(self.path, 'rb') as f:
                    self._content_cache = base64.b64encode(f.read()).decode('utf-8')
        except Exception as e:
            print(f"Error reading file {self.path}: {e}")
            self._content_cache = ""
        
        return self._content_cache
    
    def read_metadata(self) -> Dict[str, Any]:
        """Read file metadata (frontmatter for markdown files)."""
        if self._metadata_cache is not None:
            return self._metadata_cache
        
        self._metadata_cache = {}
        
        if self.suffix == '.md' and self.path.exists():
            try:
                with open(self.path, 'r', encoding='utf-8') as f:
                    post = frontmatter.load(f)
                    self._metadata_cache = post.metadata
            except Exception as e:
                print(f"Error reading metadata from {self.path}: {e}")
        
        return self._metadata_cache
    
    def write_content(self, content: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Write content to file."""
        try:
            # Ensure parent directory exists
            self.path.parent.mkdir(parents=True, exist_ok=True)
            
            if self.suffix == '.md' and metadata:
                # Write markdown with frontmatter
                post = frontmatter.Post(content, **metadata)
                with open(self.path, 'w', encoding='utf-8') as f:
                    f.write(frontmatter.dumps(post))
            elif self.suffix in ['.md', '.txt', '.html', '.json']:
                # Write text content
                with open(self.path, 'w', encoding='utf-8') as f:
                    f.write(content)
            else:
                # Write binary content (base64 decoded)
                import base64
                with open(self.path, 'wb') as f:
                    f.write(base64.b64decode(content))
            
            # Clear cache
            self._content_cache = None
            self._metadata_cache = None
            
            return True
        except Exception as e:
            print(f"Error writing file {self.path}: {e}")
            return False


class FileManager(BaseModel):
    """Manages local file system operations and watching."""
    
    # Signals
    file_changed = BaseModel.data_changed  # Reuse from base
    
    def __init__(self, parent=None):
        """Initialize the file manager."""
        super().__init__(parent)
        self.watched_directories: Set[Path] = set()
        self.observer = Observer()
        self.file_watcher = FileWatcher(self)
        self._is_watching = False
    
    def start_watching(self) -> None:
        """Start file system watching."""
        if not self._is_watching and self.watched_directories:
            self.observer.start()
            self._is_watching = True
            self.logger.info("File watching started")
    
    def stop_watching(self) -> None:
        """Stop file system watching."""
        if self._is_watching:
            self.observer.stop()
            self.observer.join()
            self._is_watching = False
            self.logger.info("File watching stopped")
    
    def add_watch_directory(self, directory: Path) -> bool:
        """Add a directory to watch for changes."""
        try:
            if directory.exists() and directory.is_dir():
                self.observer.schedule(self.file_watcher, str(directory), recursive=True)
                self.watched_directories.add(directory)
                self.logger.info(f"Added watch directory: {directory}")
                return True
        except Exception as e:
            self._set_error(f"Failed to add watch directory {directory}: {str(e)}")
        return False
    
    def remove_watch_directory(self, directory: Path) -> bool:
        """Remove a directory from watching."""
        try:
            if directory in self.watched_directories:
                # Note: watchdog doesn't provide easy way to remove specific watch
                # We'd need to restart the observer with remaining directories
                self.watched_directories.discard(directory)
                self.logger.info(f"Removed watch directory: {directory}")
                return True
        except Exception as e:
            self._set_error(f"Failed to remove watch directory {directory}: {str(e)}")
        return False
    
    def scan_directory(self, directory: Path, recursive: bool = True) -> List[FileInfo]:
        """Scan directory for supported files."""
        files = []
        
        try:
            if not directory.exists() or not directory.is_dir():
                return files
            
            pattern = "**/*" if recursive else "*"
            for path in directory.glob(pattern):
                if path.is_file():
                    file_info = FileInfo(path)
                    if file_info.is_supported:
                        files.append(file_info)
        
        except Exception as e:
            self._set_error(f"Error scanning directory {directory}: {str(e)}")
        
        return files
    
    def get_file_info(self, file_path: Path) -> Optional[FileInfo]:
        """Get information about a specific file."""
        try:
            if file_path.exists():
                return FileInfo(file_path)
        except Exception as e:
            self._set_error(f"Error getting file info for {file_path}: {str(e)}")
        return None
    
    def create_file(self, file_path: Path, content: str = "", 
                   metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Create a new file with content."""
        try:
            file_info = FileInfo(file_path)
            return file_info.write_content(content, metadata)
        except Exception as e:
            self._set_error(f"Error creating file {file_path}: {str(e)}")
            return False
    
    def copy_file(self, source: Path, destination: Path) -> bool:
        """Copy a file to a new location."""
        try:
            import shutil
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
            return True
        except Exception as e:
            self._set_error(f"Error copying file {source} to {destination}: {str(e)}")
            return False
    
    def move_file(self, source: Path, destination: Path) -> bool:
        """Move a file to a new location."""
        try:
            import shutil
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(source), str(destination))
            return True
        except Exception as e:
            self._set_error(f"Error moving file {source} to {destination}: {str(e)}")
            return False
    
    def delete_file(self, file_path: Path) -> bool:
        """Delete a file."""
        try:
            if file_path.exists():
                file_path.unlink()
                return True
        except Exception as e:
            self._set_error(f"Error deleting file {file_path}: {str(e)}")
        return False
    
    def get_directory_tree(self, root_directory: Path, max_depth: int = 3) -> Dict[str, Any]:
        """Get directory tree structure."""
        def build_tree(path: Path, current_depth: int = 0) -> Dict[str, Any]:
            if current_depth >= max_depth:
                return {"name": path.name, "type": "directory", "children": []}
            
            tree = {
                "name": path.name,
                "path": str(path),
                "type": "directory",
                "children": []
            }
            
            try:
                for item in sorted(path.iterdir()):
                    if item.is_dir():
                        tree["children"].append(build_tree(item, current_depth + 1))
                    elif item.is_file():
                        file_info = FileInfo(item)
                        if file_info.is_supported:
                            tree["children"].append({
                                "name": item.name,
                                "path": str(item),
                                "type": "file",
                                "size": file_info.size,
                                "modified": file_info.modified_time.isoformat(),
                                "format": file_info.format_category
                            })
            except PermissionError:
                pass  # Skip directories we can't read
            
            return tree
        
        return build_tree(root_directory)
    
    def __del__(self):
        """Cleanup when object is destroyed."""
        self.stop_watching()
