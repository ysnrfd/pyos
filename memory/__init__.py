"""
PyOS Memory Management Module

Provides comprehensive memory management including:
- Physical memory management
- Virtual memory and paging
- Memory allocation
- Memory protection
"""

from .paging import (
    PageFlags,
    Page,
    PageTable,
    PageTableEntry,
    FrameAllocator
)
from .virtual_memory import (
    RegionType,
    MemoryRegion,
    AddressSpace
)
from .allocator import (
    MemoryBlock,
    BuddyAllocator,
    SlabAllocator
)
from .memory_manager import MemoryManager

__all__ = [
    # Paging
    'PageFlags',
    'Page',
    'PageTable',
    'PageTableEntry',
    'FrameAllocator',
    # Virtual Memory
    'RegionType',
    'MemoryRegion',
    'AddressSpace',
    # Allocator
    'MemoryBlock',
    'BuddyAllocator',
    'SlabAllocator',
    # Manager
    'MemoryManager',
]
