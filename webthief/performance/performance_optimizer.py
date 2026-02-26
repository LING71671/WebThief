"""
性能优化器：整合内存管理和并发控制

功能：
- 统一的性能优化入口
- 自动化资源管理
- 性能指标收集和报告
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Callable, Optional

from rich.console import Console
from rich.table import Table

from .concurrency_manager import ConcurrencyConfig, ConcurrencyManager, TaskMetrics
from .memory_manager import MemoryManager, MemoryStats

console = Console()


@dataclass
class PerformanceReport:
    """性能报告"""
    start_time: float = 0.0
    end_time: float = 0.0
    duration_seconds: float = 0.0
    total_files: int = 0
    total_bytes: int = 0
    successful_files: int = 0
    failed_files: int = 0
    avg_download_speed: float = 0.0
    avg_response_time: float = 0.0
    peak_concurrency: int = 0
    peak_memory_mb: float = 0.0
    avg_memory_percent: float = 0.0
    peak_cpu_percent: float = 0.0

    def to_dict(self) -> dict:
        return {
            "duration_seconds": round(self.duration_seconds, 2),
            "total_files": self.total_files,
            "total_bytes": self.total_bytes,
            "total_size_mb": round(self.total_bytes / (1024 * 1024), 2),
            "successful_files": self.successful_files,
            "failed_files": self.failed_files,
            "avg_download_speed_mbps": round(self.avg_download_speed, 2),
            "avg_response_time": round(self.avg_response_time, 3),
            "peak_concurrency": self.peak_concurrency,
            "peak_memory_mb": round(self.peak_memory_mb, 2),
            "avg_memory_percent": round(self.avg_memory_percent, 2),
            "peak_cpu_percent": round(self.peak_cpu_percent, 2),
        }


class PerformanceOptimizer:
    """性能优化器"""

    def __init__(
        self,
        base_concurrency: int = 20,
        memory_limit_mb: Optional[float] = None,
        enable_monitoring: bool = True,
    ):
        self.base_concurrency = base_concurrency
        self.enable_monitoring = enable_monitoring

        self.memory_manager = MemoryManager(
            memory_limit_mb=memory_limit_mb,
            check_interval=1.0,
        )

        self.concurrency_manager = ConcurrencyManager(
            config=ConcurrencyConfig(
                min_concurrency=2,
                max_concurrency=base_concurrency * 2,
                initial_concurrency=base_concurrency,
            ),
            on_adjustment=self._on_concurrency_adjustment,
        )

        self._report = PerformanceReport()
        self._concurrency_history: list[int] = []
        self._lock = threading.RLock()
        self._on_resource_warning: Optional[Callable[[str], None]] = None

    def _on_concurrency_adjustment(self, new_value: int, reason: str) -> None:
        with self._lock:
            self._concurrency_history.append(new_value)
            if new_value > self._report.peak_concurrency:
                self._report.peak_concurrency = new_value

    def start(self) -> None:
        self._report.start_time = time.time()

        if self.enable_monitoring:
            self.memory_manager.start_monitoring()
            self.memory_manager.register_callback(self._on_memory_update)

        console.print("[green]性能优化器已启动[/]")

    def stop(self) -> None:
        self._report.end_time = time.time()
        self._report.duration_seconds = self._report.end_time - self._report.start_time

        if self.enable_monitoring:
            self.memory_manager.stop_monitoring()

        console.print("[green]性能优化器已停止[/]")

    def _on_memory_update(self, stats: MemoryStats) -> None:
        with self._lock:
            if stats.process_used_mb > self._report.peak_memory_mb:
                self._report.peak_memory_mb = stats.process_used_mb
            if stats.cpu_percent > self._report.peak_cpu_percent:
                self._report.peak_cpu_percent = stats.cpu_percent

            if stats.used_percent > 0:
                current_avg = self._report.avg_memory_percent
                count = len(self.memory_manager.get_history(100))
                if count > 0:
                    self._report.avg_memory_percent = (
                        (current_avg * (count - 1) + stats.used_percent) / count
                    )

        if stats.is_critical and self._on_resource_warning:
            try:
                self._on_resource_warning(f"内存使用危急: {stats.used_percent:.1f}%")
            except Exception:
                pass

    def get_optimal_concurrency(self) -> int:
        memory_recommended = self.memory_manager.get_recommended_concurrency(self.base_concurrency)
        self.concurrency_manager.adjust_concurrency()
        current = self.concurrency_manager.current_concurrency
        optimal = min(memory_recommended, current)
        return max(2, optimal)

    def should_use_streaming(self, content_length: Optional[int]) -> bool:
        return self.memory_manager.should_use_streaming(content_length)

    def record_download(
        self,
        url: str,
        success: bool,
        duration: float,
        bytes_count: int = 0,
    ) -> None:
        with self._lock:
            self._report.total_files += 1

            if success:
                self._report.successful_files += 1
                self._report.total_bytes += bytes_count
            else:
                self._report.failed_files += 1

            if self._report.duration_seconds > 0:
                self._report.avg_download_speed = (
                    self._report.total_bytes / (1024 * 1024) / self._report.duration_seconds
                )

        self.concurrency_manager.record_task_result(success, duration, bytes_count)

    def get_memory_stats(self) -> MemoryStats:
        return self.memory_manager.get_current_stats()

    def get_concurrency_stats(self) -> TaskMetrics:
        return self.concurrency_manager.metrics

    def get_report(self) -> PerformanceReport:
        return self._report

    def print_report(self) -> None:
        report = self._report

        console.print("\n" + "=" * 60)
        console.print("[bold cyan]性能报告[/]")
        console.print("=" * 60)

        table = Table(title="下载统计", show_header=True, header_style="bold magenta")
        table.add_column("指标", style="cyan")
        table.add_column("值", style="green")

        table.add_row("总耗时", f"{report.duration_seconds:.2f} 秒")
        table.add_row("总文件数", str(report.total_files))
        table.add_row("成功", str(report.successful_files))
        table.add_row("失败", str(report.failed_files))
        table.add_row("总大小", f"{report.total_bytes / (1024 * 1024):.2f} MB")
        table.add_row("平均速度", f"{report.avg_download_speed:.2f} MB/s")

        console.print(table)

        concurrency_table = Table(title="并发统计", show_header=True, header_style="bold magenta")
        concurrency_table.add_column("指标", style="cyan")
        concurrency_table.add_column("值", style="green")

        concurrency_table.add_row("峰值并发", str(report.peak_concurrency))
        concurrency_table.add_row("成功率", f"{self.concurrency_manager.metrics.success_rate:.1%}")
        concurrency_table.add_row("平均响应时间", f"{self.concurrency_manager.metrics.avg_response_time:.3f}s")

        console.print(concurrency_table)

        resource_table = Table(title="资源使用", show_header=True, header_style="bold magenta")
        resource_table.add_column("指标", style="cyan")
        resource_table.add_column("值", style="green")

        resource_table.add_row("峰值内存", f"{report.peak_memory_mb:.1f} MB")
        resource_table.add_row("平均内存使用率", f"{report.avg_memory_percent:.1f}%")
        resource_table.add_row("峰值 CPU", f"{report.peak_cpu_percent:.1f}%")

        console.print(resource_table)
        console.print("=" * 60 + "\n")

    def set_resource_warning_callback(self, callback: Callable[[str], None]) -> None:
        self._on_resource_warning = callback

    def __enter__(self) -> "PerformanceOptimizer":
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.stop()
