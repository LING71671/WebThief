"""
WebThief Browser API Simulator - 浏览器 API 模拟模块

提供浏览器原生 API 的模拟和垫片功能，用于：
- Service Worker 注册拦截
- IndexedDB 文件存储模拟
- Web Crypto API 模拟
- Notification API 模拟
- Geolocation API 模拟
- API 调用记录和回放
"""

from .browser_api_simulator import BrowserAPISimulator
from .indexeddb_simulator import IndexedDBSimulator
from .service_worker_simulator import ServiceWorkerSimulator

__all__ = [
    "BrowserAPISimulator",
    "IndexedDBSimulator",
    "ServiceWorkerSimulator",
]
