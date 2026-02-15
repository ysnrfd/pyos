"""
IPC Exceptions

Exceptions related to Inter-Process Communication mechanisms.
These handle errors in pipes, message queues, and shared memory.

Author: YSNRFD
Version: 1.0.0
"""

from typing import Optional, Any


class IPCException(Exception):
    """
    Base exception for all IPC-related errors.
    
    This is the parent class for all exceptions that occur within
    the IPC subsystem.
    
    Attributes:
        message: Human-readable error description
        error_code: Numeric error code for programmatic handling
    """
    
    def __init__(
        self,
        message: str,
        error_code: Optional[int] = None,
        context: Optional[dict[str, Any]] = None
    ) -> None:
        super().__init__(message)
        self.message = message
        self.error_code = error_code or 6000
        self.context = context or {}
    
    def __str__(self) -> str:
        return f"[Error {self.error_code}] {self.message}"


class PipeError(IPCException):
    """
    Error in pipe operations.
    
    This exception is raised when pipe operations fail due to:
    - Broken pipe (no reader)
    - Pipe buffer full
    - Invalid pipe descriptor
    
    Example:
        >>> raise PipeError("Broken pipe", pipe_id=1)
    """
    
    def __init__(
        self,
        message: str,
        pipe_id: Optional[int] = None,
        context: Optional[dict[str, Any]] = None
    ) -> None:
        ctx = context or {}
        if pipe_id is not None:
            ctx["pipe_id"] = pipe_id
        super().__init__(
            message=message,
            error_code=6001,
            context=ctx
        )
        self.pipe_id = pipe_id


class MessageQueueError(IPCException):
    """
    Error in message queue operations.
    
    This exception is raised when message queue operations fail due to:
    - Queue full
    - Queue deleted
    - Invalid message size
    - Permission denied
    
    Example:
        >>> raise MessageQueueError("Queue full", queue_id=1)
    """
    
    def __init__(
        self,
        message: str,
        queue_id: Optional[int] = None,
        context: Optional[dict[str, Any]] = None
    ) -> None:
        ctx = context or {}
        if queue_id is not None:
            ctx["queue_id"] = queue_id
        super().__init__(
            message=message,
            error_code=6002,
            context=ctx
        )
        self.queue_id = queue_id


class SharedMemoryError(IPCException):
    """
    Error in shared memory operations.
    
    This exception is raised when shared memory operations fail due to:
    - Segment not found
    - Size limit exceeded
    - Attachment limit exceeded
    - Permission denied
    
    Example:
        >>> raise SharedMemoryError("Cannot attach to segment", segment_id=1)
    """
    
    def __init__(
        self,
        message: str,
        segment_id: Optional[int] = None,
        context: Optional[dict[str, Any]] = None
    ) -> None:
        ctx = context or {}
        if segment_id is not None:
            ctx["segment_id"] = segment_id
        super().__init__(
            message=message,
            error_code=6003,
            context=ctx
        )
        self.segment_id = segment_id
