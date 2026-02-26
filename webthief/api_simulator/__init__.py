"""
WebThief API Simulator - API 响应缓存模块

提供基本的 API 响应缓存功能：
- URL -> 响应映射
- JSON 文件存储
- 缓存过期管理
"""

from .api_cache import APICache, CachedResponse
from .api_simulator import APISimulator, create_simulator

__all__ = [
    "APISimulator",
    "APICache",
    "CachedResponse",
    "create_simulator",
]
