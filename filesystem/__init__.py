"""
PyOS Virtual File System Module

Provides a complete file system implementation:
- Hierarchical directory structure
- Inode-based file management
- POSIX-like permissions
- File operations
"""

from .inode import Inode, FileType, Permission
from .path_resolver import PathResolver, ParsedPath
from .vfs import VirtualFileSystem, OpenMode, FileHandle

__all__ = [
    # Inode
    'Inode',
    'FileType',
    'Permission',
    # Path Resolver
    'PathResolver',
    'ParsedPath',
    # VFS
    'VirtualFileSystem',
    'OpenMode',
    'FileHandle',
]
