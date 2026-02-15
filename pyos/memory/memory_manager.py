"""
Memory Manager Module

Central memory management subsystem that:
- Manages physical memory
- Handles virtual memory for processes
- Provides memory allocation APIs
- Enforces memory limits

Author: YSNRFD
Version: 1.0.0
"""

import threading
from typing import Optional, Any

from .paging import PageTable, PageFlags, FrameAllocator
from .virtual_memory import AddressSpace, RegionType
from .allocator import BuddyAllocator, SlabAllocator
from pyos.core.registry import Subsystem, SubsystemState
from pyos.core.config_loader import get_config
from pyos.exceptions import (
    MemoryAllocationError,
    MemoryDeallocationError,
    OutOfMemoryError,
    MemoryProtectionError,
    SegmentationFault,
)
from pyos.logger import Logger, get_logger


class MemoryManager(Subsystem):
    """
    Memory Management Subsystem.
    
    Provides:
    - Physical memory management
    - Virtual memory for each process
    - Memory allocation/deallocation
    - Memory protection
    - Page fault handling
    
    Example:
        >>> mm = MemoryManager()
        >>> mm.initialize()
        >>> addr = mm.allocate(1024, pid=1)
    """
    
    def __init__(self):
        super().__init__('memory')
        self._total_memory: int = 0
        self._page_size: int = 0
        self._total_frames: int = 0
        
        self._frame_allocator: Optional[FrameAllocator] = None
        self._buddy_allocator: Optional[BuddyAllocator] = None
        self._slab_allocators: dict[str, SlabAllocator] = {}
        
        self._address_spaces: dict[int, AddressSpace] = {}
        self._process_memory: dict[int, int] = {}  # pid -> bytes allocated
        
        self._lock = threading.Lock()
    
    def initialize(self) -> None:
        """Initialize the memory manager."""
        self._logger.info("Initializing memory manager")
        
        config = get_config()
        
        self._total_memory = config.memory.total_memory
        self._page_size = config.memory.page_size
        self._total_frames = self._total_memory // self._page_size
        
        # Initialize frame allocator
        self._frame_allocator = FrameAllocator(self._total_frames)
        
        # Initialize buddy allocator for kernel memory
        kernel_memory = self._total_memory // 4  # Reserve 1/4 for kernel
        self._buddy_allocator = BuddyAllocator(kernel_memory)
        
        # Initialize slab allocators for common kernel objects
        self._slab_allocators = {
            'pcb': SlabAllocator(256),  # Process control blocks
            'inode': SlabAllocator(128),  # Inodes
            'file': SlabAllocator(64),  # File structures
        }
        
        # Create address space for kernel (PID 0)
        self.create_address_space(0)
        
        self.set_state(SubsystemState.INITIALIZED)
        self._logger.info(
            "Memory manager initialized",
            context={
                'total_memory': f"{self._total_memory // 1024 // 1024} MB",
                'page_size': f"{self._page_size} bytes",
                'total_frames': self._total_frames
            }
        )
    
    def start(self) -> None:
        """Start the memory manager."""
        self.set_state(SubsystemState.RUNNING)
        self._logger.info("Memory manager started")
    
    def stop(self) -> None:
        """Stop the memory manager."""
        self._logger.info("Stopping memory manager")
        self.set_state(SubsystemState.STOPPED)
    
    def cleanup(self) -> None:
        """Clean up memory manager resources."""
        self._address_spaces.clear()
        self._process_memory.clear()
    
    @property
    def total_memory(self) -> int:
        """Get total physical memory in bytes."""
        return self._total_memory
    
    @property
    def page_size(self) -> int:
        """Get the page size in bytes."""
        return self._page_size
    
    @property
    def free_memory(self) -> int:
        """Get free memory in bytes."""
        if self._frame_allocator:
            return self._frame_allocator.free_frames * self._page_size
        return 0
    
    @property
    def used_memory(self) -> int:
        """Get used memory in bytes."""
        return self._total_memory - self.free_memory
    
    def create_address_space(self, pid: int) -> AddressSpace:
        """
        Create a new address space for a process.
        
        Args:
            pid: Process ID
        
        Returns:
            The new AddressSpace
        """
        with self._lock:
            if pid in self._address_spaces:
                return self._address_spaces[pid]
            
            addr_space = AddressSpace(pid, self._page_size)
            self._address_spaces[pid] = addr_space
            self._process_memory[pid] = 0
            
            self._logger.debug(
                "Created address space",
                pid=pid
            )
            
            return addr_space
    
    def destroy_address_space(self, pid: int) -> None:
        """
        Destroy an address space.
        
        Args:
            pid: Process ID
        """
        with self._lock:
            addr_space = self._address_spaces.pop(pid, None)
            
            if addr_space:
                # Free all frames
                page_table = addr_space.page_table
                for page_num in page_table.get_all_pages():
                    entry = page_table.get_entry(page_num)
                    if entry:
                        self._frame_allocator.free(entry.physical_frame)
                
                addr_space.clear()
                self._process_memory.pop(pid, None)
                
                self._logger.debug(
                    "Destroyed address space",
                    pid=pid
                )
    
    def allocate(
        self,
        size: int,
        pid: int = 0,
        flags: PageFlags = PageFlags.PRESENT | PageFlags.WRITABLE | PageFlags.USER
    ) -> int:
        """
        Allocate memory for a process.
        
        Args:
            size: Number of bytes to allocate
            pid: Process ID (0 for kernel)
            flags: Memory protection flags
        
        Returns:
            Virtual address of allocated memory
        
        Raises:
            MemoryAllocationError: If allocation fails
            OutOfMemoryError: If system is out of memory
        """
        config = get_config()
        
        # Check process memory limit
        if pid != 0:
            current = self._process_memory.get(pid, 0)
            if current + size > config.memory.max_memory_per_process:
                raise MemoryAllocationError(
                    f"Process memory limit exceeded",
                    size=size
                )
        
        # Calculate pages needed
        pages_needed = (size + self._page_size - 1) // self._page_size
        
        with self._lock:
            # Check if enough physical memory
            if self._frame_allocator.free_frames < pages_needed:
                raise OutOfMemoryError(
                    requested=size,
                    available=self.free_memory
                )
            
            # Get address space
            addr_space = self._address_spaces.get(pid)
            if not addr_space:
                addr_space = self.create_address_space(pid)
            
            # Allocate region
            virtual_start = addr_space._heap_end
            region = addr_space.add_region(
                start=virtual_start,
                size=pages_needed * self._page_size,
                region_type=RegionType.HEAP,
                flags=flags,
                name="heap"
            )
            
            # Map pages
            for i in range(pages_needed):
                virtual_page = (virtual_start + i * self._page_size) // self._page_size
                
                frame = self._frame_allocator.allocate()
                if frame is None:
                    # Rollback
                    for j in range(i):
                        prev_page = (virtual_start + j * self._page_size) // self._page_size
                        prev_entry = addr_space.page_table.get_entry(prev_page)
                        if prev_entry:
                            self._frame_allocator.free(prev_entry.physical_frame)
                            addr_space.page_table.unmap_page(prev_page)
                    raise OutOfMemoryError("Unexpected out of memory")
                
                addr_space.page_table.map_page(virtual_page, frame, flags)
            
            # Update process memory usage
            actual_size = pages_needed * self._page_size
            self._process_memory[pid] = self._process_memory.get(pid, 0) + actual_size
            addr_space._heap_end = virtual_start + actual_size
            
            self._logger.debug(
                f"Allocated memory",
                pid=pid,
                context={
                    'address': hex(virtual_start),
                    'size': actual_size,
                    'pages': pages_needed
                }
            )
            
            return virtual_start
    
    def free(self, address: int, pid: int = 0) -> None:
        """
        Free allocated memory.
        
        Args:
            address: Virtual address to free
            pid: Process ID
        
        Raises:
            MemoryDeallocationError: If deallocation fails
        """
        with self._lock:
            addr_space = self._address_spaces.get(pid)
            if not addr_space:
                raise MemoryDeallocationError(
                    "Address space not found",
                    address=address
                )
            
            # Find the region
            region = addr_space.find_region(address)
            if not region:
                raise MemoryDeallocationError(
                    "Address not allocated",
                    address=address
                )
            
            # Unmap pages
            start_page = region.start // self._page_size
            num_pages = region.size // self._page_size
            
            for i in range(num_pages):
                page_num = start_page + i
                entry = addr_space.page_table.get_entry(page_num)
                
                if entry:
                    self._frame_allocator.free(entry.physical_frame)
                    addr_space.page_table.unmap_page(page_num)
            
            # Remove region
            addr_space.remove_region(region.start)
            
            # Update process memory
            self._process_memory[pid] = self._process_memory.get(pid, 0) - region.size
            
            self._logger.debug(
                f"Freed memory",
                pid=pid,
                context={'address': hex(address), 'size': region.size}
            )
    
    def protect(
        self,
        address: int,
        size: int,
        flags: PageFlags,
        pid: int = 0
    ) -> None:
        """
        Change memory protection.
        
        Args:
            address: Virtual address
            size: Size of region
            flags: New protection flags
            pid: Process ID
        
        Raises:
            MemoryProtectionError: If protection change fails
        """
        with self._lock:
            addr_space = self._address_spaces.get(pid)
            if not addr_space:
                raise MemoryProtectionError(
                    "Address space not found",
                    address=address
                )
            
            region = addr_space.find_region(address)
            if not region:
                raise MemoryProtectionError(
                    "Address not allocated",
                    address=address
                )
            
            region.flags = flags
            
            # Update page table entries
            start_page = address // self._page_size
            num_pages = (size + self._page_size - 1) // self._page_size
            
            for i in range(num_pages):
                addr_space.page_table.update_flags(start_page + i, flags)
            
            self._logger.debug(
                f"Changed memory protection",
                pid=pid,
                context={'address': hex(address), 'flags': str(flags)}
            )
    
    def translate(
        self,
        virtual_address: int,
        pid: int = 0
    ) -> Optional[int]:
        """
        Translate virtual address to physical address.
        
        Args:
            virtual_address: Virtual address
            pid: Process ID
        
        Returns:
            Physical address or None if not mapped
        """
        addr_space = self._address_spaces.get(pid)
        if not addr_space:
            return None
        
        page_num = virtual_address // self._page_size
        offset = virtual_address % self._page_size
        
        frame = addr_space.page_table.translate(page_num)
        if frame is None:
            return None
        
        return frame * self._page_size + offset
    
    def handle_page_fault(
        self,
        virtual_address: int,
        pid: int,
        access_type: str = "read"
    ) -> bool:
        """
        Handle a page fault.
        
        Args:
            virtual_address: Faulting address
            pid: Process ID
            access_type: "read", "write", or "execute"
        
        Returns:
            True if fault handled, False if segfault
        """
        addr_space = self._address_spaces.get(pid)
        if not addr_space:
            self._logger.warning(
                f"Page fault: no address space",
                pid=pid,
                context={'address': hex(virtual_address)}
            )
            return False
        
        region = addr_space.find_region(virtual_address)
        if not region:
            self._logger.warning(
                f"Page fault: no region",
                pid=pid,
                context={'address': hex(virtual_address)}
            )
            return False
        
        # Check permissions
        if access_type == "write" and PageFlags.WRITABLE not in region.flags:
            self._logger.warning(
                f"Page fault: write to read-only",
                pid=pid,
                context={'address': hex(virtual_address)}
            )
            return False
        
        # Page should be allocated, this shouldn't happen
        page_num = virtual_address // self._page_size
        entry = addr_space.page_table.get_entry(page_num)
        
        if entry is None:
            # Need to allocate a frame
            frame = self._frame_allocator.allocate()
            if frame is None:
                self._logger.error(f"Out of memory during page fault")
                return False
            
            addr_space.page_table.map_page(page_num, frame, region.flags)
            return True
        
        return True
    
    def allocate_kernel(self, size: int) -> Optional[int]:
        """
        Allocate kernel memory using buddy allocator.
        
        Args:
            size: Bytes to allocate
        
        Returns:
            Kernel virtual address
        """
        return self._buddy_allocator.allocate(size, pid=0)
    
    def free_kernel(self, address: int) -> bool:
        """Free kernel memory."""
        return self._buddy_allocator.free(address)
    
    def allocate_object(self, slab_name: str) -> Optional[int]:
        """Allocate from a slab allocator."""
        slab = self._slab_allocators.get(slab_name)
        if slab:
            return slab.allocate()
        return None
    
    def free_object(self, slab_name: str, index: int) -> bool:
        """Free to a slab allocator."""
        slab = self._slab_allocators.get(slab_name)
        if slab:
            return slab.free(index)
        return False
    
    def get_process_memory_usage(self, pid: int) -> int:
        """Get memory usage for a process."""
        return self._process_memory.get(pid, 0)
    
    def get_stats(self) -> dict[str, Any]:
        """Get memory manager statistics."""
        buddy_stats = self._buddy_allocator.get_stats() if self._buddy_allocator else {}
        
        return {
            'total': self._total_memory,
            'used': self.used_memory,
            'free': self.free_memory,
            'utilization': (self.used_memory / self._total_memory * 100) 
                         if self._total_memory > 0 else 0,
            'total_frames': self._total_frames,
            'free_frames': self._frame_allocator.free_frames 
                          if self._frame_allocator else 0,
            'address_spaces': len(self._address_spaces),
            'kernel_allocator': buddy_stats,
        }
    
    def get_process_stats(self, pid: int) -> Optional[dict[str, Any]]:
        """Get memory statistics for a process."""
        addr_space = self._address_spaces.get(pid)
        if not addr_space:
            return None
        
        return {
            'pid': pid,
            'total_allocated': self._process_memory.get(pid, 0),
            'regions': addr_space.get_layout(),
            'page_table': addr_space.page_table.get_stats()
        }
