"""
WebSocket 消息记录器

提供 WebSocket 消息的记录、存储和检索功能。
支持消息过滤、搜索和导出。
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import time
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from typing import Any, Callable

from rich.console import Console
from rich.table import Table

console = Console()


class MessageType(Enum):
    """消息类型枚举"""
    TEXT = "text"
    BINARY = "binary"
    PING = "ping"
    PONG = "pong"
    CLOSE = "close"


class MessageDirection(Enum):
    """消息方向枚举"""
    CLIENT_TO_SERVER = "client_to_server"
    SERVER_TO_CLIENT = "server_to_client"


@dataclass
class WebSocketMessage:
    """
    WebSocket 消息数据类
    
    Attributes:
        message_id: 消息唯一标识
        connection_id: 所属连接 ID
        direction: 消息方向
        message_type: 消息类型
        payload: 消息负载
        timestamp: 时间戳
        size: 消息大小（字节）
        metadata: 附加元数据
    """
    message_id: str
    connection_id: str
    direction: MessageDirection
    message_type: MessageType
    payload: str | bytes
    timestamp: float = field(default_factory=time.time)
    size: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """初始化后计算大小"""
        if self.size == 0:
            if isinstance(self.payload, bytes):
                self.size = len(self.payload)
            else:
                self.size = len(self.payload.encode('utf-8'))
    
    @property
    def is_text(self) -> bool:
        """是否为文本消息"""
        return self.message_type == MessageType.TEXT
    
    @property
    def is_binary(self) -> bool:
        """是否为二进制消息"""
        return self.message_type == MessageType.BINARY
    
    @property
    def is_outgoing(self) -> bool:
        """是否为发往服务器的消息"""
        return self.direction == MessageDirection.CLIENT_TO_SERVER
    
    @property
    def is_incoming(self) -> bool:
        """是否为来自服务器的消息"""
        return self.direction == MessageDirection.SERVER_TO_CLIENT
    
    @property
    def payload_preview(self) -> str:
        """获取负载预览（前 100 字符）"""
        if isinstance(self.payload, bytes):
            preview = self.payload[:100]
            try:
                return preview.decode('utf-8', errors='replace')
            except Exception:
                return f"<binary: {len(self.payload)} bytes>"
        else:
            return self.payload[:100] if len(self.payload) > 100 else self.payload
    
    def to_dict(self) -> dict[str, Any]:
        """
        转换为字典格式
        
        Returns:
            消息字典
        """
        payload_data: str
        if isinstance(self.payload, bytes):
            import base64
            payload_data = base64.b64encode(self.payload).decode('ascii')
        else:
            payload_data = self.payload
        
        return {
            "message_id": self.message_id,
            "connection_id": self.connection_id,
            "direction": self.direction.value,
            "message_type": self.message_type.value,
            "payload": payload_data,
            "timestamp": self.timestamp,
            "size": self.size,
            "metadata": self.metadata,
            "is_binary": isinstance(self.payload, bytes),
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "WebSocketMessage":
        """
        从字典创建消息对象
        
        Args:
            data: 消息字典
            
        Returns:
            消息对象
        """
        payload: str | bytes = data["payload"]
        if data.get("is_binary", False):
            import base64
            payload = base64.b64decode(payload)
        
        return cls(
            message_id=data["message_id"],
            connection_id=data["connection_id"],
            direction=MessageDirection(data["direction"]),
            message_type=MessageType(data["message_type"]),
            payload=payload,
            timestamp=data["timestamp"],
            size=data["size"],
            metadata=data.get("metadata", {}),
        )


@dataclass
class RecorderConfig:
    """
    记录器配置
    
    Attributes:
        storage_path: 存储路径
        max_messages: 最大消息数（0 表示无限制）
        enable_compression: 是否启用压缩
        flush_interval: 刷新间隔（秒）
        filter_direction: 过滤消息方向（None 表示不过滤）
        filter_type: 过滤消息类型（None 表示不过滤）
        on_message: 消息记录回调
    """
    storage_path: str = "./websocket_messages"
    max_messages: int = 0
    enable_compression: bool = False
    flush_interval: float = 5.0
    filter_direction: MessageDirection | None = None
    filter_type: MessageType | None = None
    on_message: Callable[[WebSocketMessage], Any] | None = None


class MessageRecorder:
    """
    WebSocket 消息记录器
    
    提供消息记录、存储和检索功能。
    
    Example:
        ```python
        config = RecorderConfig(
            storage_path="./recordings",
            max_messages=10000
        )
        
        recorder = MessageRecorder(config)
        
        # 记录消息
        message = recorder.record(
            connection_id="conn_001",
            direction=MessageDirection.CLIENT_TO_SERVER,
            message_type=MessageType.TEXT,
            payload="Hello, World!"
        )
        
        # 搜索消息
        results = recorder.search("Hello")
        
        # 导出记录
        recorder.export("session_1.json")
        
        # 打印统计
        recorder.print_statistics()
        ```
    """
    
    def __init__(self, config: RecorderConfig | None = None):
        """
        初始化消息记录器
        
        Args:
            config: 记录器配置，为 None 时使用默认配置
        """
        self.config = config or RecorderConfig()
        self._messages: list[WebSocketMessage] = []
        self._message_counter = 0
        self._lock = asyncio.Lock()
        self._flush_task: asyncio.Task | None = None
        self._session_start = time.time()
        
        # 确保存储目录存在
        Path(self.config.storage_path).mkdir(parents=True, exist_ok=True)
    
    @property
    def message_count(self) -> int:
        """获取消息总数"""
        return len(self._messages)
    
    @property
    def total_bytes(self) -> int:
        """获取总字节数"""
        return sum(msg.size for msg in self._messages)
    
    def _generate_message_id(self) -> str:
        """生成消息唯一 ID"""
        self._message_counter += 1
        return f"msg_{self._message_counter:08d}"
    
    def _should_filter(
        self,
        direction: MessageDirection,
        message_type: MessageType
    ) -> bool:
        """检查是否应该过滤该消息"""
        if self.config.filter_direction and direction != self.config.filter_direction:
            return True
        if self.config.filter_type and message_type != self.config.filter_type:
            return True
        return False
    
    def record(
        self,
        connection_id: str,
        direction: MessageDirection,
        message_type: MessageType,
        payload: str | bytes,
        metadata: dict[str, Any] | None = None
    ) -> WebSocketMessage | None:
        """
        记录一条消息
        
        Args:
            connection_id: 连接 ID
            direction: 消息方向
            message_type: 消息类型
            payload: 消息负载
            metadata: 附加元数据
            
        Returns:
            消息对象，如果被过滤则返回 None
        """
        # 检查过滤器
        if self._should_filter(direction, message_type):
            return None
        
        # 检查消息数限制
        if self.config.max_messages > 0 and len(self._messages) >= self.config.max_messages:
            # 移除最旧的消息
            self._messages.pop(0)
        
        # 创建消息对象
        message = WebSocketMessage(
            message_id=self._generate_message_id(),
            connection_id=connection_id,
            direction=direction,
            message_type=message_type,
            payload=payload,
            metadata=metadata or {},
        )
        
        # 添加到列表
        self._messages.append(message)
        
        # 调用回调
        if self.config.on_message:
            try:
                self.config.on_message(message)
            except Exception as e:
                console.print(f"[red]✗ 消息回调错误: {e}[/]")
        
        return message
    
    async def record_async(
        self,
        connection_id: str,
        direction: MessageDirection,
        message_type: MessageType,
        payload: str | bytes,
        metadata: dict[str, Any] | None = None
    ) -> WebSocketMessage | None:
        """
        异步记录一条消息
        
        Args:
            connection_id: 连接 ID
            direction: 消息方向
            message_type: 消息类型
            payload: 消息负载
            metadata: 附加元数据
            
        Returns:
            消息对象，如果被过滤则返回 None
        """
        async with self._lock:
            return self.record(connection_id, direction, message_type, payload, metadata)
    
    def get_messages(
        self,
        connection_id: str | None = None,
        direction: MessageDirection | None = None,
        message_type: MessageType | None = None,
        limit: int = 0
    ) -> list[WebSocketMessage]:
        """
        获取消息列表
        
        Args:
            connection_id: 过滤连接 ID
            direction: 过滤方向
            message_type: 过滤类型
            limit: 限制数量（0 表示无限制）
            
        Returns:
            消息列表
        """
        messages = self._apply_message_filters(
            self._messages, connection_id, direction, message_type
        )

        if limit > 0:
            messages = messages[-limit:]

        return messages

    def _apply_message_filters(
        self,
        messages: list[WebSocketMessage],
        connection_id: str | None,
        direction: MessageDirection | None,
        message_type: MessageType | None
    ) -> list[WebSocketMessage]:
        """应用消息过滤器"""
        if connection_id:
            messages = [m for m in messages if m.connection_id == connection_id]
        if direction:
            messages = [m for m in messages if m.direction == direction]
        if message_type:
            messages = [m for m in messages if m.message_type == message_type]
        return messages
    
    def search(self, query: str, case_sensitive: bool = False) -> list[WebSocketMessage]:
        """
        搜索消息
        
        Args:
            query: 搜索关键词
            case_sensitive: 是否区分大小写
            
        Returns:
            匹配的消息列表
        """
        results = []
        search_query = query if case_sensitive else query.lower()
        
        for msg in self._messages:
            if isinstance(msg.payload, bytes):
                try:
                    payload_str = msg.payload.decode('utf-8', errors='replace')
                except Exception:
                    continue
            else:
                payload_str = msg.payload
            
            payload_search = payload_str if case_sensitive else payload_str.lower()
            
            if search_query in payload_search:
                results.append(msg)
        
        return results
    
    def get_by_time_range(
        self,
        start_time: float,
        end_time: float
    ) -> list[WebSocketMessage]:
        """
        按时间范围获取消息
        
        Args:
            start_time: 开始时间戳
            end_time: 结束时间戳
            
        Returns:
            消息列表
        """
        return [
            msg for msg in self._messages
            if start_time <= msg.timestamp <= end_time
        ]
    
    def clear(self) -> int:
        """
        清空所有消息
        
        Returns:
            清除的消息数
        """
        count = len(self._messages)
        self._messages.clear()
        self._message_counter = 0
        return count
    
    def export(self, filename: str | None = None) -> str:
        """
        导出记录到文件
        
        Args:
            filename: 文件名（可选）
            
        Returns:
            导出文件路径
        """
        if filename is None:
            filename = f"session_{int(self._session_start)}.json"
        
        filepath = Path(self.config.storage_path) / filename
        
        data = {
            "version": "1.0",
            "created_at": self._session_start,
            "message_count": len(self._messages),
            "messages": [msg.to_dict() for msg in self._messages],
        }
        
        content = json.dumps(data, indent=2, ensure_ascii=False)
        
        if self.config.enable_compression:
            import gzip
            filepath = filepath.with_suffix('.json.gz')
            with gzip.open(filepath, 'wt', encoding='utf-8') as f:
                f.write(content)
        else:
            filepath.write_text(content, encoding='utf-8')
        
        console.print(f"[green]✓ 已导出 {len(self._messages)} 条消息到 {filepath}[/]")
        return str(filepath)
    
    def import_from_file(self, filepath: str) -> int:
        """
        从文件导入记录
        
        Args:
            filepath: 文件路径
            
        Returns:
            导入的消息数
        """
        path = Path(filepath)
        
        if path.suffix == '.gz':
            import gzip
            with gzip.open(path, 'rt', encoding='utf-8') as f:
                content = f.read()
        else:
            content = path.read_text(encoding='utf-8')
        
        data = json.loads(content)
        
        messages = [
            WebSocketMessage.from_dict(msg_data)
            for msg_data in data.get("messages", [])
        ]
        
        self._messages.extend(messages)
        
        console.print(f"[green]✓ 已导入 {len(messages)} 条消息[/]")
        return len(messages)
    
    def get_statistics(self) -> dict[str, Any]:
        """
        获取统计信息
        
        Returns:
            统计信息字典
        """
        if not self._messages:
            return {
                "message_count": 0,
                "total_bytes": 0,
                "session_duration": time.time() - self._session_start,
                "messages_per_direction": {},
                "messages_per_type": {},
                "connections": set(),
            }
        
        # 按方向统计
        direction_counts: dict[str, int] = {}
        for direction in MessageDirection:
            direction_counts[direction.value] = sum(
                1 for m in self._messages if m.direction == direction
            )
        
        # 按类型统计
        type_counts: dict[str, int] = {}
        for msg_type in MessageType:
            type_counts[msg_type.value] = sum(
                1 for m in self._messages if m.message_type == msg_type
            )
        
        # 连接 ID 集合
        connections = {m.connection_id for m in self._messages}
        
        return {
            "message_count": len(self._messages),
            "total_bytes": self.total_bytes,
            "session_duration": time.time() - self._session_start,
            "messages_per_direction": direction_counts,
            "messages_per_type": type_counts,
            "connections": connections,
            "first_message_time": self._messages[0].timestamp,
            "last_message_time": self._messages[-1].timestamp,
        }
    
    def print_statistics(self) -> None:
        """打印统计信息"""
        stats = self.get_statistics()
        
        table = Table(title="消息记录统计")
        table.add_column("指标", style="cyan")
        table.add_column("值", style="green", justify="right")
        
        table.add_row("消息总数", str(stats["message_count"]))
        table.add_row("总字节数", f"{stats['total_bytes']:,}")
        table.add_row("会话时长", f"{stats['session_duration']:.1f} 秒")
        table.add_row("连接数", str(len(stats["connections"])))
        
        console.print(table)
        
        # 方向分布
        if stats["messages_per_direction"]:
            dir_table = Table(title="消息方向分布")
            dir_table.add_column("方向", style="cyan")
            dir_table.add_column("数量", style="green", justify="right")
            
            for direction, count in stats["messages_per_direction"].items():
                dir_table.add_row(direction, str(count))
            
            console.print(dir_table)
        
        # 类型分布
        if stats["messages_per_type"]:
            type_table = Table(title="消息类型分布")
            type_table.add_column("类型", style="cyan")
            type_table.add_column("数量", style="green", justify="right")
            
            for msg_type, count in stats["messages_per_type"].items():
                type_table.add_row(msg_type, str(count))
            
            console.print(type_table)
    
    def print_messages(self, limit: int = 20) -> None:
        """
        打印消息列表
        
        Args:
            limit: 显示数量
        """
        if not self._messages:
            console.print("[yellow]没有记录的消息[/]")
            return
        
        messages = self._messages[-limit:]
        
        table = Table(title=f"最近 {len(messages)} 条消息")
        table.add_column("ID", style="dim", width=12)
        table.add_column("方向", width=8)
        table.add_column("类型", width=8)
        table.add_column("大小", justify="right", width=8)
        table.add_column("预览", width=40)
        
        for msg in messages:
            direction_icon = "→" if msg.is_outgoing else "←"
            direction_color = "cyan" if msg.is_outgoing else "green"
            
            table.add_row(
                msg.message_id,
                f"[{direction_color}]{direction_icon}[/]",
                msg.message_type.value,
                f"{msg.size}B",
                msg.payload_preview[:40],
            )
        
        console.print(table)
    
    async def start_auto_flush(self) -> None:
        """启动自动刷新任务"""
        if self.config.flush_interval <= 0:
            return
        
        async def flush_loop():
            while True:
                await asyncio.sleep(self.config.flush_interval)
                if self._messages:
                    self.export()
        
        self._flush_task = asyncio.create_task(flush_loop())
    
    async def stop_auto_flush(self) -> None:
        """停止自动刷新任务"""
        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass
            self._flush_task = None
