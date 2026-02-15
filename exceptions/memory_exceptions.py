"""
Memory Exceptions

Exceptions related to memory management, allocation, and protection.
These handle errors in virtual memory, paging, and memory protection.

Author: YSNRFD
Version: 1.0.0
"""

from typing import Optional, Any


class MemoryException(Exception):
    """
    Base exception for all memory-related errors.
    
    This is the parent class for all exceptions that occur within
    the memory management subsystem.
    
    Attributes:
        message: Human-readable error description
        address: Memory address associated with the error (if applicable)
        error_code: Numeric error code for programmatic handling
    """
    
    def __init__(
        self,
        message: str,
        address: Optional[int] = None,
        size: Optional[int] = None,
        error_code: Optional[int] = None,
        context: Optional[dict[str, Any]] = None
    ) -> None:
        super().__init__(message)
        self.message = message
        self.address = address
        self.size = size
        self.error_code = error_code or 3000
        self.context = context or {}
        if address is not None:
            self.context["address"] = hex(address)
        if size is not None:
            self.context["size"] = size
    
    def __str__(self) -> str:
        base = f"[Error {self.error_code}] {self.message}"
        if self.address is not None:
            base = f"{base} (address=0x{self.address:x})"
        return base


class MemoryAllocationError(MemoryException):
    """
    Error allocating memory.
    
    This exception is raised when the system fails to allocate
    memory. Common causes include:
    - Out of memory
    - Fragmentation
    - Invalid size request
    - Pool exhausted
    
    Example:
        >>> raise MemoryAllocationError("Failed to allocate 1024 bytes", size=1024)
    """
    
    def __init__(
        self,
        message: str,
        size: Optional[int] = None,
        context: Optional[dict[str, Any]] = None
    ) -> None:
        super().__init__(
            message=message,
            size=size,
            error_code=3001,
            context=context
        )


class MemoryDeallocationError(MemoryException):
    """
    Error deallocating memory.
    
    This exception is raised when the system fails to deallocate
    memory. Common causes include:
    - Double free
    - Invalid pointer
    - Memory corruption
    
    Example:
        >>> raise MemoryDeallocationError("Double free detected", address=0x1000)
    """
    
    def __init__(
        self,
        message: str,
        address: Optional[int] = None,
        context: Optional[dict[str, Any]] = None
    ) -> None:
        super().__init__(
            message=message,
            address=address,
            error_code=3002,
            context=context
        )


class PageFaultError(MemoryException):
    """
    Page fault error.
    
    This exception is raised when a page fault occurs that cannot
    be handled. Types include:
    - Hard page fault (page not in memory)
    - Protection fault
    - Copy-on-write fault
    
    Example:
        >>> raise PageFaultError("Page not present", address=0x7fff0000)
    """
    
    def __init__(
        self,
        message: str,
        address: int,
        page_number: Optional[int] = None,
        fault_type: Optional[str] = None,
        context: Optional[dict[str, Any]] = None
    ) -> None:
        ctx = context or {}
        if page_number is not None:
            ctx["page_number"] = page_number
        if fault_type:
            ctx["fault_type"] = fault_type
        super().__init__(
            message=message,
            address=address,
            error_code=3003,
            context=ctx
        )
        self.page_number = page_number
        self.fault_type = fault_type


class OutOfMemoryError(MemoryException):
    """
    System is out of memory.
    
    This exception is raised when the system has exhausted all
    available memory and cannot satisfy allocation requests.
    This is a critical error that may require process termination.
    
    Example:
        >>> raise OutOfMemoryError("System out of memory", requested=4096)
    """
    
    def __init__(
        self,
        message: str = "Out of memory",
        requested: Optional[int] = None,
        available: Optional[int] = None,
        context: Optional[dict[str, Any]] = None
    ) -> None:
        ctx = context or {}
        if requested is not None:
            ctx["requested"] = requested
        if available is not None:
            ctx["available"] = available
        super().__init__(
            message=message,
            error_code=3004,
            context=ctx
        )
        self.requested = requested
        self.available = available


class MemoryProtectionError(MemoryException):
    """
    Memory protection violation.
    
    This exception is raised when a process attempts to access
    memory in a way that violates protection rules:
    - Writing to read-only memory
    - Executing non-executable memory
    - Accessing kernel memory from user mode
    
    Example:
        >>> raise MemoryProtectionError("Write to read-only page", address=0x1000)
    """
    
    def __init__(
        self,
        message: str,
        address: int,
        access_type: Optional[str] = None,
        context: Optional[dict[str, Any]] = None
    ) -> None:
        ctx = context or {}
        if access_type:
            ctx["access_type"] = access_type
        super().__init__(
            message=message,
            address=address,
            error_code=3005,
            context=ctx
        )
        self.access_type = access_type


class SegmentationFault(MemoryException):
    """
    Segmentation fault.
    
    This exception is raised when a process attempts to access
    memory that it doesn't have permission to access or that
    doesn't exist.
    
    Example:
        >>> raise SegmentationFault("Invalid memory access", address=0xdeadbeef)
    """
    
    def __init__(
        self,
        message: str = "Segmentation fault",
        address: Optional[int] = None,
        pid: Optional[int] = None,
        context: Optional[dict[str, Any]] = None
    ) -> None:
        ctx = context or {}
        if pid is not None:
            ctx["pid"] = pid
        super().__init__(
            message=message,
            address=address,
            error_code=3006,
            context=ctx
        )
        self.pid = pid
