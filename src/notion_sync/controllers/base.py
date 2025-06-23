"""
Base controller classes for the Notion Sync application.
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from PySide6.QtCore import QObject, Signal, QTimer
from notion_sync.utils.logging_config import LoggerMixin


class BaseController(QObject, LoggerMixin):
    """Base controller class with common functionality."""
    
    # Common signals
    model_updated = Signal()
    view_update_requested = Signal(str, dict)  # update_type, data
    error_occurred = Signal(str)
    status_changed = Signal(str)
    
    def __init__(self, parent: Optional[QObject] = None):
        """Initialize the base controller."""
        super().__init__(parent)
        self._models: Dict[str, Any] = {}
        self._views: Dict[str, Any] = {}
        self._is_initialized = False
    
    def add_model(self, name: str, model: Any) -> None:
        """Add a model to the controller."""
        self._models[name] = model
        self._connect_model_signals(model)
    
    def add_view(self, name: str, view: Any) -> None:
        """Add a view to the controller."""
        self._views[name] = view
        self._connect_view_signals(view)
    
    def get_model(self, name: str) -> Optional[Any]:
        """Get a model by name."""
        return self._models.get(name)
    
    def get_view(self, name: str) -> Optional[Any]:
        """Get a view by name."""
        return self._views.get(name)
    
    def _connect_model_signals(self, model: Any) -> None:
        """Connect model signals to controller methods."""
        if hasattr(model, 'data_changed'):
            model.data_changed.connect(self._on_model_data_changed)
        if hasattr(model, 'error_occurred'):
            model.error_occurred.connect(self._on_model_error)
        if hasattr(model, 'progress_updated'):
            model.progress_updated.connect(self._on_model_progress)
    
    def _connect_view_signals(self, view: Any) -> None:
        """Connect view signals to controller methods."""
        if hasattr(view, 'action_requested'):
            view.action_requested.connect(self._on_view_action)
    
    def _on_model_data_changed(self) -> None:
        """Handle model data changes."""
        self.model_updated.emit()
        self._update_views()
    
    def _on_model_error(self, error: str) -> None:
        """Handle model errors."""
        self.error_occurred.emit(error)
        self.logger.error(f"Model error: {error}")
    
    def _on_model_progress(self, percentage: int, message: str) -> None:
        """Handle model progress updates."""
        self.view_update_requested.emit("progress", {
            "percentage": percentage,
            "message": message
        })
    
    def _on_view_action(self, action: str, parameters: Dict[str, Any]) -> None:
        """Handle view actions."""
        self.logger.debug(f"View action: {action} with parameters: {parameters}")
        self._handle_action(action, parameters)
    
    @abstractmethod
    def _handle_action(self, action: str, parameters: Dict[str, Any]) -> None:
        """Handle specific actions. Override in subclasses."""
        pass
    
    @abstractmethod
    def _update_views(self) -> None:
        """Update views with current model data. Override in subclasses."""
        pass
    
    def initialize(self) -> None:
        """Initialize the controller."""
        if self._is_initialized:
            return
        
        self._setup_connections()
        self._load_initial_data()
        self._is_initialized = True
        self.logger.info(f"{self.__class__.__name__} initialized")
    
    def _setup_connections(self) -> None:
        """Set up additional connections. Override in subclasses."""
        pass
    
    def _load_initial_data(self) -> None:
        """Load initial data. Override in subclasses."""
        pass


class AsyncController(BaseController):
    """Base controller with async operation support."""
    
    def __init__(self, parent: Optional[QObject] = None):
        """Initialize the async controller."""
        super().__init__(parent)
        self._pending_operations: List[str] = []
        self._operation_timer = QTimer()
        self._operation_timer.timeout.connect(self._check_operations)
        self._operation_timer.start(1000)  # Check every second
    
    def _start_operation(self, operation_name: str) -> None:
        """Start tracking an async operation."""
        if operation_name not in self._pending_operations:
            self._pending_operations.append(operation_name)
            self.status_changed.emit(f"Starting {operation_name}...")
            self.logger.debug(f"Started operation: {operation_name}")
    
    def _finish_operation(self, operation_name: str, success: bool = True) -> None:
        """Finish tracking an async operation."""
        if operation_name in self._pending_operations:
            self._pending_operations.remove(operation_name)
            status = "completed" if success else "failed"
            self.status_changed.emit(f"{operation_name} {status}")
            self.logger.debug(f"Finished operation: {operation_name} ({status})")
    
    def _check_operations(self) -> None:
        """Check the status of pending operations."""
        if self._pending_operations:
            current_ops = ", ".join(self._pending_operations)
            self.status_changed.emit(f"Running: {current_ops}")
        else:
            self.status_changed.emit("Ready")
    
    @property
    def has_pending_operations(self) -> bool:
        """Check if there are pending operations."""
        return len(self._pending_operations) > 0


class SyncController(AsyncController):
    """Base controller for synchronization operations."""
    
    # Sync-specific signals
    sync_started = Signal(str)  # sync_type
    sync_finished = Signal(str, bool)  # sync_type, success
    sync_progress = Signal(str, int, str)  # sync_type, percentage, message
    conflict_detected = Signal(dict)  # conflict_data
    
    def __init__(self, parent: Optional[QObject] = None):
        """Initialize the sync controller."""
        super().__init__(parent)
        self._sync_in_progress = False
        self._current_sync_type: Optional[str] = None
    
    @property
    def sync_in_progress(self) -> bool:
        """Check if sync is currently in progress."""
        return self._sync_in_progress
    
    @property
    def current_sync_type(self) -> Optional[str]:
        """Get the current sync type."""
        return self._current_sync_type
    
    def _start_sync(self, sync_type: str) -> None:
        """Start a sync operation."""
        if self._sync_in_progress:
            self.logger.warning(f"Sync already in progress: {self._current_sync_type}")
            return
        
        self._sync_in_progress = True
        self._current_sync_type = sync_type
        self.sync_started.emit(sync_type)
        self._start_operation(f"sync_{sync_type}")
        self.logger.info(f"Started sync: {sync_type}")
    
    def _finish_sync(self, success: bool = True) -> None:
        """Finish the current sync operation."""
        if not self._sync_in_progress:
            return
        
        sync_type = self._current_sync_type
        self._sync_in_progress = False
        self._current_sync_type = None
        
        if sync_type:
            self.sync_finished.emit(sync_type, success)
            self._finish_operation(f"sync_{sync_type}", success)
            self.logger.info(f"Finished sync: {sync_type} ({'success' if success else 'failed'})")
    
    def _update_sync_progress(self, percentage: int, message: str = "") -> None:
        """Update sync progress."""
        if self._sync_in_progress and self._current_sync_type:
            self.sync_progress.emit(self._current_sync_type, percentage, message)
    
    @abstractmethod
    async def start_sync(self, sync_type: str, **kwargs) -> bool:
        """Start a synchronization operation. Override in subclasses."""
        pass
