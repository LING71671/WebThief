"""
HTML 解析模块

负责解析 HTML DOM，提取资源 URL 并重写为本地路径。
本模块作为入口，实际功能已拆分到以下子模块：
- html_extractor.py: HTML 资源提取
- html_rewriter.py: HTML 重写
- html_injector.py: 浏览器 API 垫片注入
"""

from __future__ import annotations

from urllib.parse import urlparse

from bs4 import BeautifulSoup
from rich.console import Console

from .core import ParseResult, ParserConfig
from .extractor import HTMLResourceExtractor
from .rewriter import HTMLRewriter
from .injector import BrowserAPIShimInjector
from ..utils import url_to_local_path, should_skip_url

console = Console()


def parse_html(
    html: str,
    config: ParserConfig,
    current_page_local_path: str = "index.html",
) -> ParseResult:
    """
    解析 HTML，提取所有资源 URL 并重写路径

    Args:
        html: HTML 内容
        config: 解析器配置
        current_page_local_path: 当前页面的本地路径

    Returns:
        ParseResult: 包含重写后的 HTML 和资源映射表
    """
    result = ParseResult()
    soup = BeautifulSoup(html, "lxml")

    console.print("[bold magenta]🔍 AST 解析 HTML 资源引用...[/]")

    resource_map: dict[str, str] = {}

    # 提取资源 URL
    extractor = HTMLResourceExtractor(config, resource_map)
    extractor.extract_all(soup)

    # 提取页面链接
    extractor.extract_page_links(soup)

    # 合并拦截层嗅探到的 URL
    for url in config.intercepted_urls:
        if url not in resource_map and not should_skip_url(url):
            extractor._register_url(url)

    # 应用路径重写到 DOM
    rewriter = HTMLRewriter(config, resource_map)
    rewriter.rewrite_all(soup, current_page_local_path)

    # 注入浏览器 API 垫片
    if config.inject_browser_api_shim:
        injector = BrowserAPIShimInjector(config)
        injector.inject(soup)

    console.print(f"[bold green]  ✓ 发现 {len(resource_map)} 个资源引用[/]")

    result.html = str(soup)
    result.resource_map = dict(resource_map)
    result.css_sub_resources = {
        url: url_to_local_path(url, urlparse(config.base_url).netloc)
        for url in extractor.discovered_css_urls
    }
    result.page_links = extractor.page_links

    return result


# 向后兼容导出
__all__ = [
    "parse_html",
    "HTMLResourceExtractor",
    "HTMLRewriter",
    "BrowserAPIShimInjector",
]
