"""
WebThief Core 模块

包含核心功能模块：
- downloader: 高并发下载引擎
- storage: 镜像存储管理
- orchestrator: 流水线编排器
- renderer: 浏览器渲染引擎
- site_crawler: 站点递归抓取器
- spa_prerender: SPA 预渲染
- sanitizer: HTML 清理器
"""

from .downloader import Downloader, DownloadResult
from .storage import Storage
from .orchestrator import Orchestrator
from .renderer import Renderer, RenderResult
from .site_crawler import SiteCrawler
from .spa_prerender import SPAPrerender
from .sanitizer import sanitize, inject_runtime_resource_map

__all__ = [
    "Downloader",
    "DownloadResult",
    "Storage",
    "Orchestrator",
    "Renderer",
    "RenderResult",
    "SiteCrawler",
    "SPAPrerender",
    "sanitize",
    "inject_runtime_resource_map",
]
