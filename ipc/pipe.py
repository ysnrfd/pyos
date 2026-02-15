"""
IPC Manager Module

Implements inter-process communication:
- Pipes
- Message queues
- Shared memory simulation

Author: YSNRFD
Version: 1.0.0
"""

import threading
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Optional, Any, List

from pyos.core.registry import Subsystem, SubsystemState
from pyos.core.config_loader import get_config
from pyos.exceptions import PipeError, MessageQueueError
from pyos.logger import Logger, get_logger


@dataclass
class Pipe:
    """A pipe for one-way communication."""
    pipe_id: int
    buffer: deque = field(default_factory=deque)
    read_fd: Optional[int] = None
    write_fd: Optional[int] = None
    owner_pid: int = 0
    buffer_size: int = 65536
    
    def read(self, size: int = -1) -> bytes:
        """Read from the pipe."""
        if not self.buffer:
            return bytes()
        
        if size < 0:
            size = len(self.buffer)
        
        data = bytes()
        for _ in range(min(size, len(self.buffer))):
            if self.buffer:
                data += self.buffer.popleft()
        
        return data
    
    def write(self, data: bytes) -> int:
        """Write to the pipe."""
        if len(self.buffer) + len(data) > self.buffer_size:
            raise PipeError("Pipe buffer full", pipe_id=self.pipe_id)
        
        self.buffer.append(data)
        return len(data)
    
    @property
    def available(self) -> int:
        return len(self.buffer)


@dataclass
class Message:
    """A message for message queue."""
    message_id: int
    type: int
    data: bytes
    sender_pid: int
    timestamp: float = field(default_factory=time.time)


@dataclass
class MessageQueue:
    """A message queue for IPC."""
    queue_id: int
    messages: deque = field(default_factory=deque)
    owner_pid: int = 0
    max_messages: int = 64
    max_size: int = 4096


@dataclass
class SharedMemorySegment:
    """A shared memory segment."""
    segment_id: int
    size: int
    data: bytearray
    attached_pids: List[int] = field(default_factory=list)
    owner_pid: int = 0
    permissions: int = 0o600


class IPCManager(Subsystem):
    """
    Inter-Process Communication Manager.
    
    Provides:
    - Pipe creation and management
    - Message queues
    - Shared memory segments
    
    Example:
        >>> ipc = IPCManager()
        >>> read_fd, write_fd = ipc.create_pipe(pid=1)
    """
    
    def __init__(self):
        super().__init__('ipc')
        self._pipes: dict[int, Pipe] = {}
        self._pipes_by_fd: dict[int, int] = {}  # fd -> pipe_id
        self._next_pipe_id = 1
        self._next_fd = 100  # Start pipe FDs at 100
        
        self._queues: dict[int, MessageQueue] = {}
        self._next_queue_id = 1
        
        self._segments: dict[int, SharedMemorySegment] = {}
        self._next_segment_id = 1
        
        self._lock = threading.Lock()
    
    def initialize(self) -> None:
        """Initialize the IPC manager."""
        config = get_config()
        
        self._max_pipes = config.ipc.max_pipes
        self._max_queues = config.ipc.max_message_queues
        self._max_segments = config.ipc.max_shared_memory_segments
        self._pipe_buffer_size = config.ipc.pipe_buffer_size
        
        self.set_state(SubsystemState.INITIALIZED)
        self._logger.info("IPC manager initialized")
    
    def start(self) -> None:
        """Start the IPC manager."""
        self.set_state(SubsystemState.RUNNING)
    
    def stop(self) -> None:
        """Stop the IPC manager."""
        self.set_state(SubsystemState.STOPPED)
    
    def cleanup(self) -> None:
        """Clean up resources."""
        self._pipes.clear()
        self._queues.clear()
        self._segments.clear()
    
    # Pipe operations
    
    def create_pipe(self, owner_pid: int) -> tuple[int, int]:
        """
        Create a new pipe.
        
        Args:
            owner_pid: Process ID that owns the pipe
        
        Returns:
            Tuple of (read_fd, write_fd)
        """
        with self._lock:
            if len(self._pipes) >= self._max_pipes:
                raise PipeError("Maximum pipes reached")
            
            pipe_id = self._next_pipe_id
            self._next_pipe_id += 1
            
            read_fd = self._next_fd
            self._next_fd += 1
            write_fd = self._next_fd
            self._next_fd += 1
            
            pipe = Pipe(
                pipe_id=pipe_id,
                owner_pid=owner_pid,
                buffer_size=self._pipe_buffer_size,
                read_fd=read_fd,
                write_fd=write_fd
            )
            
            self._pipes[pipe_id] = pipe
            self._pipes_by_fd[read_fd] = pipe_id
            self._pipes_by_fd[write_fd] = pipe_id
            
            self._logger.debug(
                f"Created pipe",
                context={'pipe_id': pipe_id, 'read_fd': read_fd, 'write_fd': write_fd}
            )
            
            return read_fd, write_fd
    
    def read_pipe(self, fd: int, size: int = -1) -> bytes:
        """Read from a pipe by file descriptor."""
        pipe_id = self._pipes_by_fd.get(fd)
        if pipe_id is None:
            raise PipeError("Invalid file descriptor")
        
        pipe = self._pipes.get(pipe_id)
        if pipe is None or pipe.read_fd != fd:
            raise PipeError("Not a read end of pipe")
        
        return pipe.read(size)
    
    def write_pipe(self, fd: int, data: bytes) -> int:
        """Write to a pipe by file descriptor."""
        pipe_id = self._pipes_by_fd.get(fd)
        if pipe_id is None:
            raise PipeError("Invalid file descriptor")
        
        pipe = self._pipes.get(pipe_id)
        if pipe is None or pipe.write_fd != fd:
            raise PipeError("Not a write end of pipe")
        
        return pipe.write(data)
    
    def close_pipe_fd(self, fd: int) -> bool:
        """Close one end of a pipe."""
        pipe_id = self._pipes_by_fd.get(fd)
        if pipe_id is None:
            return False
        
        pipe = self._pipes.get(pipe_id)
        if pipe is None:
            return False
        
        if pipe.read_fd == fd:
            pipe.read_fd = None
        elif pipe.write_fd == fd:
            pipe.write_fd = None
        
        del self._pipes_by_fd[fd]
        
        # Remove pipe if both ends closed
        if pipe.read_fd is None and pipe.write_fd is None:
            del self._pipes[pipe_id]
        
        return True
    
    # Message Queue operations
    
    def create_message_queue(self, owner_pid: int) -> int:
        """Create a new message queue."""
        with self._lock:
            if len(self._queues) >= self._max_queues:
                raise MessageQueueError("Maximum message queues reached")
            
            queue_id = self._next_queue_id
            self._next_queue_id += 1
            
            queue = MessageQueue(
                queue_id=queue_id,
                owner_pid=owner_pid
            )
            
            self._queues[queue_id] = queue
            
            return queue_id
    
    def send_message(
        self,
        queue_id: int,
        sender_pid: int,
        msg_type: int,
        data: bytes
    ) -> int:
        """Send a message to a queue."""
        queue = self._queues.get(queue_id)
        if queue is None:
            raise MessageQueueError("Queue not found", queue_id=queue_id)
        
        if len(queue.messages) >= queue.max_messages:
            raise MessageQueueError("Queue full", queue_id=queue_id)
        
        msg = Message(
            message_id=len(queue.messages) + 1,
            type=msg_type,
            data=data,
            sender_pid=sender_pid
        )
        
        queue.messages.append(msg)
        
        return msg.message_id
    
    def receive_message(
        self,
        queue_id: int,
        msg_type: int = 0
    ) -> Optional[Message]:
        """Receive a message from a queue."""
        queue = self._queues.get(queue_id)
        if queue is None:
            raise MessageQueueError("Queue not found", queue_id=queue_id)
        
        if msg_type == 0:
            # Get first message
            if queue.messages:
                return queue.messages.popleft()
        else:
            # Get message of specific type
            for i, msg in enumerate(queue.messages):
                if msg.type == msg_type:
                    return queue.messages.popleft(i)
        
        return None
    
    # Shared Memory operations
    
    def create_shared_memory(
        self,
        owner_pid: int,
        size: int,
        permissions: int = 0o600
    ) -> int:
        """Create a shared memory segment."""
        with self._lock:
            if len(self._segments) >= self._max_segments:
                raise MessageQueueError("Maximum shared memory segments reached")
            
            segment_id = self._next_segment_id
            self._next_segment_id += 1
            
            segment = SharedMemorySegment(
                segment_id=segment_id,
                size=size,
                data=bytearray(size),
                owner_pid=owner_pid,
                permissions=permissions
            )
            
            self._segments[segment_id] = segment
            
            return segment_id
    
    def attach_shared_memory(self, segment_id: int, pid: int) -> Optional[bytearray]:
        """Attach to a shared memory segment."""
        segment = self._segments.get(segment_id)
        if segment is None:
            return None
        
        if pid not in segment.attached_pids:
            segment.attached_pids.append(pid)
        
        return segment.data
    
    def detach_shared_memory(self, segment_id: int, pid: int) -> bool:
        """Detach from a shared memory segment."""
        segment = self._segments.get(segment_id)
        if segment is None:
            return False
        
        if pid in segment.attached_pids:
            segment.attached_pids.remove(pid)
        
        return True
    
    def delete_shared_memory(self, segment_id: int) -> bool:
        """Delete a shared memory segment."""
        if segment_id in self._segments:
            del self._segments[segment_id]
            return True
        return False
    
    def cleanup_process(self, pid: int) -> None:
        """Clean up IPC resources for a process."""
        # Close pipes
        for pipe_id, pipe in list(self._pipes.items()):
            if pipe.owner_pid == pid:
                if pipe.read_fd and pipe.read_fd in self._pipes_by_fd:
                    del self._pipes_by_fd[pipe.read_fd]
                if pipe.write_fd and pipe.write_fd in self._pipes_by_fd:
                    del self._pipes_by_fd[pipe.write_fd]
                del self._pipes[pipe_id]
        
        # Remove message queues
        for queue_id, queue in list(self._queues.items()):
            if queue.owner_pid == pid:
                del self._queues[queue_id]
        
        # Detach shared memory
        for segment in self._segments.values():
            if pid in segment.attached_pids:
                segment.attached_pids.remove(pid)
    
    def get_stats(self) -> dict[str, Any]:
        """Get IPC statistics."""
        return {
            'pipes': len(self._pipes),
            'message_queues': len(self._queues),
            'shared_segments': len(self._segments),
            'total_fds': len(self._pipes_by_fd),
        }
