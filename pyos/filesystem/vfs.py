"""
Virtual File System (VFS) Module

Implements a complete virtual file system with:
- Hierarchical directory tree
- Inode-based file management
- Permission enforcement
- File operations (open, read, write, delete)
- Path resolution

Author: YSNRFD
Version: 1.0.0
"""

import threading
from dataclasses import dataclass
from typing import Optional, Any, List
from enum import Enum

from .inode import Inode, FileType, Permission
from .path_resolver import PathResolver
from pyos.core.registry import Subsystem, SubsystemState
from pyos.core.config_loader import get_config
from pyos.exceptions import (
    FileNotFoundError,
    FileExistsError,
    PermissionDeniedError,
    DirectoryNotEmptyError,
    NotAFileError,
    NotADirectoryError,
    DiskFullError,
)
from pyos.logger import Logger, get_logger


class OpenMode(Enum):
    """File open modes."""
    READ = 'r'
    WRITE = 'w'
    APPEND = 'a'
    READ_WRITE = 'r+'


@dataclass
class FileHandle:
    """A handle to an open file."""
    fd: int
    ino: int
    path: str
    mode: OpenMode
    offset: int = 0
    pid: int = 0
    
    def can_read(self) -> bool:
        return self.mode in (OpenMode.READ, OpenMode.READ_WRITE)
    
    def can_write(self) -> bool:
        return self.mode in (OpenMode.WRITE, OpenMode.APPEND, OpenMode.READ_WRITE)


class VirtualFileSystem(Subsystem):
    """
    Virtual File System Subsystem.
    
    Provides a complete file system implementation with:
    - Hierarchical directory structure
    - POSIX-like permissions
    - File and directory operations
    
    Example:
        >>> vfs = VirtualFileSystem()
        >>> vfs.initialize()
        >>> fd = vfs.open('/tmp/test.txt', OpenMode.WRITE, uid=0)
        >>> vfs.write(fd, b'Hello, World!')
    """
    
    def __init__(self):
        super().__init__('filesystem')
        self._inodes: dict[int, Inode] = {}
        self._next_ino = 2  # 1 is reserved for root
        self._root_ino: Optional[int] = None
        self._open_files: dict[int, FileHandle] = {}
        self._next_fd = 3  # 0, 1, 2 reserved for stdin, stdout, stderr
        self._lock = threading.Lock()
        self._total_size = 0
        self._max_size = 100 * 1024 * 1024  # 100 MB virtual disk
    
    def initialize(self) -> None:
        """Initialize the filesystem."""
        self._logger.info("Initializing virtual filesystem")
        
        config = get_config()
        self._max_size = config.filesystem.max_file_size * 10
        
        # Create root directory
        root = Inode(
            ino=1,
            file_type=FileType.DIRECTORY,
            mode=0o755,
            uid=0,
            gid=0
        )
        
        self._inodes[1] = root
        self._root_ino = 1
        
        # Create standard directories
        self._create_standard_dirs()
        
        self.set_state(SubsystemState.INITIALIZED)
        self._logger.info("Virtual filesystem initialized")
    
    def _create_standard_dirs(self) -> None:
        """Create standard UNIX directories."""
        dirs = [
            ('/bin', 0o755),
            ('/etc', 0o755),
            ('/home', 0o755),
            ('/tmp', 0o777),
            ('/var', 0o755),
            ('/var/log', 0o755),
            ('/usr', 0o755),
            ('/root', 0o700),
        ]
        
        for path, mode in dirs:
            try:
                self.mkdir(path, mode=mode, uid=0, gid=0)
            except FileExistsError:
                pass
    
    def start(self) -> None:
        """Start the filesystem."""
        self.set_state(SubsystemState.RUNNING)
        self._logger.info("Virtual filesystem started")
    
    def stop(self) -> None:
        """Stop the filesystem."""
        self._logger.info("Stopping virtual filesystem")
        self.set_state(SubsystemState.STOPPED)
    
    def cleanup(self) -> None:
        """Clean up filesystem resources."""
        self._open_files.clear()
    
    def _generate_ino(self) -> int:
        """Generate a new inode number."""
        with self._lock:
            ino = self._next_ino
            self._next_ino += 1
            return ino
    
    def _generate_fd(self) -> int:
        """Generate a new file descriptor."""
        with self._lock:
            fd = self._next_fd
            self._next_fd += 1
            return fd
    
    def _resolve_path(self, path: str, cwd: str = '/') -> Optional[int]:
        """
        Resolve a path to an inode number.
        
        Args:
            path: Path to resolve
            cwd: Current working directory
        
        Returns:
            Inode number or None if not found
        """
        resolved = PathResolver.resolve(path, cwd)
        components = [c for c in resolved.split('/') if c]
        
        current_ino = self._root_ino
        
        for component in components:
            if current_ino is None:
                return None
            
            inode = self._inodes.get(current_ino)
            if inode is None or not inode.is_directory:
                return None
            
            current_ino = inode.get_entry(component)
        
        return current_ino
    
    def _get_parent_path(self, path: str) -> tuple[str, str]:
        """Get parent directory and basename."""
        return PathResolver.split(path)
    
    def stat(self, path: str, cwd: str = '/') -> Optional[Inode]:
        """
        Get inode information for a path.
        
        Args:
            path: Path to stat
            cwd: Current working directory
        
        Returns:
            Inode or None if not found
        """
        ino = self._resolve_path(path, cwd)
        if ino is None:
            return None
        return self._inodes.get(ino)
    
    def exists(self, path: str, cwd: str = '/') -> bool:
        """Check if a path exists."""
        return self._resolve_path(path, cwd) is not None
    
    def is_directory(self, path: str, cwd: str = '/') -> bool:
        """Check if a path is a directory."""
        inode = self.stat(path, cwd)
        return inode is not None and inode.is_directory
    
    def is_file(self, path: str, cwd: str = '/') -> bool:
        """Check if a path is a regular file."""
        inode = self.stat(path, cwd)
        return inode is not None and inode.is_regular_file
    
    def create(
        self,
        path: str,
        mode: int = 0o644,
        uid: int = 0,
        gid: int = 0,
        cwd: str = '/'
    ) -> int:
        """
        Create a new file.
        
        Args:
            path: Path for the new file
            mode: Permission mode
            uid: Owner user ID
            gid: Owner group ID
            cwd: Current working directory
        
        Returns:
            Inode number of created file
        
        Raises:
            FileExistsError: If file already exists
            PermissionDeniedError: If no write permission
        """
        resolved = PathResolver.resolve(path, cwd)
        
        # Check if already exists
        if self.exists(resolved):
            raise FileExistsError(resolved)
        
        # Get parent directory
        parent_path, name = self._get_parent_path(resolved)
        parent_ino = self._resolve_path(parent_path, '/')
        
        if parent_ino is None:
            raise FileNotFoundError(f"Parent directory: {parent_path}")
        
        parent = self._inodes[parent_ino]
        
        # Check parent write permission
        if not parent.can_write(uid, gid):
            raise PermissionDeniedError(parent_path, operation="write", uid=uid)
        
        # Create new inode
        ino = self._generate_ino()
        inode = Inode(
            ino=ino,
            file_type=FileType.REGULAR,
            mode=mode,
            uid=uid,
            gid=gid
        )
        
        self._inodes[ino] = inode
        parent.add_entry(name, ino)
        
        self._logger.debug(
            f"Created file",
            context={'path': resolved, 'ino': ino, 'mode': oct(mode)}
        )
        
        return ino
    
    def mkdir(
        self,
        path: str,
        mode: int = 0o755,
        uid: int = 0,
        gid: int = 0,
        cwd: str = '/'
    ) -> int:
        """
        Create a new directory.
        
        Args:
            path: Path for the new directory
            mode: Permission mode
            uid: Owner user ID
            gid: Owner group ID
            cwd: Current working directory
        
        Returns:
            Inode number of created directory
        """
        resolved = PathResolver.resolve(path, cwd)
        
        if self.exists(resolved):
            raise FileExistsError(resolved)
        
        parent_path, name = self._get_parent_path(resolved)
        parent_ino = self._resolve_path(parent_path, '/')
        
        if parent_ino is None:
            raise FileNotFoundError(f"Parent directory: {parent_path}")
        
        parent = self._inodes[parent_ino]
        
        if not parent.can_write(uid, gid):
            raise PermissionDeniedError(parent_path, operation="write", uid=uid)
        
        # Create new inode
        ino = self._generate_ino()
        inode = Inode(
            ino=ino,
            file_type=FileType.DIRECTORY,
            mode=mode,
            uid=uid,
            gid=gid
        )
        
        # Add . and .. entries
        inode.add_entry('.', ino)
        inode.add_entry('..', parent_ino)
        
        self._inodes[ino] = inode
        parent.add_entry(name, ino)
        
        self._logger.debug(
            f"Created directory",
            context={'path': resolved, 'ino': ino}
        )
        
        return ino
    
    def unlink(
        self,
        path: str,
        uid: int = 0,
        gid: int = 0,
        cwd: str = '/'
    ) -> None:
        """
        Delete a file.
        
        Args:
            path: Path to delete
            uid: User ID requesting deletion
            gid: Group ID
            cwd: Current working directory
        """
        resolved = PathResolver.resolve(path, cwd)
        
        ino = self._resolve_path(resolved, '/')
        if ino is None:
            raise FileNotFoundError(resolved)
        
        inode = self._inodes[ino]
        
        # Check if directory
        if inode.is_directory:
            raise NotAFileError(resolved, actual_type="directory")
        
        parent_path, name = self._get_parent_path(resolved)
        parent = self._inodes.get(self._resolve_path(parent_path, '/'))
        
        if parent and not parent.can_write(uid, gid):
            raise PermissionDeniedError(parent_path, operation="write", uid=uid)
        
        # Remove from parent
        if parent:
            parent.remove_entry(name)
        
        # Decrease link count
        inode.nlink -= 1
        
        # Remove if no links
        if inode.nlink <= 0:
            self._total_size -= inode.size
            del self._inodes[ino]
        
        self._logger.debug(f"Deleted file", context={'path': resolved})
    
    def rmdir(
        self,
        path: str,
        uid: int = 0,
        gid: int = 0,
        cwd: str = '/'
    ) -> None:
        """
        Delete an empty directory.
        
        Args:
            path: Path to delete
            uid: User ID
            gid: Group ID
            cwd: Current working directory
        """
        resolved = PathResolver.resolve(path, cwd)
        
        if resolved == '/':
            raise PermissionDeniedError("/", operation="rmdir")
        
        ino = self._resolve_path(resolved, '/')
        if ino is None:
            raise FileNotFoundError(resolved)
        
        inode = self._inodes[ino]
        
        if not inode.is_directory:
            raise NotADirectoryError(resolved)
        
        # Check if empty (only . and ..)
        entries = [e for e in inode.list_entries() if e[0] not in ('.', '..')]
        if entries:
            raise DirectoryNotEmptyError(resolved)
        
        parent_path, name = self._get_parent_path(resolved)
        parent = self._inodes.get(self._resolve_path(parent_path, '/'))
        
        if parent and not parent.can_write(uid, gid):
            raise PermissionDeniedError(parent_path, operation="write", uid=uid)
        
        # Remove from parent
        if parent:
            parent.remove_entry(name)
        
        del self._inodes[ino]
        
        self._logger.debug(f"Removed directory", context={'path': resolved})
    
    def open(
        self,
        path: str,
        mode: OpenMode,
        uid: int = 0,
        gid: int = 0,
        cwd: str = '/',
        pid: int = 0
    ) -> int:
        """
        Open a file.
        
        Args:
            path: Path to open
            mode: Open mode
            uid: User ID
            gid: Group ID
            cwd: Current working directory
            pid: Process ID
        
        Returns:
            File descriptor
        """
        resolved = PathResolver.resolve(path, cwd)
        
        ino = self._resolve_path(resolved, '/')
        
        # Create file if writing and doesn't exist
        if ino is None and mode in (OpenMode.WRITE, OpenMode.APPEND):
            ino = self.create(resolved, uid=uid, gid=gid)
        elif ino is None:
            raise FileNotFoundError(resolved)
        
        inode = self._inodes.get(ino)
        if inode is None:
            raise FileNotFoundError(resolved)
        
        # Check permissions
        if mode in (OpenMode.READ, OpenMode.READ_WRITE):
            if not inode.can_read(uid, gid):
                raise PermissionDeniedError(resolved, operation="read", uid=uid)
        
        if mode in (OpenMode.WRITE, OpenMode.APPEND, OpenMode.READ_WRITE):
            if not inode.can_write(uid, gid):
                raise PermissionDeniedError(resolved, operation="write", uid=uid)
        
        # Create file handle
        fd = self._generate_fd()
        handle = FileHandle(
            fd=fd,
            ino=ino,
            path=resolved,
            mode=mode,
            pid=pid
        )
        
        # Set initial offset
        if mode == OpenMode.APPEND:
            handle.offset = inode.size
        elif mode == OpenMode.WRITE:
            inode.truncate(0)
        
        self._open_files[fd] = handle
        
        return fd
    
    def close(self, fd: int) -> bool:
        """Close a file descriptor."""
        if fd in self._open_files:
            del self._open_files[fd]
            return True
        return False
    
    def read(self, fd: int, size: int = -1) -> bytes:
        """
        Read from an open file.
        
        Args:
            fd: File descriptor
            size: Bytes to read (-1 for all remaining)
        
        Returns:
            Data read
        """
        handle = self._open_files.get(fd)
        if handle is None:
            raise ValueError(f"Invalid file descriptor: {fd}")
        
        if not handle.can_read():
            raise PermissionDeniedError(handle.path, operation="read")
        
        inode = self._inodes[handle.ino]
        data = inode.read(handle.offset, size)
        
        handle.offset += len(data)
        
        return data
    
    def write(self, fd: int, data: bytes) -> int:
        """
        Write to an open file.
        
        Args:
            fd: File descriptor
            data: Data to write
        
        Returns:
            Number of bytes written
        """
        handle = self._open_files.get(fd)
        if handle is None:
            raise ValueError(f"Invalid file descriptor: {fd}")
        
        if not handle.can_write():
            raise PermissionDeniedError(handle.path, operation="write")
        
        # Check disk space
        if self._total_size + len(data) > self._max_size:
            raise DiskFullError(requested=len(data))
        
        inode = self._inodes[handle.ino]
        
        # Write at current offset
        written = inode.write(data, handle.offset)
        handle.offset += written
        self._total_size += written
        
        return written
    
    def seek(self, fd: int, offset: int, whence: int = 0) -> int:
        """
        Seek in a file.
        
        Args:
            fd: File descriptor
            offset: Offset
            whence: 0=SET, 1=CUR, 2=END
        
        Returns:
            New offset
        """
        handle = self._open_files.get(fd)
        if handle is None:
            raise ValueError(f"Invalid file descriptor: {fd}")
        
        inode = self._inodes[handle.ino]
        
        if whence == 0:  # SEEK_SET
            handle.offset = offset
        elif whence == 1:  # SEEK_CUR
            handle.offset += offset
        elif whence == 2:  # SEEK_END
            handle.offset = inode.size + offset
        
        return handle.offset
    
    def readdir(self, path: str, cwd: str = '/') -> List[dict[str, Any]]:
        """
        List directory contents.
        
        Args:
            path: Directory path
            cwd: Current working directory
        
        Returns:
            List of directory entries
        """
        resolved = PathResolver.resolve(path, cwd)
        ino = self._resolve_path(resolved, '/')
        
        if ino is None:
            raise FileNotFoundError(resolved)
        
        inode = self._inodes[ino]
        
        if not inode.is_directory:
            raise NotADirectoryError(resolved)
        
        entries = []
        for name, child_ino in inode.list_entries():
            child = self._inodes.get(child_ino)
            if child:
                entries.append({
                    'name': name,
                    'ino': child_ino,
                    'type': child.file_type.name,
                    'size': child.size,
                    'mode': oct(child.mode),
                })
        
        return entries
    
    def chmod(
        self,
        path: str,
        mode: int,
        uid: int = 0,
        gid: int = 0,
        cwd: str = '/'
    ) -> None:
        """Change file permissions."""
        resolved = PathResolver.resolve(path, cwd)
        ino = self._resolve_path(resolved, '/')
        
        if ino is None:
            raise FileNotFoundError(resolved)
        
        inode = self._inodes[ino]
        
        # Only owner or root can chmod
        if uid != 0 and uid != inode.uid:
            raise PermissionDeniedError(resolved, operation="chmod", uid=uid)
        
        inode.chmod(mode)
    
    def chown(
        self,
        path: str,
        new_uid: int,
        new_gid: int,
        uid: int = 0,
        cwd: str = '/'
    ) -> None:
        """Change file owner."""
        resolved = PathResolver.resolve(path, cwd)
        ino = self._resolve_path(resolved, '/')
        
        if ino is None:
            raise FileNotFoundError(resolved)
        
        inode = self._inodes[ino]
        
        # Only root can chown
        if uid != 0:
            raise PermissionDeniedError(resolved, operation="chown", uid=uid)
        
        inode.chown(new_uid, new_gid)
    
    def get_stats(self) -> dict[str, Any]:
        """Get filesystem statistics."""
        return {
            'total_inodes': len(self._inodes),
            'open_files': len(self._open_files),
            'total_size': self._total_size,
            'max_size': self._max_size,
            'utilization': self._total_size / self._max_size * 100 if self._max_size else 0
        }
