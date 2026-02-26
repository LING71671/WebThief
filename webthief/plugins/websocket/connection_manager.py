"""
WebSocket 连接管理器

管理多个并发 WebSocket 连接，提供连接状态跟踪、
消息路由和连接生命周期管理。
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable
from urllib.parse import urlparse

from rich.console import Console
from rich.table import Table

console = Console()


class ConnectionState(Enum):
    """连接状态枚举"""
    CONNECTING = "connecting"
    CONNECTED = "connected"
    DISCONNECTING = "disconnecting"
    DISCONNECTED = "disconnected"
    ERROR = "error"


@dataclass
class ConnectionInfo:
    """
    WebSocket 连接信息数据类
    
    Attributes:
        connection_id: 连接唯一标识
        url: WebSocket URL
        origin: 来源页面 URL
        remote_address: 远程地址
        connected_at: 连接时间戳
        state: 连接状态
        protocol: 子协议
        extensions: 扩展列表
        request_headers: 请求头
        message_count: 消息计数
        bytes_sent: 发送字节数
        bytes_received: 接收字节数
        last_activity: 最后活动时间
        metadata: 附加元数据
    """
    connection_id: str
    url: str
    origin: str = ""
    remote_address: str = ""
    connected_at: float = field(default_factory=time.time)
    state: ConnectionState = ConnectionState.CONNECTING
    protocol: str = ""
    extensions: list[str] = field(default_factory=list)
    request_headers: dict[str, str] = field(default_factory=dict)
    message_count: int = 0
    bytes_sent: int = 0
    bytes_received: int = 0
    last_activity: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)
    
    @property
    def duration(self) -> float:
        """获取连接持续时间"""
        return time.time() - self.connected_at
    
    @property
    def is_active(self) -> bool:
        """连接是否活跃"""
        return self.state == ConnectionState.CONNECTED
    
    @property
    def host(self) -> str:
        """获取主机名"""
        parsed = urlparse(self.url)
        return parsed.netloc
    
    @property
    def path(self) -> str:
        """获取路径"""
        parsed = urlparse(self.url)
        return parsed.path or "/"
    
    def to_dict(self) -> dict[str, Any]:
        """
        转换为字典格式
        
        Returns:
            连接信息字典
        """
        return {
            "connection_id": self.connection_id,
            "url": self.url,
            "origin": self.origin,
            "remote_address": self.remote_address,
            "connected_at": self.connected_at,
            "state": self.state.value,
            "protocol": self.protocol,
            "extensions": self.extensions,
            "request_headers": self.request_headers,
            "message_count": self.message_count,
            "bytes_sent": self.bytes_sent,
            "bytes_received": self.bytes_received,
            "last_activity": self.last_activity,
            "duration": self.duration,
            "metadata": self.metadata,
        }


@dataclass
class ConnectionManagerConfig:
    """
    连接管理器配置
    
    Attributes:
        max_connections: 最大连接数（0 表示无限制）
        idle_timeout: 空闲超时时间（秒）
        enable_logging: 是否启用日志
        on_connect: 连接建立回调
        on_disconnect: 连接断开回调
        on_message: 消息接收回调
        on_error: 错误回调
    """
    max_connections: int = 0
    idle_timeout: float = 300.0
    enable_logging: bool = True
    on_connect: Callable[[ConnectionInfo], Any] | None = None
    on_disconnect: Callable[[ConnectionInfo], Any] | None = None
    on_message: Callable[[str, str | bytes], Any] | None = None
    on_error: Callable[[str, Exception], Any] | None = None


class ConnectionManager:
    """
    WebSocket 连接管理器
    
    管理多个并发 WebSocket 连接，提供连接状态跟踪、
    消息路由和连接生命周期管理。
    
    Example:
        ```python
        config = ConnectionManagerConfig(
            max_connections=100,
            idle_timeout=300.0
        )
        
        manager = ConnectionManager(config)
        
        # 注册连接
        conn_info = await manager.register_connection(
            url="wss://example.com/ws",
            origin="https://example.com"
        )
        
        # 更新连接状态
        manager.update_state(conn_info.connection_id, ConnectionState.CONNECTED)
        
        # 记录消息
        manager.record_message(conn_info.connection_id, "Hello", direction="send")
        
        # 获取所有连接
        connections = manager.get_all_connections()
        
        # 关闭连接
        await manager.close_connection(conn_info.connection_id)
        ```
    """
    
    def __init__(self, config: ConnectionManagerConfig | None = None):
        """
        初始化连接管理器
        
        Args:
            config: 管理器配置，为 None 时使用默认配置
        """
        self.config = config or ConnectionManagerConfig()
        self._connections: dict[str, ConnectionInfo] = {}
        self._connection_counter = 0
        self._lock = asyncio.Lock()
        self._cleanup_task: asyncio.Task | None = None
    
    @property
    def connection_count(self) -> int:
        """获取当前连接数"""
        return len(self._connections)
    
    @property
    def active_connections(self) -> list[ConnectionInfo]:
        """获取所有活跃连接"""
        return [
            conn for conn in self._connections.values()
            if conn.state == ConnectionState.CONNECTED
        ]
    
    def _generate_connection_id(self) -> str:
        """生成连接唯一 ID"""
        self._connection_counter += 1
        return f"conn_{self._connection_counter:06d}"
    
    async def register_connection(
        self,
        url: str,
        origin: str = "",
        remote_address: str = "",
        protocol: str = "",
        extensions: list[str] | None = None,
        request_headers: dict[str, str] | None = None,
        metadata: dict[str, Any] | None = None
    ) -> ConnectionInfo:
        """
        注册新连接
        
        Args:
            url: WebSocket URL
            origin: 来源页面 URL
            remote_address: 远程地址
            protocol: 子协议
            extensions: 扩展列表
            request_headers: 请求头
            metadata: 附加元数据
            
        Returns:
            连接信息对象
            
        Raises:
            RuntimeError: 超过最大连接数限制
        """
        await self._check_connection_limit()

        connection = self._create_connection_info(
            url, origin, remote_address, protocol, extensions, request_headers, metadata
        )

        await self._register_connection_internal(connection)
        self._log_connection(connection)
        await self._invoke_connect_callback(connection)

        return connection

    async def _check_connection_limit(self) -> None:
        """检查连接数限制"""
        if self.config.max_connections <= 0:
            return

        async with self._lock:
            active_count = len([
                c for c in self._connections.values()
                if c.state == ConnectionState.CONNECTED
            ])
            if active_count >= self.config.max_connections:
                raise RuntimeError(
                    f"已达到最大连接数限制: {self.config.max_connections}"
                )

    def _create_connection_info(
        self,
        url: str,
        origin: str,
        remote_address: str,
        protocol: str,
        extensions: list[str] | None,
        request_headers: dict[str, str] | None,
        metadata: dict[str, Any] | None
    ) -> ConnectionInfo:
        """创建连接信息对象"""
        connection_id = self._generate_connection_id()
        return ConnectionInfo(
            connection_id=connection_id,
            url=url,
            origin=origin,
            remote_address=remote_address,
            protocol=protocol,
            extensions=extensions or [],
            request_headers=request_headers or {},
            metadata=metadata or {},
        )

    async def _register_connection_internal(self, connection: ConnectionInfo) -> None:
        """内部注册连接"""
        async with self._lock:
            self._connections[connection.connection_id] = connection

    def _log_connection(self, connection: ConnectionInfo) -> None:
        """打印连接日志"""
        if not self.config.enable_logging:
            return

        console.print(f"[cyan]🔌 连接建立: {connection.connection_id}[/]")
        console.print(f"   [dim]URL: {connection.url}[/]")
        if connection.origin:
            console.print(f"   [dim]Origin: {connection.origin}[/]")

    async def _invoke_connect_callback(self, connection: ConnectionInfo) -> None:
        """调用连接回调"""
        if not self.config.on_connect:
            return

        try:
            result = self.config.on_connect(connection)
            if asyncio.iscoroutine(result):
                await result
        except Exception as e:
            console.print(f"[red]✗ 连接回调错误: {e}[/]")
    
    async def unregister_connection(self, connection_id: str) -> bool:
        """
        注销连接
        
        Args:
            connection_id: 连接 ID
            
        Returns:
            是否成功注销
        """
        async with self._lock:
            connection = self._connections.get(connection_id)
            if not connection:
                return False
            
            connection.state = ConnectionState.DISCONNECTED
            del self._connections[connection_id]
        
        # 打印日志
        if self.config.enable_logging:
            duration = connection.duration
            console.print(
                f"[dim]🔌 连接关闭: {connection_id} "
                f"(持续 {duration:.1f} 秒, {connection.message_count} 条消息)[/]"
            )
        
        # 调用回调
        if self.config.on_disconnect:
            try:
                result = self.config.on_disconnect(connection)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                console.print(f"[red]✗ 断开回调错误: {e}[/]")
        
        return True
    
    def update_state(
        self,
        connection_id: str,
        state: ConnectionState,
        error_message: str | None = None
    ) -> bool:
        """
        更新连接状态
        
        Args:
            connection_id: 连接 ID
            state: 新状态
            error_message: 错误消息（可选）
            
        Returns:
            是否成功更新
        """
        connection = self._connections.get(connection_id)
        if not connection:
            return False
        
        connection.state = state
        connection.last_activity = time.time()
        
        if error_message:
            connection.metadata["error"] = error_message
        
        return True
    
    def record_message(
        self,
        connection_id: str,
        payload: str | bytes,
        direction: str = "received"
    ) -> bool:
        """
        记录消息
        
        Args:
            connection_id: 连接 ID
            payload: 消息负载
            direction: 方向 ("sent" 或 "received")
            
        Returns:
            是否成功记录
        """
        connection = self._connections.get(connection_id)
        if not connection:
            return False
        
        connection.message_count += 1
        connection.last_activity = time.time()
        
        # 计算字节数
        if isinstance(payload, bytes):
            size = len(payload)
        else:
            size = len(payload.encode('utf-8'))
        
        if direction == "sent":
            connection.bytes_sent += size
        else:
            connection.bytes_received += size
        
        # 调用回调
        if self.config.on_message:
            try:
                self.config.on_message(connection_id, payload)
            except Exception as e:
                console.print(f"[red]✗ 消息回调错误: {e}[/]")
        
        return True
    
    def record_error(self, connection_id: str, error: Exception) -> bool:
        """
        记录错误
        
        Args:
            connection_id: 连接 ID
            error: 异常对象
            
        Returns:
            是否成功记录
        """
        connection = self._connections.get(connection_id)
        if not connection:
            return False
        
        connection.state = ConnectionState.ERROR
        connection.metadata["last_error"] = str(error)
        connection.metadata["last_error_time"] = time.time()
        
        # 调用回调
        if self.config.on_error:
            try:
                self.config.on_error(connection_id, error)
            except Exception as e:
                console.print(f"[red]✗ 错误回调错误: {e}[/]")
        
        return True
    
    def get_connection(self, connection_id: str) -> ConnectionInfo | None:
        """
        获取连接信息
        
        Args:
            connection_id: 连接 ID
            
        Returns:
            连接信息对象，如果不存在则返回 None
        """
        return self._connections.get(connection_id)
    
    def get_all_connections(self) -> list[ConnectionInfo]:
        """
        获取所有连接
        
        Returns:
            连接信息列表
        """
        return list(self._connections.values())
    
    def get_connections_by_url(self, url_pattern: str) -> list[ConnectionInfo]:
        """
        按 URL 模式获取连接
        
        Args:
            url_pattern: URL 模式（支持部分匹配）
            
        Returns:
            匹配的连接列表
        """
        return [
            conn for conn in self._connections.values()
            if url_pattern in conn.url
        ]
    
    def get_connections_by_origin(self, origin: str) -> list[ConnectionInfo]:
        """
        按来源获取连接
        
        Args:
            origin: 来源 URL
            
        Returns:
            匹配的连接列表
        """
        return [
            conn for conn in self._connections.values()
            if conn.origin == origin
        ]
    
    def get_connections_by_state(self, state: ConnectionState) -> list[ConnectionInfo]:
        """
        按状态获取连接
        
        Args:
            state: 连接状态
            
        Returns:
            匹配的连接列表
        """
        return [
            conn for conn in self._connections.values()
            if conn.state == state
        ]
    
    async def close_connection(self, connection_id: str, reason: str = "") -> bool:
        """
        关闭连接
        
        Args:
            connection_id: 连接 ID
            reason: 关闭原因
            
        Returns:
            是否成功关闭
        """
        connection = self._connections.get(connection_id)
        if not connection:
            return False
        
        connection.state = ConnectionState.DISCONNECTING
        if reason:
            connection.metadata["close_reason"] = reason
        
        # 实际关闭操作由外部处理
        return True
    
    async def close_all_connections(self, reason: str = "") -> int:
        """
        关闭所有连接
        
        Args:
            reason: 关闭原因
            
        Returns:
            关闭的连接数
        """
        count = 0
        for connection_id in list(self._connections.keys()):
            if await self.close_connection(connection_id, reason):
                count += 1
        return count
    
    async def start_cleanup_task(self) -> None:
        """启动空闲连接清理任务"""
        if self.config.idle_timeout <= 0:
            return
        
        async def cleanup_loop():
            while True:
                await asyncio.sleep(60)  # 每分钟检查一次
                await self._cleanup_idle_connections()
        
        self._cleanup_task = asyncio.create_task(cleanup_loop())
    
    async def stop_cleanup_task(self) -> None:
        """停止清理任务"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None
    
    async def _cleanup_idle_connections(self) -> int:
        """
        清理空闲连接
        
        Returns:
            清理的连接数
        """
        current_time = time.time()
        idle_threshold = current_time - self.config.idle_timeout
        
        count = 0
        for connection_id, connection in list(self._connections.items()):
            if connection.last_activity < idle_threshold:
                await self.close_connection(connection_id, "空闲超时")
                count += 1
        
        if count > 0:
            console.print(f"[yellow]⚠ 已清理 {count} 个空闲连接[/]")
        
        return count
    
    def get_statistics(self) -> dict[str, Any]:
        """
        获取连接统计信息
        
        Returns:
            统计信息字典
        """
        total_messages = sum(c.message_count for c in self._connections.values())
        total_bytes_sent = sum(c.bytes_sent for c in self._connections.values())
        total_bytes_received = sum(c.bytes_received for c in self._connections.values())
        
        states = {}
        for state in ConnectionState:
            states[state.value] = len(self.get_connections_by_state(state))
        
        return {
            "total_connections": len(self._connections),
            "active_connections": len(self.active_connections),
            "total_messages": total_messages,
            "total_bytes_sent": total_bytes_sent,
            "total_bytes_received": total_bytes_received,
            "states": states,
        }
    
    def print_connections(self) -> None:
        """打印连接列表"""
        if not self._connections:
            console.print("[yellow]没有活跃的连接[/]")
            return
        
        table = Table(title=f"WebSocket 连接 ({len(self._connections)})")
        table.add_column("ID", style="cyan", width=12)
        table.add_column("URL", style="green", width=40)
        table.add_column("状态", style="yellow", width=12)
        table.add_column("消息", style="white", justify="right", width=8)
        table.add_column("持续时间", style="dim", width=10)
        
        for conn in self._connections.values():
            # 截断 URL
            url_display = conn.url
            if len(url_display) > 38:
                url_display = url_display[:35] + "..."
            
            # 状态颜色
            state_color = {
                ConnectionState.CONNECTED: "green",
                ConnectionState.CONNECTING: "yellow",
                ConnectionState.DISCONNECTING: "orange",
                ConnectionState.DISCONNECTED: "dim",
                ConnectionState.ERROR: "red",
            }.get(conn.state, "white")
            
            table.add_row(
                conn.connection_id,
                url_display,
                f"[{state_color}]{conn.state.value}[/]",
                str(conn.message_count),
                f"{conn.duration:.1f}s"
            )
        
        console.print(table)
    
    def print_statistics(self) -> None:
        """打印统计信息"""
        stats = self.get_statistics()
        
        table = Table(title="连接统计")
        table.add_column("指标", style="cyan")
        table.add_column("值", style="green", justify="right")
        
        table.add_row("总连接数", str(stats["total_connections"]))
        table.add_row("活跃连接", str(stats["active_connections"]))
        table.add_row("总消息数", str(stats["total_messages"]))
        table.add_row("发送字节", f"{stats['total_bytes_sent']:,}")
        table.add_row("接收字节", f"{stats['total_bytes_received']:,}")
        
        console.print(table)
        
        # 状态分布
        states_table = Table(title="连接状态分布")
        states_table.add_column("状态", style="cyan")
        states_table.add_column("数量", style="green", justify="right")
        
        for state, count in stats["states"].items():
            states_table.add_row(state, str(count))
        
        console.print(states_table)
