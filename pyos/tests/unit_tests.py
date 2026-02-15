#!/usr/bin/env python3
"""
PyOS Unit Tests

Comprehensive test suite for all PyOS components.

Run with: python -m pytest tests/unit_tests.py -v
Or: python tests/unit_tests.py

Author: YSNRFD
Version: 1.0.0
"""

import unittest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestExceptions(unittest.TestCase):
    """Test the exception hierarchy."""
    
    def test_kernel_exception(self):
        """Test KernelException creation and properties."""
        from exceptions import KernelException
        
        exc = KernelException("Test error", error_code=1001, recoverable=True)
        
        self.assertEqual(exc.message, "Test error")
        self.assertEqual(exc.error_code, 1001)
        self.assertTrue(exc.recoverable)
        self.assertIn("1001", str(exc))
    
    def test_kernel_panic(self):
        """Test KernelPanic exception."""
        from exceptions import KernelPanic
        
        exc = KernelPanic("System failure")
        
        self.assertEqual(exc.error_code, 9999)
        self.assertFalse(exc.recoverable)
    
    def test_process_exceptions(self):
        """Test process exceptions."""
        from exceptions import ProcessCreationError, ProcessNotFoundError
        
        exc = ProcessCreationError("No PIDs available", parent_pid=1)
        self.assertEqual(exc.parent_pid, 1)
        
        exc = ProcessNotFoundError(42)
        self.assertEqual(exc.pid, 42)
    
    def test_memory_exceptions(self):
        """Test memory exceptions."""
        from exceptions import OutOfMemoryError, SegmentationFault
        
        exc = OutOfMemoryError(requested=1024, available=512)
        self.assertEqual(exc.requested, 1024)
        self.assertEqual(exc.available, 512)
        
        exc = SegmentationFault(pid=1, address=0xDEADBEEF)
        self.assertEqual(exc.pid, 1)


class TestLogger(unittest.TestCase):
    """Test the logging system."""
    
    def test_logger_creation(self):
        """Test logger creation and singleton."""
        from logger import Logger, LogLevel
        
        Logger.initialize(level=LogLevel.DEBUG)
        
        log1 = Logger('test1')
        log2 = Logger('test1')
        
        self.assertIs(log1, log2)  # Same subsystem = same instance
    
    def test_log_levels(self):
        """Test log level filtering."""
        from logger import LogLevel
        
        self.assertTrue(LogLevel.ERROR > LogLevel.INFO)
        self.assertTrue(LogLevel.DEBUG < LogLevel.WARNING)


class TestConfig(unittest.TestCase):
    """Test the configuration system."""
    
    def test_default_config(self):
        """Test default configuration values."""
        from core.config_loader import Config
        
        config = Config()
        
        self.assertEqual(config.kernel.name, "PyOS")
        self.assertEqual(config.scheduler.quantum, 100)
        self.assertEqual(config.memory.page_size, 4096)
    
    def test_config_loader(self):
        """Test configuration loading."""
        from core.config_loader import ConfigLoader
        
        loader = ConfigLoader()
        config = loader.config
        
        self.assertIsNotNone(config)
        self.assertEqual(config.kernel.name, "PyOS")


class TestProcessManagement(unittest.TestCase):
    """Test process management."""
    
    def test_pcb_creation(self):
        """Test PCB creation."""
        from process.pcb import ProcessControlBlock
        from process.states import ProcessState
        
        pcb = ProcessControlBlock(
            pid=100,
            parent_pid=1,
            name="test_process"
        )
        
        self.assertEqual(pcb.pid, 100)
        self.assertEqual(pcb.name, "test_process")
        self.assertEqual(pcb.state, ProcessState.NEW)
    
    def test_pid_generation(self):
        """Test PID generation."""
        from process.pcb import ProcessControlBlock
        
        ProcessControlBlock.reset_pid_counter()
        
        pid1 = ProcessControlBlock.generate_pid()
        pid2 = ProcessControlBlock.generate_pid()
        
        self.assertGreater(pid2, pid1)
    
    def test_process_states(self):
        """Test process state transitions."""
        from process.pcb import ProcessControlBlock
        from process.states import ProcessState
        
        pcb = ProcessControlBlock(pid=1, parent_pid=0, name="test")
        
        pcb.state = ProcessState.READY
        self.assertEqual(pcb.state, ProcessState.READY)
        
        pcb.state = ProcessState.RUNNING
        self.assertEqual(pcb.state, ProcessState.RUNNING)
    
    def test_scheduler(self):
        """Test round-robin scheduler."""
        from process.scheduler import RoundRobinScheduler
        from process.pcb import ProcessControlBlock
        from process.states import ProcessState
        
        scheduler = RoundRobinScheduler(quantum=100)
        
        pcb1 = ProcessControlBlock(pid=1, parent_pid=0, name="p1")
        pcb1.state = ProcessState.READY
        pcb2 = ProcessControlBlock(pid=2, parent_pid=0, name="p2")
        pcb2.state = ProcessState.READY
        
        scheduler.add_process(pcb1)
        scheduler.add_process(pcb2)
        
        self.assertEqual(scheduler.count(), 2)
        
        next_proc = scheduler.get_next_process()
        self.assertEqual(next_proc.pid, 1)
        
        next_proc = scheduler.get_next_process()
        self.assertEqual(next_proc.pid, 2)


class TestMemoryManagement(unittest.TestCase):
    """Test memory management."""
    
    def test_frame_allocator(self):
        """Test frame allocation."""
        from memory.paging import FrameAllocator
        
        allocator = FrameAllocator(total_frames=100)
        
        frame1 = allocator.allocate()
        frame2 = allocator.allocate()
        
        self.assertIsNotNone(frame1)
        self.assertIsNotNone(frame2)
        self.assertNotEqual(frame1, frame2)
        
        self.assertTrue(allocator.free(frame1))
        self.assertEqual(allocator.free_frames, 99)
    
    def test_page_table(self):
        """Test page table operations."""
        from memory.paging import PageTable, PageFlags
        
        pt = PageTable(page_size=4096)
        
        pt.map_page(0, 100, PageFlags.PRESENT | PageFlags.WRITABLE)
        
        frame = pt.translate(0)
        self.assertEqual(frame, 100)
        
        pt.unmap_page(0)
        frame = pt.translate(0)
        self.assertIsNone(frame)
    
    def test_buddy_allocator(self):
        """Test buddy allocator."""
        from memory.allocator import BuddyAllocator
        
        allocator = BuddyAllocator(total_size=4096, min_block_size=16)
        
        addr1 = allocator.allocate(64)
        self.assertIsNotNone(addr1)
        
        stats = allocator.get_stats()
        self.assertGreater(stats['allocated_blocks'], 0)
        
        self.assertTrue(allocator.free(addr1))


class TestFilesystem(unittest.TestCase):
    """Test the virtual file system."""
    
    def test_path_resolver(self):
        """Test path resolution."""
        from filesystem.path_resolver import PathResolver
        
        self.assertEqual(PathResolver.normalize('/home/../tmp/.'), '/tmp')
        self.assertEqual(PathResolver.join('/home', 'user'), '/home/user')
        self.assertEqual(PathResolver.basename('/home/user/file.txt'), 'file.txt')
        self.assertEqual(PathResolver.dirname('/home/user/file.txt'), '/home/user')
    
    def test_inode_operations(self):
        """Test inode operations."""
        from filesystem.inode import Inode, FileType, Permission
        
        inode = Inode(ino=1, file_type=FileType.REGULAR)
        
        # Test write and read
        written = inode.write(b'Hello, World!')
        self.assertEqual(written, 13)
        
        data = inode.read()
        self.assertEqual(data, b'Hello, World!')
        
        # Test permissions
        self.assertTrue(inode.can_read(0, 0))  # Root
        self.assertTrue(inode.can_write(0, 0))
    
    def test_directory_inode(self):
        """Test directory inode operations."""
        from filesystem.inode import Inode, FileType
        
        dir_inode = Inode(ino=1, file_type=FileType.DIRECTORY)
        
        dir_inode.add_entry('file1', 2)
        dir_inode.add_entry('file2', 3)
        
        self.assertEqual(dir_inode.get_entry('file1'), 2)
        
        entries = dir_inode.list_entries()
        self.assertEqual(len(entries), 2)


class TestUsers(unittest.TestCase):
    """Test user management."""
    
    def test_user_creation(self):
        """Test user creation."""
        from users.user_manager import UserManager
        
        # Note: This would normally initialize the subsystem
        # For testing, we just check the data structures
        from users.user_manager import User, Role
        
        user = User(
            uid=100,
            username='testuser',
            password_hash='hash',
            gid=100,
            home='/home/testuser'
        )
        
        self.assertEqual(user.uid, 100)
        self.assertIn(Role.USER, user.roles)


class TestShell(unittest.TestCase):
    """Test shell functionality."""
    
    def test_parser(self):
        """Test command parsing."""
        from shell.parser import CommandParser
        
        parser = CommandParser()
        
        cmd = parser.parse('ls -la /home')
        self.assertEqual(cmd.command, 'ls')
        self.assertEqual(cmd.args, ['-la', '/home'])
    
    def test_parser_with_pipe(self):
        """Test pipe parsing."""
        from shell.parser import CommandParser
        
        parser = CommandParser()
        
        cmd = parser.parse('ls | grep test')
        self.assertEqual(cmd.command, 'ls')
        self.assertIsNotNone(cmd.pipe_to)
        self.assertEqual(cmd.pipe_to.command, 'grep')
    
    def test_parser_with_redirection(self):
        """Test redirection parsing."""
        from shell.parser import CommandParser
        
        parser = CommandParser()
        
        cmd = parser.parse('echo hello > output.txt')
        self.assertEqual(len(cmd.redirections), 1)
        self.assertEqual(cmd.redirections[0].type, 'out')
        self.assertEqual(cmd.redirections[0].path, 'output.txt')


class TestIPC(unittest.TestCase):
    """Test IPC mechanisms."""
    
    def test_pipe_creation(self):
        """Test pipe creation."""
        from ipc.pipe import Pipe
        
        pipe = Pipe(pipe_id=1, owner_pid=1)
        
        written = pipe.write(b'test data')
        self.assertEqual(written, 9)
        
        data = pipe.read()
        self.assertEqual(data, b'test data')


class TestSecurity(unittest.TestCase):
    """Test security features."""
    
    def test_resource_limits(self):
        """Test resource limits."""
        from security.sandbox import ResourceLimits
        
        limits = ResourceLimits(
            cpu_time=60,
            memory=1024*1024
        )
        
        self.assertEqual(limits.cpu_time, 60)
        self.assertEqual(limits.memory, 1024*1024)


class TestMonitoring(unittest.TestCase):
    """Test monitoring features."""
    
    def test_metric_series(self):
        """Test metric series."""
        from monitoring.metrics import MetricSeries
        
        series = MetricSeries('test_metric')
        
        series.add(10.0)
        series.add(20.0)
        series.add(30.0)
        
        self.assertEqual(series.latest(), 30.0)
        self.assertEqual(series.average(3), 20.0)


def run_tests():
    """Run all tests."""
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    sys.exit(run_tests())
