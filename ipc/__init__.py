"""
PyOS IPC Module

Provides inter-process communication:
- Pipes
- Message queues
- Shared memory
"""

from .pipe import IPCManager, Pipe, Message, MessageQueue, SharedMemorySegment

__all__ = [
    'IPCManager',
    'Pipe',
    'Message',
    'MessageQueue',
    'SharedMemorySegment',
]
