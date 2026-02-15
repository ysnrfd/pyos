"""
Inode Module

Implements the inode abstraction for the virtual file system.
Inodes store metadata about files and directories.

Author: YSNRFD
Version: 1.0.0
"""

import time
from dataclasses import dataclass, field
from enum import Enum, Flag
from typing import Optional, Any, List

from pyos.logger import Logger, get_logger


class FileType(Enum):
    """Types of files."""
    REGULAR = 1
    DIRECTORY = 2
    SYMLINK = 3
    DEVICE = 4
    FIFO = 5
    SOCKET = 6


class Permission(Flag):
    """File permission bits."""
    # Owner permissions
    OWNER_READ = 0o400
    OWNER_WRITE = 0o200
    OWNER_EXEC = 0o100
    
    # Group permissions
    GROUP_READ = 0o040
    GROUP_WRITE = 0o020
    GROUP_EXEC = 0o010
    
    # Other permissions
    OTHER_READ = 0o004
    OTHER_WRITE = 0o002
    OTHER_EXEC = 0o001
    
    # Common combinations
    OWNER_RW = OWNER_READ | OWNER_WRITE
    OWNER_RWX = OWNER_READ | OWNER_WRITE | OWNER_EXEC
    GROUP_RW = GROUP_READ | GROUP_WRITE
    OTHER_RW = OTHER_READ | OTHER_WRITE
    
    # Default permissions
    DEFAULT_FILE = OWNER_RW | GROUP_READ | OTHER_READ
    DEFAULT_DIR = OWNER_RWX | GROUP_READ | GROUP_EXEC | OTHER_READ | OTHER_EXEC


@dataclass
class Inode:
    """
    Inode - Index Node.
    
    Stores metadata about a file or directory:
    - Type and permissions
    - Owner and group
    - Size and timestamps
    - Data blocks (simulated)
    
    In a real filesystem, inodes would also contain:
    - Block pointers
    - Indirect block pointers
    - Extended attributes
    """
    
    ino: int  # Inode number
    file_type: FileType
    mode: int = 0o644  # Permission mode (octal)
    uid: int = 0  # Owner user ID
    gid: int = 0  # Owner group ID
    size: int = 0
    nlink: int = 1  # Number of hard links
    
    # Timestamps
    atime: float = field(default_factory=time.time)  # Access time
    mtime: float = field(default_factory=time.time)  # Modification time
    ctime: float = field(default_factory=time.time)  # Change time
    
    # File content (simulated)
    _data: bytes = field(default_factory=bytes, repr=False)
    
    # For directories: mapping of name -> inode number
    _entries: dict[str, int] = field(default_factory=dict, repr=False)
    
    def __post_init__(self):
        self._logger = get_logger('inode')
    
    @property
    def is_directory(self) -> bool:
        return self.file_type == FileType.DIRECTORY
    
    @property
    def is_regular_file(self) -> bool:
        return self.file_type == FileType.REGULAR
    
    @property
    def is_symlink(self) -> bool:
        return self.file_type == FileType.SYMLINK
    
    def check_permission(self, uid: int, gid: int, perm: Permission) -> bool:
        """
        Check if a user has a specific permission.
        
        Args:
            uid: User ID
            gid: Group ID
            perm: Permission to check
        
        Returns:
            True if permission is granted
        """
        # Root has all permissions
        if uid == 0:
            return True
        
        # Determine which permission set to use
        if uid == self.uid:
            # Owner permissions
            if perm in (Permission.OWNER_READ, Permission.OWNER_WRITE, Permission.OWNER_EXEC):
                check_mode = self.mode & 0o700
            else:
                check_mode = self.mode & 0o700
        elif gid == self.gid:
            # Group permissions
            check_mode = self.mode & 0o070
        else:
            # Other permissions
            check_mode = self.mode & 0o007
        
        # Map permission to bit position
        perm_bits = {
            Permission.OWNER_READ: 0o400,
            Permission.OWNER_WRITE: 0o200,
            Permission.OWNER_EXEC: 0o100,
            Permission.GROUP_READ: 0o040,
            Permission.GROUP_WRITE: 0o020,
            Permission.GROUP_EXEC: 0o010,
            Permission.OTHER_READ: 0o004,
            Permission.OTHER_WRITE: 0o002,
            Permission.OTHER_EXEC: 0o001,
        }
        
        bit = perm_bits.get(perm, 0)
        
        if uid == self.uid:
            return (self.mode & bit) != 0
        elif gid == self.gid:
            bit = bit >> 3  # Shift to group position
            return (self.mode & bit) != 0
        else:
            bit = bit >> 6  # Shift to other position
            return (self.mode & bit) != 0
    
    def can_read(self, uid: int, gid: int) -> bool:
        """Check read permission."""
        if uid == 0:
            return True
        perm = Permission.OWNER_READ if uid == self.uid else (
            Permission.GROUP_READ if gid == self.gid else Permission.OTHER_READ
        )
        return self.check_permission(uid, gid, perm)
    
    def can_write(self, uid: int, gid: int) -> bool:
        """Check write permission."""
        if uid == 0:
            return True
        perm = Permission.OWNER_WRITE if uid == self.uid else (
            Permission.GROUP_WRITE if gid == self.gid else Permission.OTHER_WRITE
        )
        return self.check_permission(uid, gid, perm)
    
    def can_execute(self, uid: int, gid: int) -> bool:
        """Check execute permission."""
        if uid == 0:
            return True
        perm = Permission.OWNER_EXEC if uid == self.uid else (
            Permission.GROUP_EXEC if gid == self.gid else Permission.OTHER_EXEC
        )
        return self.check_permission(uid, gid, perm)
    
    def chmod(self, mode: int) -> None:
        """Change permission mode."""
        self.mode = mode & 0o777  # Only lower 9 bits
        self.ctime = time.time()
    
    def chown(self, uid: int, gid: int) -> None:
        """Change owner and group."""
        self.uid = uid
        self.gid = gid
        self.ctime = time.time()
    
    def touch(self) -> None:
        """Update access and modification times."""
        self.atime = time.time()
        self.mtime = time.time()
    
    # File operations
    
    def read(self, offset: int = 0, size: int = -1) -> bytes:
        """
        Read data from the file.
        
        Args:
            offset: Byte offset to start reading
            size: Number of bytes to read (-1 for all)
        
        Returns:
            Data read from the file
        """
        if not self.is_regular_file:
            return bytes()
        
        self.atime = time.time()
        
        if size < 0:
            return self._data[offset:]
        return self._data[offset:offset + size]
    
    def write(self, data: bytes, offset: int = 0) -> int:
        """
        Write data to the file.
        
        Args:
            data: Data to write
            offset: Byte offset to write at
        
        Returns:
            Number of bytes written
        """
        if not self.is_regular_file:
            return 0
        
        # Handle offset beyond current size
        if offset > len(self._data):
            # Pad with zeros
            self._data = self._data + bytes(offset - len(self._data))
        
        # Write data
        if offset + len(data) > len(self._data):
            self._data = self._data[:offset] + data
        else:
            self._data = self._data[:offset] + data + self._data[offset + len(data):]
        
        self.size = len(self._data)
        self.mtime = time.time()
        self.ctime = time.time()
        
        return len(data)
    
    def truncate(self, size: int) -> None:
        """Truncate the file to the given size."""
        if size < 0:
            size = 0
        
        self._data = self._data[:size]
        self.size = len(self._data)
        self.mtime = time.time()
        self.ctime = time.time()
    
    # Directory operations
    
    def add_entry(self, name: str, ino: int) -> None:
        """Add a directory entry."""
        if not self.is_directory:
            raise ValueError("Not a directory")
        
        self._entries[name] = ino
        self.nlink += 1
        self.mtime = time.time()
    
    def remove_entry(self, name: str) -> Optional[int]:
        """Remove a directory entry."""
        if not self.is_directory:
            raise ValueError("Not a directory")
        
        ino = self._entries.pop(name, None)
        if ino is not None:
            self.nlink -= 1
            self.mtime = time.time()
        return ino
    
    def get_entry(self, name: str) -> Optional[int]:
        """Get the inode number for a directory entry."""
        if not self.is_directory:
            return None
        return self._entries.get(name)
    
    def list_entries(self) -> List[tuple[str, int]]:
        """List all directory entries."""
        if not self.is_directory:
            return []
        return list(self._entries.items())
    
    def to_dict(self) -> dict[str, Any]:
        """Convert inode to dictionary for display."""
        return {
            'ino': self.ino,
            'type': self.file_type.name,
            'mode': oct(self.mode),
            'uid': self.uid,
            'gid': self.gid,
            'size': self.size,
            'nlink': self.nlink,
            'atime': time.strftime('%Y-%m-%d %H:%M', time.localtime(self.atime)),
            'mtime': time.strftime('%Y-%m-%d %H:%M', time.localtime(self.mtime)),
        }
