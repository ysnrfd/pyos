"""
PyOS Logger Module

A comprehensive logging system for the operating system that provides:
- Structured logging with contextual information
- Multiple log levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- Log rotation and file output
- Kernel event logging
- Subsystem-specific loggers
- Thread-safe operation

Author: YSNRFD
Version: 1.0.0
"""

import logging
import sys
import threading
from datetime import datetime
from enum import IntEnum
from pathlib import Path
from typing import Optional, Any, List
from functools import wraps
import traceback


class LogLevel(IntEnum):
    """Log level enumeration with numeric values for comparison."""
    DEBUG = 10
    INFO = 20
    NOTICE = 25
    WARNING = 30
    ERROR = 40
    CRITICAL = 50
    PANIC = 60


class LogFormatter(logging.Formatter):
    """
    Custom log formatter for PyOS.
    
    Provides formatted output with:
    - Timestamp with microsecond precision
    - Log level with color coding (if terminal supports it)
    - Subsystem identification
    - Process/thread context
    - Structured message format
    """
    
    # ANSI color codes for terminal output
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'NOTICE': '\033[34m',     # Blue
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
        'PANIC': '\033[41m\033[97m',  # Red background, white text
    }
    RESET = '\033[0m'
    
    def __init__(self, use_colors: bool = True):
        super().__init__()
        self.use_colors = use_colors and self._supports_color()
    
    @staticmethod
    def _supports_color() -> bool:
        """Check if the terminal supports ANSI colors."""
        # Check if we're in a TTY
        if not hasattr(sys.stdout, 'isatty'):
            return False
        if not sys.stdout.isatty():
            return False
        return True
    
    def format(self, record: logging.LogRecord) -> str:
        """Format a log record."""
        # Get timestamp
        timestamp = datetime.fromtimestamp(record.created).strftime(
            '%Y-%m-%d %H:%M:%S.%f'
        )[:-3]
        
        # Get log level
        level = record.levelname
        
        # Color the level if enabled
        if self.use_colors and level in self.COLORS:
            level_display = f"{self.COLORS[level]}{level:8s}{self.RESET}"
        else:
            level_display = f"{level:8s}"
        
        # Build the message components
        components = [f"[{timestamp}]", level_display]
        
        # Add subsystem if available
        if hasattr(record, 'subsystem'):
            components.append(f"[{record.subsystem}]")
        
        # Add PID if available
        if hasattr(record, 'pid') and record.pid is not None:
            components.append(f"(pid={record.pid})")
        
        # Add the message
        components.append(str(record.getMessage()))
        
        # Add extra context if available
        if hasattr(record, 'context') and record.context:
            context_str = " ".join(f"{k}={v}" for k, v in record.context.items())
            components.append(f"{{{context_str}}}")
        
        message = " ".join(components)
        
        # Add exception info if present
        if record.exc_info:
            message += "\n" + self.formatException(record.exc_info)
        
        return message


class KernelLogHandler(logging.Handler):
    """
    Special handler for kernel events.
    
    This handler captures all log events and stores them in memory
    for later retrieval by monitoring and observability systems.
    """
    
    def __init__(self, max_entries: int = 10000):
        super().__init__()
        self.max_entries = max_entries
        self._log_buffer: List[dict[str, Any]] = []
        self._lock = threading.Lock()
    
    def emit(self, record: logging.LogRecord) -> None:
        """Store log record in buffer."""
        log_entry = {
            'timestamp': record.created,
            'level': record.levelname,
            'message': record.getMessage(),
            'subsystem': getattr(record, 'subsystem', None),
            'pid': getattr(record, 'pid', None),
            'context': getattr(record, 'context', {}),
        }
        
        with self._lock:
            self._log_buffer.append(log_entry)
            # Trim buffer if needed
            if len(self._log_buffer) > self.max_entries:
                self._log_buffer = self._log_buffer[-self.max_entries:]
    
    def get_logs(
        self,
        level: Optional[str] = None,
        subsystem: Optional[str] = None,
        limit: int = 100
    ) -> List[dict[str, Any]]:
        """Retrieve logs with optional filtering."""
        with self._lock:
            logs = self._log_buffer.copy()
        
        # Filter by level
        if level:
            logs = [l for l in logs if l['level'] == level]
        
        # Filter by subsystem
        if subsystem:
            logs = [l for l in logs if l['subsystem'] == subsystem]
        
        return logs[-limit:]
    
    def clear(self) -> None:
        """Clear the log buffer."""
        with self._lock:
            self._log_buffer.clear()


class Logger:
    """
    Main logging class for PyOS.
    
    Provides a centralized logging interface for all kernel subsystems
    with support for:
    - Multiple output handlers (console, file, kernel buffer)
    - Log rotation
    - Subsystem-specific loggers
    - Structured context data
    
    Example:
        >>> log = Logger('kernel')
        >>> log.info("System starting up", context={'version': '1.0.0'})
        >>> log.error("Failed to allocate memory", pid=42)
    """
    
    _instances: dict[str, 'Logger'] = {}
    _lock = threading.Lock()
    _initialized = False
    _kernel_handler: Optional[KernelLogHandler] = None
    _global_level: int = LogLevel.INFO
    
    def __new__(cls, subsystem: str = 'kernel') -> 'Logger':
        """Get or create a logger for a subsystem."""
        with cls._lock:
            if subsystem not in cls._instances:
                instance = super().__new__(cls)
                instance._subsystem = subsystem
                instance._logger = logging.getLogger(f'pyos.{subsystem}')
                cls._instances[subsystem] = instance
            return cls._instances[subsystem]
    
    def __init__(self, subsystem: str = 'kernel'):
        """Initialize the logger."""
        # Skip if already initialized
        if hasattr(self, '_subsystem') and self._logger.handlers:
            return
        
        self._logger.setLevel(self._global_level)
    
    @classmethod
    def initialize(
        cls,
        level: int = LogLevel.INFO,
        log_file: Optional[str] = None,
        use_colors: bool = True
    ) -> None:
        """
        Initialize the logging system.
        
        This must be called once before using any loggers.
        
        Args:
            level: Minimum log level to capture
            log_file: Optional file path for log output
            use_colors: Whether to use ANSI colors in console output
        """
        with cls._lock:
            if cls._initialized:
                return
            
            cls._global_level = level
            
            # Create kernel log handler
            cls._kernel_handler = KernelLogHandler()
            cls._kernel_handler.setLevel(level)
            
            # Configure root logger
            root_logger = logging.getLogger('pyos')
            root_logger.setLevel(level)
            
            # Add console handler
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(level)
            console_handler.setFormatter(LogFormatter(use_colors=use_colors))
            root_logger.addHandler(console_handler)
            
            # Add kernel handler
            root_logger.addHandler(cls._kernel_handler)
            
            # Add file handler if specified
            if log_file:
                file_path = Path(log_file)
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_handler = logging.FileHandler(log_file)
                file_handler.setLevel(level)
                file_handler.setFormatter(LogFormatter(use_colors=False))
                root_logger.addHandler(file_handler)
            
            cls._initialized = True
    
    @classmethod
    def get_kernel_logs(
        cls,
        level: Optional[str] = None,
        subsystem: Optional[str] = None,
        limit: int = 100
    ) -> List[dict[str, Any]]:
        """Get logs from the kernel log buffer."""
        if cls._kernel_handler is None:
            return []
        return cls._kernel_handler.get_logs(level=level, subsystem=subsystem, limit=limit)
    
    def _log(
        self,
        level: int,
        message: str,
        pid: Optional[int] = None,
        context: Optional[dict[str, Any]] = None
    ) -> None:
        """Internal logging method."""
        extra = {
            'subsystem': self._subsystem,
            'pid': pid,
            'context': context or {},
        }
        self._logger.log(level, message, extra=extra)
    
    def debug(
        self,
        message: str,
        pid: Optional[int] = None,
        context: Optional[dict[str, Any]] = None
    ) -> None:
        """Log a debug message."""
        self._log(LogLevel.DEBUG, message, pid, context)
    
    def info(
        self,
        message: str,
        pid: Optional[int] = None,
        context: Optional[dict[str, Any]] = None
    ) -> None:
        """Log an info message."""
        self._log(LogLevel.INFO, message, pid, context)
    
    def notice(
        self,
        message: str,
        pid: Optional[int] = None,
        context: Optional[dict[str, Any]] = None
    ) -> None:
        """Log a notice message."""
        self._log(LogLevel.NOTICE, message, pid, context)
    
    def warning(
        self,
        message: str,
        pid: Optional[int] = None,
        context: Optional[dict[str, Any]] = None
    ) -> None:
        """Log a warning message."""
        self._log(LogLevel.WARNING, message, pid, context)
    
    def error(
        self,
        message: str,
        pid: Optional[int] = None,
        context: Optional[dict[str, Any]] = None
    ) -> None:
        """Log an error message."""
        self._log(LogLevel.ERROR, message, pid, context)
    
    def critical(
        self,
        message: str,
        pid: Optional[int] = None,
        context: Optional[dict[str, Any]] = None
    ) -> None:
        """Log a critical message."""
        self._log(LogLevel.CRITICAL, message, pid, context)
    
    def panic(
        self,
        message: str,
        pid: Optional[int] = None,
        context: Optional[dict[str, Any]] = None
    ) -> None:
        """Log a kernel panic message."""
        self._log(LogLevel.PANIC, message, pid, context)
    
    def exception(
        self,
        message: str,
        exc: Optional[Exception] = None,
        pid: Optional[int] = None,
        context: Optional[dict[str, Any]] = None
    ) -> None:
        """Log an exception with stack trace."""
        if exc:
            self._logger.exception(
                message,
                exc_info=exc,
                extra={
                    'subsystem': self._subsystem,
                    'pid': pid,
                    'context': context or {},
                }
            )
        else:
            self._logger.exception(
                message,
                extra={
                    'subsystem': self._subsystem,
                    'pid': pid,
                    'context': context or {},
                }
            )


def log_function_call(logger: Optional[Logger] = None):
    """
    Decorator to log function calls.
    
    Example:
        >>> @log_function_call()
        ... def allocate_memory(size: int) -> bytes:
        ...     return bytes(size)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            nonlocal logger
            if logger is None:
                logger = Logger('function')
            
            func_name = func.__name__
            logger.debug(
                f"Calling {func_name}",
                context={'args': str(args)[:100], 'kwargs': str(kwargs)[:100]}
            )
            
            try:
                result = func(*args, **kwargs)
                logger.debug(f"Function {func_name} completed successfully")
                return result
            except Exception as e:
                logger.error(
                    f"Function {func_name} raised {type(e).__name__}: {e}"
                )
                raise
        
        return wrapper
    return decorator


# Convenience function to get a logger
def get_logger(subsystem: str) -> Logger:
    """
    Get a logger for the specified subsystem.
    
    Args:
        subsystem: Name of the subsystem (e.g., 'kernel', 'process', 'memory')
    
    Returns:
        Logger instance for the subsystem
    """
    return Logger(subsystem)
