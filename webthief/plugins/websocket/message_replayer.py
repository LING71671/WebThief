"""
WebSocket 消息回放器

支持从录制文件回放 WebSocket 消息，
支持定时回放、条件回放和消息修改。
"""

from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table

from webthief.plugins.websocket.message_recorder import (
    WebSocketMessage,
    MessageType,
    MessageDirection,
)

console = Console()


class ReplayMode(Enum):
    """回放模式枚举"""
    REALTIME = "realtime"           # 按原始时间间隔回放
    FAST = "fast"                   # 快速回放（无延迟）
    STEP = "step"                   # 单步回放（手动控制）
    CUSTOM = "custom"               # 自定义间隔


class ReplayState(Enum):
    """回放状态枚举"""
    IDLE = "idle"
    PLAYING = "playing"
    PAUSED = "paused"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class ReplayConfig:
    """
    回放配置
    
    Attributes:
        mode: 回放模式
        speed_multiplier: 速度倍数（仅 REALTIME 模式有效）
        custom_interval: 自定义间隔（秒，仅 CUSTOM 模式有效）
        enable_message_modification: 是否启用消息修改
        message_modifier: 消息修改函数
        stop_on_error: 遇到错误是否停止
        loop_playback: 是否循环播放
        filter_direction: 过滤消息方向（None 表示不过滤）
        filter_connection: 过滤连接 ID（None 表示不过滤）
    """
    mode: ReplayMode = ReplayMode.REALTIME
    speed_multiplier: float = 1.0
    custom_interval: float = 0.1
    enable_message_modification: bool = False
    message_modifier: Callable[[WebSocketMessage], WebSocketMessage] | None = None
    stop_on_error: bool = True
    loop_playback: bool = False
    filter_direction: MessageDirection | None = None
    filter_connection: str | None = None


@dataclass
class ReplayResult:
    """
    回放结果
    
    Attributes:
        total_messages: 总消息数
        played_messages: 已播放消息数
        skipped_messages: 跳过消息数
        errors: 错误列表
        start_time: 开始时间
        end_time: 结束时间
    """
    total_messages: int = 0
    played_messages: int = 0
    skipped_messages: int = 0
    errors: list[str] = field(default_factory=list)
    start_time: float | None = None
    end_time: float | None = None
    
    @property
    def duration(self) -> float:
        """获取回放持续时间"""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return 0.0
    
    @property
    def success(self) -> bool:
        """是否成功完成"""
        return len(self.errors) == 0


class MessageReplayer:
    """
    WebSocket 消息回放器
    
    支持从录制文件回放 WebSocket 消息，提供多种回放模式和配置选项。
    
    Example:
        ```python
        config = ReplayConfig(
            mode=ReplayMode.REALTIME,
            speed_multiplier=2.0
        )
        
        replayer = MessageReplayer(config)
        
        # 加载录制文件
        await replayer.load_recording("session_1.json")
        
        # 设置消息发送回调
        replayer.set_send_callback(my_send_function)
        
        # 开始回放
        result = await replayer.start()
        
        # 打印结果
        replayer.print_result()
        ```
    """
    
    def __init__(self, config: ReplayConfig | None = None):
        """
        初始化消息回放器
        
        Args:
            config: 回放配置，为 None 时使用默认配置
        """
        self.config = config or ReplayConfig()
        self._messages: list[WebSocketMessage] = []
        self._filtered_messages: list[WebSocketMessage] = []
        self._state = ReplayState.IDLE
        self._current_index = 0
        self._send_callback: Callable[[str | bytes], Any] | None = None
        self._pause_event = asyncio.Event()
        self._stop_event = asyncio.Event()
        self._result = ReplayResult()
    
    @property
    def state(self) -> ReplayState:
        """获取当前状态"""
        return self._state
    
    @property
    def current_index(self) -> int:
        """获取当前播放索引"""
        return self._current_index
    
    @property
    def total_messages(self) -> int:
        """获取消息总数"""
        return len(self._filtered_messages)
    
    @property
    def progress(self) -> float:
        """获取播放进度（0.0 - 1.0）"""
        if not self._filtered_messages:
            return 0.0
        return self._current_index / len(self._filtered_messages)
    
    def set_send_callback(self, callback: Callable[[str | bytes], Any]) -> None:
        """
        设置消息发送回调函数
        
        Args:
            callback: 回调函数，接收消息负载作为参数
        """
        self._send_callback = callback
    
    async def load_recording(self, file_path: str) -> int:
        """
        加载录制文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            加载的消息数量
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"录制文件不存在: {file_path}")
        
        content = path.read_text(encoding='utf-8')
        data = json.loads(content)
        
        self._messages = [
            WebSocketMessage.from_dict(msg_data)
            for msg_data in data.get("messages", [])
        ]
        
        # 应用过滤器
        self._apply_filters()
        
        console.print(f"[green]✓ 已加载 {len(self._messages)} 条消息，过滤后 {len(self._filtered_messages)} 条[/]")
        return len(self._filtered_messages)
    
    def load_messages(self, messages: list[WebSocketMessage]) -> int:
        """
        直接加载消息列表
        
        Args:
            messages: 消息列表
            
        Returns:
            加载的消息数量
        """
        self._messages = messages.copy()
        self._apply_filters()
        return len(self._filtered_messages)
    
    def _apply_filters(self) -> None:
        """应用消息过滤器"""
        self._filtered_messages = []
        
        for msg in self._messages:
            # 方向过滤
            if self.config.filter_direction and msg.direction != self.config.filter_direction:
                continue
            
            # 连接过滤
            if self.config.filter_connection and msg.connection_id != self.config.filter_connection:
                continue
            
            self._filtered_messages.append(msg)
    
    async def start(self) -> ReplayResult:
        """
        开始回放
        
        Returns:
            回放结果
        """
        if not self._filtered_messages:
            console.print("[yellow]⚠ 没有可回放的消息[/]")
            return self._result
        
        if not self._send_callback:
            raise RuntimeError("未设置消息发送回调函数")
        
        self._state = ReplayState.PLAYING
        self._stop_event.clear()
        self._pause_event.set()
        self._result = ReplayResult(
            total_messages=len(self._filtered_messages),
            start_time=time.time()
        )
        
        try:
            if self.config.mode == ReplayMode.STEP:
                await self._replay_step_mode()
            else:
                await self._replay_auto_mode()
        except asyncio.CancelledError:
            self._state = ReplayState.PAUSED
        except Exception as e:
            self._state = ReplayState.ERROR
            self._result.errors.append(str(e))
            console.print(f"[red]✗ 回放错误: {e}[/]")
        finally:
            if self._state == ReplayState.PLAYING:
                self._state = ReplayState.COMPLETED
            self._result.end_time = time.time()
        
        return self._result
    
    async def _replay_auto_mode(self) -> None:
        """自动回放模式"""
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console
        ) as progress:
            task = progress.add_task("回放消息...", total=len(self._filtered_messages))

            prev_timestamp = None

            for i, message in enumerate(self._filtered_messages):
                if self._stop_event.is_set():
                    break

                await self._pause_event.wait()

                await self._apply_replay_delay(message, prev_timestamp)

                if not await self._try_send_message(message, i, progress, task):
                    break

                prev_timestamp = message.timestamp

            if self.config.loop_playback and not self._stop_event.is_set():
                self._current_index = 0
                await self._replay_auto_mode()

    async def _apply_replay_delay(
        self,
        message: WebSocketMessage,
        prev_timestamp: float | None
    ) -> None:
        """应用回放延迟"""
        if self.config.mode == ReplayMode.REALTIME and prev_timestamp is not None:
            delay = (message.timestamp - prev_timestamp) / self.config.speed_multiplier
            if delay > 0:
                await asyncio.sleep(delay)
        elif self.config.mode == ReplayMode.CUSTOM:
            await asyncio.sleep(self.config.custom_interval)

    async def _try_send_message(
        self,
        message: WebSocketMessage,
        index: int,
        progress: Progress,
        task
    ) -> bool:
        """尝试发送消息，返回是否应继续"""
        try:
            await self._send_message(message)
            self._result.played_messages += 1
        except Exception as e:
            self._result.errors.append(f"消息 {message.message_id}: {e}")
            if self.config.stop_on_error:
                return False

        self._current_index = index + 1
        progress.update(task, advance=1)
        return True
    
    async def _replay_step_mode(self) -> None:
        """单步回放模式"""
        for i, message in enumerate(self._filtered_messages):
            if self._stop_event.is_set():
                break
            
            self._current_index = i
            self._state = ReplayState.PAUSED
            self._pause_event.clear()
            
            # 等待用户继续
            await self._pause_event.wait()
            
            self._state = ReplayState.PLAYING
            
            try:
                await self._send_message(message)
                self._result.played_messages += 1
            except Exception as e:
                self._result.errors.append(f"消息 {message.message_id}: {e}")
                if self.config.stop_on_error:
                    raise
    
    async def _send_message(self, message: WebSocketMessage) -> None:
        """
        发送单条消息
        
        Args:
            message: 消息对象
        """
        # 应用消息修改器
        if self.config.enable_message_modification and self.config.message_modifier:
            message = self.config.message_modifier(message)
        
        # 调用发送回调
        if self._send_callback:
            result = self._send_callback(message.payload)
            if asyncio.iscoroutine(result):
                await result
        
        # 打印日志
        direction_icon = "→" if message.direction == MessageDirection.CLIENT_TO_SERVER else "←"
        console.print(f"[cyan]{direction_icon}[/] [dim]{message.message_id}[/] 已发送")
    
    def pause(self) -> None:
        """暂停回放"""
        if self._state == ReplayState.PLAYING:
            self._state = ReplayState.PAUSED
            self._pause_event.clear()
            console.print("[yellow]⏸ 回放已暂停[/]")
    
    def resume(self) -> None:
        """恢复回放"""
        if self._state == ReplayState.PAUSED:
            self._state = ReplayState.PLAYING
            self._pause_event.set()
            console.print("[green]▶ 回放已恢复[/]")
    
    def stop(self) -> None:
        """停止回放"""
        self._stop_event.set()
        self._pause_event.set()
        console.print("[red]⏹ 回放已停止[/]")
    
    def step_next(self) -> None:
        """
        单步模式下前进到下一条消息
        """
        if self.config.mode == ReplayMode.STEP and self._state == ReplayState.PAUSED:
            self._pause_event.set()
    
    def seek_to(self, index: int) -> None:
        """
        跳转到指定位置
        
        Args:
            index: 目标索引
        """
        if 0 <= index < len(self._filtered_messages):
            self._current_index = index
            console.print(f"[cyan]⏭ 跳转到消息 {index + 1}/{len(self._filtered_messages)}[/]")
    
    def seek_to_percentage(self, percentage: float) -> None:
        """
        跳转到指定百分比位置
        
        Args:
            percentage: 百分比（0.0 - 1.0）
        """
        index = int(percentage * len(self._filtered_messages))
        self.seek_to(index)
    
    def get_current_message(self) -> WebSocketMessage | None:
        """
        获取当前消息
        
        Returns:
            当前消息对象，如果没有则返回 None
        """
        if 0 <= self._current_index < len(self._filtered_messages):
            return self._filtered_messages[self._current_index]
        return None
    
    def get_message_at(self, index: int) -> WebSocketMessage | None:
        """
        获取指定索引的消息
        
        Args:
            index: 消息索引
            
        Returns:
            消息对象，如果索引无效则返回 None
        """
        if 0 <= index < len(self._filtered_messages):
            return self._filtered_messages[index]
        return None
    
    def print_result(self) -> None:
        """打印回放结果"""
        table = Table(title="回放结果")
        table.add_column("指标", style="cyan")
        table.add_column("值", style="green", justify="right")
        
        table.add_row("总消息数", str(self._result.total_messages))
        table.add_row("已播放", str(self._result.played_messages))
        table.add_row("已跳过", str(self._result.skipped_messages))
        table.add_row("错误数", str(len(self._result.errors)))
        table.add_row("持续时间", f"{self._result.duration:.2f} 秒")
        table.add_row("状态", self._state.value)
        
        console.print(table)
        
        if self._result.errors:
            console.print("\n[red]错误详情:[/]")
            for error in self._result.errors:
                console.print(f"  - {error}")
    
    def get_statistics(self) -> dict[str, Any]:
        """
        获取回放统计信息
        
        Returns:
            统计信息字典
        """
        return {
            "state": self._state.value,
            "total_messages": self._result.total_messages,
            "played_messages": self._result.played_messages,
            "skipped_messages": self._result.skipped_messages,
            "error_count": len(self._result.errors),
            "duration": self._result.duration,
            "progress": self.progress,
            "current_index": self._current_index,
        }
    
    @staticmethod
    def list_recordings(storage_path: str = "./websocket_messages") -> list[dict[str, Any]]:
        """
        列出所有可用的录制文件
        
        Args:
            storage_path: 存储路径
            
        Returns:
            录制文件信息列表
        """
        path = Path(storage_path)
        if not path.exists():
            return []
        
        recordings = []
        for file in path.glob("*.json"):
            try:
                content = file.read_text(encoding='utf-8')
                data = json.loads(content)
                recordings.append({
                    "filename": file.name,
                    "path": str(file),
                    "message_count": data.get("message_count", 0),
                    "created_at": data.get("created_at", 0),
                    "size": file.stat().st_size,
                })
            except Exception:
                continue
        
        # 按创建时间排序
        recordings.sort(key=lambda x: x["created_at"], reverse=True)
        return recordings
    
    @staticmethod
    def print_recordings_list(storage_path: str = "./websocket_messages") -> None:
        """
        打印录制文件列表
        
        Args:
            storage_path: 存储路径
        """
        recordings = MessageReplayer.list_recordings(storage_path)
        
        if not recordings:
            console.print("[yellow]没有找到录制文件[/]")
            return
        
        table = Table(title="可用的录制文件")
        table.add_column("文件名", style="cyan")
        table.add_column("消息数", style="green", justify="right")
        table.add_column("大小", style="yellow", justify="right")
        table.add_column("创建时间", style="dim")
        
        for rec in recordings:
            created_time = time.strftime(
                "%Y-%m-%d %H:%M:%S",
                time.localtime(rec["created_at"])
            )
            size_kb = rec["size"] / 1024
            table.add_row(
                rec["filename"],
                str(rec["message_count"]),
                f"{size_kb:.1f} KB",
                created_time
            )
        
        console.print(table)
