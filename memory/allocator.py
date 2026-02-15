"""
Memory Allocator Module

Implements memory allocation strategies:
- Buddy allocator for large blocks
- Slab allocator for small objects
- Memory pool management

Author: YSNRFD
Version: 1.0.0
"""

from dataclasses import dataclass
from typing import Optional, Any, List
import threading

from pyos.logger import Logger, get_logger


@dataclass
class MemoryBlock:
    """A block of allocated memory."""
    address: int
    size: int
    free: bool = True
    pid: Optional[int] = None
    
    def can_split(self, min_size: int) -> bool:
        return self.size >= min_size * 2
    
    def split(self) -> tuple['MemoryBlock', 'MemoryBlock']:
        """Split this block into two equal halves."""
        half_size = self.size // 2
        return (
            MemoryBlock(self.address, half_size, self.free, self.pid),
            MemoryBlock(self.address + half_size, half_size, self.free, self.pid)
        )


class BuddyAllocator:
    """
    Buddy system memory allocator.
    
    Allocates memory in powers of 2, allowing efficient coalescing
    of free blocks. Good for reducing external fragmentation.
    
    Algorithm:
    1. Round up request size to nearest power of 2
    2. Find a free block of that size or larger
    3. Split larger blocks until we have the right size
    4. Allocate the block
    """
    
    def __init__(self, total_size: int, min_block_size: int = 16):
        """
        Initialize the buddy allocator.
        
        Args:
            total_size: Total memory to manage (must be power of 2)
            min_block_size: Minimum allocation size
        """
        self._total_size = total_size
        self._min_block_size = min_block_size
        self._max_order = self._size_to_order(total_size)
        
        # Free lists for each order
        self._free_lists: dict[int, list[MemoryBlock]] = {
            order: [] for order in range(self._max_order + 1)
        }
        
        # All allocated blocks
        self._allocated: dict[int, MemoryBlock] = {}
        
        # Start with one large free block
        self._free_lists[self._max_order].append(
            MemoryBlock(0, total_size, free=True)
        )
        
        self._lock = threading.Lock()
        self._logger = get_logger('buddy_allocator')
    
    def _size_to_order(self, size: int) -> int:
        """Convert a size to its order (log2)."""
        order = 0
        while (1 << order) < size:
            order += 1
        return order
    
    def _order_to_size(self, order: int) -> int:
        """Convert an order to a size."""
        return 1 << order
    
    def allocate(self, size: int, pid: Optional[int] = None) -> Optional[int]:
        """
        Allocate memory.
        
        Args:
            size: Number of bytes to allocate
            pid: Optional PID for tracking
        
        Returns:
            Address of allocated block, or None if allocation failed
        """
        # Round up to minimum block size
        if size < self._min_block_size:
            size = self._min_block_size
        
        # Round up to power of 2
        order = self._size_to_order(size)
        
        with self._lock:
            # Find a free block of appropriate size
            block = self._find_free_block(order)
            
            if block is None:
                self._logger.warning(
                    f"Allocation failed",
                    context={'size': size, 'order': order}
                )
                return None
            
            block.free = False
            block.pid = pid
            self._allocated[block.address] = block
            
            self._logger.debug(
                f"Allocated block",
                context={
                    'address': hex(block.address),
                    'size': block.size,
                    'pid': pid
                }
            )
            
            return block.address
    
    def _find_free_block(self, order: int) -> Optional[MemoryBlock]:
        """Find a free block of the given order, splitting if necessary."""
        if order > self._max_order:
            return None
        
        # Check if we have a free block at this order
        if self._free_lists[order]:
            return self._free_lists[order].pop(0)
        
        # Try to split a larger block
        for higher_order in range(order + 1, self._max_order + 1):
            if self._free_lists[higher_order]:
                # Split down to our order
                block = self._free_lists[higher_order].pop(0)
                
                for o in range(higher_order - 1, order - 1, -1):
                    left, right = block.split()
                    self._free_lists[o].append(right)
                    block = left
                
                return block
        
        return None
    
    def free(self, address: int) -> bool:
        """
        Free allocated memory.
        
        Args:
            address: Address returned by allocate()
        
        Returns:
            True if freed successfully, False if not found
        """
        with self._lock:
            block = self._allocated.pop(address, None)
            
            if block is None:
                return False
            
            block.free = True
            block.pid = None
            
            # Try to coalesce with buddy
            self._coalesce(block)
            
            self._logger.debug(
                f"Freed block",
                context={'address': hex(address), 'size': block.size}
            )
            
            return True
    
    def _coalesce(self, block: MemoryBlock) -> None:
        """Coalesce free blocks with their buddies."""
        order = self._size_to_order(block.size)
        
        while order < self._max_order:
            # Find buddy address
            buddy_address = block.address ^ block.size
            buddy = None
            
            # Find buddy in free list
            for i, free_block in enumerate(self._free_lists[order]):
                if free_block.address == buddy_address:
                    buddy = self._free_lists[order].pop(i)
                    break
            
            if buddy is None:
                # No buddy to coalesce with
                self._free_lists[order].append(block)
                return
            
            # Merge with buddy
            block = MemoryBlock(
                min(block.address, buddy.address),
                block.size * 2,
                free=True
            )
            order += 1
        
        # Reached max order
        self._free_lists[order].append(block)
    
    def get_stats(self) -> dict[str, Any]:
        """Get allocator statistics."""
        total_free = sum(
            sum(b.size for b in blocks)
            for blocks in self._free_lists.values()
        )
        
        return {
            'total_size': self._total_size,
            'allocated_size': self._total_size - total_free,
            'free_size': total_free,
            'allocated_blocks': len(self._allocated),
            'fragmentation': self._calculate_fragmentation()
        }
    
    def _calculate_fragmentation(self) -> float:
        """Calculate external fragmentation percentage."""
        total_free = sum(
            sum(b.size for b in blocks)
            for blocks in self._free_lists.values()
        )
        
        if total_free == 0:
            return 0.0
        
        # Count free blocks
        free_blocks = sum(len(blocks) for blocks in self._free_lists.values())
        
        # Average free block size
        avg_free = total_free / free_blocks if free_blocks > 0 else 0
        
        # Fragmentation = 1 - (largest_free / total_free)
        largest_free = 0
        for blocks in self._free_lists.values():
            for block in blocks:
                if block.size > largest_free:
                    largest_free = block.size
        
        if total_free == 0:
            return 0.0
        
        return (1 - largest_free / total_free) * 100


class SlabAllocator:
    """
    Slab allocator for small, fixed-size objects.
    
    Reduces fragmentation for frequently allocated objects
    like process control blocks, inodes, etc.
    """
    
    def __init__(self, object_size: int, slab_size: int = 4096):
        """
        Initialize a slab allocator.
        
        Args:
            object_size: Size of objects in this slab
            slab_size: Size of each slab (page)
        """
        self._object_size = object_size
        self._slab_size = slab_size
        self._objects_per_slab = slab_size // object_size
        
        self._slabs: List[bytearray] = []
        self._free_objects: List[int] = []  # Object indices
        self._used_count = 0
        
        self._lock = threading.Lock()
        self._logger = get_logger('slab_allocator')
        
        # Allocate initial slab
        self._allocate_slab()
    
    def _allocate_slab(self) -> None:
        """Allocate a new slab."""
        slab = bytearray(self._slab_size)
        self._slabs.append(slab)
        
        # Add all objects in this slab to free list
        slab_index = len(self._slabs) - 1
        base_index = slab_index * self._objects_per_slab
        
        for i in range(self._objects_per_slab):
            self._free_objects.append(base_index + i)
    
    def allocate(self) -> Optional[int]:
        """
        Allocate an object.
        
        Returns:
            Object index (used as handle)
        """
        with self._lock:
            if not self._free_objects:
                # Try to allocate new slab
                self._allocate_slab()
            
            if not self._free_objects:
                return None
            
            index = self._free_objects.pop(0)
            self._used_count += 1
            
            return index
    
    def free(self, index: int) -> bool:
        """Free an object by its index."""
        with self._lock:
            if index < 0:
                return False
            
            self._free_objects.append(index)
            self._used_count -= 1
            return True
    
    def get_object_address(self, index: int) -> int:
        """Get the address of an object by its index."""
        slab_index = index // self._objects_per_slab
        obj_in_slab = index % self._objects_per_slab
        
        if slab_index >= len(self._slabs):
            return 0
        
        return (slab_index * self._slab_size + 
                obj_in_slab * self._object_size)
    
    def get_stats(self) -> dict[str, Any]:
        """Get slab allocator statistics."""
        return {
            'object_size': self._object_size,
            'total_slabs': len(self._slabs),
            'objects_per_slab': self._objects_per_slab,
            'total_objects': len(self._slabs) * self._objects_per_slab,
            'used_objects': self._used_count,
            'free_objects': len(self._free_objects),
            'utilization': self._used_count / (len(self._slabs) * self._objects_per_slab) * 100
                         if self._slabs else 0
        }
