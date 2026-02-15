"""
Process Control Block (PCB) Module

The PCB contains all information about a process:
- Process identification
- Process state
- CPU context
- Memory information
- Scheduling information
- Resource usage

Author: YSNRFD
Version: 1.0.0
"""

import time
from dataclasses import dataclass, field
from typing import Any, Optional, Callable, List
from collections import deque

from .states import ProcessState, ProcessFlag, Signal
from pyos.logger import Logger, get_logger


@dataclass
class CpuContext:
    """
    Simulated CPU context for a process.
    
    In a real OS, this would contain register values, program counter,
    stack pointer, etc. Here we simulate the essential information.
    """
    instruction_pointer: int = 0
    stack_pointer: int = 0
    flags: int = 0
    # Simulated general purpose registers
    registers: dict[int, int] = field(default_factory=dict)


@dataclass
class ProcessResources:
    """Resource usage and limits for a process."""
    # File descriptors
    open_files: dict[int, str] = field(default_factory=dict)
    next_fd: int = 3  # 0, 1, 2 reserved for stdin, stdout, stderr
    
    # Memory
    memory_allocated: int = 0
    memory_limit: int = 16 * 1024 * 1024  # 16 MB default
    
    # CPU time
    cpu_time: float = 0.0
    cpu_limit: float = 3600.0  # 1 hour default
    
    # Other resources
    open_pipes: List[int] = field(default_factory=list)
    message_queues: List[int] = field(default_factory=list)


@dataclass
class ProcessStats:
    """Statistics for a process."""
    # Timing
    start_time: float = field(default_factory=time.time)
    user_time: float = 0.0
    system_time: float = 0.0
    
    # Page faults
    minor_faults: int = 0
    major_faults: int = 0
    
    # Context switches
    voluntary_switches: int = 0
    involuntary_switches: int = 0
    
    # Signals
    signals_received: int = 0
    signals_delivered: int = 0


class ProcessControlBlock:
    """
    Process Control Block (PCB).
    
    The PCB is the kernel data structure that contains all information
    about a process. It is created when a process is created and
    deleted when the process terminates.
    
    Attributes:
        pid: Process ID
        parent_pid: Parent process ID
        name: Process name
        state: Current process state
        priority: Scheduling priority (lower = higher priority)
        context: CPU context for context switching
    
    Example:
        >>> pcb = ProcessControlBlock(pid=1, parent_pid=0, name="init")
        >>> pcb.state = ProcessState.READY
    """
    
    _pid_counter = 0
    _pid_lock = None  # Will be set to threading.Lock on first use
    
    def __init__(
        self,
        pid: int,
        parent_pid: int,
        name: str,
        uid: int = 0,
        gid: int = 0,
        priority: int = 20,
        command: Optional[str] = None
    ):
        # Identification
        self.pid = pid
        self.parent_pid = parent_pid
        self.name = name
        self.uid = uid
        self.gid = gid
        self.command = command or name
        
        # State
        self.state = ProcessState.NEW
        self.exit_code: Optional[int] = None
        
        # Scheduling
        self.priority = priority
        self.nice = 0
        self.time_slice = 100  # milliseconds
        self.time_remaining = self.time_slice
        
        # CPU Context
        self.context = CpuContext()
        
        # Process tree
        self.children: List[int] = []
        self.threads: List[int] = []
        
        # Resources
        self.resources = ProcessResources()
        
        # Statistics
        self.stats = ProcessStats()
        
        # Flags
        self.flags: set[ProcessFlag] = set()
        
        # Signal handling
        self.pending_signals: deque[Signal] = deque()
        self.signal_handlers: dict[Signal, Callable] = {}
        self.signal_mask: set[Signal] = set()
        
        # Working directory
        self.cwd = "/"
        
        # Environment
        self.environ: dict[str, str] = {}
        
        # User callback for execution (simulated)
        self._entry_point: Optional[Callable] = None
        self._entry_args: tuple = ()
        self._entry_kwargs: dict = field(default_factory=dict)
        
        # Logger
        self._logger = get_logger('pcb')
    
    @classmethod
    def _get_pid_lock(cls):
        """Get the PID lock, creating it if necessary."""
        import threading
        if cls._pid_lock is None:
            cls._pid_lock = threading.Lock()
        return cls._pid_lock
    
    @classmethod
    def generate_pid(cls) -> int:
        """Generate a new unique PID."""
        with cls._get_pid_lock():
            cls._pid_counter += 1
            # Skip PID 0 (idle) and 1 (init)
            if cls._pid_counter < 1:
                cls._pid_counter = 1
            return cls._pid_counter
    
    @classmethod
    def reset_pid_counter(cls) -> None:
        """Reset the PID counter (for testing)."""
        with cls._get_pid_lock():
            cls._pid_counter = 0
    
    def set_entry_point(
        self,
        func: Callable,
        args: tuple = (),
        kwargs: Optional[dict] = None
    ) -> None:
        """
        Set the entry point for the process.
        
        Args:
            func: Function to execute when process runs
            args: Positional arguments
            kwargs: Keyword arguments
        """
        self._entry_point = func
        self._entry_args = args
        self._entry_kwargs = kwargs or {}
    
    def add_child(self, child_pid: int) -> None:
        """Add a child process."""
        if child_pid not in self.children:
            self.children.append(child_pid)
    
    def remove_child(self, child_pid: int) -> None:
        """Remove a child process."""
        if child_pid in self.children:
            self.children.remove(child_pid)
    
    def allocate_fd(self, path: str) -> int:
        """
        Allocate a file descriptor.
        
        Args:
            path: Path of the file to associate with the FD
        
        Returns:
            The allocated file descriptor number
        """
        fd = self.resources.next_fd
        self.resources.open_files[fd] = path
        self.resources.next_fd += 1
        return fd
    
    def free_fd(self, fd: int) -> bool:
        """
        Free a file descriptor.
        
        Args:
            fd: File descriptor to free
        
        Returns:
            True if FD was freed, False if not found
        """
        if fd in self.resources.open_files:
            del self.resources.open_files[fd]
            return True
        return False
    
    def send_signal(self, signal: Signal) -> None:
        """Send a signal to this process."""
        if signal not in self.signal_mask:
            self.pending_signals.append(signal)
            self.stats.signals_received += 1
    
    def get_next_signal(self) -> Optional[Signal]:
        """Get the next pending signal."""
        if self.pending_signals:
            return self.pending_signals.popleft()
        return None
    
    def set_signal_handler(self, signal: Signal, handler: Callable) -> None:
        """Set a signal handler."""
        self.signal_handlers[signal] = handler
    
    def is_daemon(self) -> bool:
        """Check if this is a daemon process."""
        return ProcessFlag.DAEMON in self.flags
    
    def set_daemon(self, daemon: bool = True) -> None:
        """Set the daemon flag."""
        if daemon:
            self.flags.add(ProcessFlag.DAEMON)
        else:
            self.flags.discard(ProcessFlag.DAEMON)
    
    def update_cpu_time(self, delta: float) -> None:
        """Update CPU time usage."""
        self.stats.user_time += delta
        self.resources.cpu_time += delta
    
    def context_switch_in(self) -> None:
        """Called when this process is switched in."""
        self.stats.voluntary_switches += 1
    
    def context_switch_out(self) -> None:
        """Called when this process is switched out."""
        # Save context would happen here
        pass
    
    def to_dict(self) -> dict[str, Any]:
        """Convert PCB to a dictionary for display/monitoring."""
        return {
            'pid': self.pid,
            'ppid': self.parent_pid,
            'name': self.name,
            'state': self.state.name,
            'priority': self.priority,
            'nice': self.nice,
            'uid': self.uid,
            'gid': self.gid,
            'memory': self.resources.memory_allocated,
            'cpu_time': self.stats.user_time,
            'children': len(self.children),
            'open_files': len(self.resources.open_files),
            'cwd': self.cwd,
            'flags': [f.name for f in self.flags],
        }
    
    def __repr__(self) -> str:
        return (
            f"PCB(pid={self.pid}, name={self.name!r}, "
            f"state={self.state.name}, ppid={self.parent_pid})"
        )


# Type alias
PCB = ProcessControlBlock
