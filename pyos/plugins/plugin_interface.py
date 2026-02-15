"""
Plugin Interface Module

Defines the interface for PyOS plugins.

Author: YSNRFD
Version: 1.0.0
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional
from enum import Enum


class PluginState(Enum):
    """Plugin lifecycle state."""
    UNLOADED = "unloaded"
    LOADED = "loaded"
    ACTIVE = "active"
    ERROR = "error"


@dataclass
class PluginInfo:
    """Information about a plugin."""
    name: str
    version: str
    description: str
    author: str
    state: PluginState = PluginState.UNLOADED
    error: Optional[str] = None


class PluginInterface(ABC):
    """
    Abstract base class for PyOS plugins.
    
    Plugins can extend the OS functionality by:
    - Adding new system calls
    - Adding shell commands
    - Providing filesystem drivers
    - Adding monitoring capabilities
    
    Example:
        >>> class MyPlugin(PluginInterface):
        ...     @property
        ...     def info(self) -> PluginInfo:
        ...         return PluginInfo(
        ...             name="my_plugin",
        ...             version="1.0.0",
        ...             description="My plugin",
        ...             author="Me"
        ...         )
        ...     
        ...     def initialize(self, kernel) -> None:
        ...         # Plugin initialization
        ...         pass
    """
    
    @property
    @abstractmethod
    def info(self) -> PluginInfo:
        """Get plugin information."""
        pass
    
    @abstractmethod
    def initialize(self, kernel: Any) -> None:
        """
        Initialize the plugin.
        
        Args:
            kernel: The kernel instance
        """
        pass
    
    def shutdown(self) -> None:
        """Clean up plugin resources."""
        pass
    
    def on_event(self, event_type: str, data: Any) -> Optional[Any]:
        """
        Handle a kernel event.
        
        Args:
            event_type: Type of event
            data: Event data
        
        Returns:
            Optional response
        """
        return None
    
    def get_commands(self) -> dict[str, Any]:
        """
        Get shell commands provided by this plugin.
        
        Returns:
            Dict of command name to handler function
        """
        return {}
    
    def get_syscalls(self) -> dict[int, Any]:
        """
        Get system calls provided by this plugin.
        
        Returns:
            Dict of syscall number to handler function
        """
        return {}
