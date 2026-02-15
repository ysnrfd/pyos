"""
Security Manager Module

Implements security features:
- Process sandboxing
- Resource limits
- Access control
- Policy enforcement

Author: YSNRFD
Version: 1.0.0
"""

import threading
from dataclasses import dataclass, field
from typing import Optional, Any, Callable, List
from enum import Enum

from pyos.core.registry import Subsystem, SubsystemState
from pyos.core.config_loader import get_config
from pyos.exceptions import (
    SecurityViolationError,
    SandboxViolationError,
    PolicyViolationError,
    ResourceLimitExceeded,
)
from pyos.logger import Logger, get_logger


class ResourceType(Enum):
    """Types of resources that can be limited."""
    CPU_TIME = "cpu_time"
    MEMORY = "memory"
    FILE_DESCRIPTORS = "file_descriptors"
    PROCESSES = "processes"
    FILES = "files"
    PIPES = "pipes"


@dataclass
class ResourceLimits:
    """Resource limits for a process or user."""
    cpu_time: int = 3600  # seconds
    memory: int = 16 * 1024 * 1024  # bytes
    file_descriptors: int = 1024
    processes: int = 256
    files: int = 1024
    pipes: int = 256


@dataclass
class Sandbox:
    """
    A sandbox for restricting process capabilities.
    
    Sandboxes can:
    - Restrict filesystem access
    - Limit network access (simulated)
    - Limit resource usage
    - Restrict syscalls
    """
    sandbox_id: int
    pid: int
    allowed_paths: List[str] = field(default_factory=lambda: ['/tmp'])
    denied_paths: List[str] = field(default_factory=list)
    allowed_syscalls: set[int] = field(default_factory=set)
    denied_syscalls: set[int] = field(default_factory=set)
    limits: ResourceLimits = field(default_factory=ResourceLimits)
    enabled: bool = True


@dataclass
class Policy:
    """A security policy rule."""
    name: str
    description: str
    check: Callable[[dict], bool]
    action: str = "deny"  # "deny", "allow", "log"


class SecurityManager(Subsystem):
    """
    Security Management Subsystem.
    
    Provides:
    - Process sandboxing
    - Resource limits
    - Access control
    - Policy enforcement
    
    Example:
        >>> security = SecurityManager()
        >>> security.create_sandbox(pid=42, limits=ResourceLimits(memory=1024*1024))
    """
    
    def __init__(self):
        super().__init__('security')
        self._sandboxes: dict[int, Sandbox] = {}
        self._policies: List[Policy] = []
        self._audit_log: List[dict[str, Any]] = []
        self._next_sandbox_id = 1
        self._lock = threading.Lock()
    
    def initialize(self) -> None:
        """Initialize the security manager."""
        config = get_config()
        
        self._enable_sandbox = config.security.enable_sandbox
        self._default_limits = ResourceLimits(
            cpu_time=config.security.max_cpu_time_per_process,
            file_descriptors=config.security.max_file_descriptors
        )
        
        # Add default policies
        self._add_default_policies()
        
        self.set_state(SubsystemState.INITIALIZED)
        self._logger.info("Security manager initialized")
    
    def _add_default_policies(self) -> None:
        """Add default security policies."""
        # Prevent non-root from accessing /root
        self._policies.append(Policy(
            name="protect_root_home",
            description="Prevent non-root access to /root",
            check=lambda ctx: not (
                ctx.get('path', '').startswith('/root') and 
                ctx.get('uid', 0) != 0
            ),
            action="deny"
        ))
        
        # Prevent killing processes owned by others
        self._policies.append(Policy(
            name="protect_processes",
            description="Prevent killing processes owned by other users",
            check=lambda ctx: (
                ctx.get('uid', 0) == 0 or
                ctx.get('target_uid') == ctx.get('uid')
            ),
            action="deny"
        ))
    
    def start(self) -> None:
        """Start the security manager."""
        self.set_state(SubsystemState.RUNNING)
    
    def stop(self) -> None:
        """Stop the security manager."""
        self.set_state(SubsystemState.STOPPED)
    
    def cleanup(self) -> None:
        """Clean up resources."""
        self._sandboxes.clear()
        self._audit_log.clear()
    
    def create_sandbox(
        self,
        pid: int,
        limits: Optional[ResourceLimits] = None,
        allowed_paths: Optional[list[str]] = None
    ) -> Sandbox:
        """
        Create a sandbox for a process.
        
        Args:
            pid: Process ID
            limits: Resource limits
            allowed_paths: Paths the process can access
        
        Returns:
            Created Sandbox
        """
        with self._lock:
            sandbox_id = self._next_sandbox_id
            self._next_sandbox_id += 1
            
            sandbox = Sandbox(
                sandbox_id=sandbox_id,
                pid=pid,
                limits=limits or self._default_limits,
                allowed_paths=allowed_paths or ['/tmp', '/home']
            )
            
            self._sandboxes[pid] = sandbox
            
            self._logger.debug(
                f"Created sandbox",
                pid=pid,
                context={'sandbox_id': sandbox_id}
            )
            
            return sandbox
    
    def get_sandbox(self, pid: int) -> Optional[Sandbox]:
        """Get a process's sandbox."""
        return self._sandboxes.get(pid)
    
    def remove_sandbox(self, pid: int) -> bool:
        """Remove a sandbox."""
        if pid in self._sandboxes:
            del self._sandboxes[pid]
            return True
        return False
    
    def check_file_access(
        self,
        pid: int,
        path: str,
        access_type: str
    ) -> bool:
        """
        Check if a process can access a file.
        
        Args:
            pid: Process ID
            path: File path
            access_type: "read", "write", or "execute"
        
        Returns:
            True if access is allowed
        """
        sandbox = self._sandboxes.get(pid)
        
        if sandbox is None or not sandbox.enabled:
            return True
        
        # Check denied paths
        for denied in sandbox.denied_paths:
            if path.startswith(denied):
                self._audit(
                    pid=pid,
                    action="file_access",
                    resource=path,
                    result="denied",
                    reason="Path in denied list"
                )
                raise SandboxViolationError(
                    f"Access to {path} is denied",
                    pid=pid,
                    violation_type="file_access"
                )
        
        # Check allowed paths
        for allowed in sandbox.allowed_paths:
            if path.startswith(allowed):
                self._audit(
                    pid=pid,
                    action="file_access",
                    resource=path,
                    result="allowed"
                )
                return True
        
        # Default deny
        self._audit(
            pid=pid,
            action="file_access",
            resource=path,
            result="denied",
            reason="Path not in allowed list"
        )
        
        raise SandboxViolationError(
            f"Access to {path} is not allowed",
            pid=pid,
            violation_type="file_access"
        )
    
    def check_syscall(
        self,
        pid: int,
        syscall_number: int
    ) -> bool:
        """
        Check if a process can use a syscall.
        
        Args:
            pid: Process ID
            syscall_number: System call number
        
        Returns:
            True if syscall is allowed
        """
        sandbox = self._sandboxes.get(pid)
        
        if sandbox is None or not sandbox.enabled:
            return True
        
        if syscall_number in sandbox.denied_syscalls:
            self._audit(
                pid=pid,
                action="syscall",
                resource=str(syscall_number),
                result="denied",
                reason="Syscall in denied list"
            )
            raise SandboxViolationError(
                f"Syscall {syscall_number} is denied",
                pid=pid,
                violation_type="syscall"
            )
        
        if sandbox.allowed_syscalls and syscall_number not in sandbox.allowed_syscalls:
            self._audit(
                pid=pid,
                action="syscall",
                resource=str(syscall_number),
                result="denied",
                reason="Syscall not in allowed list"
            )
            raise SandboxViolationError(
                f"Syscall {syscall_number} is not allowed",
                pid=pid,
                violation_type="syscall"
            )
        
        return True
    
    def check_resource_limit(
        self,
        pid: int,
        resource_type: ResourceType,
        current: int,
        requested: int
    ) -> bool:
        """
        Check if a resource limit would be exceeded.
        
        Args:
            pid: Process ID
            resource_type: Type of resource
            current: Current usage
            requested: Additional requested
        
        Returns:
            True if within limits
        """
        sandbox = self._sandboxes.get(pid)
        
        if sandbox is None:
            return True
        
        limits = sandbox.limits
        
        limit_map = {
            ResourceType.CPU_TIME: limits.cpu_time,
            ResourceType.MEMORY: limits.memory,
            ResourceType.FILE_DESCRIPTORS: limits.file_descriptors,
            ResourceType.PROCESSES: limits.processes,
            ResourceType.FILES: limits.files,
            ResourceType.PIPES: limits.pipes,
        }
        
        limit = limit_map.get(resource_type)
        
        if limit is not None and current + requested > limit:
            self._audit(
                pid=pid,
                action="resource",
                resource=resource_type.value,
                result="denied",
                reason=f"Limit exceeded: {current + requested} > {limit}"
            )
            raise ResourceLimitExceeded(
                f"{resource_type.value} limit exceeded",
                pid=pid,
                resource_type=resource_type.value,
                limit=limit
            )
        
        return True
    
    def check_policy(
        self,
        context: dict[str, Any]
    ) -> bool:
        """
        Check all policies against a context.
        
        Args:
            context: Context for policy evaluation
        
        Returns:
            True if all policies pass
        """
        for policy in self._policies:
            if not policy.check(context):
                if policy.action == "deny":
                    raise PolicyViolationError(
                        f"Policy '{policy.name}' violation",
                        policy=policy.name
                    )
        
        return True
    
    def add_policy(self, policy: Policy) -> None:
        """Add a security policy."""
        self._policies.append(policy)
    
    def remove_policy(self, name: str) -> bool:
        """Remove a policy by name."""
        for i, policy in enumerate(self._policies):
            if policy.name == name:
                self._policies.pop(i)
                return True
        return False
    
    def _audit(
        self,
        pid: int,
        action: str,
        resource: str,
        result: str,
        reason: str = ""
    ) -> None:
        """Log a security event."""
        import time
        
        event = {
            'timestamp': time.time(),
            'pid': pid,
            'action': action,
            'resource': resource,
            'result': result,
            'reason': reason
        }
        
        self._audit_log.append(event)
        
        # Keep only last 1000 events
        if len(self._audit_log) > 1000:
            self._audit_log = self._audit_log[-1000:]
    
    def get_audit_log(self, limit: int = 100) -> List[dict]:
        """Get recent audit log entries."""
        return self._audit_log[-limit:]
    
    def get_stats(self) -> dict[str, Any]:
        """Get security statistics."""
        return {
            'active_sandboxes': len(self._sandboxes),
            'policies': len(self._policies),
            'audit_entries': len(self._audit_log),
        }
