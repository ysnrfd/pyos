"""
Process Manager Module

Central process management subsystem that:
- Creates and destroys processes
- Manages process lifecycle
- Coordinates scheduling
- Handles signals
- Implements fork/exec

Author: YSNRFD
Version: 1.0.0
"""

import threading
import time
from collections import defaultdict
from typing import Optional, Callable, Any, List

from .pcb import ProcessControlBlock
from .states import ProcessState, ProcessFlag, Signal
from .scheduler import SchedulerAlgorithm, create_scheduler
from .context_switch import ContextSwitcher
from pyos.core.registry import Subsystem, SubsystemState
from pyos.core.config_loader import get_config
from pyos.exceptions import (
    ProcessCreationError,
    ProcessNotFoundError,
    ProcessTerminationError,
    ForkError,
    ExecError,
    ResourceLimitExceeded,
    ZombieProcessError,
)
from pyos.logger import Logger, get_logger


class ProcessManager(Subsystem):
    """
    Process Management Subsystem.
    
    Handles all process-related operations including:
    - Process creation and destruction
    - Process scheduling
    - Context switching
    - Signal handling
    - Resource management
    
    Example:
        >>> pm = ProcessManager()
        >>> pm.initialize()
        >>> pid = pm.create_process("myapp", entry_point=my_function)
    """
    
    def __init__(self):
        super().__init__('process_manager')
        self._processes: dict[int, ProcessControlBlock] = {}
        self._pid_tree: dict[int, list[int]] = defaultdict(list)
        self._scheduler: Optional[SchedulerAlgorithm] = None
        self._context_switcher: Optional[ContextSwitcher] = None
        self._next_pid = 2  # Start at 2 (1 is init)
        self._pid_lock = threading.Lock()
        self._zombie_list: List[int] = []
    
    def initialize(self) -> None:
        """Initialize the process manager."""
        self._logger.info("Initializing process manager")
        
        config = get_config()
        
        # Create scheduler based on config
        algorithm = config.scheduler.algorithm
        kwargs = {'quantum': config.scheduler.quantum}
        
        if algorithm == 'priority':
            kwargs['priority_levels'] = config.scheduler.priority_levels
        elif algorithm == 'mlfq':
            kwargs['num_queues'] = config.scheduler.priority_levels
        
        self._scheduler = create_scheduler(algorithm=algorithm, **kwargs)
        
        # Create context switcher
        self._context_switcher = ContextSwitcher()
        
        # Create init process (PID 1)
        self._create_init_process()
        
        self.set_state(SubsystemState.INITIALIZED)
        self._logger.info("Process manager initialized")
    
    def _create_init_process(self) -> None:
        """Create the init process (PID 1)."""
        init = ProcessControlBlock(
            pid=1,
            parent_pid=0,
            name="init",
            uid=0,
            gid=0,
            priority=0
        )
        init.state = ProcessState.RUNNING
        
        self._processes[1] = init
        self._pid_tree[0].append(1)
        
        self._logger.debug("Created init process", pid=1)
    
    def start(self) -> None:
        """Start the process manager."""
        self.set_state(SubsystemState.RUNNING)
        self._logger.info("Process manager started")
    
    def stop(self) -> None:
        """Stop the process manager."""
        self._logger.info("Stopping process manager")
        
        # Terminate all processes
        for pid in list(self._processes.keys()):
            if pid != 1:  # Don't terminate init yet
                try:
                    self.terminate_process(pid)
                except Exception as e:
                    self._logger.error(f"Error terminating process {pid}: {e}")
        
        self.set_state(SubsystemState.STOPPED)
    
    def cleanup(self) -> None:
        """Clean up process manager resources."""
        self._processes.clear()
        self._pid_tree.clear()
        self._zombie_list.clear()
    
    @property
    def process_count(self) -> int:
        """Get the number of active processes."""
        return len([p for p in self._processes.values()
                   if p.state != ProcessState.ZOMBIE])
    
    @property
    def current_pid(self) -> Optional[int]:
        """Get the currently running process PID."""
        if self._context_switcher:
            return self._context_switcher.get_current_pid()
        return None
    
    def _generate_pid(self) -> int:
        """Generate a new unique PID."""
        config = get_config()
        max_pid = config.process.max_pid
        
        with self._pid_lock:
            pid = self._next_pid
            attempts = 0
            
            while pid in self._processes and attempts < max_pid:
                pid = (pid % max_pid) + 1
                if pid == 1:
                    pid = 2  # Skip PID 1
                attempts += 1
            
            if attempts >= max_pid:
                raise ProcessCreationError("No available PIDs")
            
            self._next_pid = (pid % max_pid) + 1
            if self._next_pid == 1:
                self._next_pid = 2
            
            return pid
    
    def create_process(
        self,
        name: str,
        parent_pid: Optional[int] = None,
        uid: int = 0,
        gid: int = 0,
        priority: int = 20,
        command: Optional[str] = None,
        entry_point: Optional[Callable] = None,
        entry_args: tuple = (),
        daemon: bool = False
    ) -> int:
        """
        Create a new process.
        
        Args:
            name: Process name
            parent_pid: Parent process PID (default: current or init)
            uid: User ID
            gid: Group ID
            priority: Process priority
            command: Command string
            entry_point: Function to execute
            entry_args: Arguments for entry point
            daemon: Whether this is a daemon process
        
        Returns:
            PID of the new process
        
        Raises:
            ProcessCreationError: If process cannot be created
        """
        config = get_config()
        
        # Check process limit
        if self.process_count >= config.process.max_processes:
            raise ProcessCreationError("Maximum process count reached")
        
        # Determine parent
        if parent_pid is None:
            parent_pid = self.current_pid or 1
        
        # Verify parent exists
        if parent_pid not in self._processes:
            parent_pid = 1  # Default to init
        
        # Generate PID
        pid = self._generate_pid()
        
        # Create PCB
        pcb = ProcessControlBlock(
            pid=pid,
            parent_pid=parent_pid,
            name=name,
            uid=uid,
            gid=gid,
            priority=priority,
            command=command
        )
        
        # Set entry point
        if entry_point:
            pcb.set_entry_point(entry_point, entry_args)
        
        # Set daemon flag
        if daemon:
            pcb.set_daemon(True)
        
        # Add to process table
        self._processes[pid] = pcb
        self._pid_tree[parent_pid].append(pid)
        
        # Update parent's children list
        parent = self._processes.get(parent_pid)
        if parent:
            parent.add_child(pid)
        
        # Add to scheduler
        pcb.state = ProcessState.READY
        self._scheduler.add_process(pcb)
        
        self._logger.info(
            f"Created process '{name}'",
            pid=pid,
            context={'ppid': parent_pid, 'priority': priority}
        )
        
        return pid
    
    def terminate_process(
        self,
        pid: int,
        exit_code: int = 0,
        force: bool = False
    ) -> None:
        """
        Terminate a process.
        
        Args:
            pid: Process ID to terminate
            exit_code: Exit code for the process
            force: Force termination even if process is stopped
        
        Raises:
            ProcessNotFoundError: If process doesn't exist
            ProcessTerminationError: If termination fails
        """
        pcb = self._processes.get(pid)
        if not pcb:
            raise ProcessNotFoundError(pid)
        
        if pcb.state == ProcessState.ZOMBIE:
            return  # Already terminated
        
        self._logger.info(
            f"Terminating process '{pcb.name}'",
            pid=pid,
            context={'exit_code': exit_code}
        )
        
        # Terminate children first
        for child_pid in pcb.children[:]:
            try:
                self.terminate_process(child_pid, exit_code=1)
            except Exception:
                pass
        
        # Remove from scheduler
        self._scheduler.remove_process(pcb)
        
        # Update state
        pcb.state = ProcessState.TERMINATED
        pcb.exit_code = exit_code
        
        # Update parent
        parent = self._processes.get(pcb.parent_pid)
        if parent:
            parent.remove_child(pid)
        
        # Convert to zombie if parent hasn't reaped
        if parent and parent.state != ProcessState.ZOMBIE:
            pcb.state = ProcessState.ZOMBIE
            self._zombie_list.append(pid)
            
            # Send SIGCHLD to parent
            parent.send_signal(Signal.SIGCHLD)
        else:
            # No parent, can fully remove
            self._remove_process(pid)
    
    def _remove_process(self, pid: int) -> None:
        """Fully remove a process from the system."""
        pcb = self._processes.get(pid)
        if pcb:
            # Remove from parent's children
            parent = self._processes.get(pcb.parent_pid)
            if parent:
                parent.remove_child(pid)
            
            # Remove from pid tree
            if pid in self._pid_tree[pcb.parent_pid]:
                self._pid_tree[pcb.parent_pid].remove(pid)
            
            # Remove from process table
            del self._processes[pid]
            
            # Remove from zombie list if present
            if pid in self._zombie_list:
                self._zombie_list.remove(pid)
    
    def fork(self, parent_pid: Optional[int] = None) -> int:
        """
        Fork the current process.
        
        Creates a child process that is a copy of the parent.
        
        Args:
            parent_pid: PID of process to fork (default: current)
        
        Returns:
            Child PID
        
        Raises:
            ForkError: If fork fails
        """
        if parent_pid is None:
            parent_pid = self.current_pid or 1
        
        parent = self._processes.get(parent_pid)
        if not parent:
            raise ForkError("Parent process not found", parent_pid=parent_pid)
        
        try:
            # Create child with same attributes
            child_pid = self.create_process(
                name=parent.name,
                parent_pid=parent_pid,
                uid=parent.uid,
                gid=parent.gid,
                priority=parent.priority,
                command=parent.command,
                entry_point=parent._entry_point,
                entry_args=parent._entry_args
            )
            
            child = self._processes[child_pid]
            
            # Copy context
            self._context_switcher.fork_context(parent, child)
            
            # Copy resources
            child.cwd = parent.cwd
            child.environ = parent.environ.copy()
            child.signal_handlers = parent.signal_handlers.copy()
            
            self._logger.debug(
                f"Forked process",
                pid=parent_pid,
                context={'child_pid': child_pid}
            )
            
            return child_pid
            
        except Exception as e:
            raise ForkError(f"Fork failed: {e}", parent_pid=parent_pid)
    
    def exec(self, pid: int, name: str, entry_point: Callable) -> None:
        """
        Execute a new program in the process.
        
        Replaces the process's memory space with the new program.
        
        Args:
            pid: Process ID
            name: New process name
            entry_point: Entry point function
        
        Raises:
            ExecError: If exec fails
        """
        pcb = self._processes.get(pid)
        if not pcb:
            raise ExecError("Process not found", pid=pid)
        
        try:
            # Update process
            pcb.name = name
            pcb.set_entry_point(entry_point)
            
            # Reset context
            self._context_switcher.exec_context(pcb)
            
            # Reset resources (keep file descriptors)
            pcb.resources.memory_allocated = 0
            pcb.stats = type(pcb.stats)()
            
            self._logger.debug(
                f"Exec'd process",
                pid=pid,
                context={'new_name': name}
            )
            
        except Exception as e:
            raise ExecError(f"Exec failed: {e}", pid=pid, path=name)
    
    def get_process(self, pid: int) -> ProcessControlBlock:
        """
        Get a process by PID.
        
        Args:
            pid: Process ID
        
        Returns:
            ProcessControlBlock
        
        Raises:
            ProcessNotFoundError: If process doesn't exist
        """
        pcb = self._processes.get(pid)
        if not pcb:
            raise ProcessNotFoundError(pid)
        return pcb
    
    def list_processes(self) -> List[dict[str, Any]]:
        """List all processes as dictionaries."""
        return [pcb.to_dict() for pcb in self._processes.values()]
    
    def get_children(self, pid: int) -> List[int]:
        """Get the PIDs of a process's children."""
        return self._pid_tree.get(pid, [])
    
    def send_signal(self, pid: int, signal: Signal) -> None:
        """
        Send a signal to a process.
        
        Args:
            pid: Target process ID
            signal: Signal to send
        
        Raises:
            ProcessNotFoundError: If process doesn't exist
        """
        pcb = self.get_process(pid)
        pcb.send_signal(signal)
        
        self._logger.debug(
            f"Sent signal to process",
            pid=pid,
            context={'signal': signal.name}
        )
    
    def kill(self, pid: int, signal: Signal = Signal.SIGTERM) -> None:
        """
        Kill a process with a signal.
        
        Args:
            pid: Process ID
            signal: Signal to send (default: SIGTERM)
        """
        pcb = self.get_process(pid)
        
        # Handle special signals
        if signal == Signal.SIGKILL:
            self.terminate_process(pid, exit_code=-9)
        elif signal == Signal.SIGSTOP:
            pcb.state = ProcessState.STOPPED
            self._scheduler.remove_process(pcb)
        elif signal == Signal.SIGCONT:
            if pcb.state == ProcessState.STOPPED:
                pcb.state = ProcessState.READY
                self._scheduler.add_process(pcb)
        else:
            self.send_signal(pid, signal)
    
    def reap_zombies(self) -> List[int]:
        """
        Reap all zombie processes.
        
        Returns:
            List of reaped PIDs
        """
        reaped = []
        
        for pid in self._zombie_list[:]:
            pcb = self._processes.get(pid)
            if pcb and pcb.parent_pid:
                parent = self._processes.get(pcb.parent_pid)
                # Reap if parent is init or has already waited
                if pcb.parent_pid == 1 or parent is None:
                    self._remove_process(pid)
                    reaped.append(pid)
        
        return reaped
    
    def schedule(self) -> None:
        """
        Run the scheduler to select the next process.
        
        This is called by the timer interrupt handler.
        """
        current = self._context_switcher.current_process
        
        if current:
            # Check for time slice expiry
            current.time_remaining -= 1
            
            if current.time_remaining <= 0:
                # Time slice expired
                current.update_cpu_time(0.001)  # Simulated
                self._scheduler.time_slice_expired(current)
                
                # Get next process
                next_pcb = self._scheduler.get_next_process()
                if next_pcb and next_pcb != current:
                    self._context_switcher.switch(current, next_pcb)
    
    def tick(self) -> None:
        """
        Called periodically by the kernel timer.
        """
        # Process signals for current process
        current = self._context_switcher.current_process
        if current:
            signal = current.get_next_signal()
            if signal:
                self._handle_signal(current, signal)
        
        # Reap zombies
        if self._zombie_list:
            self.reap_zombies()
    
    def _handle_signal(
        self,
        pcb: ProcessControlBlock,
        signal: Signal
    ) -> None:
        """Handle a signal for a process."""
        from .states import SIGNAL_TERMINATE, SIGNAL_IGNORE, SIGNAL_STOP
        
        handler = pcb.signal_handlers.get(signal)
        
        if handler:
            # User-defined handler
            try:
                handler(signal)
            except Exception as e:
                self._logger.error(
                    f"Signal handler error",
                    pid=pcb.pid,
                    context={'signal': signal.name, 'error': str(e)}
                )
        elif signal in SIGNAL_TERMINATE:
            self.terminate_process(pcb.pid, exit_code=128 + signal.value)
        elif signal in SIGNAL_STOP:
            pcb.state = ProcessState.STOPPED
            self._scheduler.remove_process(pcb)
        # SIGNAL_IGNORE signals are simply dropped
    
    def get_stats(self) -> dict[str, Any]:
        """Get process manager statistics."""
        return {
            'total_processes': len(self._processes),
            'active_processes': self.process_count,
            'zombie_processes': len(self._zombie_list),
            'scheduler_queue_size': self._scheduler.count(),
            'context_switches': self._context_switcher.stats.total_switches,
            'current_pid': self.current_pid
        }
