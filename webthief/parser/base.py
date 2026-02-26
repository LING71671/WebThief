"""
AST 级解析与路径重写层（核心模块）：
- HTML DOM 解析：BeautifulSoup 遍历所有资源引用属性
- CSS AST 解析：tinycss2 精准提取 url() 和 @import
- 路径重写：将所有外部 URL 映射为本地相对路径
- 浏览器 API 垫片注入：Service Worker、IndexedDB 等模拟

!! 严格禁止正则匹配链接 !!

本模块作为入口点，实际功能已拆分到以下子模块：
- parser/core.py: 核心类和配置
- parser/html.py: HTML 解析入口
- parser/extractor.py: HTML 资源提取
- parser/rewriter.py: HTML 重写
- parser/injector.py: 浏览器 API 垫片注入
- parser/css.py: CSS 解析
- parser/js.py: JS 解析
"""

from __future__ import annotations

from typing import TYPE_CHECKING

# 从子模块导入核心类
from .core import ParseResult, ParserConfig
from .html import parse_html
from .extractor import HTMLResourceExtractor
from .rewriter import HTMLRewriter
from .injector import BrowserAPIShimInjector
from .css import (
    parse_external_css,
    CSSUrlParser,
    CSSResourceCollector,
    CSSRewriter,
)
from .js import parse_external_js_assets

if TYPE_CHECKING:
    from ..plugins.browser_api import BrowserAPISimulator


class Parser:
    """
    AST 级解析器
    负责：解析 HTML/CSS → 提取资源 URL → 重写为本地路径

    本类作为对外接口，内部实现已拆分到各个子模块。
    """

    def __init__(
        self,
        base_url: str,
        intercepted_urls: set[str] | None = None,
        page_link_mode: str = "local",
        browser_api_simulator: BrowserAPISimulator | None = None,
        inject_browser_api_shim: bool = False,
    ):
        """
        Args:
            base_url: 页面原始 URL（用于解析相对路径）
            intercepted_urls: 渲染层嗅探到的 URL 集合
            browser_api_simulator: 浏览器 API 模拟器实例
            inject_browser_api_shim: 是否注入浏览器 API 垫片
        """
        self.config = ParserConfig(
            base_url=base_url,
            intercepted_urls=intercepted_urls,
            page_link_mode=page_link_mode,
            browser_api_simulator=browser_api_simulator,
            inject_browser_api_shim=inject_browser_api_shim,
        )
        self.resource_map: dict[str, str] = {}
        self.discovered_css_urls: set[str] = set()
        self.page_links: set[str] = set()

    def parse(self, html: str, current_page_local_path: str = "index.html") -> ParseResult:
        """
        解析 HTML，提取所有资源 URL 并重写路径

        Returns:
            ParseResult: 包含重写后的 HTML 和资源映射表
        """
        result = parse_html(html, self.config, current_page_local_path)

        # 同步状态到 Parser 实例
        self.resource_map = result.resource_map
        self.discovered_css_urls = set(result.css_sub_resources.keys())
        self.page_links = result.page_links

        return result


# 向后兼容的导出
__all__ = [
    # 主类
    "Parser",
    "ParseResult",
    # HTML 解析
    "parse_html",
    "HTMLResourceExtractor",
    "HTMLRewriter",
    "BrowserAPIShimInjector",
    # CSS 解析
    "CSSUrlParser",
    "CSSResourceCollector",
    "CSSRewriter",
    "parse_external_css",
    # JS 解析
    "parse_external_js_assets",
]
