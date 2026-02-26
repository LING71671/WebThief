"""
简化的 API 响应缓存模块

提供基本的 API 响应缓存功能：
- URL -> 响应映射
- JSON 文件存储
- 缓存过期管理
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from rich.console import Console
from rich.table import Table

from .api_cache import APICache, CachedResponse

console = Console()


class APISimulator:
    """
    简化的 API 响应缓存器

    提供基本的 URL -> 响应映射和 JSON 文件存储功能
    """

    def __init__(self, cache_dir: str | Path = "./api_cache"):
        """
        初始化 API 缓存器

        Args:
            cache_dir: 缓存目录
        """
        self.cache = APICache(cache_dir)

    def cache_response(
        self,
        url: str,
        response: Any,
        method: str = "GET",
        status_code: int = 200,
        headers: Optional[dict[str, str]] = None,
        content_type: str = "application/json",
        ttl: Optional[int] = None,
    ) -> CachedResponse:
        """
        缓存 API 响应

        Args:
            url: 请求 URL
            response: 响应内容
            method: HTTP 方法
            status_code: 状态码
            headers: 响应头
            content_type: 内容类型
            ttl: 过期时间（秒）

        Returns:
            缓存的响应对象
        """
        return self.cache.set(
            url=url,
            response=response,
            method=method,
            status_code=status_code,
            headers=headers,
            content_type=content_type,
            ttl=ttl,
        )

    def get_response(
        self,
        url: str,
        method: str = "GET",
        body: Any = None,
    ) -> Optional[CachedResponse]:
        """
        获取缓存的响应

        Args:
            url: 请求 URL
            method: HTTP 方法
            body: 请求体（用于 POST/PUT/PATCH）

        Returns:
            缓存的响应，如果不存在或已过期则返回 None
        """
        return self.cache.get(url, method, body)

    def load_cache(self) -> None:
        """加载缓存"""
        self.cache.load()

    def save_cache(self) -> None:
        """保存缓存"""
        self.cache.save()

    def import_from_renderer(
        self,
        response_cache: dict[str, bytes],
        response_content_types: dict[str, str],
    ) -> int:
        """
        从 Renderer 导入响应缓存

        Args:
            response_cache: Renderer 捕获的响应
            response_content_types: 内容类型映射

        Returns:
            导入的数量
        """
        return self.cache.import_from_renderer_cache(response_cache, response_content_types)

    def export_runtime_map(self) -> dict[str, dict[str, str]]:
        """导出运行时响应映射"""
        return self.cache.export_to_runtime_map()

    def get_stats(self) -> dict[str, Any]:
        """获取统计信息"""
        return self.cache.get_stats()

    def print_stats(self) -> None:
        """打印统计信息表格"""
        stats = self.get_stats()

        table = Table(title="API Cache 统计")
        table.add_column("指标", style="cyan")
        table.add_column("值", style="green")

        table.add_row("缓存总数", str(stats["total"]))
        table.add_row("活跃缓存", str(stats["active"]))
        table.add_row("过期缓存", str(stats["expired"]))

        console.print(table)

    def list_cached_urls(self) -> list[str]:
        """列出所有缓存的 URL"""
        return self.cache.get_all_urls()

    def print_cached_urls(self) -> None:
        """打印缓存的 URL 列表"""
        urls = self.list_cached_urls()

        table = Table(title=f"缓存 URL 列表 ({len(urls)} 个)")
        table.add_column("#", style="dim")
        table.add_column("URL", style="cyan")

        for index, url in enumerate(urls, 1):
            display_url = url if len(url) <= 80 else url[:77] + "..."
            table.add_row(str(index), display_url)

        console.print(table)

    def clear_cache(self) -> None:
        """清空缓存"""
        self.cache.clear()

    def clear_expired(self) -> int:
        """清理过期缓存"""
        return self.cache.clear_expired()


def create_simulator(cache_dir: str | Path = "./api_cache") -> APISimulator:
    """
    创建 API 缓存器实例

    Args:
        cache_dir: 缓存目录

    Returns:
        APISimulator 实例
    """
    return APISimulator(cache_dir=cache_dir)
