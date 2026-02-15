# PyOS - A UNIX-Inspired Operating System Simulation

<div align="center">

![PyOS Version](https://img.shields.io/badge/version-1.0.0-blue.svg)
![Python](https://img.shields.io/badge/python-3.10+-green.svg)
![License](https://img.shields.io/badge/license-MIT-orange.svg)
![Architecture](https://img.shields.io/badge/architecture-microkernel-purple.svg)

**A complete, production-grade operating system simulation implemented entirely in Python 3.10+ using only the standard library.**

*This is NOT a toy project. It resembles real OS architecture.*

</div>

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Directory Structure](#directory-structure)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Subsystem Documentation](#subsystem-documentation)
  - [Kernel Core](#kernel-core)
  - [Process Management](#process-management)
  - [Memory Management](#memory-management)
  - [Virtual File System](#virtual-file-system)
  - [User Management](#user-management)
  - [System Calls](#system-calls)
  - [IPC](#ipc)
  - [Security](#security)
  - [Monitoring](#monitoring)
  - [Shell](#shell)
  - [Plugins](#plugins)
- [API Reference](#api-reference)
- [Examples](#examples)
- [Design Decisions](#design-decisions)
- [Contributing](#contributing)
- [License](#license)

---

## Overview

PyOS is a comprehensive operating system simulation that implements core OS concepts following UNIX design principles. It provides a realistic environment for learning operating system internals while maintaining clean, production-quality code.

### Key Design Principles

- **Microkernel Architecture**: Core services run as modular subsystems
- **SOLID Principles**: Clean separation of concerns throughout
- **Type Safety**: Full type hints with strict typing
- **Documentation**: Comprehensive docstrings and comments
- **Standard Library Only**: No external dependencies required

---

## Features

### Core Subsystems

| Subsystem | Description |
|-----------|-------------|
| **Kernel** | Central kernel with singleton pattern, subsystem management, and graceful shutdown |
| **Process Manager** | PCB-based process lifecycle, signals, and multiple scheduling algorithms |
| **Scheduler** | Round Robin, Priority-based, and Multi-Level Feedback Queue (MLFQ) schedulers |
| **Memory Manager** | Virtual memory, paging, buddy allocator, and slab allocator |
| **VFS** | Inode-based virtual filesystem with POSIX permissions |
| **User Manager** | Authentication, sessions, and Role-Based Access Control (RBAC) |
| **Syscalls** | System call dispatcher with 30+ syscall handlers |
| **IPC** | Pipes, message queues, and shared memory segments |
| **Security** | Sandbox, resource limits, and security policies |
| **Monitoring** | Metrics collection, health checks, and observability |
| **Shell** | Interactive REPL with 30+ built-in commands |
| **Plugins** | Dynamic plugin loading with dependency management |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER SPACE                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐         │
│  │  Shell   │  │  Apps    │  │ Plugins  │  │  Users   │         │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘         │
│       │             │             │             │               │
│       └─────────────┴─────────────┴─────────────┘               │
│                           │                                     │
│                    ┌──────▼──────┐                              │
│                    │  Syscalls   │                              │
│                    └──────┬──────┘                              │
├───────────────────────────┼─────────────────────────────────────┤
│                     KERNEL SPACE                                │
│                    ┌──────▼──────┐                              │
│                    │   Kernel    │◄──────────────────────┐      │
│                    │    Core     │                       │      │
│                    └──────┬──────┘                       │      │
│                           │                              │      │
│  ┌────────────────────────┼────────────────────────┐     │      │
│  │                        │                        │     │      │
│  │  ┌─────────┐  ┌────────▼────────┐  ┌─────────┐  │     │      │
│  │  │ Memory  │  │ Process Manager │  │   VFS   │  │     │      │
│  │  │ Manager │  │   + Scheduler   │  │         │  │     │      │
│  │  └─────────┘  └─────────────────┘  └─────────┘  │     │      │
│  │                                                 │     │      │
│  │  ┌─────────┐  ┌─────────────────┐  ┌─────────┐  │     │      │
│  │  │  User   │  │      IPC        │  │Security │  │     │      │
│  │  │ Manager │  │ Pipes/MQ/SHM    │  │ Manager │  │     │      │
│  │  └─────────┘  └─────────────────┘  └─────────┘  │     │      │
│  │                                                 │     │      │
│  │  ┌─────────┐  ┌─────────────────┐               │     │      │
│  │  │ Syscall │  │   Monitoring    │───────────────┘     │      │
│  │  │Dispatch │  │                 │                     │      │
│  │  └─────────┘  └─────────────────┘                     │      │
│  │                                                       │      │
│  │              ┌─────────────────┐                      │      │
│  │              │   Registry      │──────────────────────┘      │
│  │              │  (Service       │                             │
│  │              │   Locator)      │                             │
│  │              └─────────────────┘                             │
│  └──────────────────────────────────────────────────────────────┤
│                           │                                     │
│                    ┌──────▼──────┐                              │
│                    │ Event Loop  │                              │
│                    │ + Interrupts│                              │
│                    └─────────────┘                              │
└─────────────────────────────────────────────────────────────────┘
```

---

## Directory Structure

```
pyos/
├── main.py                 # Main entry point
├── config.json             # System configuration
├── __init__.py             # Package initialization
├── logger.py               # Structured logging system
│
├── core/                   # Core kernel components
│   ├── __init__.py
│   ├── kernel.py           # Central kernel implementation
│   ├── bootloader.py       # Boot sequence management
│   ├── registry.py         # Subsystem registry & lifecycle
│   ├── event_loop.py       # Event loop & interrupt handling
│   └── config_loader.py    # Configuration management
│
├── process/                # Process management
│   ├── __init__.py
│   ├── process_manager.py  # Process lifecycle management
│   ├── pcb.py              # Process Control Block
│   ├── scheduler.py        # RR, Priority, MLFQ schedulers
│   ├── states.py           # Process states & signals
│   └── context_switch.py   # Context switching simulation
│
├── memory/                 # Memory management
│   ├── __init__.py
│   ├── memory_manager.py   # Memory manager facade
│   ├── virtual_memory.py   # Virtual address spaces
│   ├── paging.py           # Page tables & frame allocation
│   └── allocator.py        # Buddy & slab allocators
│
├── filesystem/             # Virtual filesystem
│   ├── __init__.py
│   ├── vfs.py              # VFS implementation
│   ├── inode.py            # Inode structures
│   └── path_resolver.py    # Path resolution
│
├── users/                  # User management
│   ├── __init__.py
│   └── user_manager.py     # Auth, sessions, RBAC
│
├── syscalls/               # System calls
│   ├── __init__.py
│   ├── dispatcher.py       # Syscall dispatcher
│   └── syscall_table.py    # Syscall definitions
│
├── ipc/                    # Inter-process communication
│   ├── __init__.py
│   └── pipe.py             # Pipes & message queues
│
├── security/               # Security subsystem
│   ├── __init__.py
│   └── sandbox.py          # Sandbox & resource limits
│
├── monitoring/             # System monitoring
│   ├── __init__.py
│   └── metrics.py          # Metrics & health checks
│
├── shell/                  # Interactive shell
│   ├── __init__.py
│   ├── shell.py            # Shell REPL
│   ├── parser.py           # Command parser
│   └── builtins.py         # Built-in commands
│
├── plugins/                # Plugin architecture
│   ├── __init__.py
│   ├── plugin_interface.py # Plugin base class
│   └── plugin_loader.py    # Plugin loader
│
├── exceptions/             # Exception hierarchy
│   ├── __init__.py
│   ├── kernel_exceptions.py
│   ├── process_exceptions.py
│   ├── memory_exceptions.py
│   ├── fs_exceptions.py
│   ├── security_exceptions.py
│   └── ipc_exceptions.py
│
└── tests/                  # Unit tests
    ├── __init__.py
    └── unit_tests.py       # Comprehensive test suite
```

---

## Installation

### Requirements

- Python 3.10 or higher
- No external dependencies required (uses only standard library)

### Setup

```bash
# Clone the repository
git clone https://github.com/ysnrfd/pyos.git
cd pyos

# Run directly (no installation needed)
python pyos/main.py
```

---

## Quick Start

### Interactive Mode

```bash
python pyos/main.py
```

### Headless Mode (for testing)

```bash
python pyos/main.py --headless
```

### Sample Session

```
PyOS Boot Sequence
==================================================
[2024-01-15 10:30:00.048] INFO     [bootloader] PyOS Bootloader starting...
[2024-01-15 10:30:00.048] INFO     [kernel] Kernel initializing...
[2024-01-15 10:30:00.092] INFO     [kernel] All subsystems initialized
[2024-01-15 10:30:00.093] INFO     [bootloader] PyOS v1.0.0 {run_level=3}
[2024-01-15 10:30:00.093] INFO     [bootloader] Welcome to PyOS - A UNIX-inspired Operating System Simulation
[2024-01-15 10:30:00.093] INFO     [bootloader] Boot complete {elapsed_ms=45.30}

Boot completed in 45.30ms
==================================================

PyOS Shell v1.0.0
Type 'help' for available commands.

root@pyos:/ $ help
PyOS Shell - Built-in Commands

File Operations:
  ls [path]         List directory contents
  cd <path>         Change directory
  pwd               Print working directory
  ...

root@pyos:/ $ ls
drwxr-xr-x        0 bin/
drwxr-xr-x        0 dev/
drwxr-xr-x        0 etc/
drwxr-xr-x        0 home/
drwxr-xr-x        0 tmp/
drwxr-xr-x        0 var/

root@pyos:/ $ ps
   PID   PPID STATE     NAME                
--------------------------------------------------
     1      0 RUNNING   init                

root@pyos:/ $ free
              total        used        free
Mem:      67108864           0    67108864

root@pyos:/ $ uname -a
PyOS 1.0.0 PyOS x86_64

root@pyos:/ $ exit
[2024-01-15 10:30:05.094] INFO     [bootloader] System shutdown complete
```

---

## Configuration

PyOS is configured via `config.json`:

```json
{
    "kernel": {
        "name": "PyOS",
        "version": "1.0.0",
        "boot_message": "Welcome to PyOS - A UNIX-inspired Operating System Simulation"
    },
    "scheduler": {
        "algorithm": "round_robin",
        "quantum": 100,
        "priority_levels": 10,
        "enable_preemption": true
    },
    "memory": {
        "total_memory": 67108864,
        "page_size": 4096,
        "max_processes": 256,
        "max_memory_per_process": 16777216
    },
    "filesystem": {
        "root_path": "/",
        "max_file_size": 10485760,
        "max_open_files": 1024,
        "enable_journaling": true
    },
    "process": {
        "max_pid": 32768,
        "init_process": "init",
        "zombie_timeout": 60,
        "max_processes": 256
    },
    "security": {
        "enable_sandbox": true,
        "max_cpu_time_per_process": 3600,
        "max_file_descriptors": 1024,
        "allow_root_login": true
    },
    "logging": {
        "level": "INFO",
        "log_file": "/var/log/pyos.log",
        "max_log_size": 1048576,
        "console_output": true
    },
    "users": {
        "default_user": "root",
        "default_shell": "/bin/pysh",
        "home_prefix": "/home"
    },
    "ipc": {
        "max_pipes": 256,
        "max_message_queues": 64,
        "max_shared_memory_segments": 32,
        "pipe_buffer_size": 65536
    },
    "shell": {
        "prompt": "$ ",
        "history_size": 1000,
        "enable_autocomplete": true
    },
    "boot": {
        "auto_start_services": ["filesystem", "process_manager", "memory_manager"],
        "init_user": "root",
        "run_level": 3
    }
}
```

### Configuration Options

| Section | Option | Description | Default |
|---------|--------|-------------|---------|
| `kernel` | `name` | OS name | `"PyOS"` |
| `kernel` | `version` | OS version | `"1.0.0"` |
| `scheduler` | `algorithm` | Scheduling algorithm | `"round_robin"` |
| `scheduler` | `quantum` | Time quantum in milliseconds | `100` |
| `memory` | `total_memory` | Total memory in bytes | `67108864` (64MB) |
| `memory` | `page_size` | Page size in bytes | `4096` |
| `filesystem` | `max_file_size` | Maximum file size | `10485760` (10MB) |
| `security` | `enable_sandbox` | Enable process sandboxing | `true` |
| `logging` | `level` | Log level | `"INFO"` |

---

## Subsystem Documentation

### Kernel Core

The kernel is the heart of PyOS, implemented as a singleton that manages all subsystems.

```python
from pyos.core.kernel import Kernel, get_kernel

# Get kernel instance (singleton)
kernel = get_kernel()

# Initialize kernel
kernel.initialize()

# Initialize subsystems
kernel.initialize_subsystems()

# Run main loop
kernel.run()

# Get kernel info
info = kernel.get_info()
print(f"{info.name} v{info.version}")
print(f"Uptime: {info.uptime:.2f}s")
print(f"Processes: {info.process_count}")
```

#### Kernel States

| State | Description |
|-------|-------------|
| `UNINITIALIZED` | Kernel not yet initialized |
| `INITIALIZING` | Kernel is initializing |
| `INITIALIZED` | Kernel initialized, subsystems not started |
| `RUNNING` | Normal operation |
| `SHUTTING_DOWN` | Shutdown in progress |
| `SHUTDOWN` | System halted |
| `PANIC` | Unrecoverable error |

---

### Process Management

PyOS implements a complete process lifecycle with PCB-based tracking.

#### Process Control Block (PCB)

```python
from pyos.process.pcb import ProcessControlBlock
from pyos.process.states import ProcessState

# PCB contains:
# - pid: Process ID
# - ppid: Parent Process ID
# - name: Process name
# - state: Current state
# - priority: Scheduling priority
# - uid/gid: User/Group IDs
# - memory: Memory regions
# - file_descriptors: Open files
# - cwd: Current working directory
```

#### Process States

```
    NEW ──────────► READY ◄──────────┐
                     │               │
                     ▼               │
                  RUNNING ──────────►│
                     │   (preempt)   │
                     │               │
                     ▼               │
                  WAITING ───────────┘
                     │
                     ▼
                TERMINATED ──► ZOMBIE
```

#### Scheduler Algorithms

```python
from pyos.process.scheduler import (
    RoundRobinScheduler,
    PriorityScheduler,
    MLFQScheduler
)

# Round Robin
rr_scheduler = RoundRobinScheduler(quantum=100)

# Priority-based
p_scheduler = PriorityScheduler(priority_levels=10)

# Multi-Level Feedback Queue
mlfq_scheduler = MLFQScheduler(num_queues=8)
```

---

### Memory Management

PyOS implements virtual memory with paging and multiple allocators.

#### Memory Layout

```
Virtual Address Space (per process):
┌────────────────────┐ 0xFFFFFFFF
│   Kernel Space     │ (not accessible from user mode)
├────────────────────┤ 0x80000000
│   Stack (grows ↓)  │
│        ↓           │
├────────────────────┤
│                    │
│   Free Space       │
│                    │
├────────────────────┤
│        ↑           │
│   Heap (grows ↑)   │
├────────────────────┤
│   BSS Segment      │
├────────────────────┤
│   Data Segment     │
├────────────────────┤
│   Text Segment     │
└────────────────────┘ 0x00000000
```

#### Memory APIs

```python
from pyos.memory.memory_manager import MemoryManager

mm = MemoryManager()

# Get memory statistics
stats = mm.get_stats()
# Returns: {
#     'total': 67108864,
#     'used': 1048576,
#     'free': 66060288,
#     'utilization': 0.016,
#     'total_frames': 16384,
#     'free_frames': 16358,
#     'address_spaces': 5
# }

# Create address space for process
addr_space = mm.create_address_space(pid=1)

# Allocate pages
pages = mm.allocate_pages(pid=1, num_pages=4)

# Allocate kernel memory (slab allocator)
block = mm.allocate_kernel(size=1024)
mm.free_kernel(block)
```

---

### Virtual File System

PyOS implements an inode-based VFS with POSIX-style permissions.

#### Inode Structure

```python
from pyos.filesystem.inode import Inode, InodeType, Permission

# Inode types
class InodeType(Enum):
    FILE = auto()
    DIRECTORY = auto()
    SYMLINK = auto()
    DEVICE = auto()

# POSIX permissions
class Permission:
    S_IRUSR = 0o400  # Owner read
    S_IWUSR = 0o200  # Owner write
    S_IXUSR = 0o100  # Owner execute
    S_IRGRP = 0o040  # Group read
    S_IWGRP = 0o020  # Group write
    S_IXGRP = 0o010  # Group execute
    S_IROTH = 0o004  # Others read
    S_IWOTH = 0o002  # Others write
    S_IXOTH = 0o001  # Others execute
```

#### File Operations

```python
from pyos.filesystem.vfs import VirtualFileSystem, OpenMode

vfs = VirtualFileSystem()

# Create directory
vfs.mkdir('/home/user', mode=0o755, uid=1000, gid=1000)

# Create file
fd = vfs.open('/home/user/test.txt', OpenMode.WRITE | OpenMode.CREATE, uid=1000, gid=1000)
vfs.write(fd, b'Hello, World!')
vfs.close(fd)

# Read file
fd = vfs.open('/home/user/test.txt', OpenMode.READ, uid=1000, gid=1000)
content = vfs.read(fd)
vfs.close(fd)

# List directory
entries = vfs.readdir('/home/user', cwd='/')
for entry in entries:
    print(f"{entry['name']}: {entry['type']}")
```

---

### User Management

PyOS supports multi-user operation with authentication and RBAC.

```python
from pyos.users.user_manager import UserManager, Role, Permission

um = UserManager()

# Create user
user = um.create_user('alice', 'password123')

# Authenticate
session = um.login('alice', 'password123')
print(f"Session token: {session.session_id}")

# Check permissions
if um.check_permission(user.uid, Permission.FILE_READ):
    print("User can read files")

# Role-based access
um.assign_role(user.uid, Role.ADMIN)

# Logout
um.logout(session.session_id)
```

#### Roles & Permissions

| Role | Permissions |
|------|-------------|
| `GUEST` | Read-only access |
| `USER` | Standard user access |
| `POWER_USER` | Extended permissions |
| `ADMIN` | Administrative access |
| `ROOT` | Full system access |

---

### System Calls

PyOS provides a comprehensive syscall interface.

#### Available System Calls

| Syscall | Description |
|---------|-------------|
| `read` | Read from file descriptor |
| `write` | Write to file descriptor |
| `open` | Open file |
| `close` | Close file descriptor |
| `fork` | Create child process |
| `exec` | Execute program |
| `exit` | Terminate process |
| `wait` | Wait for child process |
| `getpid` | Get process ID |
| `kill` | Send signal to process |
| `mkdir` | Create directory |
| `rmdir` | Remove directory |
| `unlink` | Remove file |
| `chmod` | Change permissions |
| `chown` | Change ownership |
| `brk` | Change data segment size |
| `mmap` | Map memory |
| `munmap` | Unmap memory |
| `pipe` | Create pipe |
| `dup` | Duplicate file descriptor |

#### Using Syscalls

```python
from pyos.syscalls.dispatcher import SyscallDispatcher

dispatcher = SyscallDispatcher()

# Dispatch syscall
result = dispatcher.dispatch({
    'syscall': 'open',
    'path': '/etc/passwd',
    'mode': 'r',
    'uid': 0,
    'gid': 0
})
```

---

### IPC

PyOS implements multiple IPC mechanisms.

#### Pipes

```python
from pyos.ipc.pipe import Pipe, IPCManager

# Create pipe
pipe = Pipe(buffer_size=65536)

# Write to pipe
pipe.write(b'Hello through pipe!', writer_pid=1)

# Read from pipe
data = pipe.read(size=1024, reader_pid=2)
```

#### Message Queues

```python
# Create message queue
mq = ipc_manager.create_message_queue(key=1234)

# Send message
mq.send(message={'type': 1, 'data': 'Hello'}, sender_pid=1)

# Receive message
msg = mq.receive(receiver_pid=2, msg_type=1)
```

#### Shared Memory

```python
# Create shared memory segment
shm = ipc_manager.create_shared_memory(size=4096, key=5678)

# Attach to process
shm.attach(pid=1)

# Read/write
shm.write(0, b'Data in shared memory')
data = shm.read(0, 20)
```

---

### Security

PyOS implements security sandboxing and resource limits.

```python
from pyos.security.sandbox import SecurityManager, ResourceLimit

sm = SecurityManager()

# Set resource limits
sm.set_limit(pid=1, ResourceLimit.CPU_TIME, 3600)
sm.set_limit(pid=1, ResourceLimit.MEMORY, 16777216)
sm.set_limit(pid=1, ResourceLimit.FILE_DESCRIPTORS, 1024)

# Check access
if sm.check_file_access(pid=1, '/etc/shadow', 'read'):
    print("Access granted")

# Create sandbox
sandbox = sm.create_sandbox(pid=1, policy='restricted')
```

#### Resource Limits

| Limit | Description |
|-------|-------------|
| `CPU_TIME` | Maximum CPU seconds |
| `MEMORY` | Maximum memory bytes |
| `FILE_DESCRIPTORS` | Maximum open files |
| `PROCESSES` | Maximum child processes |
| `FILE_SIZE` | Maximum file size |

---

### Monitoring

PyOS provides comprehensive system monitoring.

```python
from pyos.monitoring.metrics import MonitoringManager

mon = MonitoringManager()

# Get metrics
metrics = mon.collect_metrics()
# Returns:
# {
#     'cpu': {'utilization': 0.25, 'processes': 5},
#     'memory': {'used': 1048576, 'free': 66060288},
#     'processes': {'running': 1, 'sleeping': 4, 'zombies': 0},
#     'filesystem': {'reads': 150, 'writes': 45},
#     'uptime': 3600.5
# }

# Health check
health = mon.health_check()
# Returns: {'kernel': True, 'memory': True, 'filesystem': True, ...}
```

---

### Shell

PyOS includes an interactive shell with 30+ built-in commands.

#### Built-in Commands

| Command | Description |
|---------|-------------|
| `help` | Display help |
| `exit` | Exit shell |
| `ls` | List directory |
| `cd` | Change directory |
| `pwd` | Print working directory |
| `mkdir` | Create directory |
| `rmdir` | Remove directory |
| `touch` | Create file |
| `rm` | Remove file |
| `cat` | Display file contents |
| `echo` | Print text |
| `ps` | List processes |
| `kill` | Send signal |
| `chmod` | Change permissions |
| `chown` | Change ownership |
| `whoami` | Current user |
| `id` | User/Group IDs |
| `uname` | System info |
| `uptime` | System uptime |
| `free` | Memory usage |
| `df` | Disk usage |
| `date` | Current date/time |
| `clear` | Clear screen |
| `history` | Command history |
| `export` | Set variable |
| `env` | Show environment |
| `useradd` | Create user |
| `userdel` | Delete user |
| `passwd` | Change password |
| `su` | Switch user |
| `login` | Login |
| `logout` | Logout |

---

### Plugins

PyOS supports a plugin architecture for extensibility.

```python
from pyos.plugins.plugin_interface import Plugin, PluginInfo
from pyos.plugins.plugin_loader import PluginLoader

# Define plugin
class MyPlugin(Plugin):
    @property
    def info(self) -> PluginInfo:
        return PluginInfo(
            name='my_plugin',
            version='1.0.0',
            description='My custom plugin',
            author='Developer',
            dependencies=[]
        )
    
    def initialize(self) -> None:
        print("Plugin initialized!")
    
    def cleanup(self) -> None:
        print("Plugin cleaned up!")

# Load plugin
loader = PluginLoader()
loader.load_plugin('/path/to/plugin')
loader.initialize_all()
```

---

## API Reference

### Kernel API

```python
class Kernel:
    """Central kernel singleton."""
    
    @property
    def state(self) -> KernelState: ...
    @property
    def uptime(self) -> float: ...
    @property
    def process_manager(self) -> ProcessManager: ...
    @property
    def memory_manager(self) -> MemoryManager: ...
    @property
    def filesystem(self) -> VirtualFileSystem: ...
    @property
    def user_manager(self) -> UserManager: ...
    @property
    def security_manager(self) -> SecurityManager: ...
    @property
    def ipc_manager(self) -> IPCManager: ...
    @property
    def monitoring(self) -> MonitoringManager: ...
    
    def initialize(self) -> None: ...
    def initialize_subsystems(self) -> None: ...
    def run(self) -> None: ...
    def shutdown(self) -> None: ...
    def panic(self, message: str) -> None: ...
    def get_info(self) -> KernelInfo: ...
```

### Process Manager API

```python
class ProcessManager(Subsystem):
    def create_process(self, name: str, parent_pid: int, **kwargs) -> ProcessControlBlock: ...
    def terminate_process(self, pid: int) -> None: ...
    def get_process(self, pid: int) -> Optional[ProcessControlBlock]: ...
    def list_processes(self) -> List[dict]: ...
    def schedule(self) -> Optional[int]: ...
    def kill(self, pid: int, signal: Signal) -> None: ...
    def wait(self, pid: int) -> Optional[int]: ...
```

### Memory Manager API

```python
class MemoryManager(Subsystem):
    def create_address_space(self, pid: int) -> AddressSpace: ...
    def destroy_address_space(self, pid: int) -> None: ...
    def allocate_pages(self, pid: int, num_pages: int) -> List[int]: ...
    def free_pages(self, pid: int, pages: List[int]) -> None: ...
    def allocate_kernel(self, size: int) -> int: ...
    def free_kernel(self, ptr: int) -> None: ...
    def get_stats(self) -> dict: ...
```

### VFS API

```python
class VirtualFileSystem(Subsystem):
    def open(self, path: str, mode: OpenMode, uid: int, gid: int) -> int: ...
    def close(self, fd: int) -> None: ...
    def read(self, fd: int, size: int = -1) -> bytes: ...
    def write(self, fd: int, data: bytes) -> int: ...
    def mkdir(self, path: str, mode: int, uid: int, gid: int) -> None: ...
    def rmdir(self, path: str, uid: int, gid: int) -> None: ...
    def unlink(self, path: str, uid: int, gid: int) -> None: ...
    def stat(self, path: str, cwd: str) -> Optional[Inode]: ...
    def readdir(self, path: str, cwd: str) -> List[dict]: ...
```

---

## Examples

### Creating a Simple Process

```python
from pyos.core.bootloader import boot_system

# Boot the system
result, kernel = boot_system()

if result.success:
    # Create a process
    pm = kernel.process_manager
    pcb = pm.create_process(
        name='my_process',
        parent_pid=1,
        uid=1000,
        gid=1000,
        priority=5
    )
    
    print(f"Created process PID: {pcb.pid}")
    
    # Do work...
    
    # Shutdown
    kernel.shutdown()
```

### Working with Files

```python
from pyos.core.kernel import get_kernel
from pyos.filesystem.vfs import OpenMode

kernel = get_kernel()
vfs = kernel.filesystem

# Create and write file
fd = vfs.open('/tmp/example.txt', OpenMode.WRITE | OpenMode.CREATE, uid=0, gid=0)
vfs.write(fd, b'Hello, PyOS!\nThis is a test file.\n')
vfs.close(fd)

# Read file back
fd = vfs.open('/tmp/example.txt', OpenMode.READ, uid=0, gid=0)
content = vfs.read(fd)
print(content.decode())
vfs.close(fd)
```

### Using IPC

```python
from pyos.core.kernel import get_kernel

kernel = get_kernel()
ipc = kernel.ipc_manager

# Create pipe
read_fd, write_fd = ipc.create_pipe()

# Write from process 1
ipc.write_pipe(write_fd, b'Hello from process 1!', pid=1)

# Read from process 2
data = ipc.read_pipe(read_fd, size=1024, pid=2)
print(data.decode())
```

---

## Design Decisions

### Why Python Standard Library Only?

1. **Portability**: Runs anywhere Python 3.10+ is available
2. **Educational**: Focus on OS concepts, not framework details
3. **Simplicity**: No dependency management issues
4. **Transparency**: All code is understandable without external docs

### Why Microkernel Architecture?

1. **Modularity**: Each subsystem is independent and testable
2. **Flexibility**: Easy to add, remove, or modify subsystems
3. **Fault Isolation**: Problems in one subsystem don't crash others
4. **Real-world Relevance**: Modern OS design patterns

### Singleton Pattern for Kernel

1. **Single Point of Control**: Centralized resource management
2. **Global Access**: Easy access from any component
3. **State Consistency**: No conflicting kernel states

---

## Testing

### Run Unit Tests

```bash
cd pyos/tests
python unit_tests.py
```

### Run Headless Test

```bash
python pyos/main.py --headless
```

### Example Test Output

```
=== Running test commands ===

Creating test file...
Reading test file...
Content: Hello, PyOS!

Process list:
  PID 1: init (RUNNING)

Memory stats: {'total': 67108864, 'used': 0, 'free': 67108864, ...}

=== Test complete ===
```

---

## Performance

PyOS is designed for educational purposes and realistic OS simulation, not raw performance. However, it achieves:

- **Boot time**: ~45ms
- **Process creation**: <1ms
- **Memory allocation**: <0.1ms
- **File operations**: <0.5ms

---

## Contributing

Contributions are welcome! Please follow these guidelines:

1. **Code Style**: Follow PEP 8 and use type hints
2. **Documentation**: Add docstrings to all public APIs
3. **Testing**: Add tests for new functionality
4. **Architecture**: Maintain separation of concerns


---

## License

MIT License

Copyright (c) 2026 YSNRFD

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

---

<div align="center">

**PyOS - Real Operating System Concepts in Python**

*Built with ❤️ for education and exploration*

</div>
