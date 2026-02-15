"""
Process States Module

Defines the lifecycle states for processes in PyOS.

Author: YSNRFD
Version: 1.0.0
"""

from enum import Enum, auto
from typing import Optional


class ProcessState(Enum):
    """
    Process lifecycle states.
    
    State transitions:
        NEW -> READY: Process created and ready to run
        READY -> RUNNING: Scheduler selects process
        RUNNING -> READY: Preempted or yielded
        RUNNING -> WAITING: Blocked on I/O or resource
        WAITING -> READY: Resource available
        RUNNING -> TERMINATED: Process completed
        TERMINATED -> ZOMBIE: Process waiting for parent to reap
        ZOMBIE -> (removed): Parent reaps the process
    """
    
    NEW = auto()
    """Process is being created."""
    
    READY = auto()
    """Process is ready to run but waiting for CPU."""
    
    RUNNING = auto()
    """Process is currently executing."""
    
    WAITING = auto()
    """Process is blocked waiting for an event."""
    
    TERMINATED = auto()
    """Process has finished execution."""
    
    ZOMBIE = auto()
    """Process has terminated but not yet reaped by parent."""
    
    STOPPED = auto()
    """Process is stopped (e.g., by a signal)."""


class ProcessFlag(Enum):
    """Process flags and attributes."""
    RUNNING = auto()       # Normal process
    DAEMON = auto()        # Daemon process
    SESSION_LEADER = auto() # Session leader
    GROUP_LEADER = auto()  # Process group leader
    TRACED = auto()        # Being traced by ptrace
    KTHREAD = auto()       # Kernel thread


class Signal(Enum):
    """Standard UNIX signals."""
    SIGHUP = 1      # Hangup
    SIGINT = 2      # Interrupt
    SIGQUIT = 3     # Quit
    SIGILL = 4      # Illegal instruction
    SIGTRAP = 5     # Trap
    SIGABRT = 6     # Abort
    SIGBUS = 7      # Bus error
    SIGFPE = 8      # Floating point exception
    SIGKILL = 9     # Kill (cannot be caught)
    SIGUSR1 = 10    # User-defined signal 1
    SIGSEGV = 11    # Segmentation fault
    SIGUSR2 = 12    # User-defined signal 2
    SIGPIPE = 13    # Broken pipe
    SIGALRM = 14    # Alarm clock
    SIGTERM = 15    # Termination
    SIGSTKFLT = 16  # Stack fault
    SIGCHLD = 17    # Child status changed
    SIGCONT = 18    # Continue
    SIGSTOP = 19    # Stop (cannot be caught)
    SIGTSTP = 20    # Stop from tty
    SIGTTIN = 21    # Tty input for background process
    SIGTTOU = 22    # Tty output for background process


# Default signal dispositions
SIGNAL_TERMINATE = {Signal.SIGHUP, Signal.SIGINT, Signal.SIGKILL, 
                    Signal.SIGTERM, Signal.SIGUSR1, Signal.SIGUSR2}
SIGNAL_IGNORE = {Signal.SIGCHLD, Signal.SIGCONT}
SIGNAL_STOP = {Signal.SIGSTOP, Signal.SIGTSTP, Signal.SIGTTIN, Signal.SIGTTOU}
SIGNAL_CORE = {Signal.SIGQUIT, Signal.SIGILL, Signal.SIGABRT, 
               Signal.SIGBUS, Signal.SIGFPE, Signal.SIGSEGV, Signal.SIGTRAP}
