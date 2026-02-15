"""
Paging Module

Implements virtual memory paging including:
- Page table management
- Page allocation and deallocation
- Page fault handling
- Memory protection bits

Author: YSNRFD
Version: 1.0.0
"""

from dataclasses import dataclass, field
from enum import Enum, Flag, auto
from typing import Optional, Any, List
from collections import defaultdict

from pyos.logger import Logger, get_logger


class PageFlags(Flag):
    """Page table entry flags."""
    PRESENT = 1       # Page is in memory
    WRITABLE = 2      # Page can be written
    USER = 4          # User-mode access allowed
    ACCESSED = 8      # Page has been accessed
    DIRTY = 16        # Page has been written to
    EXECUTABLE = 32   # Page can be executed
    COPY_ON_WRITE = 64  # Copy-on-write flag


@dataclass
class Page:
    """A single memory page."""
    page_number: int
    frame_number: int
    flags: PageFlags = PageFlags(0)
    ref_count: int = 0
    
    def is_present(self) -> bool:
        return PageFlags.PRESENT in self.flags
    
    def is_writable(self) -> bool:
        return PageFlags.WRITABLE in self.flags
    
    def is_user_accessible(self) -> bool:
        return PageFlags.USER in self.flags
    
    def is_dirty(self) -> bool:
        return PageFlags.DIRTY in self.flags
    
    def set_present(self, present: bool = True) -> None:
        if present:
            self.flags |= PageFlags.PRESENT
        else:
            self.flags &= ~PageFlags.PRESENT
    
    def set_dirty(self, dirty: bool = True) -> None:
        if dirty:
            self.flags |= PageFlags.DIRTY
        else:
            self.flags &= ~PageFlags.DIRTY


@dataclass
class PageTableEntry:
    """Entry in a page table."""
    virtual_page: int
    physical_frame: int
    flags: PageFlags
    last_accessed: float = 0.0


class PageTable:
    """
    A page table for a single process.
    
    Maps virtual page numbers to physical frame numbers.
    Uses a two-level page table structure for efficiency.
    """
    
    def __init__(self, page_size: int = 4096):
        self._page_size = page_size
        self._entries: dict[int, PageTableEntry] = {}
        self._logger = get_logger('page_table')
    
    @property
    def page_size(self) -> int:
        return self._page_size
    
    def map_page(
        self,
        virtual_page: int,
        physical_frame: int,
        flags: PageFlags = PageFlags.PRESENT | PageFlags.WRITABLE | PageFlags.USER
    ) -> None:
        """Map a virtual page to a physical frame."""
        self._entries[virtual_page] = PageTableEntry(
            virtual_page=virtual_page,
            physical_frame=physical_frame,
            flags=flags
        )
        
        self._logger.debug(
            f"Mapped page",
            context={
                'virtual_page': virtual_page,
                'physical_frame': physical_frame,
                'flags': str(flags)
            }
        )
    
    def unmap_page(self, virtual_page: int) -> Optional[PageTableEntry]:
        """Unmap a virtual page."""
        return self._entries.pop(virtual_page, None)
    
    def get_entry(self, virtual_page: int) -> Optional[PageTableEntry]:
        """Get the page table entry for a virtual page."""
        return self._entries.get(virtual_page)
    
    def translate(self, virtual_page: int) -> Optional[int]:
        """Translate a virtual page to a physical frame."""
        entry = self._entries.get(virtual_page)
        if entry and PageFlags.PRESENT in entry.flags:
            return entry.physical_frame
        return None
    
    def update_flags(self, virtual_page: int, flags: PageFlags) -> bool:
        """Update flags for a page."""
        entry = self._entries.get(virtual_page)
        if entry:
            entry.flags = flags
            return True
        return False
    
    def get_all_pages(self) -> List[int]:
        """Get all mapped virtual page numbers."""
        return list(self._entries.keys())
    
    def get_stats(self) -> dict[str, Any]:
        """Get page table statistics."""
        present = sum(1 for e in self._entries.values() 
                     if PageFlags.PRESENT in e.flags)
        dirty = sum(1 for e in self._entries.values() 
                   if PageFlags.DIRTY in e.flags)
        
        return {
            'total_pages': len(self._entries),
            'present_pages': present,
            'dirty_pages': dirty,
            'memory_used': len(self._entries) * self._page_size
        }
    
    def clear(self) -> None:
        """Clear all mappings."""
        self._entries.clear()


class FrameAllocator:
    """
    Physical frame allocator.
    
    Manages allocation of physical memory frames using a bitmap.
    """
    
    def __init__(self, total_frames: int):
        self._total_frames = total_frames
        self._allocated: set[int] = set()
        self._next_frame = 0
        self._lock = None  # Will be set to threading.Lock on first use
    
    def _get_lock(self):
        """Get the lock, creating it if necessary."""
        import threading
        if self._lock is None:
            self._lock = threading.Lock()
        return self._lock
    
    def allocate(self) -> Optional[int]:
        """Allocate a physical frame."""
        with self._get_lock():
            if len(self._allocated) >= self._total_frames:
                return None
            
            # Find a free frame
            frame = self._next_frame
            attempts = 0
            
            while frame in self._allocated and attempts < self._total_frames:
                frame = (frame + 1) % self._total_frames
                attempts += 1
            
            if attempts >= self._total_frames:
                return None
            
            self._allocated.add(frame)
            self._next_frame = (frame + 1) % self._total_frames
            
            return frame
    
    def free(self, frame: int) -> bool:
        """Free a physical frame."""
        with self._get_lock():
            if frame in self._allocated:
                self._allocated.remove(frame)
                return True
            return False
    
    def is_allocated(self, frame: int) -> bool:
        """Check if a frame is allocated."""
        return frame in self._allocated
    
    @property
    def free_frames(self) -> int:
        """Get the number of free frames."""
        return self._total_frames - len(self._allocated)
    
    @property
    def used_frames(self) -> int:
        """Get the number of used frames."""
        return len(self._allocated)
    
    def get_stats(self) -> dict[str, int]:
        """Get allocator statistics."""
        return {
            'total_frames': self._total_frames,
            'used_frames': self.used_frames,
            'free_frames': self.free_frames
        }
