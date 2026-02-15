"""
PyOS Kernel Core

The central kernel module that:
- Manages all subsystems
- Handles system calls
- Coordinates process scheduling
- Manages memory allocation
- Handles interrupts
- Provides graceful shutdown

Author: YSNRFD
Version: 1.0.0
"""

import threading
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Optional, Callable, List

from pyos.logger import Logger, get_logger
from pyos.exceptions import (
    KernelPanic,
    SubsystemInitError,
    ShutdownError,
    ProcessException,
)
from pyos.core.config_loader import get_config
from pyos.core.registry import (
    SubsystemRegistry,
    Subsystem,
    SubsystemState,
    SubsystemPriority,
    get_registry
)
from pyos.core.event_loop import EventLoop, InterruptType


class KernelState(Enum):
    """Kernel operational state."""
    UNINITIALIZED = auto()
    INITIALIZING = auto()
    INITIALIZED = auto()
    RUNNING = auto()
    SHUTTING_DOWN = auto()
    SHUTDOWN = auto()
    PANIC = auto()


@dataclass
class KernelInfo:
    """Kernel information structure."""
    name: str
    version: str
    uptime: float = 0.0
    state: KernelState = KernelState.UNINITIALIZED
    process_count: int = 0
    memory_used: int = 0
    memory_total: int = 0


class Kernel:
    """
    The central kernel of PyOS.
    
    The kernel is responsible for:
    - Initializing and managing all subsystems
    - Running the main event loop
    - Handling system calls
    - Managing process lifecycle
    - Coordinating memory allocation
    - Handling interrupts and signals
    - Providing graceful shutdown
    
    The kernel follows a microkernel-like architecture where
    most services are implemented as subsystems.
    
    Example:
        >>> kernel = Kernel()
        >>> kernel.initialize()
        >>> kernel.run()
    """
    
    _instance: Optional['Kernel'] = None
    _lock = threading.Lock()
    
    def __new__(cls) -> 'Kernel':
        """Singleton pattern for kernel access."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance
    
    def __init__(self):
        """Initialize the kernel structure."""
        if self._initialized:
            return
        
        self._state = KernelState.UNINITIALIZED
        self._logger = get_logger('kernel')
        self._registry = get_registry()
        self._event_loop = EventLoop()
        self._start_time: Optional[float] = None
        self._shutdown_requested = False
        self._shutdown_handlers: List[Callable] = []
        
        # Subsystem references (populated during init)
        self._process_manager = None
        self._memory_manager = None
        self._filesystem = None
        self._user_manager = None
        self._syscall_dispatcher = None
        self._security_manager = None
        self._ipc_manager = None
        self._monitoring = None
        
        self._initialized = True
    
    @property
    def state(self) -> KernelState:
        """Get the current kernel state."""
        return self._state
    
    @property
    def uptime(self) -> float:
        """Get the system uptime in seconds."""
        if self._start_time is None:
            return 0.0
        return time.time() - self._start_time
    
    @property
    def event_loop(self) -> EventLoop:
        """Get the event loop instance."""
        return self._event_loop
    
    @property
    def registry(self) -> SubsystemRegistry:
        """Get the subsystem registry."""
        return self._registry
    
    def initialize(self) -> None:
        """
        Initialize the kernel.
        
        This sets up the core kernel structures but does not
        initialize subsystems. Call initialize_subsystems() after.
        """
        self._state = KernelState.INITIALIZING
        self._logger.info("Kernel initializing...")
        
        config = get_config()
        self._info = KernelInfo(
            name=config.kernel.name,
            version=config.kernel.version
        )
        
        # Register interrupt handlers
        self._register_interrupt_handlers()
        
        self._state = KernelState.INITIALIZED
        self._logger.info("Kernel core initialized")
    
    def initialize_subsystems(self) -> None:
        """
        Initialize all kernel subsystems.
        
        This must be called after initialize() and before run().
        Subsystems are initialized in dependency order.
        """
        from pyos.process.process_manager import ProcessManager
        from pyos.memory.memory_manager import MemoryManager
        from pyos.filesystem.vfs import VirtualFileSystem
        from pyos.users.user_manager import UserManager
        from pyos.syscalls.dispatcher import SyscallDispatcher
        from pyos.security.sandbox import SecurityManager
        from pyos.ipc.pipe import IPCManager
        from pyos.monitoring.metrics import MonitoringManager
        
        self._logger.info("Initializing subsystems...")
        
        # Register subsystems with dependencies
        # Memory must come first
        memory_manager = MemoryManager()
        self._registry.register(
            'memory',
            memory_manager,
            priority=SubsystemPriority.HIGH
        )
        self._memory_manager = memory_manager
        
        # Process manager depends on memory
        process_manager = ProcessManager()
        self._registry.register(
            'process_manager',
            process_manager,
            priority=SubsystemPriority.HIGH,
            dependencies=['memory']
        )
        self._process_manager = process_manager
        
        # Filesystem
        filesystem = VirtualFileSystem()
        self._registry.register(
            'filesystem',
            filesystem,
            priority=SubsystemPriority.NORMAL
        )
        self._filesystem = filesystem
        
        # User manager
        user_manager = UserManager()
        self._registry.register(
            'users',
            user_manager,
            priority=SubsystemPriority.NORMAL,
            dependencies=['filesystem']
        )
        self._user_manager = user_manager
        
        # Security manager
        security_manager = SecurityManager()
        self._registry.register(
            'security',
            security_manager,
            priority=SubsystemPriority.NORMAL,
            dependencies=['users']
        )
        self._security_manager = security_manager
        
        # IPC
        ipc_manager = IPCManager()
        self._registry.register(
            'ipc',
            ipc_manager,
            priority=SubsystemPriority.NORMAL
        )
        self._ipc_manager = ipc_manager
        
        # Syscall dispatcher depends on most other subsystems
        syscall_dispatcher = SyscallDispatcher()
        self._registry.register(
            'syscalls',
            syscall_dispatcher,
            priority=SubsystemPriority.NORMAL,
            dependencies=['process_manager', 'memory', 'filesystem', 'users', 'ipc']
        )
        self._syscall_dispatcher = syscall_dispatcher
        
        # Monitoring
        monitoring = MonitoringManager()
        self._registry.register(
            'monitoring',
            monitoring,
            priority=SubsystemPriority.LOW,
            dependencies=['process_manager', 'memory']
        )
        self._monitoring = monitoring
        
        # Initialize all subsystems
        self._registry.initialize_all()
        self._registry.start_all()
        
        self._logger.info("All subsystems initialized")
    
    def _register_interrupt_handlers(self) -> None:
        """Register handlers for simulated interrupts."""
        self._event_loop.register_interrupt_handler(
            InterruptType.TIMER,
            self._handle_timer_interrupt
        )
        self._event_loop.register_interrupt_handler(
            InterruptType.SYSCALL,
            self._handle_syscall_interrupt
        )
        self._event_loop.register_interrupt_handler(
            InterruptType.FAULT,
            self._handle_fault_interrupt
        )
    
    def _handle_timer_interrupt(self, interrupt) -> None:
        """Handle timer interrupt - triggers scheduler."""
        if self._process_manager:
            self._process_manager.schedule()
    
    def _handle_syscall_interrupt(self, interrupt) -> None:
        """Handle syscall interrupt."""
        if self._syscall_dispatcher and interrupt.data:
            self._syscall_dispatcher.dispatch(interrupt.data)
    
    def _handle_fault_interrupt(self, interrupt) -> None:
        """Handle fault interrupt (page fault, etc.)."""
        self._logger.warning(
            f"Fault interrupt received",
            context={'data': str(interrupt.data)}
        )
    
    def run(self) -> None:
        """
        Run the kernel main loop.
        
        This starts the event loop and begins normal operation.
        """
        self._state = KernelState.RUNNING
        self._start_time = time.time()
        
        config = get_config()
        
        self._logger.info(
            f"{config.kernel.name} v{config.kernel.version} running"
        )
        
        # Start the event loop
        self._event_loop.start()
        
        # Schedule periodic tasks
        self._schedule_periodic_tasks()
        
        self._logger.info("System ready")
    
    def _schedule_periodic_tasks(self) -> None:
        """Schedule periodic kernel tasks."""
        config = get_config()
        
        # Schedule scheduler tick
        quantum_ms = config.scheduler.quantum / 1000.0
        self._event_loop.schedule_timer(
            callback=self._scheduler_tick,
            delay=quantum_ms,
            recurring=True
        )
        
        # Schedule monitoring update
        self._event_loop.schedule_timer(
            callback=self._monitoring_tick,
            delay=1.0,
            recurring=True
        )
    
    def _scheduler_tick(self) -> None:
        """Called periodically to trigger scheduling."""
        if self._process_manager:
            self._process_manager.tick()
    
    def _monitoring_tick(self) -> None:
        """Called periodically to update monitoring."""
        if self._monitoring:
            self._monitoring.update()
    
    def request_shutdown(self, reason: str = "User requested") -> None:
        """
        Request a system shutdown.
        
        Args:
            reason: Reason for shutdown
        """
        self._logger.info(f"Shutdown requested: {reason}")
        self._shutdown_requested = True
    
    def register_shutdown_handler(self, handler: Callable) -> None:
        """
        Register a handler to be called during shutdown.
        
        Args:
            handler: Function to call during shutdown
        """
        self._shutdown_handlers.append(handler)
    
    def shutdown(self) -> None:
        """
        Shutdown the kernel gracefully.
        
        This:
        1. Sets state to SHUTTING_DOWN
        2. Calls all shutdown handlers
        3. Stops all subsystems
        4. Cleans up resources
        5. Stops the event loop
        """
        if self._state == KernelState.SHUTDOWN:
            return
        
        self._state = KernelState.SHUTTING_DOWN
        self._logger.info("System shutting down...")
        
        # Call shutdown handlers
        for handler in self._shutdown_handlers:
            try:
                handler()
            except Exception as e:
                self._logger.error(f"Error in shutdown handler: {e}")
        
        # Stop subsystems
        self._registry.stop_all()
        self._registry.cleanup_all()
        
        # Stop event loop
        self._event_loop.stop()
        
        self._state = KernelState.SHUTDOWN
        self._logger.info(
            "System shutdown complete",
            context={'uptime': f"{self.uptime:.2f}s"}
        )
    
    def panic(self, message: str) -> None:
        """
        Trigger a kernel panic.
        
        This is for unrecoverable errors that require immediate halt.
        
        Args:
            message: Description of the panic condition
        """
        self._state = KernelState.PANIC
        self._logger.panic(f"KERNEL PANIC: {message}")
        
        # Attempt to dump state
        self._dump_state()
        
        # Halt
        self._event_loop.stop()
        raise KernelPanic(message)
    
    def _dump_state(self) -> None:
        """Dump kernel state for debugging."""
        self._logger.critical("=== KERNEL STATE DUMP ===")
        
        if self._process_manager:
            procs = self._process_manager.list_processes()
            self._logger.critical(f"Processes: {len(procs)}")
            for p in procs[:10]:  # First 10 processes
                self._logger.critical(f"  - PID {p['pid']}: {p['name']} ({p['state']})")
        
        if self._memory_manager:
            stats = self._memory_manager.get_stats()
            self._logger.critical(f"Memory: {stats}")
    
    def get_info(self) -> KernelInfo:
        """Get kernel information."""
        self._info.uptime = self.uptime
        self._info.state = self._state
        
        if self._process_manager:
            self._info.process_count = self._process_manager.process_count
        
        if self._memory_manager:
            stats = self._memory_manager.get_stats()
            self._info.memory_used = stats.get('used', 0)
            self._info.memory_total = stats.get('total', 0)
        
        return self._info
    
    # Subsystem accessors
    @property
    def process_manager(self):
        """Get the process manager."""
        return self._process_manager
    
    @property
    def memory_manager(self):
        """Get the memory manager."""
        return self._memory_manager
    
    @property
    def filesystem(self):
        """Get the virtual filesystem."""
        return self._filesystem
    
    @property
    def user_manager(self):
        """Get the user manager."""
        return self._user_manager
    
    @property
    def syscall_dispatcher(self):
        """Get the syscall dispatcher."""
        return self._syscall_dispatcher
    
    @property
    def security_manager(self):
        """Get the security manager."""
        return self._security_manager
    
    @property
    def ipc_manager(self):
        """Get the IPC manager."""
        return self._ipc_manager
    
    @property
    def monitoring(self):
        """Get the monitoring manager."""
        return self._monitoring


def get_kernel() -> Kernel:
    """Get the global kernel instance."""
    return Kernel()
