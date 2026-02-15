"""
Security Exceptions

Exceptions related to security, authentication, and authorization.
These handle errors in access control, sandboxing, and policy enforcement.

Author: YSNRFD
Version: 1.0.0
"""

from typing import Optional, Any


class SecurityException(Exception):
    """
    Base exception for all security-related errors.
    
    This is the parent class for all exceptions that occur within
    the security subsystem.
    
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
        self.error_code = error_code or 5000
        self.context = context or {}
    
    def __str__(self) -> str:
        return f"[Error {self.error_code}] {self.message}"


class SecurityViolationError(SecurityException):
    """
    General security violation.
    
    This exception is raised when a security violation is detected
    that doesn't fit into other specific categories.
    
    Example:
        >>> raise SecurityViolationError("Suspicious activity detected")
    """
    
    def __init__(
        self,
        message: str,
        context: Optional[dict[str, Any]] = None
    ) -> None:
        super().__init__(
            message=message,
            error_code=5001,
            context=context
        )


class AuthenticationError(SecurityException):
    """
    Authentication failure.
    
    This exception is raised when authentication fails due to:
    - Invalid credentials
    - Unknown user
    - Account locked
    - Session expired
    
    Example:
        >>> raise AuthenticationError("Invalid password")
    """
    
    def __init__(
        self,
        message: str = "Authentication failed",
        username: Optional[str] = None,
        context: Optional[dict[str, Any]] = None
    ) -> None:
        ctx = context or {}
        if username:
            ctx["username"] = username
        super().__init__(
            message=message,
            error_code=5002,
            context=ctx
        )
        self.username = username


class AuthorizationError(SecurityException):
    """
    Authorization failure.
    
    This exception is raised when a user is authenticated but
    doesn't have permission to perform the requested operation.
    
    Example:
        >>> raise AuthorizationError("User cannot access resource")
    """
    
    def __init__(
        self,
        message: str = "Access denied",
        uid: Optional[int] = None,
        resource: Optional[str] = None,
        context: Optional[dict[str, Any]] = None
    ) -> None:
        ctx = context or {}
        if uid is not None:
            ctx["uid"] = uid
        if resource:
            ctx["resource"] = resource
        super().__init__(
            message=message,
            error_code=5003,
            context=ctx
        )
        self.uid = uid
        self.resource = resource


class SandboxViolationError(SecurityException):
    """
    Sandbox boundary violation.
    
    This exception is raised when a process attempts to exceed
    its sandbox restrictions:
    - Accessing files outside allowed paths
    - Executing forbidden operations
    - Accessing network (simulated)
    
    Example:
        >>> raise SandboxViolationError("Process attempted to escape sandbox", pid=42)
    """
    
    def __init__(
        self,
        message: str,
        pid: Optional[int] = None,
        violation_type: Optional[str] = None,
        context: Optional[dict[str, Any]] = None
    ) -> None:
        ctx = context or {}
        if pid is not None:
            ctx["pid"] = pid
        if violation_type:
            ctx["violation_type"] = violation_type
        super().__init__(
            message=message,
            error_code=5004,
            context=ctx
        )
        self.pid = pid
        self.violation_type = violation_type


class PolicyViolationError(SecurityException):
    """
    Security policy violation.
    
    This exception is raised when an action violates the system's
    security policy rules.
    
    Example:
        >>> raise PolicyViolationError("Action violates security policy", policy="no-root-login")
    """
    
    def __init__(
        self,
        message: str,
        policy: Optional[str] = None,
        context: Optional[dict[str, Any]] = None
    ) -> None:
        ctx = context or {}
        if policy:
            ctx["policy"] = policy
        super().__init__(
            message=message,
            error_code=5005,
            context=ctx
        )
        self.policy = policy
