"""
WebSocket 代理模块

提供 WebSocket 连接拦截、消息记录、回放和连接管理功能。
与 Playwright 集成，支持双向消息代理。
"""

from webthief.plugins.websocket.websocket_proxy import (
    WebSocketProxy,
    WebSocketProxyConfig,
    ProxyMode,
)
from webthief.plugins.websocket.message_recorder import (
    MessageRecorder,
    RecorderConfig,
    MessageType,
    MessageDirection,
    WebSocketMessage,
)
from webthief.plugins.websocket.message_replayer import (
    MessageReplayer,
    ReplayConfig,
    ReplayMode,
    ReplayState,
    ReplayResult,
)
from webthief.plugins.websocket.connection_manager import (
    ConnectionManager,
    ConnectionManagerConfig,
    ConnectionInfo,
    ConnectionState,
)

__all__ = [
    # WebSocket Proxy
    "WebSocketProxy",
    "WebSocketProxyConfig",
    "ProxyMode",
    # Message Recorder
    "MessageRecorder",
    "RecorderConfig",
    "MessageType",
    "MessageDirection",
    "WebSocketMessage",
    # Message Replayer
    "MessageReplayer",
    "ReplayConfig",
    "ReplayMode",
    "ReplayState",
    "ReplayResult",
    # Connection Manager
    "ConnectionManager",
    "ConnectionManagerConfig",
    "ConnectionInfo",
    "ConnectionState",
]
