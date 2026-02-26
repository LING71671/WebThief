"""
HTML 重写模块

负责将 HTML DOM 中的外部 URL 重写为本地路径。
"""

from __future__ import annotations

from urllib.parse import urlparse

from bs4 import BeautifulSoup

from .core import ParserConfig
from .css import CSSUrlParser
from ..utils import (
    normalize_url,
    normalize_crawl_url,
    url_to_local_page_path,
    should_skip_url,
    make_relative_path,
    is_same_host,
)


class HTMLRewriter:
    """HTML 重写器"""

    def __init__(self, config: ParserConfig, resource_map: dict[str, str]) -> None:
        self.config = config
        self.base_url = config.base_url
        self.base_domain = urlparse(config.base_url).netloc
        self.resource_map = resource_map
        self.page_link_mode = config.page_link_mode

    def rewrite_all(self, soup: BeautifulSoup, current_page_local_path: str) -> None:
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
        for tag_name, attr_name in self.config.RESOURCE_ATTRS:
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
                self._add_background_image_style(tag, local_ref)

    def _add_background_image_style(self, tag, local_ref: str) -> None:
        """添加 background-image 样式"""
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

    def _rewrite_css_urls(self, css_text: str) -> str:
        """
        重写 CSS 文本中的 url() 引用为本地路径
        使用 tinycss2 进行精准替换
        """
        import tinycss2

        try:
            tokens = tinycss2.parse_component_value_list(css_text)
            CSSUrlParser.rewrite_tokens_urls(tokens, self.resource_map, self.base_url)
            return tinycss2.serialize(tokens)
        except Exception:
            return css_text

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
        """重写同 host 页面链接"""
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
                self._rewrite_link_to_absolute(tag, absolute, fragment)
                continue

            target_local = url_to_local_page_path(absolute, self.base_domain)
            rel = make_relative_path(current_page_local_path, target_local)
            tag["href"] = rel + (f"#{fragment}" if fragment else "")

    def _rewrite_link_to_absolute(self, tag, absolute: str, fragment: str) -> None:
        """将链接重写为绝对路径"""
        tag["href"] = absolute + (f"#{fragment}" if fragment else "")
        tag["target"] = "_blank"
        rel_val = tag.get("rel")
        if isinstance(rel_val, list):
            rel_set = set(rel_val)
            rel_set.update({"noopener", "noreferrer"})
            tag["rel"] = list(rel_set)
        else:
            tag["rel"] = "noopener noreferrer"

    @staticmethod
    def _is_lazy_placeholder(src: str) -> bool:
        """判断 src 是否为常见占位图"""
        if not src:
            return True
        s = src.strip().lower()
        if not s:
            return True
        if s.startswith("data:image"):
            return len(s) < 256 or "r0lgodh" in s
        return any(
            keyword in s
            for keyword in ("placeholder", "spacer", "blank", "loading", "pixel")
        )

    def _promote_lazy_resource_to_runtime_attr(
        self, tag, attr: str, local_ref: str
    ) -> None:
        """将 data-src/data-srcset 的真实地址同步到 src/srcset"""
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
