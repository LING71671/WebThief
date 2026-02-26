"""
WebThief 插件模块

包含扩展功能模块，这些模块提供了高级特性：

插件列表:
---------
websocket : WebSocket 代理模块
    - WebSocket 连接拦截和代理
    - 消息记录和回放
    - 连接管理

browser_api : 浏览器 API 模拟模块
    - Service Worker 模拟
    - IndexedDB 文件存储模拟
    - Web Crypto API 模拟

frontend : 前端架构适配模块
    - 微前端架构检测
    - React Server Components 处理
    - JavaScript 模块依赖解析

使用示例:
---------
```python
# 导入 WebSocket 代理
from webthief.plugins.websocket import WebSocketProxy, ProxyMode

# 导入浏览器 API 模拟器
from webthief.plugins.browser_api import BrowserAPISimulator

# 导入前端适配器
from webthief.plugins.frontend import FrontendAdapter
```
"""

from webthief.plugins import websocket
from webthief.plugins import browser_api
from webthief.plugins import frontend

__all__ = [
    "websocket",
    "browser_api",
    "frontend",
]
