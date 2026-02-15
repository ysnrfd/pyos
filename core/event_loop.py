"""
PyOS Event Loop

An event-driven loop for the kernel that handles:
- Timer-based events
- Interrupt simulation
- System call dispatch
- Process scheduling
- Graceful shutdown

Author: YSNRFD
Version: 1.0.0
"""

import asyncio
import heapq
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Optional, Coroutine, List
from collections import deque
import signal

from pyos.logger import Logger, get_logger


class EventType(Enum):
    """Types of kernel events."""
    TIMER = auto()
    INTERRUPT = auto()
    SYSCALL = auto()
    SCHEDULE = auto()
    SIGNAL = auto()
    IPC = auto()
    CUSTOM = auto()


class EventPriority(Enum):
    """Priority levels for event processing."""
    CRITICAL = 0
    HIGH = 10
    NORMAL = 20
    LOW = 30


@dataclass(order=True)
class Event:
    """
    A kernel event.
    
    Events are processed by the event loop in priority order.
    Timer events are sorted by scheduled time.
    """
    scheduled_time: float = field(compare=True)
    event_type: EventType = field(compare=False)
    priority: int = field(compare=True)
    callback: Callable = field(compare=False, default=lambda: None)
    data: Any = field(compare=False, default=None)
    recurring: bool = field(compare=False, default=False)
    interval: float = field(compare=False, default=0.0)
    event_id: int = field(compare=False, default=0)
    
    def execute(self) -> Optional['Event']:
        """Execute the event callback and return next event if recurring."""
        if self.data:
            return self.callback(self.data)
        return self.callback()


class InterruptType(Enum):
    """Simulated interrupt types."""
    TIMER = 0
    KEYBOARD = 1
    DISK = 2
    NETWORK = 3
    SYSCALL = 4
    FAULT = 5


@dataclass
class Interrupt:
    """A simulated interrupt."""
    interrupt_type: InterruptType
    vector: int
    data: Any = None
    timestamp: float = field(default_factory=time.time)


class EventLoop:
    """
    The kernel event loop.
    
    Manages event scheduling, interrupt handling, and the main
    execution loop for the kernel.
    
    The event loop runs in its own thread and processes events
    in priority order. Timer events are scheduled with heapq.
    
    Example:
        >>> loop = EventLoop()
        >>> loop.schedule_timer(my_callback, delay=1.0)
        >>> loop.run()
    """
    
    def __init__(self):
        self._logger = get_logger('event_loop')
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._event_counter = 0
        self._event_lock = threading.Lock()
        
        # Event queues
        self._timer_queue: List[Event] = []  # heapq
        self._immediate_queue: deque[Event] = deque()
        self._interrupt_queue: deque[Interrupt] = deque()
        
        # Interrupt handlers
        self._interrupt_handlers: dict[int, Callable] = {}
        
        # Statistics
        self._events_processed = 0
        self._interrupts_processed = 0
        
        # Shutdown event
        self._shutdown_event = threading.Event()
    
    def start(self) -> None:
        """Start the event loop in a background thread."""
        if self._running:
            return
        
        self._running = True
        self._shutdown_event.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        self._logger.info("Event loop started")
    
    def stop(self) -> None:
        """Stop the event loop."""
        if not self._running:
            return
        
        self._running = False
        self._shutdown_event.set()
        
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        
        self._logger.info(
            "Event loop stopped",
            context={
                'events_processed': self._events_processed,
                'interrupts_processed': self._interrupts_processed
            }
        )
    
    def _run_loop(self) -> None:
        """Main event loop implementation."""
        self._logger.debug("Event loop thread started")
        
        while self._running:
            try:
                self._process_events()
                time.sleep(0.001)  # Small sleep to prevent busy-waiting
            except Exception as e:
                self._logger.error(f"Error in event loop: {e}")
        
        self._logger.debug("Event loop thread exiting")
    
    def _process_events(self) -> None:
        """Process pending events."""
        current_time = time.time()
        
        # Process interrupts first (highest priority)
        while self._interrupt_queue:
            interrupt = self._interrupt_queue.popleft()
            self._handle_interrupt(interrupt)
        
        # Process immediate events
        while self._immediate_queue:
            event = self._immediate_queue.popleft()
            self._execute_event(event)
        
        # Process timer events that are due
        while self._timer_queue and self._timer_queue[0].scheduled_time <= current_time:
            event = heapq.heappop(self._timer_queue)
            self._execute_event(event)
    
    def _execute_event(self, event: Event) -> None:
        """Execute a single event."""
        try:
            result = event.execute()
            self._events_processed += 1
            
            # Handle recurring events
            if event.recurring and self._running:
                new_event = Event(
                    scheduled_time=time.time() + event.interval,
                    event_type=event.event_type,
                    priority=event.priority,
                    callback=event.callback,
                    data=event.data,
                    recurring=True,
                    interval=event.interval,
                    event_id=self._next_event_id()
                )
                heapq.heappush(self._timer_queue, new_event)
                
        except Exception as e:
            self._logger.error(
                f"Error executing event: {e}",
                context={'event_type': event.event_type.name}
            )
    
    def _handle_interrupt(self, interrupt: Interrupt) -> None:
        """Handle a simulated interrupt."""
        handler = self._interrupt_handlers.get(interrupt.vector)
        
        if handler:
            try:
                handler(interrupt)
                self._interrupts_processed += 1
            except Exception as e:
                self._logger.error(
                    f"Error handling interrupt: {e}",
                    context={
                        'type': interrupt.interrupt_type.name,
                        'vector': interrupt.vector
                    }
                )
        else:
            self._logger.warning(
                f"No handler for interrupt",
                context={
                    'type': interrupt.interrupt_type.name,
                    'vector': interrupt.vector
                }
            )
    
    def _next_event_id(self) -> int:
        """Generate the next event ID."""
        with self._event_lock:
            self._event_counter += 1
            return self._event_counter
    
    def schedule_timer(
        self,
        callback: Callable,
        delay: float,
        priority: EventPriority = EventPriority.NORMAL,
        data: Any = None,
        recurring: bool = False
    ) -> int:
        """
        Schedule a timer event.
        
        Args:
            callback: Function to call when event fires
            delay: Delay in seconds before event fires
            priority: Event priority
            data: Data to pass to callback
            recurring: Whether to repeat the event
        
        Returns:
            Event ID for cancellation
        """
        event = Event(
            scheduled_time=time.time() + delay,
            event_type=EventType.TIMER,
            priority=priority.value,
            callback=callback,
            data=data,
            recurring=recurring,
            interval=delay if recurring else 0.0,
            event_id=self._next_event_id()
        )
        
        heapq.heappush(self._timer_queue, event)
        return event.event_id
    
    def schedule_immediate(
        self,
        callback: Callable,
        priority: EventPriority = EventPriority.NORMAL,
        data: Any = None
    ) -> int:
        """
        Schedule an immediate event.
        
        Args:
            callback: Function to call
            priority: Event priority
            data: Data to pass to callback
        
        Returns:
            Event ID
        """
        event = Event(
            scheduled_time=time.time(),
            event_type=EventType.CUSTOM,
            priority=priority.value,
            callback=callback,
            data=data,
            event_id=self._next_event_id()
        )
        
        self._immediate_queue.append(event)
        return event.event_id
    
    def raise_interrupt(
        self,
        interrupt_type: InterruptType,
        data: Any = None
    ) -> None:
        """
        Raise a simulated interrupt.
        
        Args:
            interrupt_type: Type of interrupt
            data: Additional interrupt data
        """
        interrupt = Interrupt(
            interrupt_type=interrupt_type,
            vector=interrupt_type.value,
            data=data
        )
        self._interrupt_queue.append(interrupt)
    
    def register_interrupt_handler(
        self,
        interrupt_type: InterruptType,
        handler: Callable[[Interrupt], None]
    ) -> None:
        """
        Register a handler for an interrupt type.
        
        Args:
            interrupt_type: Type of interrupt to handle
            handler: Function to call when interrupt occurs
        """
        self._interrupt_handlers[interrupt_type.value] = handler
        self._logger.debug(
            f"Registered interrupt handler",
            context={'type': interrupt_type.name}
        )
    
    def cancel_event(self, event_id: int) -> bool:
        """
        Cancel a scheduled event.
        
        Args:
            event_id: ID of event to cancel
        
        Returns:
            True if event was cancelled, False if not found
        """
        # Check timer queue
        for i, event in enumerate(self._timer_queue):
            if event.event_id == event_id:
                self._timer_queue.pop(i)
                heapq.heapify(self._timer_queue)
                return True
        
        return False
    
    def get_stats(self) -> dict[str, Any]:
        """Get event loop statistics."""
        return {
            'running': self._running,
            'events_processed': self._events_processed,
            'interrupts_processed': self._interrupts_processed,
            'pending_timers': len(self._timer_queue),
            'pending_immediate': len(self._immediate_queue),
            'pending_interrupts': len(self._interrupt_queue),
        }
    
    def wait_for_shutdown(self, timeout: Optional[float] = None) -> bool:
        """
        Wait for the event loop to shut down.
        
        Args:
            timeout: Maximum time to wait (None for indefinite)
        
        Returns:
            True if shutdown occurred, False if timeout
        """
        return self._shutdown_event.wait(timeout)
