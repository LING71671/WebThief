"""
HTML 资源提取模块

负责从 HTML DOM 中提取资源 URL。
"""

from __future__ import annotations

from urllib.parse import urlparse, urljoin

from bs4 import BeautifulSoup
from rich.console import Console

from .core import ParserConfig
from .css import CSSUrlParser
from ..utils import (
    normalize_url,
    normalize_crawl_url,
    url_to_local_path,
    should_skip_url,
    parse_srcset,
    is_same_host,
)

console = Console()


class HTMLResourceExtractor:
    """HTML 资源提取器"""

    def __init__(self, config: ParserConfig, resource_map: dict[str, str]) -> None:
        self.config = config
        self.base_url = config.base_url
        self.base_domain = urlparse(config.base_url).netloc
        self.resource_map = resource_map
        self.discovered_css_urls: set[str] = set()
        self.page_links: set[str] = set()

    def extract_all(self, soup: BeautifulSoup) -> None:
        """提取所有资源 URL"""
        self._process_base_tag(soup)
        self._process_resource_attrs(soup)
        self._process_srcset(soup)
        self._process_inline_styles(soup)
        self._process_style_tags(soup)
        self._mark_css_links(soup)
        self._process_meta_images(soup)

    def _process_base_tag(self, soup: BeautifulSoup) -> None:
        """处理 <base> 标签"""
        base_tag = soup.find("base", href=True)
        if base_tag:
            self.base_url = urljoin(self.base_url, base_tag["href"])
            self.config.base_url = self.base_url
            base_tag.decompose()

    def _register_url(self, url: str) -> str | None:
        """
        注册一个资源 URL，返回对应的本地路径。
        如果 URL 应跳过则返回 None。
        """
        if should_skip_url(url):
            return None

        absolute = normalize_url(url, self.base_url)
        if not absolute or should_skip_url(absolute):
            return None

        if absolute not in self.resource_map:
            local_path = url_to_local_path(absolute, self.base_domain)
            self.resource_map[absolute] = local_path

        return self.resource_map[absolute]

    def _process_resource_attrs(self, soup: BeautifulSoup) -> None:
        """遍历标准的 HTML 资源引用属性"""
        for tag_name, attr_name in self.config.RESOURCE_ATTRS:
            for tag in soup.find_all(tag_name):
                val = tag.get(attr_name)
                if val and isinstance(val, str):
                    val = val.strip()
                    if val:
                        self._register_url(val)

        # 处理通配符 —— 所有带 src 的元素
        for tag in soup.find_all(True, src=True):
            src = tag.get("src", "").strip()
            if src:
                self._register_url(src)

        # 其他 data- 属性
        self._process_data_attrs(soup)

    def _process_data_attrs(self, soup: BeautifulSoup) -> None:
        """处理 data-* 资源属性"""
        for tag in soup.find_all(True):
            for attr in list(tag.attrs.keys()):
                if attr.startswith("data-") and (
                    "src" in attr.lower()
                    or "background" in attr.lower()
                    or attr.lower() in {"data-bg", "data-bg-src", "data-original"}
                ):
                    val = tag.get(attr, "")
                    if isinstance(val, str) and val.strip():
                        self._register_url(val.strip())

    def _process_srcset(self, soup: BeautifulSoup) -> None:
        """解析 srcset 属性中的多个 URL"""
        for attr_name in ("srcset", "data-srcset"):
            for tag in soup.find_all(True, attrs={attr_name: True}):
                srcset = tag.get(attr_name, "")
                if isinstance(srcset, str):
                    urls = parse_srcset(srcset)
                    for url in urls:
                        self._register_url(url)

    def _process_inline_styles(self, soup: BeautifulSoup) -> None:
        """处理 style="" 属性中的 url() 引用"""
        for tag in soup.find_all(True, style=True):
            style_val = tag.get("style", "")
            if isinstance(style_val, str) and "url(" in style_val:
                urls = self._extract_css_urls(style_val)
                for url in urls:
                    self._register_url(url)

    def _process_style_tags(self, soup: BeautifulSoup) -> None:
        """使用 tinycss2 AST 解析 <style> 标签中的 CSS"""
        import tinycss2

        for style_tag in soup.find_all("style"):
            css_text = style_tag.string
            if css_text:
                urls = self._parse_css_ast(css_text)
                for url in urls:
                    self._register_url(url)

    def _mark_css_links(self, soup: BeautifulSoup) -> None:
        """标记外部 CSS 文件链接，以便后续深度解析"""
        # 处理 rel="stylesheet"
        for link in soup.find_all("link", rel="stylesheet"):
            self._register_and_mark_css(link)

        # 处理 rel=["stylesheet"]（BeautifulSoup 将 rel 解析为列表）
        for link in soup.find_all("link"):
            rel = link.get("rel", [])
            if isinstance(rel, list) and "stylesheet" in rel:
                self._register_and_mark_css(link)

    def _register_and_mark_css(self, link) -> None:
        """注册 CSS 链接并标记为需要深度解析"""
        href = link.get("href", "").strip()
        if href and not should_skip_url(href):
            self._register_url(href)
            absolute = normalize_url(href, self.base_url)
            self.discovered_css_urls.add(absolute)

    def _process_meta_images(self, soup: BeautifulSoup) -> None:
        """处理 meta 标签中的图片引用（og:image, twitter:image 等）"""
        for meta in soup.find_all("meta"):
            prop = meta.get("property", "") or meta.get("name", "")
            if any(kw in prop.lower() for kw in ("image", "icon", "logo")):
                content = meta.get("content", "").strip()
                if content and not should_skip_url(content):
                    self._register_url(content)

    def _parse_css_ast(self, css_text: str) -> list[str]:
        """
        使用 tinycss2 解析 CSS 文本，提取所有 url() 和 @import 引用
        返回发现的 URL 列表
        """
        import tinycss2

        urls = []
        try:
            tokens = tinycss2.parse_stylesheet(
                css_text, skip_comments=True, skip_whitespace=False
            )
            self._walk_css_tokens(tokens, urls)
        except Exception as e:
            console.print(f"[yellow]  ⚠ CSS AST 解析警告: {e}[/]")
            urls.extend(self._extract_css_urls(css_text))
        return urls

    def _walk_css_tokens(self, nodes, urls: list[str]) -> None:
        """递归遍历 CSS AST 节点，收集 url()"""
        for node in nodes:
            # @import 规则
            if node.type == "at-rule" and node.lower_at_keyword == "import":
                self._extract_import_url(node, urls)
                continue

            # 有 content (如 qualified-rule, at-rule body)
            if hasattr(node, "content") and node.content:
                CSSUrlParser.scan_values_for_urls(
                    node.content, urls, skip_check=should_skip_url
                )

            # prelude (如 at-rule 的 prelude)
            if hasattr(node, "prelude") and node.prelude:
                CSSUrlParser.scan_values_for_urls(
                    node.prelude, urls, skip_check=should_skip_url
                )

    def _extract_import_url(self, node, urls: list[str]) -> None:
        """从 @import 规则中提取 URL"""
        for val in node.prelude:
            extracted = CSSUrlParser.extract_url_from_token(val, allow_string=True)
            if not extracted or should_skip_url(extracted):
                continue

            urls.append(extracted)
            normalized = normalize_url(extracted, self.base_url)
            if normalized:
                self.discovered_css_urls.add(normalized)

    def _extract_css_urls(self, css_text: str) -> list[str]:
        """
        从 CSS 文本中提取 url() 值（回退方法，仅在 AST 解析失败时使用）
        """
        import tinycss2

        urls = []
        try:
            tokens = tinycss2.parse_component_value_list(css_text)
            CSSUrlParser.scan_values_for_urls(tokens, urls, skip_check=should_skip_url)
        except Exception:
            pass
        return urls

    def extract_page_links(self, soup: BeautifulSoup) -> None:
        """提取同 host 页面链接"""
        for tag in soup.find_all("a", href=True):
            href = (tag.get("href") or "").strip()
            if not href or should_skip_url(href):
                continue
            absolute = normalize_crawl_url(href, self.base_url)
            if absolute and is_same_host(absolute, self.base_domain):
                self.page_links.add(absolute)
