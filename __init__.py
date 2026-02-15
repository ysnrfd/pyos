"""
PyOS - A UNIX-inspired Operating System Simulation

This package provides a complete, production-grade operating system simulation
implemented entirely in Python 3.10+ using only the standard library.
"""

__version__ = "1.0.0"
__author__ = "YSNRFD"

# Import main components for convenience
from .core.kernel import Kernel, get_kernel
from .core.bootloader import Bootloader, boot_system
from .shell.shell import Shell, create_shell

__all__ = [
    'Kernel',
    'get_kernel',
    'Bootloader',
    'boot_system',
    'Shell',
    'create_shell',
]
