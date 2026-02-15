"""
PyOS Subsystem Registry

A centralized registry for managing kernel subsystems and their dependencies.
Provides:
- Subsystem registration and lifecycle management
- Dependency resolution
- Service locator pattern
- Clean shutdown coordination

Author: YSNRFD
Version: 1.0.0
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Optional, Callable, TypeVar, Generic, List
from collections import defaultdict
import threading

from pyos.logger import Logger, get_logger


class SubsystemState(Enum):
    """Lifecycle state of a subsystem."""
    UNREGISTERED = auto()
    REGISTERED = auto()
    INITIALIZING = auto()
    INITIALIZED = auto()
    RUNNING = auto()
    STOPPING = auto()
    STOPPED = auto()
    ERROR = auto()


class SubsystemPriority(Enum):
    """Initialization priority for subsystems."""
    CRITICAL = 0     # Must initialize first (kernel, logging)
    HIGH = 10        # Core services (memory, process)
    NORMAL = 20      # Standard services (filesystem, ipc)
    LOW = 30         # Optional services (plugins)
    DAEMON = 40      # Background services


@dataclass
class SubsystemInfo:
    """Information about a registered subsystem."""
    name: str
    instance: 'Subsystem'
    priority: SubsystemPriority
    dependencies: List[str]
    state: SubsystemState = SubsystemState.UNREGISTERED
    error: Optional[Exception] = None


class Subsystem(ABC):
    """
    Abstract base class for all kernel subsystems.
    
    All subsystems must implement this interface to be registered
    with the kernel and participate in the lifecycle management.
    
    Lifecycle:
        1. __init__() - Subsystem is created
        2. initialize() - Subsystem is initialized
        3. start() - Subsystem starts operation
        4. stop() - Subsystem stops operation
        5. cleanup() - Subsystem cleans up resources
    """
    
    def __init__(self, name: str):
        self._name = name
        self._logger = get_logger(name)
        self._state = SubsystemState.UNREGISTERED
    
    @property
    def name(self) -> str:
        """Get the subsystem name."""
        return self._name
    
    @property
    def state(self) -> SubsystemState:
        """Get the current state."""
        return self._state
    
    @property
    def logger(self) -> Logger:
        """Get the subsystem logger."""
        return self._logger
    
    def set_state(self, state: SubsystemState) -> None:
        """Set the subsystem state."""
        self._state = state
        self._logger.debug(f"State changed to {state.name}")
    
    @abstractmethod
    def initialize(self) -> None:
        """
        Initialize the subsystem.
        
        Called during system boot to prepare the subsystem for operation.
        Should allocate resources and perform initial setup.
        
        Raises:
            SubsystemInitError: If initialization fails
        """
        pass
    
    def start(self) -> None:
        """
        Start the subsystem.
        
        Called after initialization to begin normal operation.
        Default implementation does nothing.
        """
        pass
    
    def stop(self) -> None:
        """
        Stop the subsystem.
        
        Called during shutdown to stop active operations.
        Default implementation does nothing.
        """
        pass
    
    def cleanup(self) -> None:
        """
        Clean up subsystem resources.
        
        Called during shutdown to release all resources.
        Default implementation does nothing.
        """
        pass
    
    def health_check(self) -> bool:
        """
        Check if the subsystem is healthy.
        
        Returns:
            True if the subsystem is healthy, False otherwise
        """
        return self._state in (
            SubsystemState.INITIALIZED,
            SubsystemState.RUNNING
        )


T = TypeVar('T')


class SubsystemRegistry:
    """
    Central registry for kernel subsystems.
    
    Manages subsystem registration, initialization, and lifecycle.
    Implements the Service Locator pattern for dependency injection.
    
    Example:
        >>> registry = SubsystemRegistry()
        >>> registry.register('memory', MemoryManager(), 
        ...                   priority=SubsystemPriority.HIGH)
        >>> memory = registry.get('memory')
    """
    
    _instance: Optional['SubsystemRegistry'] = None
    _lock = threading.Lock()
    
    def __new__(cls) -> 'SubsystemRegistry':
        """Singleton pattern for global registry access."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._subsystems = {}
                cls._instance._initialized = False
                cls._instance._logger = get_logger('registry')
            return cls._instance
    
    def register(
        self,
        name: str,
        subsystem: Subsystem,
        priority: SubsystemPriority = SubsystemPriority.NORMAL,
        dependencies: Optional[list[str]] = None
    ) -> None:
        """
        Register a subsystem with the kernel.
        
        Args:
            name: Unique name for the subsystem
            subsystem: Subsystem instance
            priority: Initialization priority
            dependencies: List of subsystem names this depends on
        
        Raises:
            ValueError: If subsystem with name already exists
        """
        with self._lock:
            if name in self._subsystems:
                raise ValueError(f"Subsystem '{name}' already registered")
            
            info = SubsystemInfo(
                name=name,
                instance=subsystem,
                priority=priority,
                dependencies=dependencies or [],
                state=SubsystemState.REGISTERED
            )
            
            self._subsystems[name] = info
            subsystem._state = SubsystemState.REGISTERED
            
            self._logger.debug(
                f"Registered subsystem '{name}'",
                context={'priority': priority.name}
            )
    
    def unregister(self, name: str) -> None:
        """
        Unregister a subsystem.
        
        Args:
            name: Name of subsystem to unregister
        
        Raises:
            KeyError: If subsystem not found
        """
        with self._lock:
            if name not in self._subsystems:
                raise KeyError(f"Subsystem '{name}' not found")
            
            info = self._subsystems[name]
            if info.state == SubsystemState.RUNNING:
                info.instance.stop()
            if info.state in (SubsystemState.RUNNING, SubsystemState.INITIALIZED):
                info.instance.cleanup()
            
            del self._subsystems[name]
            self._logger.debug(f"Unregistered subsystem '{name}'")
    
    def get(self, name: str) -> Subsystem:
        """
        Get a subsystem by name.
        
        Args:
            name: Name of the subsystem
        
        Returns:
            The subsystem instance
        
        Raises:
            KeyError: If subsystem not found
        """
        with self._lock:
            if name not in self._subsystems:
                raise KeyError(f"Subsystem '{name}' not found")
            return self._subsystems[name].instance
    
    def get_typed(self, name: str, expected_type: type[T]) -> T:
        """
        Get a subsystem with type checking.
        
        Args:
            name: Name of the subsystem
            expected_type: Expected type of the subsystem
        
        Returns:
            The subsystem instance cast to expected type
        
        Raises:
            KeyError: If subsystem not found
            TypeError: If subsystem is not of expected type
        """
        subsystem = self.get(name)
        if not isinstance(subsystem, expected_type):
            raise TypeError(
                f"Subsystem '{name}' is {type(subsystem).__name__}, "
                f"expected {expected_type.__name__}"
            )
        return subsystem
    
    def get_state(self, name: str) -> SubsystemState:
        """Get the state of a subsystem."""
        with self._lock:
            if name not in self._subsystems:
                raise KeyError(f"Subsystem '{name}' not found")
            return self._subsystems[name].state
    
    def initialize_all(self) -> None:
        """
        Initialize all subsystems in dependency order.
        
        Sorts subsystems by priority and initializes them
        in order, ensuring dependencies are initialized first.
        
        Raises:
            SubsystemInitError: If any subsystem fails to initialize
        """
        if self._initialized:
            return
        
        # Get initialization order
        order = self._resolve_initialization_order()
        
        self._logger.info("Starting subsystem initialization")
        
        for name in order:
            info = self._subsystems[name]
            
            try:
                info.state = SubsystemState.INITIALIZING
                info.instance.set_state(SubsystemState.INITIALIZING)
                
                self._logger.debug(f"Initializing subsystem '{name}'")
                info.instance.initialize()
                
                info.state = SubsystemState.INITIALIZED
                info.instance.set_state(SubsystemState.INITIALIZED)
                
                self._logger.debug(f"Subsystem '{name}' initialized")
                
            except Exception as e:
                info.state = SubsystemState.ERROR
                info.error = e
                self._logger.error(
                    f"Failed to initialize '{name}': {e}",
                    context={'error': str(e)}
                )
                raise
        
        self._initialized = True
        self._logger.info("All subsystems initialized")
    
    def start_all(self) -> None:
        """Start all initialized subsystems."""
        order = self._resolve_initialization_order()
        
        for name in order:
            info = self._subsystems[name]
            if info.state == SubsystemState.INITIALIZED:
                try:
                    self._logger.debug(f"Starting subsystem '{name}'")
                    info.instance.start()
                    info.state = SubsystemState.RUNNING
                    info.instance.set_state(SubsystemState.RUNNING)
                except Exception as e:
                    info.state = SubsystemState.ERROR
                    info.error = e
                    self._logger.error(f"Failed to start '{name}': {e}")
                    raise
    
    def stop_all(self) -> None:
        """Stop all running subsystems in reverse order."""
        order = list(reversed(self._resolve_initialization_order()))
        
        self._logger.info("Stopping all subsystems")
        
        for name in order:
            info = self._subsystems[name]
            if info.state == SubsystemState.RUNNING:
                try:
                    self._logger.debug(f"Stopping subsystem '{name}'")
                    info.instance.stop()
                    info.state = SubsystemState.STOPPED
                    info.instance.set_state(SubsystemState.STOPPED)
                except Exception as e:
                    self._logger.error(f"Error stopping '{name}': {e}")
    
    def cleanup_all(self) -> None:
        """Clean up all subsystems in reverse order."""
        order = list(reversed(self._resolve_initialization_order()))
        
        for name in order:
            info = self._subsystems[name]
            if info.state not in (SubsystemState.UNREGISTERED, SubsystemState.ERROR):
                try:
                    self._logger.debug(f"Cleaning up subsystem '{name}'")
                    info.instance.cleanup()
                except Exception as e:
                    self._logger.error(f"Error cleaning up '{name}': {e}")
    
    def _resolve_initialization_order(self) -> List[str]:
        """
        Resolve the order in which subsystems should be initialized.
        
        Uses topological sort considering both priority and dependencies.
        """
        # Sort by priority first
        sorted_names = sorted(
            self._subsystems.keys(),
            key=lambda n: self._subsystems[n].priority.value
        )
        
        # Build dependency graph
        graph: dict[str, set[str]] = defaultdict(set)
        in_degree: dict[str, int] = {n: 0 for n in sorted_names}
        
        for name in sorted_names:
            info = self._subsystems[name]
            for dep in info.dependencies:
                if dep in self._subsystems:
                    graph[dep].add(name)
                    in_degree[name] += 1
        
        # Topological sort
        result: List[str] = []
        ready = [n for n in sorted_names if in_degree[n] == 0]
        
        while ready:
            # Take the highest priority ready item
            ready.sort(key=lambda n: self._subsystems[n].priority.value)
            current = ready.pop(0)
            result.append(current)
            
            for dependent in graph[current]:
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    ready.append(dependent)
        
        # Check for cycles
        if len(result) != len(sorted_names):
            missing = set(sorted_names) - set(result)
            raise RuntimeError(
                f"Circular dependency detected involving: {missing}"
            )
        
        return result
    
    def list_subsystems(self) -> List[dict[str, Any]]:
        """List all registered subsystems with their status."""
        result = []
        for name, info in self._subsystems.items():
            result.append({
                'name': name,
                'priority': info.priority.name,
                'state': info.state.name,
                'dependencies': info.dependencies,
                'healthy': info.instance.health_check(),
            })
        return result
    
    def health_check(self) -> dict[str, bool]:
        """Check health of all subsystems."""
        return {
            name: info.instance.health_check()
            for name, info in self._subsystems.items()
        }


def get_registry() -> SubsystemRegistry:
    """Get the global subsystem registry."""
    return SubsystemRegistry()
