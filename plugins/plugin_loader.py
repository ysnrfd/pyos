"""
Plugin Loader Module

Manages plugin discovery, loading, and lifecycle.

Author: YSNRFD
Version: 1.0.0
"""

import threading
import importlib.util
from pathlib import Path
from typing import Optional, Any, List
from dataclasses import dataclass

from .plugin_interface import PluginInterface, PluginState
from pyos.core.registry import Subsystem, SubsystemState
from pyos.exceptions import KernelException
from pyos.logger import Logger, get_logger


class PluginLoadError(KernelException):
    """Error loading a plugin."""
    pass


class PluginLoader(Subsystem):
    """
    Plugin Management Subsystem.
    
    Provides:
    - Plugin discovery
    - Plugin loading
    - Lifecycle management
    - Event dispatch to plugins
    
    Example:
        >>> loader = PluginLoader()
        >>> loader.load_plugin('/path/to/plugin.py')
        >>> loader.activate_plugin('my_plugin')
    """
    
    def __init__(self):
        super().__init__('plugins')
        self._plugins: dict[str, PluginInterface] = {}
        self._kernel = None
        self._lock = threading.Lock()
    
    def initialize(self) -> None:
        """Initialize the plugin loader."""
        from pyos.core.kernel import get_kernel
        self._kernel = get_kernel()
        
        self.set_state(SubsystemState.INITIALIZED)
        self._logger.info("Plugin loader initialized")
    
    def start(self) -> None:
        """Start the plugin loader."""
        self.set_state(SubsystemState.RUNNING)
    
    def stop(self) -> None:
        """Stop the plugin loader and all plugins."""
        for name in list(self._plugins.keys()):
            self.unload_plugin(name)
        
        self.set_state(SubsystemState.STOPPED)
    
    def cleanup(self) -> None:
        """Clean up resources."""
        self._plugins.clear()
    
    def discover_plugins(self, plugin_dir: str) -> List[str]:
        """
        Discover plugins in a directory.
        
        Args:
            plugin_dir: Directory to search
        
        Returns:
            List of discovered plugin file paths
        """
        plugin_path = Path(plugin_dir)
        
        if not plugin_path.exists():
            return []
        
        plugins = []
        
        for file in plugin_path.glob('*.py'):
            if file.name.startswith('_'):
                continue
            plugins.append(str(file))
        
        return plugins
    
    def load_plugin(self, plugin_path: str) -> str:
        """
        Load a plugin from a file.
        
        Args:
            plugin_path: Path to the plugin file
        
        Returns:
            Plugin name
        
        Raises:
            PluginLoadError: If loading fails
        """
        with self._lock:
            try:
                # Load the module
                spec = importlib.util.spec_from_file_location(
                    f"plugin_{Path(plugin_path).stem}",
                    plugin_path
                )
                
                if spec is None or spec.loader is None:
                    raise PluginLoadError(f"Cannot load plugin from {plugin_path}")
                
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                # Find plugin class
                plugin_class = None
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if (isinstance(attr, type) and 
                        issubclass(attr, PluginInterface) and 
                        attr is not PluginInterface):
                        plugin_class = attr
                        break
                
                if plugin_class is None:
                    raise PluginLoadError(
                        f"No PluginInterface class found in {plugin_path}"
                    )
                
                # Instantiate plugin
                plugin = plugin_class()
                info = plugin.info
                
                self._plugins[info.name] = plugin
                info.state = PluginState.LOADED
                
                self._logger.info(
                    f"Loaded plugin '{info.name}'",
                    context={'version': info.version}
                )
                
                return info.name
                
            except Exception as e:
                raise PluginLoadError(f"Failed to load plugin: {e}")
    
    def activate_plugin(self, name: str) -> bool:
        """
        Activate a loaded plugin.
        
        Args:
            name: Plugin name
        
        Returns:
            True if activated successfully
        """
        plugin = self._plugins.get(name)
        
        if plugin is None:
            return False
        
        try:
            plugin.initialize(self._kernel)
            plugin.info.state = PluginState.ACTIVE
            
            # Register plugin commands with shell
            commands = plugin.get_commands()
            if commands and self._kernel:
                # Would register with shell
                pass
            
            self._logger.info(f"Activated plugin '{name}'")
            return True
            
        except Exception as e:
            plugin.info.state = PluginState.ERROR
            plugin.info.error = str(e)
            
            self._logger.error(
                f"Failed to activate plugin '{name}'",
                context={'error': str(e)}
            )
            return False
    
    def deactivate_plugin(self, name: str) -> bool:
        """Deactivate a plugin."""
        plugin = self._plugins.get(name)
        
        if plugin is None:
            return False
        
        try:
            plugin.shutdown()
            plugin.info.state = PluginState.LOADED
            
            self._logger.info(f"Deactivated plugin '{name}'")
            return True
            
        except Exception as e:
            self._logger.error(
                f"Error deactivating plugin '{name}'",
                context={'error': str(e)}
            )
            return False
    
    def unload_plugin(self, name: str) -> bool:
        """Unload a plugin completely."""
        with self._lock:
            plugin = self._plugins.get(name)
            
            if plugin is None:
                return False
            
            try:
                if plugin.info.state == PluginState.ACTIVE:
                    plugin.shutdown()
                
                del self._plugins[name]
                
                self._logger.info(f"Unloaded plugin '{name}'")
                return True
                
            except Exception as e:
                self._logger.error(
                    f"Error unloading plugin '{name}'",
                    context={'error': str(e)}
                )
                return False
    
    def get_plugin(self, name: str) -> Optional[PluginInterface]:
        """Get a plugin by name."""
        return self._plugins.get(name)
    
    def list_plugins(self) -> List[dict[str, Any]]:
        """List all loaded plugins."""
        return [
            {
                'name': plugin.info.name,
                'version': plugin.info.version,
                'description': plugin.info.description,
                'author': plugin.info.author,
                'state': plugin.info.state.value,
                'error': plugin.info.error
            }
            for plugin in self._plugins.values()
        ]
    
    def dispatch_event(
        self,
        event_type: str,
        data: Any
    ) -> dict[str, Any]:
        """
        Dispatch an event to all active plugins.
        
        Args:
            event_type: Type of event
            data: Event data
        
        Returns:
            Dict of plugin name to response
        """
        responses = {}
        
        for name, plugin in self._plugins.items():
            if plugin.info.state == PluginState.ACTIVE:
                try:
                    response = plugin.on_event(event_type, data)
                    if response is not None:
                        responses[name] = response
                except Exception as e:
                    self._logger.error(
                        f"Error in plugin '{name}' event handler",
                        context={'error': str(e)}
                    )
        
        return responses
    
    def get_stats(self) -> dict[str, Any]:
        """Get plugin loader statistics."""
        active = sum(
            1 for p in self._plugins.values()
            if p.info.state == PluginState.ACTIVE
        )
        
        return {
            'total_plugins': len(self._plugins),
            'active_plugins': active,
        }
