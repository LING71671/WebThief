"""
内存管理器：监控系统资源使用

功能：
- 实时监控内存使用率
- 监控 CPU 使用率
- 动态调整并发数建议
- 大文件流式处理支持
"""

from __future__ import annotations

import gc
import os
import sys
import threading
import time
from dataclasses import dataclass, field
from typing import Callable, Optional

from rich.console import Console

console = Console()

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False


@dataclass
class MemoryStats:
    """内存统计信息"""
    total_mb: float = 0.0
    available_mb: float = 0.0
    used_mb: float = 0.0
    used_percent: float = 0.0
    process_used_mb: float = 0.0
    cpu_percent: float = 0.0
    timestamp: float = field(default_factory=time.time)

    @property
    def is_high_pressure(self) -> bool:
        return self.used_percent > 80.0

    @property
    def is_critical(self) -> bool:
        return self.used_percent > 90.0

    def to_dict(self) -> dict:
        return {
            "total_mb": round(self.total_mb, 2),
            "available_mb": round(self.available_mb, 2),
            "used_mb": round(self.used_mb, 2),
            "used_percent": round(self.used_percent, 2),
            "process_used_mb": round(self.process_used_mb, 2),
            "cpu_percent": round(self.cpu_percent, 2),
            "is_high_pressure": self.is_high_pressure,
            "is_critical": self.is_critical,
        }


class MemoryManager:
    """内存管理器"""

    LOW_PRESSURE_THRESHOLD = 60.0
    MEDIUM_PRESSURE_THRESHOLD = 75.0
    HIGH_PRESSURE_THRESHOLD = 85.0
    CRITICAL_THRESHOLD = 95.0
    LARGE_FILE_THRESHOLD = 10 * 1024 * 1024  # 10MB

    def __init__(
        self,
        memory_limit_mb: Optional[float] = None,
        check_interval: float = 1.0,
        enable_gc: bool = True,
    ):
        self.memory_limit_mb = memory_limit_mb
        self.check_interval = check_interval
        self.enable_gc = enable_gc

        self._current_stats: Optional[MemoryStats] = None
        self._monitoring = False
        self._monitor_task: Optional[threading.Thread] = None
        self._callbacks: list[Callable[[MemoryStats], None]] = []
        self._lock = threading.Lock()
        self._history: list[MemoryStats] = []
        self._max_history = 100
        self.stream_buffer_size = 64 * 1024  # 64KB

    def get_current_stats(self) -> MemoryStats:
        """获取当前内存统计信息"""
        if PSUTIL_AVAILABLE:
            return self._get_stats_with_psutil()
        return self._get_stats_fallback()

    def _get_stats_with_psutil(self) -> MemoryStats:
        """使用 psutil 获取详细内存信息"""
        try:
            mem = psutil.virtual_memory()
            process = psutil.Process(os.getpid())
            process_mem = process.memory_info()
            cpu_percent = psutil.cpu_percent(interval=0.1)

            return MemoryStats(
                total_mb=mem.total / (1024 * 1024),
                available_mb=mem.available / (1024 * 1024),
                used_mb=mem.used / (1024 * 1024),
                used_percent=mem.percent,
                process_used_mb=process_mem.rss / (1024 * 1024),
                cpu_percent=cpu_percent,
            )
        except Exception as e:
            console.print(f"[yellow]获取内存信息失败: {e}[/]")
            return self._get_stats_fallback()

    def _get_stats_fallback(self) -> MemoryStats:
        """备用内存获取方法"""
        try:
            import resource
            rusage = resource.getrusage(resource.RUSAGE_SELF)
            process_mb = rusage.ru_maxrss / 1024

            return MemoryStats(
                process_used_mb=process_mb,
            )
        except Exception:
            return MemoryStats()

    def start_monitoring(self) -> None:
        """启动后台监控线程"""
        if self._monitoring:
            return

        self._monitoring = True
        self._monitor_task = threading.Thread(
            target=self._monitor_loop,
            daemon=True,
            name="MemoryMonitor"
        )
        self._monitor_task.start()
        console.print("[green]内存监控已启动[/]")

    def stop_monitoring(self) -> None:
        """停止后台监控"""
        self._monitoring = False
        if self._monitor_task:
            self._monitor_task.join(timeout=2.0)
            self._monitor_task = None

    def _monitor_loop(self) -> None:
        """监控循环"""
        while self._monitoring:
            try:
                stats = self.get_current_stats()
                with self._lock:
                    self._current_stats = stats
                    self._history.append(stats)
                    if len(self._history) > self._max_history:
                        self._history.pop(0)

                for callback in self._callbacks:
                    try:
                        callback(stats)
                    except Exception as e:
                        console.print(f"[red]内存监控回调错误: {e}[/]")

                if self.enable_gc and stats.is_high_pressure:
                    self._trigger_gc()

            except Exception as e:
                console.print(f"[red]内存监控错误: {e}[/]")

            time.sleep(self.check_interval)

    def _trigger_gc(self) -> None:
        """触发垃圾回收"""
        collected = gc.collect()
        console.print(f"[yellow]内存压力高，已触发 GC，回收 {collected} 个对象[/]")

    def register_callback(self, callback: Callable[[MemoryStats], None]) -> None:
        """注册内存状态变化回调"""
        self._callbacks.append(callback)

    def unregister_callback(self, callback: Callable[[MemoryStats], None]) -> None:
        """取消注册回调"""
        if callback in self._callbacks:
            self._callbacks.remove(callback)

    def get_recommended_concurrency(self, base_concurrency: int) -> int:
        """根据当前内存状态推荐并发数"""
        stats = self.get_current_stats()

        if not stats.used_percent:
            return base_concurrency

        if stats.used_percent > self.CRITICAL_THRESHOLD:
            return max(1, base_concurrency // 4)
        elif stats.used_percent > self.HIGH_PRESSURE_THRESHOLD:
            return max(2, base_concurrency // 2)
        elif stats.used_percent > self.MEDIUM_PRESSURE_THRESHOLD:
            return max(4, int(base_concurrency * 0.75))
        elif stats.used_percent > self.LOW_PRESSURE_THRESHOLD:
            return max(6, int(base_concurrency * 0.9))

        return base_concurrency

    def should_use_streaming(self, content_length: Optional[int]) -> bool:
        """判断是否应该使用流式处理"""
        if content_length is None:
            return False

        stats = self.get_current_stats()

        if content_length > self.LARGE_FILE_THRESHOLD:
            return True

        if stats.is_high_pressure and content_length > 1024 * 1024:
            return True

        return False

    def get_history(self, limit: int = 10) -> list[MemoryStats]:
        """获取历史记录"""
        with self._lock:
            return self._history[-limit:]

    def __enter__(self) -> "MemoryManager":
        self.start_monitoring()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.stop_monitoring()
