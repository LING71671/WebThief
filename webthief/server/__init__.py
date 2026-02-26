"""
WebThief 本地服务器管理器模块

提供本地 HTTP/WebSocket 服务器管理功能，支持：
- 静态文件服务
- 端口自动检测与冲突处理
- 浏览器自动打开
- HTTPS 模拟（可选）
- WebSocket 连接支持
"""

from .server_manager import ServerManager, ServerConfig, ServerStatus

__all__ = [
    "ServerManager",
    "ServerConfig",
    "ServerStatus",
]
