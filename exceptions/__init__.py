"""
PyOS Exception Hierarchy

This module defines a comprehensive exception hierarchy for the operating system.
All custom exceptions inherit from PyOSError as the base class, with specific
sub-categories for different subsystems.

Architecture:
    PyOSError (Base)
    ├── KernelException
    │   ├── KernelPanic
    │   ├── BootFailureError
    │   ├── SubsystemInitError
    │   └── ShutdownError
    ├── ProcessException
    │   ├── ProcessCreationError
    │   ├── ProcessTerminationError
    │   ├── ProcessNotFoundError
    │   ├── ContextSwitchError
    │   ├── ForkError
    │   ├── ExecError
    │   ├── ZombieProcessError
    │   └── ResourceLimitExceeded
    ├── MemoryException
    │   ├── MemoryAllocationError
    │   ├── MemoryDeallocationError
    │   ├── PageFaultError
    │   ├── OutOfMemoryError
    │   ├── MemoryProtectionError
    │   └── SegmentationFault
    ├── FileSystemException
    │   ├── FileNotFoundError
    │   ├── FileExistsError
    │   ├── PermissionDeniedError
    │   ├── DirectoryNotEmptyError
    │   ├── DiskFullError
    │   ├── PathResolutionError
    │   └── FileLockError
    ├── SecurityException
    │   ├── SecurityViolationError
    │   ├── AuthenticationError
    │   ├── AuthorizationError
    │   ├── SandboxViolationError
    │   └── PolicyViolationError
    ├── IPCException
    │   ├── PipeError
    │   ├── MessageQueueError
    │   └── SharedMemoryError
    └── SyscallException
        ├── InvalidSyscallError
        └── SyscallPermissionError
"""

from .kernel_exceptions import (
    KernelException,
    KernelPanic,
    BootFailureError,
    SubsystemInitError,
    ShutdownError,
)

from .process_exceptions import (
    ProcessException,
    ProcessCreationError,
    ProcessTerminationError,
    ProcessNotFoundError,
    ContextSwitchError,
    ForkError,
    ExecError,
    ZombieProcessError,
    ResourceLimitExceeded,
    SignalError,
)

from .memory_exceptions import (
    MemoryException,
    MemoryAllocationError,
    MemoryDeallocationError,
    PageFaultError,
    OutOfMemoryError,
    MemoryProtectionError,
    SegmentationFault,
)

from .fs_exceptions import (
    FileSystemException,
    FileNotFoundError,
    FileExistsError,
    PermissionDeniedError,
    DirectoryNotEmptyError,
    DiskFullError,
    PathResolutionError,
    FileLockError,
    NotAFileError,
    NotADirectoryError,
)

from .security_exceptions import (
    SecurityException,
    SecurityViolationError,
    AuthenticationError,
    AuthorizationError,
    SandboxViolationError,
    PolicyViolationError,
)

from .ipc_exceptions import (
    IPCException,
    PipeError,
    MessageQueueError,
    SharedMemoryError,
)

__all__ = [
    # Kernel exceptions
    "KernelException",
    "KernelPanic",
    "BootFailureError",
    "SubsystemInitError",
    "ShutdownError",
    # Process exceptions
    "ProcessException",
    "ProcessCreationError",
    "ProcessTerminationError",
    "ProcessNotFoundError",
    "ContextSwitchError",
    "ForkError",
    "ExecError",
    "ZombieProcessError",
    "ResourceLimitExceeded",
    "SignalError",
    # Memory exceptions
    "MemoryException",
    "MemoryAllocationError",
    "MemoryDeallocationError",
    "PageFaultError",
    "OutOfMemoryError",
    "MemoryProtectionError",
    "SegmentationFault",
    # Filesystem exceptions
    "FileSystemException",
    "FileNotFoundError",
    "FileExistsError",
    "PermissionDeniedError",
    "DirectoryNotEmptyError",
    "DiskFullError",
    "PathResolutionError",
    "FileLockError",
    "NotAFileError",
    "NotADirectoryError",
    # Security exceptions
    "SecurityException",
    "SecurityViolationError",
    "AuthenticationError",
    "AuthorizationError",
    "SandboxViolationError",
    "PolicyViolationError",
    # IPC exceptions
    "IPCException",
    "PipeError",
    "MessageQueueError",
    "SharedMemoryError",
]
