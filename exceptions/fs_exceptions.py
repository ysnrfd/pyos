"""
Filesystem Exceptions

Exceptions related to file system operations, VFS, and file handling.
These handle errors in file operations, permissions, and path resolution.

Author: YSNRFD
Version: 1.0.0
"""

from typing import Optional, Any


class FileSystemException(Exception):
    """
    Base exception for all filesystem-related errors.
    
    This is the parent class for all exceptions that occur within
    the filesystem subsystem.
    
    Attributes:
        message: Human-readable error description
        path: File path associated with the error (if applicable)
        error_code: Numeric error code for programmatic handling
    """
    
    def __init__(
        self,
        message: str,
        path: Optional[str] = None,
        error_code: Optional[int] = None,
        context: Optional[dict[str, Any]] = None
    ) -> None:
        super().__init__(message)
        self.message = message
        self.path = path
        self.error_code = error_code or 4000
        self.context = context or {}
        if path:
            self.context["path"] = path
    
    def __str__(self) -> str:
        base = f"[Error {self.error_code}] {self.message}"
        if self.path:
            base = f"{base} (path={self.path})"
        return base


class FileNotFoundError(FileSystemException):
    """
    The specified file does not exist.
    
    This exception is raised when attempting to access a file
    that doesn't exist in the filesystem.
    
    Example:
        >>> raise FileNotFoundError("/path/to/file")
    """
    
    def __init__(
        self,
        path: str,
        context: Optional[dict[str, Any]] = None
    ) -> None:
        super().__init__(
            message=f"File not found: {path}",
            path=path,
            error_code=4001,
            context=context
        )


class FileExistsError(FileSystemException):
    """
    The specified file already exists.
    
    This exception is raised when attempting to create a file
    that already exists and the operation doesn't allow overwriting.
    
    Example:
        >>> raise FileExistsError("/path/to/file")
    """
    
    def __init__(
        self,
        path: str,
        context: Optional[dict[str, Any]] = None
    ) -> None:
        super().__init__(
            message=f"File already exists: {path}",
            path=path,
            error_code=4002,
            context=context
        )


class PermissionDeniedError(FileSystemException):
    """
    Permission denied for the operation.
    
    This exception is raised when a user attempts to perform an
    operation for which they don't have the necessary permissions.
    
    Example:
        >>> raise PermissionDeniedError("/root/file", operation="write")
    """
    
    def __init__(
        self,
        path: str,
        operation: Optional[str] = None,
        uid: Optional[int] = None,
        context: Optional[dict[str, Any]] = None
    ) -> None:
        ctx = context or {}
        if operation:
            ctx["operation"] = operation
        if uid is not None:
            ctx["uid"] = uid
        super().__init__(
            message=f"Permission denied: {path}",
            path=path,
            error_code=4003,
            context=ctx
        )
        self.operation = operation
        self.uid = uid


class DirectoryNotEmptyError(FileSystemException):
    """
    Directory is not empty.
    
    This exception is raised when attempting to remove a directory
    that still contains files or subdirectories.
    
    Example:
        >>> raise DirectoryNotEmptyError("/path/to/dir")
    """
    
    def __init__(
        self,
        path: str,
        context: Optional[dict[str, Any]] = None
    ) -> None:
        super().__init__(
            message=f"Directory not empty: {path}",
            path=path,
            error_code=4004,
            context=context
        )


class DiskFullError(FileSystemException):
    """
    No space left on device.
    
    This exception is raised when attempting to write data but
    there's no space left on the virtual filesystem.
    
    Example:
        >>> raise DiskFullError(requested=1024, available=0)
    """
    
    def __init__(
        self,
        message: str = "No space left on device",
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
            error_code=4005,
            context=ctx
        )
        self.requested = requested
        self.available = available


class PathResolutionError(FileSystemException):
    """
    Error resolving path.
    
    This exception is raised when the system cannot resolve a
    filesystem path. Common causes include:
    - Component does not exist
    - Component is not a directory
    - Symlink loop
    - Permission denied during traversal
    
    Example:
        >>> raise PathResolutionError("/invalid/path", component="invalid")
    """
    
    def __init__(
        self,
        path: str,
        component: Optional[str] = None,
        reason: Optional[str] = None,
        context: Optional[dict[str, Any]] = None
    ) -> None:
        ctx = context or {}
        if component:
            ctx["component"] = component
        if reason:
            ctx["reason"] = reason
        super().__init__(
            message=f"Path resolution failed: {path}",
            path=path,
            error_code=4006,
            context=ctx
        )
        self.component = component
        self.reason = reason


class FileLockError(FileSystemException):
    """
    Error acquiring file lock.
    
    This exception is raised when a file lock cannot be acquired
    because another process holds a conflicting lock.
    
    Example:
        >>> raise FileLockError("/path/to/file", lock_type="write")
    """
    
    def __init__(
        self,
        path: str,
        lock_type: Optional[str] = None,
        held_by: Optional[int] = None,
        context: Optional[dict[str, Any]] = None
    ) -> None:
        ctx = context or {}
        if lock_type:
            ctx["lock_type"] = lock_type
        if held_by is not None:
            ctx["held_by_pid"] = held_by
        super().__init__(
            message=f"File lock error: {path}",
            path=path,
            error_code=4007,
            context=ctx
        )
        self.lock_type = lock_type
        self.held_by = held_by


class NotAFileError(FileSystemException):
    """
    Path is not a regular file.
    
    This exception is raised when a file operation is attempted
    on a path that is not a regular file (e.g., a directory).
    
    Example:
        >>> raise NotAFileError("/path/to/directory")
    """
    
    def __init__(
        self,
        path: str,
        actual_type: Optional[str] = None,
        context: Optional[dict[str, Any]] = None
    ) -> None:
        ctx = context or {}
        if actual_type:
            ctx["actual_type"] = actual_type
        super().__init__(
            message=f"Not a file: {path}",
            path=path,
            error_code=4008,
            context=ctx
        )
        self.actual_type = actual_type


class NotADirectoryError(FileSystemException):
    """
    Path is not a directory.
    
    This exception is raised when a directory operation is attempted
    on a path that is not a directory.
    
    Example:
        >>> raise NotADirectoryError("/path/to/file")
    """
    
    def __init__(
        self,
        path: str,
        context: Optional[dict[str, Any]] = None
    ) -> None:
        super().__init__(
            message=f"Not a directory: {path}",
            path=path,
            error_code=4009,
            context=context
        )
