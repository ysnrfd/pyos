#!/usr/bin/env python3
"""
PyOS - A UNIX-inspired Operating System Simulation

This is the main entry point for PyOS.

PyOS is a complete, production-grade operating system simulation
implemented entirely in Python 3.10+ using only the standard library.

Features:
- Modular kernel architecture
- Process management with scheduling
- Virtual memory management
- Virtual file system with permissions
- Multi-user support with authentication
- System call interface
- IPC (pipes, message queues, shared memory)
- Security sandboxing
- Monitoring and observability
- Plugin architecture
- Interactive shell

Author: YSNRFD
Updated By : DeathAmir
Version: 1.0.0 Patched
"""

from __future__ import annotations

import os
import sys
from typing import Optional

# Ensure the pyos directory is in the path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

import pyos  # noqa: F401  # ensures package availability
from pyos.core.bootloader import Bootloader
from pyos.shell.shell import Shell


def _config_path() -> str:
    """Resolve config.json path relative to this file."""
    return os.path.join(os.path.dirname(__file__), "config.json")


def _print_boot_header() -> None:
    """Print a standardized boot header."""
    print("PyOS Boot Sequence")
    print("=" * 50)


def _print_boot_footer(elapsed_ms: float) -> None:
    """Print a standardized boot footer."""
    print(f"\nBoot completed in {elapsed_ms:.2f}ms")
    print("=" * 50)


def _boot_system(config_path: str) -> Bootloader:
    """
    Boot the system and return the Bootloader instance.
    Raises SystemExit on failure.
    """
    _print_boot_header()

    bootloader = Bootloader(config_path)
    result = bootloader.boot()

    if not result.success:
        print(f"\nBoot failed at stage {result.stage.name}")
        print(f"Error: {result.message}")
        if result.error:
            print(f"Details: {result.error}")
        raise SystemExit(1)

    _print_boot_footer(result.elapsed_time * 1000)
    return bootloader


def main() -> None:
    """
    Main entry point for PyOS.
    
    Boot sequence:
    1. Load configuration
    2. Initialize logging
    3. Initialize kernel
    4. Initialize subsystems
    5. Start shell
    6. Shutdown
    """
    config_path = _config_path()

    # Boot the system
    bootloader = _boot_system(config_path)

    # Get the kernel
    kernel = bootloader.get_kernel()

    # Run the kernel
    kernel.run()

    # Start the shell
    shell = Shell(kernel)

    try:
        shell.run()
    except KeyboardInterrupt:
        print("\n\nInterrupted")
    finally:
        # Shutdown
        bootloader.shutdown()


def run_headless() -> int:
    """
    Run PyOS in headless mode for testing.
    
    This boots the system and runs a test script
    without starting the interactive shell.
    """
    config_path = _config_path()

    bootloader = Bootloader(config_path)
    result = bootloader.boot()

    if not result.success:
        print(f"Boot failed: {result.message}")
        return 1

    kernel = bootloader.get_kernel()
    kernel.run()

    # Run test commands
    print("\n=== Running test commands ===\n")

    # Test filesystem
    vfs = kernel.filesystem
    if vfs:
        print("Creating test file...")
        from pyos.filesystem.vfs import OpenMode

        fd = vfs.open("/tmp/test.txt", OpenMode.WRITE, uid=0, gid=0)
        vfs.write(fd, b"Hello, PyOS!\n")
        vfs.close(fd)

        print("Reading test file...")
        fd = vfs.open("/tmp/test.txt", OpenMode.READ, uid=0, gid=0)
        content = vfs.read(fd)
        vfs.close(fd)
        print(f"Content: {content.decode()}")

    # Test process manager
    pm = kernel.process_manager
    if pm:
        print("\nProcess list:")
        for proc in pm.list_processes():
            print(f"  PID {proc['pid']}: {proc['name']} ({proc['state']})")

    # Test memory manager
    mm = kernel.memory_manager
    if mm:
        print(f"\nMemory stats: {mm.get_stats()}")

    # Shutdown
    bootloader.shutdown()

    print("\n=== Test complete ===\n")
    return 0


def _parse_args(argv: list[str]) -> bool:
    """Return True if headless mode is requested."""
    return len(argv) > 1 and argv[1] == "--headless"


if __name__ == "__main__":
    # Check for headless mode
    if _parse_args(sys.argv):
        sys.exit(run_headless())

    # Run normal interactive mode
    main()
