"""
PyOS Bootloader

The bootloader is responsible for:
- Loading configuration
- Initializing logging
- Starting the kernel
- Handling boot failures
- Running self-tests

This is the entry point for the operating system.

Author: YSNRFD
Version: 1.0.0
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional, TYPE_CHECKING
import sys
import time

if TYPE_CHECKING:
    from pyos.core.kernel import Kernel

from pyos.logger import Logger, get_logger, LogLevel
from pyos.exceptions import (
    BootFailureError,
    KernelPanic,
    SubsystemInitError,
)
from pyos.core.config_loader import ConfigLoader, get_config


class BootStage(Enum):
    """Boot process stages."""
    PRE_INIT = auto()
    CONFIG_LOAD = auto()
    LOGGING_INIT = auto()
    KERNEL_INIT = auto()
    SUBSYSTEM_INIT = auto()
    POST_INIT = auto()
    COMPLETE = auto()
    FAILED = auto()


@dataclass
class BootResult:
    """Result of the boot process."""
    success: bool
    stage: BootStage
    message: str
    elapsed_time: float
    error: Optional[Exception] = None


class Bootloader:
    """
    The system bootloader.
    
    Handles the complete boot sequence from loading configuration
    to starting the kernel and all subsystems.
    
    Boot Sequence:
        1. Pre-initialization checks
        2. Load configuration
        3. Initialize logging
        4. Initialize kernel
        5. Initialize subsystems
        6. Post-initialization
        7. Complete
    
    Example:
        >>> bootloader = Bootloader()
        >>> result = bootloader.boot()
        >>> if result.success:
        ...     print("System booted successfully")
    """
    
    def __init__(self, config_path: str = "config.json"):
        self._config_path = config_path
        self._stage = BootStage.PRE_INIT
        self._logger: Optional[Logger] = None
        self._start_time: float = 0
        self._kernel = None
    
    @property
    def stage(self) -> BootStage:
        """Get the current boot stage."""
        return self._stage
    
    def boot(self) -> BootResult:
        """
        Execute the boot sequence.
        
        Returns:
            BootResult indicating success or failure
        """
        self._start_time = time.time()
        
        try:
            # Stage 1: Pre-initialization
            self._stage = BootStage.PRE_INIT
            self._pre_init()
            
            # Stage 2: Load configuration
            self._stage = BootStage.CONFIG_LOAD
            self._load_config()
            
            # Stage 3: Initialize logging
            self._stage = BootStage.LOGGING_INIT
            self._init_logging()
            
            self._logger = get_logger('bootloader')
            self._logger.info("PyOS Bootloader starting...")
            
            # Stage 4: Initialize kernel
            self._stage = BootStage.KERNEL_INIT
            self._init_kernel()
            
            # Stage 5: Initialize subsystems
            self._stage = BootStage.SUBSYSTEM_INIT
            self._init_subsystems()
            
            # Stage 6: Post-initialization
            self._stage = BootStage.POST_INIT
            self._post_init()
            
            # Stage 7: Complete
            self._stage = BootStage.COMPLETE
            elapsed = time.time() - self._start_time
            
            if self._logger:
                self._logger.info(
                    f"Boot complete",
                    context={'elapsed_ms': f"{elapsed * 1000:.2f}"}
                )
            
            return BootResult(
                success=True,
                stage=self._stage,
                message="System booted successfully",
                elapsed_time=elapsed
            )
            
        except Exception as e:
            self._stage = BootStage.FAILED
            elapsed = time.time() - self._start_time
            
            if self._logger:
                self._logger.critical(
                    f"Boot failed at stage {self._stage.name}: {e}"
                )
            
            return BootResult(
                success=False,
                stage=self._stage,
                message=f"Boot failed: {e}",
                elapsed_time=elapsed,
                error=e
            )
    
    def _pre_init(self) -> None:
        """Pre-initialization checks."""
        # Check Python version
        if sys.version_info < (3, 10):
            raise BootFailureError(
                "Python 3.10+ required",
                subsystem="bootloader"
            )
        
        # Environment checks can go here
    
    def _load_config(self) -> None:
        """Load system configuration."""
        loader = ConfigLoader()
        try:
            loader.load(self._config_path)
        except BootFailureError:
            # Use defaults if config not found
            pass  # ConfigLoader already has defaults
    
    def _init_logging(self) -> None:
        """Initialize the logging system."""
        config = get_config()
        
        # Map log level string to LogLevel
        level_map = {
            'DEBUG': LogLevel.DEBUG,
            'INFO': LogLevel.INFO,
            'NOTICE': LogLevel.NOTICE,
            'WARNING': LogLevel.WARNING,
            'ERROR': LogLevel.ERROR,
            'CRITICAL': LogLevel.CRITICAL,
        }
        
        level = level_map.get(config.logging.level, LogLevel.INFO)
        
        Logger.initialize(
            level=level,
            log_file=None,  # Don't write to file in simulation
            use_colors=True
        )
    
    def _init_kernel(self) -> None:
        """Initialize the kernel."""
        # Import here to avoid circular dependency
        from pyos.core.kernel import Kernel
        
        self._kernel = Kernel()
        self._kernel.initialize()
        
        if self._logger:
            self._logger.debug("Kernel initialized")
    
    def _init_subsystems(self) -> None:
        """Initialize kernel subsystems."""
        if self._kernel:
            self._kernel.initialize_subsystems()
        
        if self._logger:
            self._logger.debug("Subsystems initialized")
    
    def _post_init(self) -> None:
        """Post-initialization tasks."""
        config = get_config()
        
        if self._logger:
            self._logger.info(
                f"{config.kernel.name} v{config.kernel.version}",
                context={'run_level': config.boot.run_level}
            )
            self._logger.info(config.kernel.boot_message)
    
    def get_kernel(self):
        """Get the initialized kernel instance."""
        return self._kernel
    
    def shutdown(self) -> None:
        """Shutdown the system gracefully."""
        if self._logger:
            self._logger.info("System shutdown initiated")
        
        if self._kernel:
            self._kernel.shutdown()
        
        if self._logger:
            self._logger.info("System shutdown complete")


def boot_system(config_path: str = "config.json") -> tuple[BootResult, Optional['Kernel']]:
    """
    Convenience function to boot the system.
    
    Args:
        config_path: Path to configuration file
    
    Returns:
        Tuple of (BootResult, Kernel or None)
    """
    bootloader = Bootloader(config_path)
    result = bootloader.boot()
    return result, bootloader.get_kernel()
