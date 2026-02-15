"""
Process Scheduler Module

Implements scheduling algorithms for process management:
- Round Robin scheduling
- Priority-based scheduling
- Multi-level feedback queue

Author: YSNRFD
Version: 1.0.0
"""

import time
from abc import ABC, abstractmethod
from collections import deque
from dataclasses import dataclass
from typing import Optional, Callable, List
import heapq

from .pcb import ProcessControlBlock
from .states import ProcessState
from pyos.core.config_loader import get_config
from pyos.logger import Logger, get_logger


class SchedulerAlgorithm(ABC):
    """
    Abstract base class for scheduling algorithms.
    """
    
    @abstractmethod
    def add_process(self, pcb: ProcessControlBlock) -> None:
        """Add a process to the scheduler."""
        pass
    
    @abstractmethod
    def remove_process(self, pcb: ProcessControlBlock) -> None:
        """Remove a process from the scheduler."""
        pass
    
    @abstractmethod
    def get_next_process(self) -> Optional[ProcessControlBlock]:
        """Get the next process to run."""
        pass
    
    @abstractmethod
    def time_slice_expired(self, pcb: ProcessControlBlock) -> None:
        """Called when a process's time slice expires."""
        pass
    
    @abstractmethod
    def yield_process(self, pcb: ProcessControlBlock) -> None:
        """Called when a process voluntarily yields."""
        pass
    
    @abstractmethod
    def count(self) -> int:
        """Return the number of schedulable processes."""
        pass


class RoundRobinScheduler(SchedulerAlgorithm):
    """
    Round Robin scheduling algorithm.
    
    Each process gets a fixed time slice (quantum). When the quantum
    expires, the process is moved to the end of the ready queue.
    
    Advantages:
    - Fair allocation of CPU time
    - Good response time for interactive processes
    - Simple to implement
    
    Disadvantages:
    - No priority consideration
    - May not be optimal for CPU-bound vs I/O-bound mix
    """
    
    def __init__(self, quantum: int = 100):
        """
        Initialize the Round Robin scheduler.
        
        Args:
            quantum: Time slice in milliseconds
        """
        self.quantum = quantum
        self.ready_queue: deque[ProcessControlBlock] = deque()
        self._logger = get_logger('scheduler_rr')
    
    def add_process(self, pcb: ProcessControlBlock) -> None:
        """Add a process to the end of the ready queue."""
        pcb.time_slice = self.quantum
        pcb.time_remaining = self.quantum
        self.ready_queue.append(pcb)
        self._logger.debug(
            f"Added process to queue",
            pid=pcb.pid,
            context={'position': len(self.ready_queue)}
        )
    
    def remove_process(self, pcb: ProcessControlBlock) -> None:
        """Remove a process from the queue."""
        try:
            self.ready_queue.remove(pcb)
        except ValueError:
            pass
    
    def get_next_process(self) -> Optional[ProcessControlBlock]:
        """Get the next process from the front of the queue."""
        if self.ready_queue:
            pcb = self.ready_queue.popleft()
            pcb.time_remaining = self.quantum
            return pcb
        return None
    
    def time_slice_expired(self, pcb: ProcessControlBlock) -> None:
        """Move process to end of queue when quantum expires."""
        pcb.time_remaining = self.quantum
        self.ready_queue.append(pcb)
    
    def yield_process(self, pcb: ProcessControlBlock) -> None:
        """Process yields, goes to end of queue."""
        self.ready_queue.append(pcb)
    
    def count(self) -> int:
        """Return number of processes in queue."""
        return len(self.ready_queue)


class PriorityScheduler(SchedulerAlgorithm):
    """
    Priority-based scheduling algorithm.
    
    Each process has a priority (lower value = higher priority).
    Processes are scheduled in priority order. Same priority
    processes are scheduled round-robin.
    
    Features:
    - Static priority based on process type
    - Dynamic priority adjustment (nice value)
    - Aging to prevent starvation
    """
    
    def __init__(
        self,
        quantum: int = 100,
        priority_levels: int = 40,
        enable_aging: bool = True,
        aging_interval: float = 5.0
    ):
        """
        Initialize the Priority scheduler.
        
        Args:
            quantum: Base time slice in milliseconds
            priority_levels: Number of priority levels
            enable_aging: Enable aging to prevent starvation
            aging_interval: Seconds before priority boost
        """
        self.quantum = quantum
        self.priority_levels = priority_levels
        self.enable_aging = enable_aging
        self.aging_interval = aging_interval
        
        # Queue for each priority level
        self.queues: List[deque[ProcessControlBlock]] = [
            deque() for _ in range(priority_levels)
        ]
        
        # Track wait times for aging
        self._wait_times: dict[int, float] = {}
        
        self._logger = get_logger('scheduler_priority')
    
    def _get_priority_index(self, pcb: ProcessControlBlock) -> int:
        """Get the queue index for a process priority."""
        # Priority ranges from 0 (highest) to priority_levels-1 (lowest)
        priority = pcb.priority + pcb.nice
        return min(max(0, priority), self.priority_levels - 1)
    
    def add_process(self, pcb: ProcessControlBlock) -> None:
        """Add a process to the appropriate priority queue."""
        idx = self._get_priority_index(pcb)
        pcb.time_slice = self.quantum
        pcb.time_remaining = self.quantum
        
        self.queues[idx].append(pcb)
        
        if self.enable_aging:
            self._wait_times[pcb.pid] = time.time()
        
        self._logger.debug(
            f"Added process to priority queue",
            pid=pcb.pid,
            context={'priority': idx, 'queue_size': len(self.queues[idx])}
        )
    
    def remove_process(self, pcb: ProcessControlBlock) -> None:
        """Remove a process from its priority queue."""
        idx = self._get_priority_index(pcb)
        try:
            self.queues[idx].remove(pcb)
        except ValueError:
            pass
        
        self._wait_times.pop(pcb.pid, None)
    
    def get_next_process(self) -> Optional[ProcessControlBlock]:
        """Get the highest priority ready process."""
        self._apply_aging()
        
        for queue in self.queues:
            if queue:
                pcb = queue.popleft()
                pcb.time_remaining = pcb.time_slice
                self._wait_times.pop(pcb.pid, None)
                return pcb
        
        return None
    
    def time_slice_expired(self, pcb: ProcessControlBlock) -> None:
        """Return process to its priority queue."""
        self.add_process(pcb)
    
    def yield_process(self, pcb: ProcessControlBlock) -> None:
        """Process yields, returns to queue."""
        self.add_process(pcb)
    
    def _apply_aging(self) -> None:
        """Apply aging to prevent starvation."""
        if not self.enable_aging:
            return
        
        current_time = time.time()
        
        for pid, wait_start in list(self._wait_times.items()):
            wait_time = current_time - wait_start
            if wait_time > self.aging_interval:
                # Find the process and boost its priority
                for queue in self.queues:
                    for pcb in queue:
                        if pcb.pid == pid:
                            # Decrease priority value (increase actual priority)
                            pcb.priority = max(0, pcb.priority - 1)
                            self._logger.debug(
                                f"Applied aging boost",
                                pid=pid,
                                context={'new_priority': pcb.priority}
                            )
                            break
    
    def count(self) -> int:
        """Return total number of processes in all queues."""
        return sum(len(q) for q in self.queues)


class MultiLevelFeedbackQueueScheduler(SchedulerAlgorithm):
    """
    Multi-Level Feedback Queue (MLFQ) scheduler.
    
    Multiple queues with different priorities and time slices.
    Processes move between queues based on their behavior:
    - CPU-bound processes move to lower priority (longer time slice)
    - I/O-bound processes stay in higher priority (shorter time slice)
    
    This provides good response time for interactive processes
    while still being fair to CPU-bound processes.
    """
    
    def __init__(
        self,
        num_queues: int = 4,
        base_quantum: int = 50,
        quantum_multiplier: float = 2.0,
        aging_interval: float = 10.0
    ):
        """
        Initialize MLFQ scheduler.
        
        Args:
            num_queues: Number of priority queues
            base_quantum: Quantum for highest priority queue (ms)
            quantum_multiplier: Quantum multiplier for each lower level
            aging_interval: Seconds before priority boost
        """
        self.num_queues = num_queues
        self.base_quantum = base_quantum
        self.quantum_multiplier = quantum_multiplier
        self.aging_interval = aging_interval
        
        # Create queues with increasing time slices
        self.queues: List[deque[ProcessControlBlock]] = [
            deque() for _ in range(num_queues)
        ]
        self.quantums = [
            int(base_quantum * (quantum_multiplier ** i))
            for i in range(num_queues)
        ]
        
        # Track which queue each process is in
        self._process_queue: dict[int, int] = {}
        self._wait_times: dict[int, float] = {}
        
        self._logger = get_logger('scheduler_mlfq')
    
    def add_process(self, pcb: ProcessControlBlock) -> None:
        """Add a new process to the highest priority queue."""
        queue_idx = 0
        pcb.time_slice = self.quantums[queue_idx]
        pcb.time_remaining = pcb.time_slice
        
        self.queues[queue_idx].append(pcb)
        self._process_queue[pcb.pid] = queue_idx
        self._wait_times[pcb.pid] = time.time()
    
    def remove_process(self, pcb: ProcessControlBlock) -> None:
        """Remove a process from its queue."""
        queue_idx = self._process_queue.pop(pcb.pid, -1)
        if 0 <= queue_idx < self.num_queues:
            try:
                self.queues[queue_idx].remove(pcb)
            except ValueError:
                pass
        self._wait_times.pop(pcb.pid, None)
    
    def get_next_process(self) -> Optional[ProcessControlBlock]:
        """Get the next process from the highest priority non-empty queue."""
        self._apply_aging()
        
        for idx, queue in enumerate(self.queues):
            if queue:
                pcb = queue.popleft()
                pcb.time_remaining = pcb.time_slice
                self._wait_times.pop(pcb.pid, None)
                return pcb
        
        return None
    
    def time_slice_expired(self, pcb: ProcessControlBlock) -> None:
        """
        Process used full time slice, demote to lower priority.
        
        This indicates a CPU-bound process.
        """
        current_idx = self._process_queue.get(pcb.pid, 0)
        
        # Demote to lower priority (higher index)
        new_idx = min(current_idx + 1, self.num_queues - 1)
        pcb.time_slice = self.quantums[new_idx]
        pcb.time_remaining = pcb.time_slice
        
        self.queues[new_idx].append(pcb)
        self._process_queue[pcb.pid] = new_idx
        self._wait_times[pcb.pid] = time.time()
        
        self._logger.debug(
            f"Demoted process",
            pid=pcb.pid,
            context={'old_queue': current_idx, 'new_queue': new_idx}
        )
    
    def yield_process(self, pcb: ProcessControlBlock) -> None:
        """
        Process yielded before time slice expired.
        
        This indicates an I/O-bound process, keep in current queue.
        """
        current_idx = self._process_queue.get(pcb.pid, 0)
        self.queues[current_idx].append(pcb)
        self._wait_times[pcb.pid] = time.time()
    
    def _apply_aging(self) -> None:
        """Boost priority of processes that have waited too long."""
        current_time = time.time()
        
        for pid, wait_start in list(self._wait_times.items()):
            wait_time = current_time - wait_start
            if wait_time > self.aging_interval:
                # Boost to highest priority
                current_idx = self._process_queue.get(pid, -1)
                if current_idx > 0:
                    # Find and move the process
                    for pcb in self.queues[current_idx]:
                        if pcb.pid == pid:
                            self.queues[current_idx].remove(pcb)
                            self.queues[0].append(pcb)
                            self._process_queue[pid] = 0
                            pcb.time_slice = self.quantums[0]
                            
                            self._logger.debug(
                                f"Boosted process priority",
                                pid=pid,
                                context={'old_queue': current_idx, 'new_queue': 0}
                            )
                            break
                self._wait_times[pid] = current_time
    
    def count(self) -> int:
        """Return total number of processes."""
        return sum(len(q) for q in self.queues)
    
    def get_queue_stats(self) -> List[dict]:
        """Get statistics for each queue."""
        return [
            {
                'level': i,
                'processes': len(self.queues[i]),
                'quantum': self.quantums[i]
            }
            for i in range(self.num_queues)
        ]


def create_scheduler(algorithm: str = "round_robin", **kwargs) -> SchedulerAlgorithm:
    """
    Factory function to create a scheduler.
    
    Args:
        algorithm: Scheduler type ('round_robin', 'priority', 'mlfq')
        **kwargs: Additional arguments for the scheduler
    
    Returns:
        Scheduler instance
    """
    schedulers = {
        'round_robin': RoundRobinScheduler,
        'priority': PriorityScheduler,
        'mlfq': MultiLevelFeedbackQueueScheduler,
    }
    
    scheduler_class = schedulers.get(algorithm, RoundRobinScheduler)
    return scheduler_class(**kwargs)
