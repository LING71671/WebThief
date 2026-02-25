"""
AST 级解析与路径重写层（核心模块）：
- HTML DOM 解析：BeautifulSoup 遍历所有资源引用属性
- CSS AST 解析：tinycss2 精准提取 url() 和 @import
- 路径重写：将所有外部 URL 映射为本地相对路径

!! 严格禁止正则匹配链接 !!
"""

from __future__ import annotations

import re
from urllib.parse import urlparse, urljoin

from bs4 import BeautifulSoup
import tinycss2
from rich.console import Console

from .utils import (
    is_same_host,
    normalize_url,
    normalize_crawl_url,
    url_to_local_path,
    url_to_local_page_path,
    should_skip_url,
    parse_srcset,
    make_relative_path,
)

console = Console()


class ParseResult:
    """解析结果容器"""
    __slots__ = ("html", "resource_map", "css_sub_resources", "page_links")

    def __init__(self):
        self.html: str = ""
        # 原始 URL → 本地路径 的映射表
        self.resource_map: dict[str, str] = {}
        # CSS 中发现的子资源（嵌套 CSS 内的 url()）
        self.css_sub_resources: dict[str, str] = {}
        # 页面内部链接（用于站点递归）
        self.page_links: set[str] = set()


class Parser:
    """
    AST 级解析器
    负责：解析 HTML/CSS → 提取资源 URL → 重写为本地路径
    """

    # HTML 中需要检查的资源属性
    RESOURCE_ATTRS = [
        ("img",    "src"),
        ("img",    "data-src"),
        ("img",    "data-original"),
        ("script", "src"),
        ("link",   "href"),
        ("source", "src"),
        ("source", "srcset"),
        ("video",  "src"),
        ("video",  "poster"),
        ("audio",  "src"),
        ("embed",  "src"),
        ("object", "data"),
        ("input",  "src"),      # input type=image
        ("iframe", "src"),
        ("use",    "href"),     # SVG <use>
        ("use",    "xlink:href"),
        ("image",  "href"),     # SVG <image>
        ("image",  "xlink:href"),
    ]

    def __init__(
        self,
        base_url: str,
        intercepted_urls: set[str] | None = None,
        page_link_mode: str = "local",
    ):
        """
        Args:
            base_url: 页面原始 URL（用于解析相对路径）
            intercepted_urls: 渲染层嗅探到的 URL 集合（补充解析器可能遗漏的）
        """
        self.base_url = base_url
        self.base_domain = urlparse(base_url).netloc
        self.intercepted_urls = intercepted_urls or set()
        self.resource_map: dict[str, str] = {}  # 原始 URL → 本地路径
        self.discovered_css_urls: set[str] = set()  # 从 CSS 中发现的子资源
        self.page_links: set[str] = set()  # 同 host 页面链接
        self.page_link_mode = (
            page_link_mode if page_link_mode in {"local", "absolute"} else "local"
        )

    def parse(self, html: str, current_page_local_path: str = "index.html") -> ParseResult:
        """
        解析 HTML，提取所有资源 URL 并重写路径

        Returns:
            ParseResult: 包含重写后的 HTML 和资源映射表
        """
        result = ParseResult()
        soup = BeautifulSoup(html, "lxml")

        console.print("[bold magenta]🔍 AST 解析 HTML 资源引用...[/]")

        # 1. 处理 <base> 标签
        base_tag = soup.find("base", href=True)
        if base_tag:
            self.base_url = urljoin(self.base_url, base_tag["href"])
            # 移除 base 标签（本地不需要）
            base_tag.decompose()

        # 2. 遍历标准资源属性
        self._process_resource_attrs(soup)

        # 3. 处理 srcset 属性
        self._process_srcset(soup)

        # 4. 处理内联 style 属性中的 url()
        self._process_inline_styles(soup)

        # 5. 处理 <style> 标签中的 CSS
        self._process_style_tags(soup)

        # 6. 处理外部 CSS 文件的 <link>（标记需要 CSS 深度解析）
        self._mark_css_links(soup)

        # 7. 处理 meta 中的图片（og:image 等）
        self._process_meta_images(soup)

        # 8. 提取页面链接（用于站点递归）
        self._process_page_links(soup)

        # 9. 合并拦截层嗅探到的未被解析器发现的 URL
        self._merge_intercepted_urls()

        # 10. 应用路径重写到 DOM
        self._rewrite_dom(soup, current_page_local_path=current_page_local_path)

        console.print(
            f"[bold green]  ✓ 发现 {len(self.resource_map)} 个资源引用[/]"
        )

        result.html = str(soup)
        result.resource_map = dict(self.resource_map)
        result.css_sub_resources = {
            url: self._get_local_path(url) for url in self.discovered_css_urls
        }
        result.page_links = set(self.page_links)

        return result

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

    def _get_local_path(self, url: str) -> str:
        """获取 URL 对应的本地路径"""
        absolute = normalize_url(url, self.base_url)
        if absolute in self.resource_map:
            return self.resource_map[absolute]
        return url_to_local_path(absolute, self.base_domain)

    def _process_resource_attrs(self, soup: BeautifulSoup) -> None:
        """遍历标准的 HTML 资源引用属性"""
        for tag_name, attr_name in self.RESOURCE_ATTRS:
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
        for tag in soup.find_all(True, attrs={"srcset": True}):
            srcset = tag.get("srcset", "")
            if isinstance(srcset, str):
                urls = parse_srcset(srcset)
                for url in urls:
                    self._register_url(url)

        # data-srcset
        for tag in soup.find_all(True, attrs={"data-srcset": True}):
            srcset = tag.get("data-srcset", "")
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
        for style_tag in soup.find_all("style"):
            css_text = style_tag.string
            if css_text:
                urls = self._parse_css_ast(css_text)
                for url in urls:
                    self._register_url(url)

    def _mark_css_links(self, soup: BeautifulSoup) -> None:
        """标记外部 CSS 文件链接，以便后续深度解析"""
        for link in soup.find_all("link", rel="stylesheet"):
            href = link.get("href", "").strip()
            if href and not should_skip_url(href):
                self._register_url(href)
                # 标记为需要 CSS 深度解析
                absolute = normalize_url(href, self.base_url)
                self.discovered_css_urls.add(absolute)

        # 也处理 rel=["stylesheet"] 的情况（BeautifulSoup 将 rel 解析为列表）
        for link in soup.find_all("link"):
            rel = link.get("rel", [])
            if isinstance(rel, list) and "stylesheet" in rel:
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

    def _merge_intercepted_urls(self) -> None:
        """合并渲染层嗅探到的 URL"""
        for url in self.intercepted_urls:
            if url not in self.resource_map and not should_skip_url(url):
                self._register_url(url)

    def _process_page_links(self, soup: BeautifulSoup) -> None:
        """提取同 host 页面链接"""
        for tag in soup.find_all("a", href=True):
            href = (tag.get("href") or "").strip()
            if not href or should_skip_url(href):
                continue
            absolute = normalize_crawl_url(href, self.base_url)
            if absolute and is_same_host(absolute, self.base_domain):
                self.page_links.add(absolute)

    def _rewrite_dom(self, soup: BeautifulSoup, current_page_local_path: str) -> None:
        """将 DOM 中的所有外部 URL 重写为本地相对路径"""
        self._rewrite_tag_attrs(soup)
        self._rewrite_src_attrs(soup)
        self._rewrite_data_src_attrs(soup)
        self._rewrite_lazy_background_attrs(soup)
        self._rewrite_srcset_attrs(soup)
        self._rewrite_inline_style_attrs(soup)
        self._rewrite_style_tags(soup)
        self._rewrite_link_hrefs(soup)
        self._rewrite_meta_contents(soup)
        self._rewrite_page_links(soup, current_page_local_path)

    def _local_asset_ref(self, raw_url: str) -> str | None:
        """将资源 URL 转换为本地相对路径（不存在则返回 None）"""
        absolute = normalize_url(raw_url, self.base_url)
        if absolute in self.resource_map:
            return f"./{self.resource_map[absolute]}"
        return None

    def _rewrite_tag_attrs(self, soup: BeautifulSoup) -> None:
        """重写 RESOURCE_ATTRS 声明中的标签属性"""
        for tag_name, attr_name in self.RESOURCE_ATTRS:
            for tag in soup.find_all(tag_name):
                val = tag.get(attr_name)
                if not isinstance(val, str):
                    continue
                local_ref = self._local_asset_ref(val.strip())
                if local_ref:
                    tag[attr_name] = local_ref

    def _rewrite_src_attrs(self, soup: BeautifulSoup) -> None:
        """重写通用 src 属性"""
        for tag in soup.find_all(True, src=True):
            src = (tag.get("src") or "").strip()
            local_ref = self._local_asset_ref(src)
            if local_ref:
                tag["src"] = local_ref

    def _rewrite_data_src_attrs(self, soup: BeautifulSoup) -> None:
        """重写 data-* 中包含 src 的属性"""
        for tag in soup.find_all(True):
            for attr in list(tag.attrs.keys()):
                attr_lower = attr.lower()
                if not (
                    attr.startswith("data-")
                    and (
                        "src" in attr_lower
                        or attr_lower in {"data-original", "data-url"}
                    )
                ):
                    continue
                val = tag.get(attr, "")
                if not isinstance(val, str):
                    continue
                local_ref = self._local_asset_ref(val.strip())
                if local_ref:
                    tag[attr] = local_ref
                    self._promote_lazy_resource_to_runtime_attr(tag, attr, local_ref)

    def _rewrite_lazy_background_attrs(self, soup: BeautifulSoup) -> None:
        """重写 data-bg / data-background 等惰性背景图属性"""
        for tag in soup.find_all(True):
            for attr in list(tag.attrs.keys()):
                attr_lower = attr.lower()
                if not (
                    attr_lower in {"data-bg", "data-bg-src", "data-background"}
                    or "background" in attr_lower
                ):
                    continue
                val = tag.get(attr, "")
                if not isinstance(val, str):
                    continue
                local_ref = self._local_asset_ref(val.strip())
                if not local_ref:
                    continue
                tag[attr] = local_ref
                style_val = tag.get("style", "")
                if not isinstance(style_val, str):
                    style_val = ""
                if "background-image" not in style_val:
                    style_val = (style_val.rstrip(";") + ";" if style_val else "") + (
                        f"background-image:url('{local_ref}')"
                    )
                    tag["style"] = style_val

    def _rewrite_srcset_attrs(self, soup: BeautifulSoup) -> None:
        """重写 srcset / data-srcset"""
        for attr_name in ("srcset", "data-srcset"):
            for tag in soup.find_all(True, attrs={attr_name: True}):
                srcset = tag.get(attr_name, "")
                if isinstance(srcset, str):
                    tag[attr_name] = self._rewrite_srcset(srcset)

    def _rewrite_inline_style_attrs(self, soup: BeautifulSoup) -> None:
        """重写 style 属性中的 url()"""
        for tag in soup.find_all(True, style=True):
            style_val = tag.get("style", "")
            if isinstance(style_val, str) and "url(" in style_val:
                tag["style"] = self._rewrite_css_urls(style_val)

    def _rewrite_style_tags(self, soup: BeautifulSoup) -> None:
        """重写 <style> 文本中的 url()"""
        for style_tag in soup.find_all("style"):
            css_text = style_tag.string
            if css_text and "url(" in css_text:
                style_tag.string = self._rewrite_css_urls(css_text)

    def _rewrite_link_hrefs(self, soup: BeautifulSoup) -> None:
        """重写 link[href]"""
        for link in soup.find_all("link", href=True):
            href = (link.get("href") or "").strip()
            local_ref = self._local_asset_ref(href)
            if local_ref:
                link["href"] = local_ref

    def _rewrite_meta_contents(self, soup: BeautifulSoup) -> None:
        """重写 meta[content] 中的资源 URL"""
        for meta in soup.find_all("meta", content=True):
            content = (meta.get("content") or "").strip()
            local_ref = self._local_asset_ref(content)
            if local_ref:
                meta["content"] = local_ref

    def _rewrite_page_links(self, soup: BeautifulSoup, current_page_local_path: str) -> None:
        """重写同 host 页面链接（local 模式写本地路径，absolute 模式写原站绝对路径）"""
        for tag in soup.find_all("a", href=True):
            raw_href = (tag.get("href") or "").strip()
            if not raw_href or should_skip_url(raw_href):
                continue

            parsed_raw = urlparse(raw_href)
            fragment = parsed_raw.fragment

            absolute = normalize_crawl_url(raw_href, self.base_url)
            if not absolute or not is_same_host(absolute, self.base_domain):
                continue

            if self.page_link_mode == "absolute":
                tag["href"] = absolute + (f"#{fragment}" if fragment else "")
                tag["target"] = "_blank"
                rel_val = tag.get("rel")
                if isinstance(rel_val, list):
                    rel_set = set(rel_val)
                    rel_set.update({"noopener", "noreferrer"})
                    tag["rel"] = list(rel_set)
                else:
                    tag["rel"] = "noopener noreferrer"
                continue

            target_local = url_to_local_page_path(absolute, self.base_domain)
            rel = make_relative_path(current_page_local_path, target_local)
            tag["href"] = rel + (f"#{fragment}" if fragment else "")

    def _rewrite_srcset(self, srcset: str) -> str:
        """重写 srcset 属性中的 URL"""
        parts = []
        for entry in srcset.split(","):
            entry = entry.strip()
            if not entry:
                continue
            tokens = entry.split()
            if tokens:
                url = tokens[0]
                absolute = normalize_url(url, self.base_url)
                if absolute in self.resource_map:
                    tokens[0] = f"./{self.resource_map[absolute]}"
                parts.append(" ".join(tokens))
        return ", ".join(parts)

    # ─── CSS AST 解析 ──────────────────────────────────────

    def _parse_css_ast(self, css_text: str) -> list[str]:
        """
        使用 tinycss2 解析 CSS 文本，提取所有 url() 和 @import 引用
        返回发现的 URL 列表
        """
        urls = []
        try:
            # 解析为 token 列表
            tokens = tinycss2.parse_stylesheet(
                css_text, skip_comments=True, skip_whitespace=False
            )
            self._walk_css_tokens(tokens, urls)
        except Exception as e:
            # CSS 解析失败时回退到简单提取
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
                self._scan_component_values(node.content, urls)

            # prelude (如 at-rule 的 prelude)
            if hasattr(node, "prelude") and node.prelude:
                self._scan_component_values(node.prelude, urls)

    def _scan_component_values(self, values, urls: list[str]) -> None:
        """扫描 CSS 组件值列表，提取 url() 函数"""
        for val in values:
            extracted = self._extract_css_url_token_value(val, allow_string=False)
            if extracted and not should_skip_url(extracted):
                urls.append(extracted)
                continue

            if hasattr(val, "content") and val.content:
                self._scan_component_values(val.content, urls)
            elif hasattr(val, "arguments") and val.arguments:
                self._scan_component_values(val.arguments, urls)

    def _extract_import_url(self, node, urls: list[str]) -> None:
        """从 @import 规则中提取 URL"""
        for val in node.prelude:
            extracted = self._extract_css_url_token_value(val, allow_string=True)
            if not extracted or should_skip_url(extracted):
                continue

            urls.append(extracted)
            normalized = normalize_url(extracted, self.base_url)
            if normalized:
                self.discovered_css_urls.add(normalized)

    def _extract_css_urls(self, css_text: str) -> list[str]:
        """
        从 CSS 文本中提取 url() 值（回退方法，仅在 AST 解析失败时使用）
        使用 tinycss2 token 级解析而非正则
        """
        urls = []
        try:
            tokens = tinycss2.parse_component_value_list(css_text)
            self._scan_component_values(tokens, urls)
        except Exception:
            # 最后的回退：用极简提取
            pass
        return urls

    def _rewrite_css_urls(self, css_text: str) -> str:
        """
        重写 CSS 文本中的 url() 引用为本地路径
        使用 tinycss2 进行精准替换
        """
        try:
            tokens = tinycss2.parse_component_value_list(css_text)
            self._rewrite_css_tokens(tokens)
            return tinycss2.serialize(tokens)
        except Exception:
            return css_text

    def _rewrite_css_tokens(self, tokens) -> None:
        """递归重写 CSS token 中的 url()"""
        for token in tokens:
            if self._rewrite_single_css_token(token):
                continue

            if hasattr(token, "content") and token.content:
                self._rewrite_css_tokens(token.content)
            elif hasattr(token, "arguments") and token.arguments:
                self._rewrite_css_tokens(token.arguments)

    @staticmethod
    def _token_text(token) -> str:
        return token.value if hasattr(token, "value") else token.serialize()

    def _extract_css_url_token_value(self, token, allow_string: bool) -> str | None:
        """从 CSS token 中提取 URL 文本"""
        if token.type == "url":
            return token.value.strip()

        if allow_string and token.type == "string":
            return token.value.strip()

        if token.type == "function" and token.lower_name == "url":
            return (
                "".join(self._token_text(v) for v in token.arguments)
                .strip()
                .strip("'\"")
            )

        return None

    def _rewrite_single_css_token(self, token) -> bool:
        """重写单个 token，返回是否已处理"""
        if token.type == "url":
            url = token.value.strip()
            absolute = normalize_url(url, self.base_url)
            local_path = self.resource_map.get(absolute)
            if local_path:
                local_ref = f"./{local_path}"
                token.value = local_ref
                token.representation = f"url({local_ref})"
            return True

        if token.type == "function" and token.lower_name == "url":
            self._rewrite_url_function_token(token)
            return True

        return False

    def _rewrite_url_function_token(self, token) -> None:
        if not token.arguments:
            return

        inner = "".join(self._token_text(v) for v in token.arguments).strip().strip("'\"")
        absolute = normalize_url(inner, self.base_url)
        local_path = self.resource_map.get(absolute)
        if not local_path:
            return

        local = f"./{local_path}"
        from tinycss2.ast import StringToken

        first_arg = token.arguments[0]
        token.arguments[:] = [
            StringToken(
                first_arg.source_line,
                first_arg.source_column,
                local,
                f"'{local}'",
            )
        ]

    @staticmethod
    def _is_lazy_placeholder(src: str) -> bool:
        """判断 src 是否为常见占位图"""
        if not src:
            return True
        s = src.strip().lower()
        if not s:
            return True
        if s.startswith("data:image"):
            # 避免把完整 base64 正常图误判为占位
            return len(s) < 256 or "r0lgodh" in s
        return any(
            keyword in s
            for keyword in ("placeholder", "spacer", "blank", "loading", "pixel")
        )

    def _promote_lazy_resource_to_runtime_attr(
        self, tag, attr: str, local_ref: str
    ) -> None:
        """将 data-src/data-srcset 的真实地址同步到 src/srcset，避免 JS 失效后图片不显示"""
        attr_lower = attr.lower()
        if attr_lower in {"data-srcset", "data-lazy-srcset"}:
            current_srcset = (tag.get("srcset") or "").strip()
            if not current_srcset:
                tag["srcset"] = local_ref
            return

        if tag.name == "source":
            if "srcset" in attr_lower:
                tag["srcset"] = local_ref
            elif not tag.get("src"):
                tag["src"] = local_ref
            return

        if tag.name != "img":
            return

        current_src = (tag.get("src") or "").strip()
        if self._is_lazy_placeholder(current_src):
            tag["src"] = local_ref
        if attr_lower in {"data-srcset", "data-lazy-srcset"} and not tag.get("srcset"):
            tag["srcset"] = local_ref


def parse_external_css(
    css_text: str,
    css_url: str,
    resource_map: dict[str, str],
    base_domain: str,
    current_css_local_path: str | None = None,
) -> tuple[str, dict[str, str], set[str]]:
    """
    解析外部 CSS 文件的内容，提取 url() 引用并重写路径

    Args:
        css_text: CSS 文件内容
        css_url: 该 CSS 文件的原始 URL
        resource_map: 现有的资源映射（会被更新）
        base_domain: 站点主域名

    Returns:
        (重写后的 CSS, 新发现的资源映射, 需要进一步解析的子 CSS URL)
    """
    new_resources = {}
    sub_css_urls = set()

    try:
        tokens = tinycss2.parse_stylesheet(
            css_text, skip_comments=True, skip_whitespace=False
        )
    except Exception:
        return css_text, new_resources, sub_css_urls

    def _css_ref(local_target: str) -> str:
        if current_css_local_path:
            return make_relative_path(current_css_local_path, local_target)
        return f"./{local_target}"

    def scan_and_collect(nodes):
        for node in nodes:
            # @import
            if node.type == "at-rule" and node.lower_at_keyword == "import":
                for val in node.prelude:
                    url = None
                    if val.type == "url":
                        url = val.value.strip()
                    elif val.type == "string":
                        url = val.value.strip()
                    elif val.type == "function" and val.lower_name == "url":
                        url = "".join(
                            v.value if hasattr(v, "value") else v.serialize()
                            for v in val.arguments
                        ).strip().strip("'\"")

                    if url and not should_skip_url(url):
                        absolute = normalize_url(url, css_url)
                        if absolute:
                            local_path = url_to_local_path(absolute, base_domain)
                            new_resources[absolute] = local_path
                            resource_map[absolute] = local_path
                            sub_css_urls.add(absolute)

            # content / prelude 中的 url()
            for attr_name in ("content", "prelude"):
                values = getattr(node, attr_name, None)
                if values:
                    _scan_values(values)

    def _scan_values(values):
        for val in values:
            if val.type == "url":
                url = val.value.strip()
                if url and not should_skip_url(url):
                    absolute = normalize_url(url, css_url)
                    if absolute and absolute not in resource_map:
                        local_path = url_to_local_path(absolute, base_domain)
                        new_resources[absolute] = local_path
                        resource_map[absolute] = local_path

            elif val.type == "function" and val.lower_name == "url":
                inner = "".join(
                    v.value if hasattr(v, "value") else v.serialize()
                    for v in val.arguments
                ).strip().strip("'\"")
                if inner and not should_skip_url(inner):
                    absolute = normalize_url(inner, css_url)
                    if absolute and absolute not in resource_map:
                        local_path = url_to_local_path(absolute, base_domain)
                        new_resources[absolute] = local_path
                        resource_map[absolute] = local_path

            if hasattr(val, "content") and val.content:
                _scan_values(val.content)
            if hasattr(val, "arguments") and val.arguments:
                _scan_values(val.arguments)

    scan_and_collect(tokens)

    # 重写 CSS 中的 URL
    def rewrite_nodes(nodes):
        for node in nodes:
            if node.type == "at-rule" and node.lower_at_keyword == "import":
                for val in node.prelude:
                    url = None
                    if val.type == "url":
                        url = val.value.strip()
                    elif val.type == "string":
                        url = val.value.strip()

                    if url:
                        absolute = normalize_url(url, css_url)
                        if absolute in resource_map:
                            local = _css_ref(resource_map[absolute])
                            if val.type == "url":
                                val.value = local
                                val.representation = f"url({local})"
                            elif val.type == "string":
                                val.value = local
                                val.representation = f"'{local}'"

            for attr_name in ("content", "prelude"):
                values = getattr(node, attr_name, None)
                if values:
                    _rewrite_values(values)

    def _rewrite_values(values):
        for val in values:
            if val.type == "url":
                url = val.value.strip()
                absolute = normalize_url(url, css_url)
                if absolute in resource_map:
                    local = _css_ref(resource_map[absolute])
                    val.value = local
                    val.representation = f"url({local})"

            elif val.type == "function" and val.lower_name == "url":
                inner = "".join(
                    v.value if hasattr(v, "value") else v.serialize()
                    for v in val.arguments
                ).strip().strip("'\"")
                absolute = normalize_url(inner, css_url)
                if absolute in resource_map:
                    local = _css_ref(resource_map[absolute])
                    from tinycss2.ast import StringToken
                    new_token = StringToken(
                        val.arguments[0].source_line if val.arguments else 0,
                        val.arguments[0].source_column if val.arguments else 0,
                        local,
                        f"'{local}'",
                    )
                    val.arguments[:] = [new_token]

            if hasattr(val, "content") and val.content:
                _rewrite_values(val.content)
            if hasattr(val, "arguments") and val.arguments:
                _rewrite_values(val.arguments)

    rewrite_nodes(tokens)

    rewritten_css = tinycss2.serialize(tokens)
    return rewritten_css, new_resources, sub_css_urls


# JS 字符串中常见的静态资源引用（用于补抓 script 里硬编码图片/字体）
JS_ASSET_LITERAL_RE = re.compile(
    r"""(?P<q>['"])(?P<url>(?:(?:https?:)?//|/|\.{1,2}/|[A-Za-z0-9_-]+/)[^'"]+?\.(?:png|jpe?g|gif|webp|svg|ico|mp4|webm|mp3|ogg|wav|woff2?|ttf|otf|eot)(?:\?[^'"]*)?)(?P=q)""",
    re.IGNORECASE,
)


def parse_external_js_assets(
    js_text: str,
    js_url: str,
    resource_map: dict[str, str],
    base_domain: str,
) -> dict[str, str]:
    """
    从 JS 文本中提取静态资源 URL（字符串字面量），并并入资源映射。
    """
    new_resources: dict[str, str] = {}
    if not js_text:
        return new_resources

    parsed_js = urlparse(js_url)
    site_origin = ""
    if parsed_js.scheme and parsed_js.netloc:
        site_origin = f"{parsed_js.scheme}://{parsed_js.netloc}"

    for match in JS_ASSET_LITERAL_RE.finditer(js_text):
        raw_url = (match.group("url") or "").strip()
        if not raw_url or should_skip_url(raw_url):
            continue

        candidates: list[str] = []
        # JS 字面量里的资源路径，绝大多数是相对于站点根目录，而不是 JS 文件目录。
        if raw_url.startswith(("http://", "https://", "//", "/")):
            candidates.append(normalize_url(raw_url, js_url))
        else:
            trimmed = raw_url
            while trimmed.startswith("./"):
                trimmed = trimmed[2:]
            while trimmed.startswith("../"):
                trimmed = trimmed[3:]
            if site_origin:
                candidates.append(normalize_url(f"/{trimmed}", site_origin))
            candidates.append(normalize_url(raw_url, js_url))

        for absolute in candidates:
            if not absolute or should_skip_url(absolute):
                continue
            if absolute in resource_map:
                continue
            resource_map[absolute] = url_to_local_path(absolute, base_domain)
            new_resources[absolute] = resource_map[absolute]

    return new_resources
