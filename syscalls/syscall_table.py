"""
Syscall Table Module

Defines the system call numbers and their handlers.

Author: YSNRFD
Version: 1.0.0
"""

from enum import IntEnum


class SyscallNumber(IntEnum):
    """System call numbers."""
    # Process management
    EXIT = 1
    FORK = 2
    READ = 3
    WRITE = 4
    OPEN = 5
    CLOSE = 6
    WAITPID = 7
    CREAT = 8
    LINK = 9
    UNLINK = 10
    EXECVE = 11
    CHDIR = 12
    TIME = 13
    KILL = 14
    
    # File operations
    LSEEK = 19
    GETPID = 20
    MOUNT = 21
    UOUNT = 22
    SETUID = 23
    GETUID = 24
    ACCESS = 33
    
    # Directory operations
    MKDIR = 39
    RMDIR = 40
    DUP = 41
    PIPE = 42
    
    # Memory
    BRK = 45
    MMAP = 90
    MUNMAP = 91
    
    # Filesystem
    CHMOD = 94
    CHOWN = 95
    GETCWD = 79
    STAT = 106
    LSTAT = 107
    
    # IPC
    IPC = 117
    MSGGET = 186
    MSGSND = 189
    MSGRCV = 190
    
    # Process info
    GETPPID = 64
    GETGID = 47
    SETGID = 46


# Mapping of syscall numbers to names
SYSCALL_NAMES = {
    SyscallNumber.EXIT: "exit",
    SyscallNumber.FORK: "fork",
    SyscallNumber.READ: "read",
    SyscallNumber.WRITE: "write",
    SyscallNumber.OPEN: "open",
    SyscallNumber.CLOSE: "close",
    SyscallNumber.WAITPID: "waitpid",
    SyscallNumber.CREAT: "creat",
    SyscallNumber.LINK: "link",
    SyscallNumber.UNLINK: "unlink",
    SyscallNumber.EXECVE: "execve",
    SyscallNumber.CHDIR: "chdir",
    SyscallNumber.TIME: "time",
    SyscallNumber.KILL: "kill",
    SyscallNumber.LSEEK: "lseek",
    SyscallNumber.GETPID: "getpid",
    SyscallNumber.MKDIR: "mkdir",
    SyscallNumber.RMDIR: "rmdir",
    SyscallNumber.DUP: "dup",
    SyscallNumber.PIPE: "pipe",
    SyscallNumber.BRK: "brk",
    SyscallNumber.CHMOD: "chmod",
    SyscallNumber.CHOWN: "chown",
    SyscallNumber.GETCWD: "getcwd",
    SyscallNumber.STAT: "stat",
    SyscallNumber.GETPPID: "getppid",
    SyscallNumber.GETGID: "getgid",
    SyscallNumber.SETGID: "setgid",
}
