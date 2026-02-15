"""
Kernel Exceptions

Exceptions related to kernel operations, boot process, and subsystem management.
These represent critical failures that may require system restart.

Author: YSNRFD
Version: 1.0.0
"""

from typing import Optional, Any


class KernelException(Exception):
    """
    Base exception for all kernel-related errors.
    
    This is the parent class for all exceptions that occur within
    the kernel subsystem. It provides common functionality for
    error reporting and recovery suggestions.
    
    Attributes:
        message: Human-readable error description
        error_code: Numeric error code for programmatic handling
        recoverable: Whether the error can be recovered from
        context: Additional context about the error
    
    Example:
        >>> raise KernelException("Kernel subsystem failure", error_code=1001)
    """
    
    def __init__(
        self,
        message: str,
        error_code: Optional[int] = None,
        recoverable: bool = False,
        context: Optional[dict[str, Any]] = None
    ) -> None:
        super().__init__(message)
        self.message = message
        self.error_code = error_code or 0
        self.recoverable = recoverable
        self.context = context or {}
    
    def __str__(self) -> str:
        base = f"[Error {self.error_code}] {self.message}"
        if self.context:
            context_str = ", ".join(f"{k}={v}" for k, v in self.context.items())
            base = f"{base} ({context_str})"
        return base
    
    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"message={self.message!r}, "
            f"error_code={self.error_code}, "
            f"recoverable={self.recoverable})"
        )


class KernelPanic(KernelException):
    """
    Critical kernel failure requiring immediate system halt.
    
    A kernel panic represents an unrecoverable error in the kernel
    that makes continued operation impossible or dangerous.
    This is the most severe error in the system.
    
    The system should:
    1. Log all relevant state information
    2. Attempt to sync filesystems if possible
    3. Halt all processing
    4. Display error to user
    
    Example:
        >>> raise KernelPanic("Unrecoverable memory corruption detected")
    """
    
    def __init__(
        self,
        message: str,
        context: Optional[dict[str, Any]] = None
    ) -> None:
        super().__init__(
            message=message,
            error_code=9999,
            recoverable=False,
            context=context
        )
        self.panic_time: Optional[float] = None
    
    def get_dump_info(self) -> dict[str, Any]:
        """Get information for kernel panic dump."""
        return {
            "message": self.message,
            "error_code": self.error_code,
            "context": self.context,
            "panic_time": self.panic_time,
        }


class BootFailureError(KernelException):
    """
    Error during system boot process.
    
    This exception indicates that the system failed to initialize
    properly during the boot sequence. It may be recoverable if
    the failure occurred in a non-essential subsystem.
    
    Common causes:
    - Configuration file errors
    - Required resource unavailable
    - Hardware detection failure (simulated)
    - Dependency initialization failure
    
    Example:
        >>> raise BootFailureError("Failed to initialize memory subsystem")
    """
    
    def __init__(
        self,
        message: str,
        subsystem: Optional[str] = None,
        context: Optional[dict[str, Any]] = None
    ) -> None:
        ctx = context or {}
        if subsystem:
            ctx["subsystem"] = subsystem
        super().__init__(
            message=message,
            error_code=1001,
            recoverable=True,
            context=ctx
        )
        self.subsystem = subsystem


class SubsystemInitError(KernelException):
    """
    Error initializing a specific kernel subsystem.
    
    This exception is raised when a kernel subsystem fails to
    initialize properly. Depending on the subsystem's criticality,
    this may be recoverable or may trigger a kernel panic.
    
    Example:
        >>> raise SubsystemInitError(
        ...     "Process Manager", 
        ...     "Failed to allocate PID bitmap"
        ... )
    """
    
    def __init__(
        self,
        subsystem_name: str,
        reason: str,
        critical: bool = False,
        context: Optional[dict[str, Any]] = None
    ) -> None:
        self.subsystem_name = subsystem_name
        self.reason = reason
        self.critical = critical
        
        ctx = context or {}
        ctx.update({
            "subsystem": subsystem_name,
            "reason": reason,
            "critical": critical,
        })
        
        super().__init__(
            message=f"Failed to initialize {subsystem_name}: {reason}",
            error_code=1002,
            recoverable=not critical,
            context=ctx
        )


class ShutdownError(KernelException):
    """
    Error during system shutdown process.
    
    This exception indicates that something went wrong while
    attempting to shut down the system gracefully. Depending
    on the severity, the system may need to force a halt.
    
    Example:
        >>> raise ShutdownError("Failed to unmount filesystem")
    """
    
    def __init__(
        self,
        message: str,
        phase: Optional[str] = None,
        context: Optional[dict[str, Any]] = None
    ) -> None:
        ctx = context or {}
        if phase:
            ctx["shutdown_phase"] = phase
        super().__init__(
            message=message,
            error_code=1003,
            recoverable=True,
            context=ctx
        )
        self.phase = phase
