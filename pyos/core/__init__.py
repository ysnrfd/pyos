"""
PyOS Core Module

Core kernel components including:
- Bootloader
- Kernel
- Event Loop
- Subsystem Registry
- Configuration Loader
"""

from .bootloader import Bootloader, BootStage, BootResult, boot_system
from .kernel import Kernel, KernelState, KernelInfo, get_kernel
from .event_loop import EventLoop, Event, EventType, EventPriority, Interrupt, InterruptType
from .registry import (
    SubsystemRegistry,
    Subsystem,
    SubsystemState,
    SubsystemPriority,
    get_registry
)
from .config_loader import ConfigLoader, Config, get_config

__all__ = [
    # Bootloader
    'Bootloader',
    'BootStage',
    'BootResult',
    'boot_system',
    # Kernel
    'Kernel',
    'KernelState',
    'KernelInfo',
    'get_kernel',
    # Event Loop
    'EventLoop',
    'Event',
    'EventType',
    'EventPriority',
    'Interrupt',
    'InterruptType',
    # Registry
    'SubsystemRegistry',
    'Subsystem',
    'SubsystemState',
    'SubsystemPriority',
    'get_registry',
    # Config
    'ConfigLoader',
    'Config',
    'get_config',
]
