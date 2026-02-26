"""
并发管理器：动态调整并发数

功能：
- 基于成功率动态调整并发数
- 任务队列管理
- 性能指标收集
"""

from __future__ import annotations

import asyncio
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Optional

from rich.console import Console

console = Console()


class ConcurrencyState(Enum):
    """并发状态"""
    IDLE = "idle"
    LOW_LOAD = "low_load"
    MEDIUM_LOAD = "medium_load"
    HIGH_LOAD = "high_load"
    OVERLOADED = "overloaded"


@dataclass
class ConcurrencyConfig:
    """并发配置"""
    min_concurrency: int = 2
    max_concurrency: int = 50
    initial_concurrency: int = 10
    adjustment_interval: float = 2.0
    increase_threshold: float = 0.7
    decrease_threshold: float = 0.5
    increase_step: int = 2
    decrease_step: int = 3
    cooldown_period: float = 5.0


@dataclass
class TaskMetrics:
    """任务指标"""
    total_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    total_time: float = 0.0
    total_bytes: int = 0
    avg_response_time: float = 0.0
    success_rate: float = 1.0
    recent_times: deque = field(default_factory=lambda: deque(maxlen=100))
    recent_successes: deque = field(default_factory=lambda: deque(maxlen=100))

    def record_success(self, duration: float, bytes_count: int = 0) -> None:
        self.completed_tasks += 1
        self.total_time += duration
        self.total_bytes += bytes_count
        self.recent_times.append(duration)
        self.recent_successes.append(True)
        self._update_stats()

    def record_failure(self, duration: float = 0.0) -> None:
        self.failed_tasks += 1
        self.total_time += duration
        self.recent_successes.append(False)
        self._update_stats()

    def _update_stats(self) -> None:
        if self.recent_times:
            self.avg_response_time = sum(self.recent_times) / len(self.recent_times)
        if self.recent_successes:
            successes = sum(1 for s in self.recent_successes if s)
            self.success_rate = successes / len(self.recent_successes)

    def to_dict(self) -> dict:
        return {
            "total_tasks": self.total_tasks,
            "completed_tasks": self.completed_tasks,
            "failed_tasks": self.failed_tasks,
            "total_time": round(self.total_time, 2),
            "total_bytes": self.total_bytes,
            "avg_response_time": round(self.avg_response_time, 3),
            "success_rate": round(self.success_rate, 3),
        }


class ConcurrencyManager:
    """并发管理器"""

    def __init__(
        self,
        config: Optional[ConcurrencyConfig] = None,
        on_adjustment: Optional[Callable[[int, str], None]] = None,
    ):
        self.config = config or ConcurrencyConfig()
        self.on_adjustment = on_adjustment
        self._current_concurrency = self.config.initial_concurrency
        self._state = ConcurrencyState.IDLE
        self._metrics = TaskMetrics()
        self._lock = threading.Lock()
        self._adjustment_history: list[tuple[float, int, str]] = []
        self._last_adjustment_time = 0.0
        self._consecutive_failures = 0
        self._consecutive_successes = 0

    @property
    def current_concurrency(self) -> int:
        return self._current_concurrency

    @property
    def state(self) -> ConcurrencyState:
        return self._state

    @property
    def metrics(self) -> TaskMetrics:
        return self._metrics

    def get_semaphore(self) -> asyncio.Semaphore:
        return asyncio.Semaphore(self._current_concurrency)

    def record_task_result(self, success: bool, duration: float, bytes_count: int = 0) -> None:
        """记录任务结果"""
        with self._lock:
            self._metrics.total_tasks += 1

            if success:
                self._metrics.record_success(duration, bytes_count)
                self._consecutive_successes += 1
                self._consecutive_failures = 0
            else:
                self._metrics.record_failure(duration)
                self._consecutive_failures += 1
                self._consecutive_successes = 0

            self._update_state()

    def _update_state(self) -> None:
        """更新并发状态"""
        success_rate = self._metrics.success_rate
        avg_time = self._metrics.avg_response_time

        if self._consecutive_failures >= 5:
            self._state = ConcurrencyState.OVERLOADED
        elif success_rate < 0.3 or avg_time > 10.0:
            self._state = ConcurrencyState.HIGH_LOAD
        elif success_rate < 0.6 or avg_time > 5.0:
            self._state = ConcurrencyState.MEDIUM_LOAD
        elif self._metrics.completed_tasks > 0:
            self._state = ConcurrencyState.LOW_LOAD
        else:
            self._state = ConcurrencyState.IDLE

    def adjust_concurrency(self, force: bool = False) -> int:
        """根据当前状态调整并发数"""
        now = time.time()

        if not force and (now - self._last_adjustment_time) < self.config.cooldown_period:
            return self._current_concurrency

        old_concurrency = self._current_concurrency
        reason = ""

        with self._lock:
            if self._state == ConcurrencyState.OVERLOADED:
                new_concurrency = max(
                    self.config.min_concurrency,
                    self._current_concurrency - self.config.decrease_step * 2
                )
                reason = "系统过载"
            elif self._state == ConcurrencyState.HIGH_LOAD:
                new_concurrency = max(
                    self.config.min_concurrency,
                    self._current_concurrency - self.config.decrease_step
                )
                reason = "高负载"
            elif self._state == ConcurrencyState.MEDIUM_LOAD:
                if self._metrics.success_rate < self.config.decrease_threshold:
                    new_concurrency = max(
                        self.config.min_concurrency,
                        self._current_concurrency - 1
                    )
                    reason = "成功率下降"
                else:
                    return self._current_concurrency
            elif self._state == ConcurrencyState.LOW_LOAD:
                if self._metrics.success_rate > self.config.increase_threshold:
                    new_concurrency = min(
                        self.config.max_concurrency,
                        self._current_concurrency + self.config.increase_step
                    )
                    reason = "性能良好，增加并发"
                else:
                    return self._current_concurrency
            else:
                return self._current_concurrency

            self._current_concurrency = new_concurrency
            self._last_adjustment_time = now

            self._adjustment_history.append((now, new_concurrency, reason))
            if len(self._adjustment_history) > 50:
                self._adjustment_history.pop(0)

        if self.on_adjustment and new_concurrency != old_concurrency:
            try:
                self.on_adjustment(new_concurrency, reason)
            except Exception as e:
                console.print(f"[red]并发调整回调错误: {e}[/]")

        if new_concurrency != old_concurrency:
            console.print(f"[cyan]并发调整: {old_concurrency} -> {new_concurrency} ({reason})[/]")

        return self._current_concurrency

    def set_concurrency(self, value: int, reason: str = "手动设置") -> None:
        """手动设置并发数"""
        with self._lock:
            old_value = self._current_concurrency
            self._current_concurrency = max(
                self.config.min_concurrency,
                min(self.config.max_concurrency, value)
            )
            self._last_adjustment_time = time.time()
            self._adjustment_history.append((time.time(), self._current_concurrency, reason))

        if old_value != self._current_concurrency:
            console.print(f"[cyan]并发设置: {old_value} -> {self._current_concurrency} ({reason})[/]")

    def reset_metrics(self) -> None:
        """重置指标"""
        with self._lock:
            self._metrics = TaskMetrics()
            self._consecutive_failures = 0
            self._consecutive_successes = 0

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "current_concurrency": self._current_concurrency,
            "state": self._state.value,
            "config": {
                "min_concurrency": self.config.min_concurrency,
                "max_concurrency": self.config.max_concurrency,
                "initial_concurrency": self.config.initial_concurrency,
            },
            "metrics": self._metrics.to_dict(),
        }
