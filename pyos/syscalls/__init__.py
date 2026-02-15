"""
PyOS System Call Interface Module

Provides system call dispatching:
- System call table
- Syscall dispatcher
- Syscall results
"""

from .syscall_table import SyscallNumber, SYSCALL_NAMES
from .dispatcher import SyscallDispatcher, SyscallResult

__all__ = [
    'SyscallNumber',
    'SYSCALL_NAMES',
    'SyscallDispatcher',
    'SyscallResult',
]
