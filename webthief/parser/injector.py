"""
HTML 注入模块

负责向 HTML 注入浏览器 API 垫片。
"""

from __future__ import annotations

from bs4 import BeautifulSoup
from rich.console import Console

from .core import ParserConfig

console = Console()


class BrowserAPIShimInjector:
    """浏览器 API 垫片注入器"""

    def __init__(self, config: ParserConfig) -> None:
        self.config = config

    def inject(self, soup: BeautifulSoup) -> None:
        """
        注入浏览器 API 垫片脚本到 HTML

        在 <head> 标签末尾注入 Service Worker、IndexedDB 等模拟脚本，
        确保离线环境下这些 API 能正常工作。
        """
        if not self.config.browser_api_simulator:
            return

        shim_script = self.config.browser_api_simulator.get_injection_script()
        script_tag = soup.new_tag("script")
        script_tag.string = shim_script
        script_tag["data-webthief-shim"] = "browser-api"

        head = soup.find("head")
        if head:
            head.append(script_tag)
            console.print("[cyan]  ✓ 浏览器 API 垫片已注入到 HTML[/]")
        else:
            html_tag = soup.find("html")
            if html_tag:
                html_tag.insert(0, script_tag)
                console.print("[cyan]  ✓ 浏览器 API 垫片已注入[/]")
