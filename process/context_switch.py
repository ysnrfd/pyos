"""
Context Switch Module

Handles saving and restoring process context during switches.
This module simulates the hardware-level context switching that
occurs when the CPU switches from one process to another.

Author: YSNRFD
Version: 1.0.0
"""

import time
from dataclasses import dataclass
from typing import Optional

from .pcb import ProcessControlBlock, CpuContext
from .states import ProcessState
from pyos.logger import Logger, get_logger


@dataclass
class ContextSwitchStats:
    """Statistics for context switches."""
    total_switches: int = 0
    user_to_kernel: int = 0
    kernel_to_user: int = 0
    process_to_process: int = 0
    total_switch_time: float = 0.0
    
    @property
    def average_switch_time(self) -> float:
        if self.total_switches == 0:
            return 0.0
        return self.total_switch_time / self.total_switches


class ContextSwitcher:
    """
    Handles process context switching.
    
    In a real OS, this would:
    1. Save current process's registers to PCB
    2. Save current process's kernel stack pointer
    3. Update memory mappings (page tables)
    4. Restore next process's registers from PCB
    5. Restore next process's kernel stack pointer
    6. Jump to the saved instruction pointer
    
    Here we simulate the essential operations.
    """
    
    def __init__(self):
        self._stats = ContextSwitchStats()
        self._current_process: Optional[ProcessControlBlock] = None
        self._logger = get_logger('context_switch')
        
        # Simulated overhead for context switch (microseconds)
        self._switch_overhead = 10.0
    
    @property
    def current_process(self) -> Optional[ProcessControlBlock]:
        """Get the currently running process."""
        return self._current_process
    
    @property
    def stats(self) -> ContextSwitchStats:
        """Get context switch statistics."""
        return self._stats
    
    def switch(
        self,
        from_process: Optional[ProcessControlBlock],
        to_process: Optional[ProcessControlBlock]
    ) -> None:
        """
        Perform a context switch between two processes.
        
        Args:
            from_process: Process being switched out (None for idle)
            to_process: Process being switched in (None for idle)
        """
        start_time = time.perf_counter()
        
        # Save context of outgoing process
        if from_process:
            self._save_context(from_process)
            from_process.state = ProcessState.READY
            from_process.context_switch_out()
            
            self._logger.debug(
                "Saved context",
                pid=from_process.pid,
                context={'state': 'READY'}
            )
        
        # Restore context of incoming process
        if to_process:
            self._restore_context(to_process)
            to_process.state = ProcessState.RUNNING
            to_process.context_switch_in()
            
            self._logger.debug(
                "Restored context",
                pid=to_process.pid,
                context={'state': 'RUNNING'}
            )
        
        # Update statistics
        switch_time = (time.perf_counter() - start_time) * 1000000  # microseconds
        self._stats.total_switches += 1
        self._stats.total_switch_time += switch_time
        
        if from_process and to_process:
            self._stats.process_to_process += 1
        
        self._current_process = to_process
    
    def _save_context(self, pcb: ProcessControlBlock) -> None:
        """
        Save the context of a process.
        
        In a real system, this would save all registers,
        FPU state, etc. to the PCB.
        """
        # Simulate saving instruction pointer and stack pointer
        pcb.context.instruction_pointer += pcb.time_slice  # Simulate progress
        pcb.context.flags = 0  # Would be actual CPU flags
        
        # Simulate register save
        pcb.context.registers = {
            i: i * 1000 + pcb.pid  # Simulated register values
            for i in range(16)  # 16 general purpose registers
        }
    
    def _restore_context(self, pcb: ProcessControlBlock) -> None:
        """
        Restore the context of a process.
        
        In a real system, this would restore all registers,
        FPU state, etc. from the PCB.
        """
        # Context is already in pcb.context
        # In a real system, we would load these into actual registers
        pass
    
    def fork_context(self, parent: ProcessControlBlock, child: ProcessControlBlock) -> None:
        """
        Copy context from parent to child during fork.
        
        In a real system, this would copy the parent's registers
        to the child, with the return value modified so fork()
        returns 0 in the child.
        
        Args:
            parent: Parent process PCB
            child: Child process PCB
        """
        # Copy context
        child.context = CpuContext(
            instruction_pointer=parent.context.instruction_pointer,
            stack_pointer=parent.context.stack_pointer,
            flags=parent.context.flags,
            registers=parent.context.registers.copy()
        )
        
        # Copy resources (files, etc.)
        child.cwd = parent.cwd
        child.environ = parent.environ.copy()
        
        # Copy signal handlers
        child.signal_handlers = parent.signal_handlers.copy()
        child.signal_mask = parent.signal_mask.copy()
        
        self._logger.debug(
            "Forked context",
            pid=parent.pid,
            context={'child_pid': child.pid}
        )
    
    def exec_context(self, pcb: ProcessControlBlock) -> None:
        """
        Reset context for exec().
        
        When a process calls exec(), it gets a fresh context
        with the new program's entry point.
        
        Args:
            pcb: Process PCB to reset
        """
        pcb.context = CpuContext(
            instruction_pointer=0,  # Entry point of new program
            stack_pointer=0x7fffffff,  # Typical user stack top
            flags=0,
            registers={}
        )
        
        self._logger.debug(
            "Exec context reset",
            pid=pcb.pid
        )
    
    def get_current_pid(self) -> Optional[int]:
        """Get the PID of the currently running process."""
        if self._current_process:
            return self._current_process.pid
        return None
    
    def reset(self) -> None:
        """Reset the context switcher state."""
        self._stats = ContextSwitchStats()
        self._current_process = None
