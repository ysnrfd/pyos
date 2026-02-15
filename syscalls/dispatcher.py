"""
Syscall Dispatcher Module

Dispatches system calls to appropriate handlers.

Author: YSNRFD
Version: 1.0.0
"""

from dataclasses import dataclass
from typing import Any, Callable, Optional

from .syscall_table import SyscallNumber, SYSCALL_NAMES
from pyos.core.registry import Subsystem, SubsystemState
from pyos.exceptions import ProcessNotFoundError
from pyos.logger import Logger, get_logger


@dataclass
class SyscallResult:
    """Result of a system call."""
    success: bool
    return_value: Any
    error: Optional[str] = None
    error_code: int = 0


class SyscallDispatcher(Subsystem):
    """
    System Call Dispatcher.
    
    Handles system call routing and execution.
    
    Example:
        >>> dispatcher = SyscallDispatcher()
        >>> result = dispatcher.dispatch({
        ...     'number': SyscallNumber.GETPID,
        ...     'args': [],
        ...     'pid': 1
        ... })
    """
    
    def __init__(self):
        super().__init__('syscalls')
        self._handlers: dict[int, Callable] = {}
        self._kernel = None
        self._logger = get_logger('syscalls')
    
    def initialize(self) -> None:
        """Initialize the syscall dispatcher."""
        from pyos.core.kernel import get_kernel
        
        self._kernel = get_kernel()
        
        # Register default handlers
        self._register_handlers()
        
        self.set_state(SubsystemState.INITIALIZED)
        self._logger.info("Syscall dispatcher initialized")
    
    def _register_handlers(self) -> None:
        """Register all syscall handlers."""
        self._handlers = {
            SyscallNumber.EXIT: self._sys_exit,
            SyscallNumber.FORK: self._sys_fork,
            SyscallNumber.READ: self._sys_read,
            SyscallNumber.WRITE: self._sys_write,
            SyscallNumber.OPEN: self._sys_open,
            SyscallNumber.CLOSE: self._sys_close,
            SyscallNumber.GETPID: self._sys_getpid,
            SyscallNumber.GETPPID: self._sys_getppid,
            SyscallNumber.KILL: self._sys_kill,
            SyscallNumber.MKDIR: self._sys_mkdir,
            SyscallNumber.RMDIR: self._sys_rmdir,
            SyscallNumber.UNLINK: self._sys_unlink,
            SyscallNumber.CHDIR: self._sys_chdir,
            SyscallNumber.GETCWD: self._sys_getcwd,
            SyscallNumber.CHMOD: self._sys_chmod,
            SyscallNumber.CHOWN: self._sys_chown,
            SyscallNumber.STAT: self._sys_stat,
            SyscallNumber.LSEEK: self._sys_lseek,
            SyscallNumber.BRK: self._sys_brk,
            SyscallNumber.PIPE: self._sys_pipe,
        }
    
    def start(self) -> None:
        """Start the dispatcher."""
        self.set_state(SubsystemState.RUNNING)
    
    def stop(self) -> None:
        """Stop the dispatcher."""
        self.set_state(SubsystemState.STOPPED)
    
    def cleanup(self) -> None:
        """Clean up."""
        pass
    
    def dispatch(self, call: dict[str, Any]) -> SyscallResult:
        """
        Dispatch a system call.
        
        Args:
            call: Dict with 'number', 'args', 'pid', 'uid', 'gid'
        
        Returns:
            SyscallResult
        """
        number = call.get('number')
        args = call.get('args', [])
        pid = call.get('pid', 0)
        uid = call.get('uid', 0)
        gid = call.get('gid', 0)
        
        name = SYSCALL_NAMES.get(number, f"unknown({number})")
        
        self._logger.debug(
            f"Syscall: {name}",
            pid=pid,
            context={'args': str(args)[:50]}
        )
        
        handler = self._handlers.get(number)
        
        if handler is None:
            return SyscallResult(
                success=False,
                return_value=-1,
                error=f"Unknown syscall: {number}",
                error_code=38  # ENOSYS
            )
        
        try:
            result = handler(pid, uid, gid, *args)
            
            if isinstance(result, SyscallResult):
                return result
            
            return SyscallResult(success=True, return_value=result)
            
        except Exception as e:
            self._logger.error(
                f"Syscall error: {name}",
                pid=pid,
                context={'error': str(e)}
            )
            
            return SyscallResult(
                success=False,
                return_value=-1,
                error=str(e),
                error_code=1  # EPERM
            )
    
    def register_handler(self, number: int, handler: Callable) -> None:
        """Register a handler for a syscall number."""
        self._handlers[number] = handler
    
    # System call implementations
    
    def _sys_exit(self, pid: int, uid: int, gid: int, status: int = 0) -> SyscallResult:
        """exit(status)"""
        if self._kernel and self._kernel.process_manager:
            self._kernel.process_manager.terminate_process(pid, exit_code=status)
        return SyscallResult(success=True, return_value=0)
    
    def _sys_fork(self, pid: int, uid: int, gid: int) -> SyscallResult:
        """fork() -> child_pid"""
        if self._kernel and self._kernel.process_manager:
            try:
                child_pid = self._kernel.process_manager.fork(pid)
                return SyscallResult(success=True, return_value=child_pid)
            except Exception as e:
                return SyscallResult(success=False, return_value=-1, error=str(e))
        return SyscallResult(success=False, return_value=-1, error="No process manager")
    
    def _sys_read(self, pid: int, uid: int, gid: int, fd: int, size: int) -> SyscallResult:
        """read(fd, size) -> data"""
        if self._kernel and self._kernel.filesystem:
            try:
                data = self._kernel.filesystem.read(fd, size)
                return SyscallResult(success=True, return_value=data)
            except Exception as e:
                return SyscallResult(success=False, return_value=-1, error=str(e))
        return SyscallResult(success=False, return_value=-1, error="No filesystem")
    
    def _sys_write(self, pid: int, uid: int, gid: int, fd: int, data: bytes) -> SyscallResult:
        """write(fd, data) -> bytes_written"""
        if self._kernel and self._kernel.filesystem:
            try:
                written = self._kernel.filesystem.write(fd, data)
                return SyscallResult(success=True, return_value=written)
            except Exception as e:
                return SyscallResult(success=False, return_value=-1, error=str(e))
        return SyscallResult(success=False, return_value=-1, error="No filesystem")
    
    def _sys_open(
        self, pid: int, uid: int, gid: int,
        path: str, mode: str = 'r'
    ) -> SyscallResult:
        """open(path, mode) -> fd"""
        from pyos.filesystem.vfs import OpenMode
        
        if self._kernel and self._kernel.filesystem:
            mode_map = {
                'r': OpenMode.READ,
                'w': OpenMode.WRITE,
                'a': OpenMode.APPEND,
                'r+': OpenMode.READ_WRITE,
            }
            
            try:
                fd = self._kernel.filesystem.open(
                    path, mode_map.get(mode, OpenMode.READ),
                    uid=uid, gid=gid, pid=pid
                )
                return SyscallResult(success=True, return_value=fd)
            except Exception as e:
                return SyscallResult(success=False, return_value=-1, error=str(e))
        return SyscallResult(success=False, return_value=-1, error="No filesystem")
    
    def _sys_close(self, pid: int, uid: int, gid: int, fd: int) -> SyscallResult:
        """close(fd)"""
        if self._kernel and self._kernel.filesystem:
            if self._kernel.filesystem.close(fd):
                return SyscallResult(success=True, return_value=0)
            return SyscallResult(success=False, return_value=-1, error="Invalid fd")
        return SyscallResult(success=False, return_value=-1, error="No filesystem")
    
    def _sys_getpid(self, pid: int, uid: int, gid: int) -> SyscallResult:
        """getpid()"""
        return SyscallResult(success=True, return_value=pid)
    
    def _sys_getppid(self, pid: int, uid: int, gid: int) -> SyscallResult:
        """getppid()"""
        if self._kernel and self._kernel.process_manager:
            pcb = self._kernel.process_manager.get_process(pid)
            if pcb:
                return SyscallResult(success=True, return_value=pcb.parent_pid)
        return SyscallResult(success=False, return_value=-1)
    
    def _sys_kill(
        self, pid: int, uid: int, gid: int,
        target_pid: int, signal: int
    ) -> SyscallResult:
        """kill(pid, signal)"""
        from pyos.process.states import Signal
        
        if self._kernel and self._kernel.process_manager:
            try:
                # Find signal by number
                sig = None
                for s in Signal:
                    if s.value == signal:
                        sig = s
                        break
                
                if sig is None:
                    return SyscallResult(success=False, return_value=-1, error="Invalid signal")
                
                self._kernel.process_manager.kill(target_pid, sig)
                return SyscallResult(success=True, return_value=0)
            except ProcessNotFoundError:
                return SyscallResult(success=False, return_value=-1, error="Process not found")
            except Exception as e:
                return SyscallResult(success=False, return_value=-1, error=str(e))
        return SyscallResult(success=False, return_value=-1, error="No process manager")
    
    def _sys_mkdir(
        self, pid: int, uid: int, gid: int,
        path: str, mode: int = 0o755
    ) -> SyscallResult:
        """mkdir(path, mode)"""
        if self._kernel and self._kernel.filesystem:
            try:
                self._kernel.filesystem.mkdir(path, mode=mode, uid=uid, gid=gid)
                return SyscallResult(success=True, return_value=0)
            except Exception as e:
                return SyscallResult(success=False, return_value=-1, error=str(e))
        return SyscallResult(success=False, return_value=-1, error="No filesystem")
    
    def _sys_rmdir(self, pid: int, uid: int, gid: int, path: str) -> SyscallResult:
        """rmdir(path)"""
        if self._kernel and self._kernel.filesystem:
            try:
                self._kernel.filesystem.rmdir(path, uid=uid, gid=gid)
                return SyscallResult(success=True, return_value=0)
            except Exception as e:
                return SyscallResult(success=False, return_value=-1, error=str(e))
        return SyscallResult(success=False, return_value=-1, error="No filesystem")
    
    def _sys_unlink(self, pid: int, uid: int, gid: int, path: str) -> SyscallResult:
        """unlink(path)"""
        if self._kernel and self._kernel.filesystem:
            try:
                self._kernel.filesystem.unlink(path, uid=uid, gid=gid)
                return SyscallResult(success=True, return_value=0)
            except Exception as e:
                return SyscallResult(success=False, return_value=-1, error=str(e))
        return SyscallResult(success=False, return_value=-1, error="No filesystem")
    
    def _sys_chdir(self, pid: int, uid: int, gid: int, path: str) -> SyscallResult:
        """chdir(path)"""
        if self._kernel and self._kernel.process_manager:
            try:
                pcb = self._kernel.process_manager.get_process(pid)
                if pcb:
                    if self._kernel.filesystem.is_directory(path):
                        pcb.cwd = path
                        return SyscallResult(success=True, return_value=0)
                    return SyscallResult(success=False, return_value=-1, error="Not a directory")
            except Exception as e:
                return SyscallResult(success=False, return_value=-1, error=str(e))
        return SyscallResult(success=False, return_value=-1, error="No process manager")
    
    def _sys_getcwd(self, pid: int, uid: int, gid: int) -> SyscallResult:
        """getcwd()"""
        if self._kernel and self._kernel.process_manager:
            pcb = self._kernel.process_manager.get_process(pid)
            if pcb:
                return SyscallResult(success=True, return_value=pcb.cwd)
        return SyscallResult(success=False, return_value=-1)
    
    def _sys_chmod(
        self, pid: int, uid: int, gid: int,
        path: str, mode: int
    ) -> SyscallResult:
        """chmod(path, mode)"""
        if self._kernel and self._kernel.filesystem:
            try:
                self._kernel.filesystem.chmod(path, mode, uid=uid, gid=gid)
                return SyscallResult(success=True, return_value=0)
            except Exception as e:
                return SyscallResult(success=False, return_value=-1, error=str(e))
        return SyscallResult(success=False, return_value=-1, error="No filesystem")
    
    def _sys_chown(
        self, pid: int, uid: int, gid: int,
        path: str, new_uid: int, new_gid: int
    ) -> SyscallResult:
        """chown(path, uid, gid)"""
        if self._kernel and self._kernel.filesystem:
            try:
                self._kernel.filesystem.chown(path, new_uid, new_gid, uid=uid)
                return SyscallResult(success=True, return_value=0)
            except Exception as e:
                return SyscallResult(success=False, return_value=-1, error=str(e))
        return SyscallResult(success=False, return_value=-1, error="No filesystem")
    
    def _sys_stat(self, pid: int, uid: int, gid: int, path: str) -> SyscallResult:
        """stat(path) -> stat_dict"""
        if self._kernel and self._kernel.filesystem:
            inode = self._kernel.filesystem.stat(path)
            if inode:
                return SyscallResult(success=True, return_value=inode.to_dict())
            return SyscallResult(success=False, return_value=-1, error="File not found")
        return SyscallResult(success=False, return_value=-1, error="No filesystem")
    
    def _sys_lseek(
        self, pid: int, uid: int, gid: int,
        fd: int, offset: int, whence: int
    ) -> SyscallResult:
        """lseek(fd, offset, whence)"""
        if self._kernel and self._kernel.filesystem:
            try:
                new_offset = self._kernel.filesystem.seek(fd, offset, whence)
                return SyscallResult(success=True, return_value=new_offset)
            except Exception as e:
                return SyscallResult(success=False, return_value=-1, error=str(e))
        return SyscallResult(success=False, return_value=-1, error="No filesystem")
    
    def _sys_brk(self, pid: int, uid: int, gid: int, size: int) -> SyscallResult:
        """brk(size) - allocate memory"""
        if self._kernel and self._kernel.memory_manager:
            try:
                # For now, just return success
                return SyscallResult(success=True, return_value=size)
            except Exception as e:
                return SyscallResult(success=False, return_value=-1, error=str(e))
        return SyscallResult(success=False, return_value=-1, error="No memory manager")
    
    def _sys_pipe(self, pid: int, uid: int, gid: int) -> SyscallResult:
        """pipe() -> (read_fd, write_fd)"""
        if self._kernel and self._kernel.ipc_manager:
            try:
                read_fd, write_fd = self._kernel.ipc_manager.create_pipe(pid)
                return SyscallResult(success=True, return_value=(read_fd, write_fd))
            except Exception as e:
                return SyscallResult(success=False, return_value=-1, error=str(e))
        return SyscallResult(success=False, return_value=-1, error="No IPC manager")
