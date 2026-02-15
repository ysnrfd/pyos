"""
Virtual Memory Module

Implements virtual memory management including:
- Address space management
- Memory regions
- Memory mapping

Author: YSNRFD
Version: 1.0.0
"""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional, Any, List
import struct

from .paging import PageTable, PageFlags
from pyos.logger import Logger, get_logger


class RegionType(Enum):
    """Types of memory regions."""
    CODE = auto()
    DATA = auto()
    HEAP = auto()
    STACK = auto()
    SHARED = auto()
    MAPPED = auto()


@dataclass
class MemoryRegion:
    """A contiguous region of virtual memory."""
    start: int
    end: int
    region_type: RegionType
    flags: PageFlags
    name: str = ""
    
    @property
    def size(self) -> int:
        return self.end - self.start
    
    def contains(self, address: int) -> bool:
        return self.start <= address < self.end
    
    def overlaps(self, other: 'MemoryRegion') -> bool:
        return self.start < other.end and other.start < self.end


class AddressSpace:
    """
    Virtual address space for a process.
    
    Manages the virtual memory layout including:
    - Code segment
    - Data segment
    - Heap
    - Stack
    - Memory-mapped regions
    """
    
    # Typical memory layout constants
    CODE_START = 0x00400000    # 4 MB - Code starts here
    DATA_START = 0x10000000    # 256 MB - Data segment
    HEAP_START = 0x20000000    # 512 MB - Heap
    STACK_START = 0x7FFF0000   # Near 2 GB - Stack (grows down)
    
    def __init__(self, pid: int, page_size: int = 4096):
        self._pid = pid
        self._page_size = page_size
        self._page_table = PageTable(page_size)
        self._regions: List[MemoryRegion] = []
        self._heap_end = self.HEAP_START
        self._stack_end = self.STACK_START
        self._logger = get_logger('address_space')
    
    @property
    def pid(self) -> int:
        return self._pid
    
    @property
    def page_table(self) -> PageTable:
        return self._page_table
    
    @property
    def total_size(self) -> int:
        """Total allocated memory size."""
        return sum(r.size for r in self._regions)
    
    def add_region(
        self,
        start: int,
        size: int,
        region_type: RegionType,
        flags: PageFlags,
        name: str = ""
    ) -> MemoryRegion:
        """
        Add a memory region to the address space.
        
        Args:
            start: Starting virtual address
            size: Size of the region
            region_type: Type of the region
            flags: Protection flags
            name: Optional name for the region
        
        Returns:
            The created MemoryRegion
        """
        end = start + size
        
        # Check for overlaps
        for region in self._regions:
            if region.overlaps(MemoryRegion(start, end, region_type, flags)):
                raise ValueError(f"Region overlaps with existing region")
        
        region = MemoryRegion(
            start=start,
            end=end,
            region_type=region_type,
            flags=flags,
            name=name
        )
        
        self._regions.append(region)
        self._regions.sort(key=lambda r: r.start)
        
        self._logger.debug(
            f"Added memory region",
            context={
                'pid': self._pid,
                'start': hex(start),
                'size': size,
                'type': region_type.name
            }
        )
        
        return region
    
    def remove_region(self, start: int) -> Optional[MemoryRegion]:
        """Remove a memory region by its start address."""
        for i, region in enumerate(self._regions):
            if region.start == start:
                removed = self._regions.pop(i)
                self._logger.debug(
                    f"Removed memory region",
                    context={'pid': self._pid, 'start': hex(start)}
                )
                return removed
        return None
    
    def find_region(self, address: int) -> Optional[MemoryRegion]:
        """Find the region containing an address."""
        for region in self._regions:
            if region.contains(address):
                return region
        return None
    
    def grow_heap(self, increment: int) -> int:
        """
        Grow the heap (like brk/sbrk).
        
        Args:
            increment: Bytes to add to heap
        
        Returns:
            The previous heap end address
        """
        old_end = self._heap_end
        new_end = self._heap_end + increment
        
        if increment > 0:
            # Add region for new heap space
            self.add_region(
                start=old_end,
                size=increment,
                region_type=RegionType.HEAP,
                flags=PageFlags.PRESENT | PageFlags.WRITABLE | PageFlags.USER,
                name="heap"
            )
        
        self._heap_end = new_end
        return old_end
    
    def get_stack_pointer(self) -> int:
        """Get the current stack pointer."""
        return self._stack_end
    
    def grow_stack(self, size: int) -> None:
        """Grow the stack (typically grows downward)."""
        self._stack_end -= size
        self.add_region(
            start=self._stack_end,
            size=size,
            region_type=RegionType.STACK,
            flags=PageFlags.PRESENT | PageFlags.WRITABLE | PageFlags.USER,
            name="stack"
        )
    
    def get_layout(self) -> List[dict[str, Any]]:
        """Get the memory layout as a list of dictionaries."""
        return [
            {
                'start': hex(r.start),
                'end': hex(r.end),
                'size': r.size,
                'type': r.region_type.name,
                'name': r.name,
                'flags': str(r.flags)
            }
            for r in self._regions
        ]
    
    def clear(self) -> None:
        """Clear all regions and page table."""
        self._regions.clear()
        self._page_table.clear()
        self._heap_end = self.HEAP_START
        self._stack_end = self.STACK_START
