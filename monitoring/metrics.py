"""
Monitoring Manager Module

Implements system monitoring and metrics:
- CPU metrics
- Memory metrics
- Process statistics
- Kernel event tracking

Author: YSNRFD
Version: 1.0.0
"""

import time
from collections import deque
from dataclasses import dataclass, field
from typing import Optional, Any, List

from pyos.core.registry import Subsystem, SubsystemState
from pyos.logger import Logger, get_logger


@dataclass
class MetricSample:
    """A single metric sample."""
    timestamp: float
    value: float


@dataclass
class MetricSeries:
    """A time series of metric samples."""
    name: str
    samples: deque = field(default_factory=lambda: deque(maxlen=100))
    
    def add(self, value: float) -> None:
        self.samples.append(MetricSample(time.time(), value))
    
    def latest(self) -> Optional[float]:
        if self.samples:
            return self.samples[-1].value
        return None
    
    def average(self, n: int = 10) -> Optional[float]:
        if not self.samples:
            return None
        values = [s.value for s in list(self.samples)[-n:]]
        return sum(values) / len(values)


class MonitoringManager(Subsystem):
    """
    System Monitoring Subsystem.
    
    Provides:
    - Resource usage metrics
    - Process statistics
    - Performance monitoring
    - Health checks
    
    Example:
        >>> monitoring = MonitoringManager()
        >>> monitoring.update()
        >>> print(monitoring.get_cpu_usage())
    """
    
    def __init__(self):
        super().__init__('monitoring')
        self._metrics: dict[str, MetricSeries] = {}
        self._kernel = None
        self._last_update: float = 0
        self._update_interval: float = 1.0
    
    def initialize(self) -> None:
        """Initialize the monitoring manager."""
        from pyos.core.kernel import get_kernel
        
        self._kernel = get_kernel()
        
        # Initialize metric series
        self._metrics = {
            'cpu_usage': MetricSeries('cpu_usage'),
            'memory_usage': MetricSeries('memory_usage'),
            'process_count': MetricSeries('process_count'),
            'context_switches': MetricSeries('context_switches'),
            'syscalls_per_sec': MetricSeries('syscalls_per_sec'),
            'files_open': MetricSeries('files_open'),
        }
        
        self.set_state(SubsystemState.INITIALIZED)
        self._logger.info("Monitoring manager initialized")
    
    def start(self) -> None:
        """Start the monitoring manager."""
        self.set_state(SubsystemState.RUNNING)
    
    def stop(self) -> None:
        """Stop the monitoring manager."""
        self.set_state(SubsystemState.STOPPED)
    
    def cleanup(self) -> None:
        """Clean up resources."""
        self._metrics.clear()
    
    def update(self) -> None:
        """Update all metrics."""
        now = time.time()
        
        if now - self._last_update < self._update_interval:
            return
        
        self._last_update = now
        
        # Update CPU usage (simulated)
        if self._kernel and self._kernel.process_manager:
            process_count = self._kernel.process_manager.process_count
            self._metrics['process_count'].add(process_count)
            
            # Simulate CPU usage based on running processes
            cpu_usage = min(100, process_count * 5)
            self._metrics['cpu_usage'].add(cpu_usage)
            
            # Context switches
            stats = self._kernel.process_manager.get_stats()
            self._metrics['context_switches'].add(stats.get('context_switches', 0))
        
        # Update memory metrics
        if self._kernel and self._kernel.memory_manager:
            mem_stats = self._kernel.memory_manager.get_stats()
            memory_usage = mem_stats.get('utilization', 0)
            self._metrics['memory_usage'].add(memory_usage)
        
        # Update filesystem metrics
        if self._kernel and self._kernel.filesystem:
            fs_stats = self._kernel.filesystem.get_stats()
            self._metrics['files_open'].add(fs_stats.get('open_files', 0))
    
    def get_metric(self, name: str) -> Optional[MetricSeries]:
        """Get a metric by name."""
        return self._metrics.get(name)
    
    def get_metric_value(self, name: str) -> Optional[float]:
        """Get the current value of a metric."""
        series = self._metrics.get(name)
        if series:
            return series.latest()
        return None
    
    def get_cpu_usage(self) -> float:
        """Get current CPU usage percentage."""
        return self.get_metric_value('cpu_usage') or 0.0
    
    def get_memory_usage(self) -> float:
        """Get current memory usage percentage."""
        return self.get_metric_value('memory_usage') or 0.0
    
    def get_process_count(self) -> int:
        """Get current process count."""
        return int(self.get_metric_value('process_count') or 0)
    
    def get_all_metrics(self) -> dict[str, Any]:
        """Get all current metric values."""
        return {
            name: series.latest()
            for name, series in self._metrics.items()
        }
    
    def get_metric_history(
        self,
        name: str,
        n: int = 10
    ) -> List[dict[str, Any]]:
        """Get history of a metric."""
        series = self._metrics.get(name)
        if not series:
            return []
        
        return [
            {
                'timestamp': s.timestamp,
                'value': s.value
            }
            for s in list(series.samples)[-n:]
        ]
    
    def get_system_health(self) -> dict[str, Any]:
        """Get overall system health status."""
        cpu = self.get_cpu_usage()
        memory = self.get_memory_usage()
        
        health_status = "healthy"
        issues = []
        
        if cpu > 90:
            health_status = "warning"
            issues.append("High CPU usage")
        
        if memory > 90:
            health_status = "warning"
            issues.append("High memory usage")
        
        if cpu > 95 or memory > 95:
            health_status = "critical"
        
        return {
            'status': health_status,
            'issues': issues,
            'cpu_usage': cpu,
            'memory_usage': memory,
            'process_count': self.get_process_count(),
            'uptime': self._kernel.uptime if self._kernel else 0,
        }
    
    def get_process_stats(self, pid: int) -> Optional[dict[str, Any]]:
        """Get statistics for a specific process."""
        if not self._kernel or not self._kernel.process_manager:
            return None
        
        try:
            pcb = self._kernel.process_manager.get_process(pid)
            return pcb.to_dict()
        except Exception:
            return None
    
    def get_stats(self) -> dict[str, Any]:
        """Get monitoring manager statistics."""
        return {
            'metrics_tracked': len(self._metrics),
            'last_update': self._last_update,
            'health': self.get_system_health(),
        }
