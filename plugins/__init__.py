"""
PyOS Plugin Module

Provides plugin infrastructure:
- Plugin interface
- Plugin loader
- Lifecycle management
"""

from .plugin_interface import PluginInterface, PluginInfo, PluginState
from .plugin_loader import PluginLoader, PluginLoadError

__all__ = [
    'PluginInterface',
    'PluginInfo',
    'PluginState',
    'PluginLoader',
    'PluginLoadError',
]
