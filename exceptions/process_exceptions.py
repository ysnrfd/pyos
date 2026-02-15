"""
Process Exceptions

Exceptions related to process management, scheduling, and lifecycle.
These handle errors in process creation, termination, and state transitions.

Author: YSNRFD
Version: 1.0.0
"""

from typing import Optional, Any


class ProcessException(Exception):
    """
    Base exception for all process-related errors.
    
    This is the parent class for all exceptions that occur within
    the process management subsystem.
    
    Attributes:
        message: Human-readable error description
        pid: Process ID associated with the error (if applicable)
        error_code: Numeric error code for programmatic handling
    """
    
    def __init__(
        self,
        message: str,
        pid: Optional[int] = None,
        error_code: Optional[int] = None,
        context: Optional[dict[str, Any]] = None
    ) -> None:
        super().__init__(message)
        self.message = message
        self.pid = pid
        self.error_code = error_code or 2000
        self.context = context or {}
        if pid is not None:
            self.context["pid"] = pid
    
    def __str__(self) -> str:
        base = f"[Error {self.error_code}] {self.message}"
        if self.pid is not None:
            base = f"{base} (pid={self.pid})"
        return base


class ProcessCreationError(ProcessException):
    """
    Error creating a new process.
    
    This exception is raised when the system fails to create a new
    process. Common causes include:
    - PID exhaustion
    - Memory allocation failure
    - Resource limit exceeded
    - Invalid process parameters
    
    Example:
        >>> raise ProcessCreationError("No available PIDs", pid=None)
    """
    
    def __init__(
        self,
        message: str,
        parent_pid: Optional[int] = None,
        context: Optional[dict[str, Any]] = None
    ) -> None:
        ctx = context or {}
        if parent_pid is not None:
            ctx["parent_pid"] = parent_pid
        super().__init__(
            message=message,
            error_code=2001,
            context=ctx
        )
        self.parent_pid = parent_pid


class ProcessTerminationError(ProcessException):
    """
    Error terminating a process.
    
    This exception is raised when the system fails to properly
    terminate a process. This may occur during:
    - Kill signal handling
    - Resource cleanup
    - Zombie reaping
    
    Example:
        >>> raise ProcessTerminationError("Failed to cleanup resources", pid=42)
    """
    
    def __init__(
        self,
        message: str,
        pid: int,
        signal: Optional[int] = None,
        context: Optional[dict[str, Any]] = None
    ) -> None:
        ctx = context or {}
        if signal is not None:
            ctx["signal"] = signal
        super().__init__(
            message=message,
            pid=pid,
            error_code=2002,
            context=ctx
        )
        self.signal = signal


class ProcessNotFoundError(ProcessException):
    """
    The specified process does not exist.
    
    This exception is raised when attempting to operate on a
    process that doesn't exist or has already terminated.
    
    Example:
        >>> raise ProcessNotFoundError(42)
    """
    
    def __init__(
        self,
        pid: int,
        context: Optional[dict[str, Any]] = None
    ) -> None:
        super().__init__(
            message=f"Process {pid} not found",
            pid=pid,
            error_code=2003,
            context=context
        )


class ContextSwitchError(ProcessException):
    """
    Error during context switching.
    
    This exception indicates a failure during the process of
    saving one process's context and restoring another's.
    
    Example:
        >>> raise ContextSwitchError("Failed to save register state", pid=42)
    """
    
    def __init__(
        self,
        message: str,
        from_pid: Optional[int] = None,
        to_pid: Optional[int] = None,
        context: Optional[dict[str, Any]] = None
    ) -> None:
        ctx = context or {}
        if from_pid is not None:
            ctx["from_pid"] = from_pid
        if to_pid is not None:
            ctx["to_pid"] = to_pid
        super().__init__(
            message=message,
            pid=from_pid,
            error_code=2004,
            context=ctx
        )
        self.from_pid = from_pid
        self.to_pid = to_pid


class ForkError(ProcessException):
    """
    Error during fork() system call.
    
    This exception is raised when the fork() system call fails.
    Common causes include:
    - Memory allocation failure for child process
    - Process limit exceeded
    - PID exhaustion
    
    Example:
        >>> raise ForkError("Cannot allocate memory for child process", parent_pid=1)
    """
    
    def __init__(
        self,
        message: str,
        parent_pid: int,
        context: Optional[dict[str, Any]] = None
    ) -> None:
        super().__init__(
            message=message,
            pid=parent_pid,
            error_code=2005,
            context=context
        )
        self.parent_pid = parent_pid


class ExecError(ProcessException):
    """
    Error during exec() system call.
    
    This exception is raised when the exec() system call fails.
    Common causes include:
    - File not found
    - Permission denied
    - Invalid executable format
    - Memory allocation failure
    
    Example:
        >>> raise ExecError("File not found: /bin/program", pid=42)
    """
    
    def __init__(
        self,
        message: str,
        pid: int,
        path: Optional[str] = None,
        context: Optional[dict[str, Any]] = None
    ) -> None:
        ctx = context or {}
        if path:
            ctx["path"] = path
        super().__init__(
            message=message,
            pid=pid,
            error_code=2006,
            context=ctx
        )
        self.path = path


class ZombieProcessError(ProcessException):
    """
    Error related to zombie process handling.
    
    This exception is raised when there are issues with
    zombie processes, such as:
    - Too many zombies
    - Parent not reaping children
    - Zombie cleanup failure
    
    Example:
        >>> raise ZombieProcessError("Too many zombie processes", pid=42)
    """
    
    def __init__(
        self,
        message: str,
        pid: Optional[int] = None,
        zombie_count: Optional[int] = None,
        context: Optional[dict[str, Any]] = None
    ) -> None:
        ctx = context or {}
        if zombie_count is not None:
            ctx["zombie_count"] = zombie_count
        super().__init__(
            message=message,
            pid=pid,
            error_code=2007,
            context=ctx
        )
        self.zombie_count = zombie_count


class ResourceLimitExceeded(ProcessException):
    """
    Process resource limit exceeded.
    
    This exception is raised when a process attempts to exceed
    its allocated resource limits, such as:
    - CPU time limit
    - Memory limit
    - File descriptor limit
    - Process count limit
    
    Example:
        >>> raise ResourceLimitExceeded("Memory limit exceeded", pid=42, limit="512MB")
    """
    
    def __init__(
        self,
        message: str,
        pid: int,
        resource_type: Optional[str] = None,
        limit: Optional[Any] = None,
        context: Optional[dict[str, Any]] = None
    ) -> None:
        ctx = context or {}
        if resource_type:
            ctx["resource_type"] = resource_type
        if limit is not None:
            ctx["limit"] = limit
        super().__init__(
            message=message,
            pid=pid,
            error_code=2008,
            context=ctx
        )
        self.resource_type = resource_type
        self.limit = limit


class SignalError(ProcessException):
    """
    Error handling a signal.
    
    This exception is raised when there's an error in signal
    handling, such as:
    - Invalid signal number
    - Signal cannot be caught
    - Signal handler error
    
    Example:
        >>> raise SignalError("Invalid signal: 999", pid=42)
    """
    
    def __init__(
        self,
        message: str,
        pid: Optional[int] = None,
        signal: Optional[int] = None,
        context: Optional[dict[str, Any]] = None
    ) -> None:
        ctx = context or {}
        if signal is not None:
            ctx["signal"] = signal
        super().__init__(
            message=message,
            pid=pid,
            error_code=2009,
            context=ctx
        )
        self.signal = signal
