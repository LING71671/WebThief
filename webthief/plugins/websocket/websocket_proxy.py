"""
WebSocket 代理核心模块

提供 WebSocket 连接拦截和代理功能，与 Playwright 集成，
支持消息记录、回放和连接管理。
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from webthief.plugins.websocket.message_recorder import (
    MessageRecorder,
    RecorderConfig,
    MessageType,
    MessageDirection,
)
from webthief.plugins.websocket.message_replayer import (
    MessageReplayer,
    ReplayConfig,
    ReplayMode,
)
from webthief.plugins.websocket.connection_manager import (
    ConnectionManager,
    ConnectionManagerConfig,
    ConnectionInfo,
    ConnectionState,
)

console = Console()


class ProxyMode(Enum):
    """代理模式枚举"""
    PASSIVE = "passive"         # 被动模式：仅记录，不干预
    ACTIVE = "active"           # 主动模式：可修改消息
    BLOCK = "block"             # 阻断模式：阻止连接
    REPLAY = "replay"           # 回放模式：回放录制消息


@dataclass
class WebSocketProxyConfig:
    """
    WebSocket 代理配置
    
    Attributes:
        mode: 代理模式
        enable_recording: 是否启用消息记录
        enable_replay: 是否启用消息回放
        recorder_config: 消息记录器配置
        replayer_config: 消息回放器配置
        connection_config: 连接管理器配置
        message_filter: 消息过滤函数
        message_transformer: 消息转换函数
        connection_filter: 连接过滤函数
        on_websocket_created: WebSocket 创建回调
        on_websocket_closed: WebSocket 关闭回调
        on_message_received: 消息接收回调
        on_message_sent: 消息发送回调
    """
    mode: ProxyMode = ProxyMode.PASSIVE
    enable_recording: bool = True
    enable_replay: bool = False
    recorder_config: RecorderConfig | None = None
    replayer_config: ReplayConfig | None = None
    connection_config: ConnectionManagerConfig | None = None
    message_filter: Callable[[str, str | bytes], bool] | None = None
    message_transformer: Callable[[str, str | bytes], str | bytes] | None = None
    connection_filter: Callable[[str, str], bool] | None = None
    on_websocket_created: Callable[[str, str], Any] | None = None
    on_websocket_closed: Callable[[str], Any] | None = None
    on_message_received: Callable[[str, str | bytes], Any] | None = None
    on_message_sent: Callable[[str, str | bytes], Any] | None = None


@dataclass
class InterceptedWebSocket:
    """
    被拦截的 WebSocket 连接
    
    Attributes:
        connection_id: 连接 ID
        url: WebSocket URL
        page_url: 页面 URL
        ws: Playwright WebSocket 对象
        connection_info: 连接信息
        is_connected: 是否已连接
        message_queue: 消息队列
    """
    connection_id: str
    url: str
    page_url: str
    ws: Any  # Playwright WebSocket
    connection_info: ConnectionInfo
    is_connected: bool = True
    message_queue: asyncio.Queue = field(default_factory=asyncio.Queue)


class WebSocketProxy:
    """
    WebSocket 代理类
    
    提供 WebSocket 连接拦截和代理功能，与 Playwright 集成，
    支持消息记录、回放和连接管理。
    
    Example:
        ```python
        # 创建代理
        config = WebSocketProxyConfig(
            mode=ProxyMode.PASSIVE,
            enable_recording=True
        )
        proxy = WebSocketProxy(config)
        
        # 与 Playwright 集成
        from playwright.async_api import async_playwright
        
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            context = await browser.new_context()
            page = await context.new_page()
            
            # 设置 WebSocket 拦截
            proxy.setup_page_interception(page)
            
            # 访问页面
            await page.goto("https://example.com")
            
            # 获取统计信息
            proxy.print_statistics()
            
            # 保存录制
            await proxy.save_recording("session.json")
        ```
    """
    
    def __init__(self, config: WebSocketProxyConfig | None = None):
        """
        初始化 WebSocket 代理
        
        Args:
            config: 代理配置，为 None 时使用默认配置
        """
        self.config = config or WebSocketProxyConfig()
        
        # 初始化组件
        recorder_config = self.config.recorder_config or RecorderConfig()
        self._recorder = MessageRecorder(recorder_config)
        
        replayer_config = self.config.replayer_config or ReplayConfig()
        self._replayer = MessageReplayer(replayer_config)
        
        connection_config = self.config.connection_config or ConnectionManagerConfig()
        self._connection_manager = ConnectionManager(connection_config)
        
        # WebSocket 连接映射
        self._websockets: dict[str, InterceptedWebSocket] = {}
        self._ws_counter = 0
        
        # 状态
        self._is_running = False
    
    @property
    def is_running(self) -> bool:
        """代理是否运行中"""
        return self._is_running
    
    @property
    def connection_count(self) -> int:
        """当前连接数"""
        return self._connection_manager.connection_count
    
    @property
    def message_count(self) -> int:
        """记录的消息数"""
        return self._recorder.message_count
    
    @property
    def recorder(self) -> MessageRecorder:
        """获取消息记录器"""
        return self._recorder
    
    @property
    def replayer(self) -> MessageReplayer:
        """获取消息回放器"""
        return self._replayer
    
    @property
    def connection_manager(self) -> ConnectionManager:
        """获取连接管理器"""
        return self._connection_manager
    
    def setup_page_interception(self, page: Any) -> None:
        """
        设置页面 WebSocket 拦截
        
        Args:
            page: Playwright Page 对象
        """
        # 监听 WebSocket 创建事件
        page.on("websocket", lambda ws: self._on_websocket(ws, page.url))
        
        self._is_running = True
        console.print("[green]✓ WebSocket 拦截已启用[/]")
    
    def setup_context_interception(self, context: Any) -> None:
        """
        设置上下文 WebSocket 拦截
        
        Args:
            context: Playwright BrowserContext 对象
        """
        # 监听 WebSocket 创建事件
        context.on("websocket", lambda ws: self._on_websocket(ws, ""))
        
        self._is_running = True
        console.print("[green]✓ WebSocket 上下文拦截已启用[/]")
    
    async def _on_websocket(self, ws: Any, page_url: str) -> None:
        """
        处理 WebSocket 创建事件
        
        Args:
            ws: Playwright WebSocket 对象
            page_url: 页面 URL
        """
        url = ws.url
        
        # 应用连接过滤器
        if self.config.connection_filter:
            if not self.config.connection_filter(url, page_url):
                console.print(f"[dim]⊘ 连接被过滤: {url}[/]")
                return
        
        # 检查代理模式
        if self.config.mode == ProxyMode.BLOCK:
            console.print(f"[red]✗ 连接被阻止: {url}[/]")
            # 关闭连接
            try:
                await ws.close()
            except Exception:
                pass
            return
        
        # 注册连接
        self._ws_counter += 1
        connection_id = f"ws_{self._ws_counter:06d}"
        
        connection_info = await self._connection_manager.register_connection(
            url=url,
            origin=page_url,
            metadata={"created_by": "playwright"}
        )
        
        # 创建拦截对象
        intercepted = InterceptedWebSocket(
            connection_id=connection_id,
            url=url,
            page_url=page_url,
            ws=ws,
            connection_info=connection_info,
        )
        
        self._websockets[connection_id] = intercepted
        
        # 调用创建回调
        if self.config.on_websocket_created:
            try:
                result = self.config.on_websocket_created(connection_id, url)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                console.print(f"[red]✗ 创建回调错误: {e}[/]")
        
        # 设置消息监听
        ws.on("framereceived", lambda frame: self._on_frame_received(connection_id, frame))
        ws.on("framesent", lambda frame: self._on_frame_sent(connection_id, frame))
        ws.on("close", lambda: self._on_websocket_close(connection_id))
        
        # 更新状态
        self._connection_manager.update_state(connection_id, ConnectionState.CONNECTED)
        
        console.print(f"[cyan]🔌 WebSocket 连接: {connection_id}[/]")
        console.print(f"   [dim]URL: {url}[/]")
    
    def _on_frame_received(self, connection_id: str, frame: Any) -> None:
        """
        处理接收到的帧
        
        Args:
            connection_id: 连接 ID
            frame: WebSocket 帧
        """
        try:
            payload = frame.text if hasattr(frame, 'text') else frame.data
            
            # 应用消息过滤器
            if self.config.message_filter:
                if not self.config.message_filter(connection_id, payload):
                    return
            
            # 应用消息转换器
            if self.config.message_transformer and self.config.mode == ProxyMode.ACTIVE:
                payload = self.config.message_transformer(connection_id, payload)
            
            # 记录消息
            if self.config.enable_recording:
                asyncio.create_task(
                    self._recorder.record_server_message(connection_id, payload)
                )
            
            # 更新连接统计
            self._connection_manager.record_message(connection_id, payload, "received")
            
            # 调用回调
            if self.config.on_message_received:
                try:
                    self.config.on_message_received(connection_id, payload)
                except Exception as e:
                    console.print(f"[red]✗ 消息接收回调错误: {e}[/]")
        
        except Exception as e:
            console.print(f"[red]✗ 帧处理错误: {e}[/]")
    
    def _on_frame_sent(self, connection_id: str, frame: Any) -> None:
        """
        处理发送的帧
        
        Args:
            connection_id: 连接 ID
            frame: WebSocket 帧
        """
        try:
            payload = frame.text if hasattr(frame, 'text') else frame.data
            
            # 应用消息过滤器
            if self.config.message_filter:
                if not self.config.message_filter(connection_id, payload):
                    return
            
            # 应用消息转换器
            if self.config.message_transformer and self.config.mode == ProxyMode.ACTIVE:
                payload = self.config.message_transformer(connection_id, payload)
            
            # 记录消息
            if self.config.enable_recording:
                asyncio.create_task(
                    self._recorder.record_client_message(connection_id, payload)
                )
            
            # 更新连接统计
            self._connection_manager.record_message(connection_id, payload, "sent")
            
            # 调用回调
            if self.config.on_message_sent:
                try:
                    self.config.on_message_sent(connection_id, payload)
                except Exception as e:
                    console.print(f"[red]✗ 消息发送回调错误: {e}[/]")
        
        except Exception as e:
            console.print(f"[red]✗ 帧处理错误: {e}[/]")
    
    def _on_websocket_close(self, connection_id: str) -> None:
        """
        处理 WebSocket 关闭事件
        
        Args:
            connection_id: 连接 ID
        """
        intercepted = self._websockets.get(connection_id)
        if intercepted:
            intercepted.is_connected = False
        
        # 更新连接状态
        self._connection_manager.update_state(connection_id, ConnectionState.DISCONNECTED)
        
        # 注销连接
        asyncio.create_task(self._connection_manager.unregister_connection(connection_id))
        
        # 调用关闭回调
        if self.config.on_websocket_closed:
            try:
                self.config.on_websocket_closed(connection_id)
            except Exception as e:
                console.print(f"[red]✗ 关闭回调错误: {e}[/]")
        
        # 清理
        if connection_id in self._websockets:
            del self._websockets[connection_id]
        
        console.print(f"[dim]🔌 WebSocket 关闭: {connection_id}[/]")
    
    async def send_message(self, connection_id: str, message: str | bytes) -> bool:
        """
        发送消息到指定连接
        
        Args:
            connection_id: 连接 ID
            message: 消息内容
            
        Returns:
            是否发送成功
        """
        intercepted = self._websockets.get(connection_id)
        if not intercepted or not intercepted.is_connected:
            console.print(f"[red]✗ 连接不存在或已关闭: {connection_id}[/]")
            return False
        
        try:
            ws = intercepted.ws
            if isinstance(message, bytes):
                await ws.send_bytes(message)
            else:
                await ws.send_text(message)
            
            # 记录消息
            if self.config.enable_recording:
                await self._recorder.record_client_message(connection_id, message)
            
            # 更新统计
            self._connection_manager.record_message(connection_id, message, "sent")
            
            return True
        
        except Exception as e:
            console.print(f"[red]✗ 发送消息失败: {e}[/]")
            return False
    
    async def broadcast_message(self, message: str | bytes, url_pattern: str | None = None) -> int:
        """
        广播消息到所有或匹配的连接
        
        Args:
            message: 消息内容
            url_pattern: URL 匹配模式（可选）
            
        Returns:
            成功发送的连接数
        """
        count = 0
        
        for connection_id, intercepted in self._websockets.items():
            if not intercepted.is_connected:
                continue
            
            if url_pattern and url_pattern not in intercepted.url:
                continue
            
            if await self.send_message(connection_id, message):
                count += 1
        
        return count
    
    async def close_connection(self, connection_id: str, reason: str = "") -> bool:
        """
        关闭指定连接
        
        Args:
            connection_id: 连接 ID
            reason: 关闭原因
            
        Returns:
            是否关闭成功
        """
        intercepted = self._websockets.get(connection_id)
        if not intercepted:
            return False
        
        try:
            await intercepted.ws.close(code=1000, reason=reason)
            return True
        except Exception as e:
            console.print(f"[red]✗ 关闭连接失败: {e}[/]")
            return False
    
    async def close_all_connections(self, reason: str = "") -> int:
        """
        关闭所有连接
        
        Args:
            reason: 关闭原因
            
        Returns:
            关闭的连接数
        """
        count = 0
        for connection_id in list(self._websockets.keys()):
            if await self.close_connection(connection_id, reason):
                count += 1
        return count
    
    async def save_recording(self, filename: str | None = None) -> str:
        """
        保存消息录制
        
        Args:
            filename: 文件名（可选）
            
        Returns:
            保存的文件路径
        """
        return await self._recorder.save_to_file(filename)
    
    async def load_recording(self, file_path: str) -> int:
        """
        加载消息录制
        
        Args:
            file_path: 文件路径
            
        Returns:
            加载的消息数
        """
        return await self._recorder.load_from_file(file_path)
    
    async def start_replay(self, connection_id: str | None = None) -> None:
        """
        开始消息回放
        
        Args:
            connection_id: 目标连接 ID（可选，不指定则使用第一个可用连接）
        """
        if not connection_id:
            for cid, intercepted in self._websockets.items():
                if intercepted.is_connected:
                    connection_id = cid
                    break
        
        if not connection_id:
            console.print("[yellow]⚠ 没有可用的连接进行回放[/]")
            return
        
        # 设置回放发送回调
        self._replayer.set_send_callback(
            lambda msg: self.send_message(connection_id, msg)
        )
        
        # 开始回放
        result = await self._replayer.start()
        self._replayer.print_result()
    
    def get_connection_info(self, connection_id: str) -> ConnectionInfo | None:
        """
        获取连接信息
        
        Args:
            connection_id: 连接 ID
            
        Returns:
            连接信息，不存在则返回 None
        """
        return self._connection_manager.get_connection(connection_id)
    
    def get_all_connections(self) -> list[ConnectionInfo]:
        """
        获取所有连接
        
        Returns:
            连接信息列表
        """
        return self._connection_manager.get_all_connections()
    
    def get_messages_by_connection(self, connection_id: str) -> list[Any]:
        """
        获取指定连接的消息
        
        Args:
            connection_id: 连接 ID
            
        Returns:
            消息列表
        """
        return self._recorder.get_messages_by_connection(connection_id)
    
    def search_messages(self, keyword: str) -> list[Any]:
        """
        搜索消息
        
        Args:
            keyword: 搜索关键字
            
        Returns:
            匹配的消息列表
        """
        return self._recorder.search_messages(keyword)
    
    def get_statistics(self) -> dict[str, Any]:
        """
        获取代理统计信息
        
        Returns:
            统计信息字典
        """
        connection_stats = self._connection_manager.get_statistics()
        message_stats = self._recorder.get_statistics()
        
        return {
            "is_running": self._is_running,
            "proxy_mode": self.config.mode.value,
            "connections": connection_stats,
            "messages": message_stats,
        }
    
    def print_statistics(self) -> None:
        """打印代理统计信息"""
        stats = self.get_statistics()
        
        info = Text()
        info.append("WebSocket 代理统计\n\n", style="bold green")
        info.append(f"  代理模式: ", style="white")
        info.append(f"{stats['proxy_mode']}\n", style="cyan")
        info.append(f"  运行状态: ", style="white")
        info.append(f"{'运行中' if stats['is_running'] else '已停止'}\n", style="cyan")
        info.append(f"\n", style="white")
        info.append(f"  连接统计:\n", style="white")
        info.append(f"    总连接数: ", style="dim")
        info.append(f"{stats['connections']['total_connections']}\n", style="green")
        info.append(f"    活跃连接: ", style="dim")
        info.append(f"{stats['connections']['active_connections']}\n", style="green")
        info.append(f"    总消息数: ", style="dim")
        info.append(f"{stats['connections']['total_messages']}\n", style="green")
        info.append(f"\n", style="white")
        info.append(f"  消息统计:\n", style="white")
        info.append(f"    总消息数: ", style="dim")
        info.append(f"{stats['messages']['total_messages']}\n", style="green")
        info.append(f"    客户端→服务器: ", style="dim")
        info.append(f"{stats['messages']['client_to_server']}\n", style="green")
        info.append(f"    服务器→客户端: ", style="dim")
        info.append(f"{stats['messages']['server_to_client']}\n", style="green")
        
        panel = Panel(
            info,
            title="[bold green]WebSocket 代理[/]",
            border_style="green",
            padding=(0, 2)
        )
        console.print(panel)
    
    def print_connections(self) -> None:
        """打印连接列表"""
        self._connection_manager.print_connections()
    
    def print_messages(self, connection_id: str | None = None, limit: int = 50) -> None:
        """
        打印消息列表
        
        Args:
            connection_id: 连接 ID（可选）
            limit: 最大显示数量
        """
        if connection_id:
            messages = self._recorder.get_messages_by_connection(connection_id)
        else:
            messages = self._recorder.messages
        
        if not messages:
            console.print("[yellow]没有消息记录[/]")
            return
        
        console.print(f"\n[cyan]消息记录 ({len(messages)} 条)[/]")
        console.print("=" * 60)
        
        for msg in messages[:limit]:
            direction_icon = "→" if msg.direction == MessageDirection.CLIENT_TO_SERVER else "←"
            direction_color = "cyan" if msg.direction == MessageDirection.CLIENT_TO_SERVER else "green"
            
            timestamp = time.strftime("%H:%M:%S", time.localtime(msg.timestamp))
            
            payload_preview: str
            if isinstance(msg.payload, bytes):
                payload_preview = f"<binary: {len(msg.payload)} bytes>"
            else:
                payload_preview = msg.payload[:80]
                if len(msg.payload) > 80:
                    payload_preview += "..."
            
            console.print(
                f"[dim]{timestamp}[/] "
                f"[{direction_color}]{direction_icon}[/] "
                f"{payload_preview}"
            )
        
        if len(messages) > limit:
            console.print(f"[dim]... 还有 {len(messages) - limit} 条消息[/]")
    
    def stop(self) -> None:
        """停止代理"""
        self._is_running = False
        console.print("[yellow]WebSocket 代理已停止[/]")
    
    async def cleanup(self) -> None:
        """清理资源"""
        await self.close_all_connections()
        await self._connection_manager.stop_cleanup_task()
        await self._recorder.stop_auto_save()
        self.stop()


def create_simple_proxy(
    enable_recording: bool = True,
    storage_path: str = "./websocket_messages"
) -> WebSocketProxy:
    """
    快速创建简单 WebSocket 代理的便捷函数
    
    Args:
        enable_recording: 是否启用记录
        storage_path: 存储路径
        
    Returns:
        配置好的 WebSocketProxy 实例
    """
    config = WebSocketProxyConfig(
        mode=ProxyMode.PASSIVE,
        enable_recording=enable_recording,
        recorder_config=RecorderConfig(storage_path=storage_path)
    )
    return WebSocketProxy(config)


async def intercept_websockets_demo(url: str) -> None:
    """
    WebSocket 拦截演示函数
    
    Args:
        url: 目标页面 URL
    """
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        console.print("[red]✗ 请先安装 playwright: pip install playwright[/]")
        return
    
    # 创建代理
    proxy = create_simple_proxy(enable_recording=True)
    
    console.print(f"[cyan]正在访问: {url}[/]")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        # 设置拦截
        proxy.setup_page_interception(page)
        
        # 访问页面
        await page.goto(url)
        
        # 等待一段时间收集 WebSocket 消息
        console.print("[cyan]等待 WebSocket 消息... (按 Ctrl+C 停止)[/]")
        try:
            await asyncio.sleep(30)
        except KeyboardInterrupt:
            pass
        
        # 打印统计
        proxy.print_statistics()
        proxy.print_connections()
        
        # 保存录制
        await proxy.save_recording()
        
        await browser.close()
    
    await proxy.cleanup()
