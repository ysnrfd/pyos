"""
Path Resolver Module

Handles path resolution and manipulation in the virtual file system.

Author: YSNRFD
Version: 1.0.0
"""

from dataclasses import dataclass
from typing import Optional, List, Tuple


@dataclass
class ParsedPath:
    """A parsed path with its components."""
    is_absolute: bool
    components: List[str]
    
    def __str__(self) -> str:
        if self.is_absolute:
            return '/' + '/'.join(self.components)
        return '/'.join(self.components) if self.components else '.'


class PathResolver:
    """
    Resolves and manipulates filesystem paths.
    
    Handles:
    - Absolute and relative paths
    - . and .. components
    - Path normalization
    """
    
    @staticmethod
    def parse(path: str) -> ParsedPath:
        """
        Parse a path into components.
        
        Args:
            path: Path string to parse
        
        Returns:
            ParsedPath with components
        """
        is_absolute = path.startswith('/')
        
        # Split and filter empty components
        components = [c for c in path.split('/') if c and c != '.']
        
        return ParsedPath(is_absolute=is_absolute, components=components)
    
    @staticmethod
    def normalize(path: str) -> str:
        """
        Normalize a path by resolving . and ..
        
        Args:
            path: Path to normalize
        
        Returns:
            Normalized path string
        """
        parsed = PathResolver.parse(path)
        
        result: List[str] = []
        
        for component in parsed.components:
            if component == '..':
                if result:
                    result.pop()
            else:
                result.append(component)
        
        if parsed.is_absolute:
            return '/' + '/'.join(result)
        return '/'.join(result) if result else '.'
    
    @staticmethod
    def join(*paths: str) -> str:
        """
        Join multiple path components.
        
        Args:
            *paths: Path components to join
        
        Returns:
            Joined path string
        """
        if not paths:
            return '.'
        
        result = paths[0]
        
        for path in paths[1:]:
            if path.startswith('/'):
                result = path
            else:
                result = result.rstrip('/') + '/' + path
        
        return PathResolver.normalize(result)
    
    @staticmethod
    def resolve(path: str, cwd: str = '/') -> str:
        """
        Resolve a path relative to a current working directory.
        
        Args:
            path: Path to resolve
            cwd: Current working directory
        
        Returns:
            Absolute resolved path
        """
        parsed = PathResolver.parse(path)
        
        if parsed.is_absolute:
            return PathResolver.normalize(path)
        
        # Combine with cwd
        combined = cwd.rstrip('/') + '/' + path
        return PathResolver.normalize(combined)
    
    @staticmethod
    def dirname(path: str) -> str:
        """
        Get the directory name of a path.
        
        Args:
            path: Path string
        
        Returns:
            Directory name portion
        """
        normalized = PathResolver.normalize(path)
        
        if '/' not in normalized:
            return '.'
        
        if normalized == '/':
            return '/'
        
        return normalized.rsplit('/', 1)[0] or '/'
    
    @staticmethod
    def basename(path: str) -> str:
        """
        Get the base name of a path.
        
        Args:
            path: Path string
        
        Returns:
            Base name portion
        """
        normalized = PathResolver.normalize(path)
        
        if normalized == '/':
            return '/'
        
        if '/' not in normalized:
            return normalized
        
        return normalized.rsplit('/', 1)[1]
    
    @staticmethod
    def split(path: str) -> Tuple[str, str]:
        """
        Split a path into directory and base name.
        
        Args:
            path: Path string
        
        Returns:
            Tuple of (dirname, basename)
        """
        return (PathResolver.dirname(path), PathResolver.basename(path))
    
    @staticmethod
    def splitext(path: str) -> Tuple[str, str]:
        """
        Split a path into root and extension.
        
        Args:
            path: Path string
        
        Returns:
            Tuple of (root, extension)
        """
        basename = PathResolver.basename(path)
        
        if '.' not in basename or basename.startswith('.'):
            return (path, '')
        
        root, ext = path.rsplit('.', 1)
        return (root, '.' + ext)
    
    @staticmethod
    def is_absolute(path: str) -> bool:
        """Check if a path is absolute."""
        return path.startswith('/')
    
    @staticmethod
    def get_parent(path: str) -> str:
        """Get the parent directory path."""
        return PathResolver.dirname(path)
    
    @staticmethod
    def get_depth(path: str) -> int:
        """
        Get the depth of a path (number of components).
        
        Args:
            path: Path string
        
        Returns:
            Depth of the path
        """
        normalized = PathResolver.normalize(path)
        if normalized == '/':
            return 0
        return len([c for c in normalized.split('/') if c])
