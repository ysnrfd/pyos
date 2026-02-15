"""
PyOS Configuration Loader

A robust configuration management system that provides:
- JSON configuration file loading
- Configuration validation
- Default value handling
- Runtime configuration updates
- Type-safe access to configuration values

Author: YSNRFD
Version: 1.0.0
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional, TypeVar, Generic, List
from copy import deepcopy
import threading

from pyos.exceptions import KernelException, BootFailureError


T = TypeVar('T')


class ConfigValidationError(KernelException):
    """Raised when configuration validation fails."""
    pass


@dataclass
class SchedulerConfig:
    """Scheduler configuration settings."""
    algorithm: str = "round_robin"
    quantum: int = 100
    priority_levels: int = 10
    enable_preemption: bool = True


@dataclass
class MemoryConfig:
    """Memory management configuration settings."""
    total_memory: int = 67108864  # 64 MB
    page_size: int = 4096
    max_processes: int = 256
    max_memory_per_process: int = 16777216  # 16 MB


@dataclass
class FilesystemConfig:
    """Filesystem configuration settings."""
    root_path: str = "/"
    max_file_size: int = 10485760  # 10 MB
    max_open_files: int = 1024
    enable_journaling: bool = True


@dataclass
class ProcessConfig:
    """Process management configuration settings."""
    max_pid: int = 32768
    init_process: str = "init"
    zombie_timeout: int = 60
    max_processes: int = 256


@dataclass
class SecurityConfig:
    """Security configuration settings."""
    enable_sandbox: bool = True
    max_cpu_time_per_process: int = 3600
    max_file_descriptors: int = 1024
    allow_root_login: bool = True


@dataclass
class LoggingConfig:
    """Logging configuration settings."""
    level: str = "INFO"
    log_file: str = "/var/log/pyos.log"
    max_log_size: int = 1048576
    console_output: bool = True


@dataclass
class UsersConfig:
    """User management configuration settings."""
    default_user: str = "root"
    default_shell: str = "/bin/pysh"
    home_prefix: str = "/home"


@dataclass
class IPCConfig:
    """IPC configuration settings."""
    max_pipes: int = 256
    max_message_queues: int = 64
    max_shared_memory_segments: int = 32
    pipe_buffer_size: int = 65536


@dataclass
class ShellConfig:
    """Shell configuration settings."""
    prompt: str = "$ "
    history_size: int = 1000
    enable_autocomplete: bool = True


@dataclass
class BootConfig:
    """Boot configuration settings."""
    auto_start_services: List[str] = field(default_factory=lambda: [
        "filesystem", "process_manager", "memory_manager"
    ])
    init_user: str = "root"
    run_level: int = 3


@dataclass
class KernelConfig:
    """Kernel identification settings."""
    name: str = "PyOS"
    version: str = "1.0.0"
    boot_message: str = "Welcome to PyOS"


@dataclass
class Config:
    """
    Main configuration container.
    
    Holds all configuration settings for the operating system.
    Provides type-safe access to configuration values.
    """
    kernel: KernelConfig = field(default_factory=KernelConfig)
    scheduler: SchedulerConfig = field(default_factory=SchedulerConfig)
    memory: MemoryConfig = field(default_factory=MemoryConfig)
    filesystem: FilesystemConfig = field(default_factory=FilesystemConfig)
    process: ProcessConfig = field(default_factory=ProcessConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    users: UsersConfig = field(default_factory=UsersConfig)
    ipc: IPCConfig = field(default_factory=IPCConfig)
    shell: ShellConfig = field(default_factory=ShellConfig)
    boot: BootConfig = field(default_factory=BootConfig)


class ConfigLoader:
    """
    Configuration loader and manager.
    
    Handles loading configuration from JSON files, validating
    settings, and providing runtime configuration access.
    
    Example:
        >>> loader = ConfigLoader()
        >>> config = loader.load('config.json')
        >>> print(config.kernel.name)
        PyOS
    """
    
    _instance: Optional['ConfigLoader'] = None
    _lock = threading.Lock()
    
    def __new__(cls) -> 'ConfigLoader':
        """Singleton pattern for configuration access."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._config = Config()
                cls._instance._loaded = False
            return cls._instance
    
    def load(self, config_path: str) -> Config:
        """
        Load configuration from a JSON file.
        
        Args:
            config_path: Path to the configuration file
        
        Returns:
            Config object with loaded settings
        
        Raises:
            BootFailureError: If the file cannot be loaded or parsed
        """
        path = Path(config_path)
        
        if not path.exists():
            raise BootFailureError(
                f"Configuration file not found: {config_path}",
                subsystem="config"
            )
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise BootFailureError(
                f"Invalid JSON in configuration file: {e}",
                subsystem="config"
            )
        except IOError as e:
            raise BootFailureError(
                f"Cannot read configuration file: {e}",
                subsystem="config"
            )
        
        self._config = self._parse_config(data)
        self._loaded = True
        return self._config
    
    def _parse_config(self, data: dict[str, Any]) -> Config:
        """Parse configuration data into Config object."""
        config = Config()
        
        # Parse kernel config
        if 'kernel' in data:
            kernel_data = data['kernel']
            config.kernel = KernelConfig(
                name=kernel_data.get('name', config.kernel.name),
                version=kernel_data.get('version', config.kernel.version),
                boot_message=kernel_data.get('boot_message', config.kernel.boot_message),
            )
        
        # Parse scheduler config
        if 'scheduler' in data:
            sched_data = data['scheduler']
            config.scheduler = SchedulerConfig(
                algorithm=sched_data.get('algorithm', config.scheduler.algorithm),
                quantum=sched_data.get('quantum', config.scheduler.quantum),
                priority_levels=sched_data.get('priority_levels', config.scheduler.priority_levels),
                enable_preemption=sched_data.get('enable_preemption', config.scheduler.enable_preemption),
            )
        
        # Parse memory config
        if 'memory' in data:
            mem_data = data['memory']
            config.memory = MemoryConfig(
                total_memory=mem_data.get('total_memory', config.memory.total_memory),
                page_size=mem_data.get('page_size', config.memory.page_size),
                max_processes=mem_data.get('max_processes', config.memory.max_processes),
                max_memory_per_process=mem_data.get('max_memory_per_process', config.memory.max_memory_per_process),
            )
        
        # Parse filesystem config
        if 'filesystem' in data:
            fs_data = data['filesystem']
            config.filesystem = FilesystemConfig(
                root_path=fs_data.get('root_path', config.filesystem.root_path),
                max_file_size=fs_data.get('max_file_size', config.filesystem.max_file_size),
                max_open_files=fs_data.get('max_open_files', config.filesystem.max_open_files),
                enable_journaling=fs_data.get('enable_journaling', config.filesystem.enable_journaling),
            )
        
        # Parse process config
        if 'process' in data:
            proc_data = data['process']
            config.process = ProcessConfig(
                max_pid=proc_data.get('max_pid', config.process.max_pid),
                init_process=proc_data.get('init_process', config.process.init_process),
                zombie_timeout=proc_data.get('zombie_timeout', config.process.zombie_timeout),
                max_processes=proc_data.get('max_processes', config.process.max_processes),
            )
        
        # Parse security config
        if 'security' in data:
            sec_data = data['security']
            config.security = SecurityConfig(
                enable_sandbox=sec_data.get('enable_sandbox', config.security.enable_sandbox),
                max_cpu_time_per_process=sec_data.get('max_cpu_time_per_process', config.security.max_cpu_time_per_process),
                max_file_descriptors=sec_data.get('max_file_descriptors', config.security.max_file_descriptors),
                allow_root_login=sec_data.get('allow_root_login', config.security.allow_root_login),
            )
        
        # Parse logging config
        if 'logging' in data:
            log_data = data['logging']
            config.logging = LoggingConfig(
                level=log_data.get('level', config.logging.level),
                log_file=log_data.get('log_file', config.logging.log_file),
                max_log_size=log_data.get('max_log_size', config.logging.max_log_size),
                console_output=log_data.get('console_output', config.logging.console_output),
            )
        
        # Parse users config
        if 'users' in data:
            users_data = data['users']
            config.users = UsersConfig(
                default_user=users_data.get('default_user', config.users.default_user),
                default_shell=users_data.get('default_shell', config.users.default_shell),
                home_prefix=users_data.get('home_prefix', config.users.home_prefix),
            )
        
        # Parse IPC config
        if 'ipc' in data:
            ipc_data = data['ipc']
            config.ipc = IPCConfig(
                max_pipes=ipc_data.get('max_pipes', config.ipc.max_pipes),
                max_message_queues=ipc_data.get('max_message_queues', config.ipc.max_message_queues),
                max_shared_memory_segments=ipc_data.get('max_shared_memory_segments', config.ipc.max_shared_memory_segments),
                pipe_buffer_size=ipc_data.get('pipe_buffer_size', config.ipc.pipe_buffer_size),
            )
        
        # Parse shell config
        if 'shell' in data:
            shell_data = data['shell']
            config.shell = ShellConfig(
                prompt=shell_data.get('prompt', config.shell.prompt),
                history_size=shell_data.get('history_size', config.shell.history_size),
                enable_autocomplete=shell_data.get('enable_autocomplete', config.shell.enable_autocomplete),
            )
        
        # Parse boot config
        if 'boot' in data:
            boot_data = data['boot']
            config.boot = BootConfig(
                auto_start_services=boot_data.get('auto_start_services', config.boot.auto_start_services),
                init_user=boot_data.get('init_user', config.boot.init_user),
                run_level=boot_data.get('run_level', config.boot.run_level),
            )
        
        return config
    
    @property
    def config(self) -> Config:
        """Get the current configuration."""
        if not self._loaded:
            return Config()
        return self._config
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value by dot-notation key.
        
        Args:
            key: Dot-notation key (e.g., 'kernel.version')
            default: Default value if key not found
        
        Returns:
            Configuration value or default
        """
        parts = key.split('.')
        obj: Any = self._config
        
        for part in parts:
            if hasattr(obj, part):
                obj = getattr(obj, part)
            else:
                return default
        
        return obj
    
    def set(self, key: str, value: Any) -> None:
        """
        Set a configuration value at runtime.
        
        Args:
            key: Dot-notation key (e.g., 'scheduler.quantum')
            value: Value to set
        
        Note:
            This modifies configuration at runtime but does not
            persist changes to disk.
        """
        parts = key.split('.')
        obj: Any = self._config
        
        # Navigate to parent object
        for part in parts[:-1]:
            if hasattr(obj, part):
                obj = getattr(obj, part)
            else:
                raise ConfigValidationError(f"Invalid configuration key: {key}")
        
        # Set the value
        final_key = parts[-1]
        if hasattr(obj, final_key):
            setattr(obj, final_key, value)
        else:
            raise ConfigValidationError(f"Invalid configuration key: {key}")
    
    def reload(self, config_path: str) -> Config:
        """Reload configuration from file."""
        return self.load(config_path)
    
    def to_dict(self) -> dict[str, Any]:
        """Convert configuration to dictionary."""
        def dataclass_to_dict(obj: Any) -> Any:
            if hasattr(obj, '__dataclass_fields__'):
                return {
                    k: dataclass_to_dict(v)
                    for k, v in obj.__dict__.items()
                }
            elif isinstance(obj, list):
                return [dataclass_to_dict(item) for item in obj]
            elif isinstance(obj, dict):
                return {k: dataclass_to_dict(v) for k, v in obj.items()}
            else:
                return obj
        
        return dataclass_to_dict(self._config)


def get_config() -> Config:
    """
    Get the global configuration instance.
    
    Returns:
        Config object with current settings
    """
    loader = ConfigLoader()
    return loader.config
