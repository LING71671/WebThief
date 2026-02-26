"""
解析器核心模块

包含解析结果容器和基础工具类。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..browser_api import BrowserAPISimulator


class ParseResult:
    """解析结果容器"""

    __slots__ = ("html", "resource_map", "css_sub_resources", "page_links")

    def __init__(self) -> None:
        self.html: str = ""
        # 原始 URL → 本地路径 的映射表
        self.resource_map: dict[str, str] = {}
        # CSS 中发现的子资源（嵌套 CSS 内的 url()）
        self.css_sub_resources: dict[str, str] = {}
        # 页面内部链接（用于站点递归）
        self.page_links: set[str] = set()


class ParserConfig:
    """解析器配置类"""

    # HTML 中需要检查的资源属性
    RESOURCE_ATTRS = [
        ("img", "src"),
        ("img", "data-src"),
        ("img", "data-original"),
        ("script", "src"),
        ("link", "href"),
        ("source", "src"),
        ("source", "srcset"),
        ("video", "src"),
        ("video", "poster"),
        ("audio", "src"),
        ("embed", "src"),
        ("object", "data"),
        ("input", "src"),  # input type=image
        ("iframe", "src"),
        ("use", "href"),  # SVG <use>
        ("use", "xlink:href"),
        ("image", "href"),  # SVG <image>
        ("image", "xlink:href"),
    ]

    def __init__(
        self,
        base_url: str,
        intercepted_urls: set[str] | None = None,
        page_link_mode: str = "local",
        browser_api_simulator: BrowserAPISimulator | None = None,
        inject_browser_api_shim: bool = False,
    ) -> None:
        self.base_url = base_url
        self.intercepted_urls = intercepted_urls or set()
        self.page_link_mode = page_link_mode if page_link_mode in {"local", "absolute"} else "local"
        self.browser_api_simulator = browser_api_simulator
        self.inject_browser_api_shim = inject_browser_api_shim
