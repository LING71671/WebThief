"""
CSS 解析模块

使用 tinycss2 AST 解析 CSS，精准提取 url() 和 @import 引用。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import tinycss2
from tinycss2.ast import StringToken

from ..utils import (
    normalize_url,
    should_skip_url,
    url_to_local_path,
    make_relative_path,
)

if TYPE_CHECKING:
    from collections.abc import Callable


class CSSUrlParser:
    """CSS URL 提取与重写工具类"""

    @staticmethod
    def extract_url_from_token(token, allow_string: bool = False) -> str | None:
        """
        从 CSS token 中提取 URL 文本

        Args:
            token: CSS token 对象
            allow_string: 是否允许从字符串 token 中提取（用于 @import）

        Returns:
            提取的 URL 字符串，或 None
        """
        if token.type == "url":
            return token.value.strip()

        if allow_string and token.type == "string":
            return token.value.strip()

        if token.type == "function" and token.lower_name == "url":
            return (
                "".join(CSSUrlParser._get_token_text(v) for v in token.arguments)
                .strip()
                .strip("'\"")
            )

        return None

    @staticmethod
    def _get_token_text(token) -> str:
        """获取 token 的文本表示"""
        return token.value if hasattr(token, "value") else token.serialize()

    @staticmethod
    def scan_values_for_urls(
        values, urls: list[str], skip_check: Callable[[str], bool] | None = None
    ) -> None:
        """
        扫描 CSS 组件值列表，提取 url() 函数

        Args:
            values: CSS 组件值列表
            urls: 用于收集 URL 的列表
            skip_check: 可选的 URL 跳过检查函数
        """
        for val in values:
            url = CSSUrlParser.extract_url_from_token(val, allow_string=False)
            if url:
                if skip_check is None or not skip_check(url):
                    urls.append(url)
                continue

            # 递归扫描嵌套内容
            if hasattr(val, "content") and val.content:
                CSSUrlParser.scan_values_for_urls(val.content, urls, skip_check)
            elif hasattr(val, "arguments") and val.arguments:
                CSSUrlParser.scan_values_for_urls(val.arguments, urls, skip_check)

    @staticmethod
    def rewrite_url_in_token(token, resource_map: dict, base_url: str) -> bool:
        """
        重写单个 token 中的 URL

        Args:
            token: CSS token 对象
            resource_map: 资源 URL 到本地路径的映射
            base_url: 基础 URL

        Returns:
            是否已处理该 token
        """
        if token.type == "url":
            url = token.value.strip()
            absolute = normalize_url(url, base_url)
            local_path = resource_map.get(absolute)
            if local_path:
                local_ref = f"./{local_path}"
                token.value = local_ref
                token.representation = f"url({local_ref})"
            return True

        if token.type == "function" and token.lower_name == "url":
            CSSUrlParser._rewrite_url_function(token, resource_map, base_url)
            return True

        return False

    @staticmethod
    def _rewrite_url_function(token, resource_map: dict, base_url: str) -> None:
        """重写 url() 函数 token"""
        if not token.arguments:
            return

        inner = (
            "".join(CSSUrlParser._get_token_text(v) for v in token.arguments)
            .strip()
            .strip("'\"")
        )
        absolute = normalize_url(inner, base_url)
        local_path = resource_map.get(absolute)
        if not local_path:
            return

        local = f"./{local_path}"
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
    def rewrite_tokens_urls(tokens, resource_map: dict, base_url: str) -> None:
        """
        递归重写 CSS token 列表中的所有 url()

        Args:
            tokens: CSS token 列表
            resource_map: 资源映射
            base_url: 基础 URL
        """
        for token in tokens:
            if CSSUrlParser.rewrite_url_in_token(token, resource_map, base_url):
                continue

            if hasattr(token, "content") and token.content:
                CSSUrlParser.rewrite_tokens_urls(token.content, resource_map, base_url)
            elif hasattr(token, "arguments") and token.arguments:
                CSSUrlParser.rewrite_tokens_urls(token.arguments, resource_map, base_url)


class CSSResourceCollector:
    """
    CSS 资源收集器

    负责从 CSS AST 中收集 @import 和 url() 引用的资源 URL。
    """

    def __init__(self, css_url: str, base_domain: str, resource_map: dict[str, str]):
        """
        Args:
            css_url: 当前 CSS 文件的 URL
            base_domain: 站点主域名
            resource_map: 现有资源映射（会被更新）
        """
        self.css_url = css_url
        self.base_domain = base_domain
        self.resource_map = resource_map
        self.new_resources: dict[str, str] = {}
        self.sub_css_urls: set[str] = set()

    def collect_from_tokens(self, tokens) -> None:
        """
        从 CSS token 列表中收集所有资源引用

        Args:
            tokens: tinycss2 解析的 token 列表
        """
        for node in tokens:
            self._process_node(node)

    def _process_node(self, node) -> None:
        """处理单个 CSS AST 节点"""
        # 处理 @import 规则
        if node.type == "at-rule" and node.lower_at_keyword == "import":
            self._process_import_rule(node)
            return

        # 处理 content 和 prelude 中的 url()
        for attr_name in ("content", "prelude"):
            values = getattr(node, attr_name, None)
            if values:
                self._scan_values(values)

    def _process_import_rule(self, node) -> None:
        """处理 @import 规则"""
        for val in node.prelude:
            url = CSSUrlParser.extract_url_from_token(val, allow_string=True)
            if not url or should_skip_url(url):
                continue

            absolute = normalize_url(url, self.css_url)
            if not absolute:
                continue

            local_path = url_to_local_path(absolute, self.base_domain)
            self.new_resources[absolute] = local_path
            self.resource_map[absolute] = local_path
            self.sub_css_urls.add(absolute)

    def _scan_values(self, values) -> None:
        """扫描值列表中的 url() 引用"""
        for val in values:
            url = CSSUrlParser.extract_url_from_token(val, allow_string=False)
            if url and not should_skip_url(url):
                absolute = normalize_url(url, self.css_url)
                if absolute and absolute not in self.resource_map:
                    local_path = url_to_local_path(absolute, self.base_domain)
                    self.new_resources[absolute] = local_path
                    self.resource_map[absolute] = local_path

            # 递归扫描嵌套内容
            if hasattr(val, "content") and val.content:
                self._scan_values(val.content)
            if hasattr(val, "arguments") and val.arguments:
                self._scan_values(val.arguments)


class CSSRewriter:
    """
    CSS URL 重写器

    负责将 CSS 中的 URL 引用重写为本地路径。
    """

    def __init__(
        self,
        css_url: str,
        resource_map: dict[str, str],
        current_css_local_path: str | None = None,
    ):
        """
        Args:
            css_url: 当前 CSS 文件的 URL
            resource_map: 资源 URL 到本地路径的映射
            current_css_local_path: 当前 CSS 文件的本地路径（用于计算相对路径）
        """
        self.css_url = css_url
        self.resource_map = resource_map
        self.current_css_local_path = current_css_local_path

    def rewrite_tokens(self, tokens) -> None:
        """
        重写 CSS token 列表中的所有 URL 引用

        Args:
            tokens: tinycss2 解析的 token 列表
        """
        for node in tokens:
            self._rewrite_node(node)

    def _rewrite_node(self, node) -> None:
        """重写单个节点中的 URL"""
        # 处理 @import 规则
        if node.type == "at-rule" and node.lower_at_keyword == "import":
            self._rewrite_import_rule(node)

        # 处理 content 和 prelude 中的 url()
        for attr_name in ("content", "prelude"):
            values = getattr(node, attr_name, None)
            if values:
                self._rewrite_values(values)

    def _rewrite_import_rule(self, node) -> None:
        """重写 @import 规则中的 URL"""
        for val in node.prelude:
            url = CSSUrlParser.extract_url_from_token(val, allow_string=True)
            if not url:
                continue

            absolute = normalize_url(url, self.css_url)
            if absolute not in self.resource_map:
                continue

            local = self._get_local_ref(self.resource_map[absolute])
            if val.type == "url":
                val.value = local
                val.representation = f"url({local})"
            elif val.type == "string":
                val.value = local
                val.representation = f"'{local}'"

    def _rewrite_values(self, values) -> None:
        """重写值列表中的 url() 引用"""
        for val in values:
            if val.type == "url":
                self._rewrite_url_token(val)
            elif val.type == "function" and val.lower_name == "url":
                self._rewrite_url_function_token(val)

            # 递归处理嵌套内容
            if hasattr(val, "content") and val.content:
                self._rewrite_values(val.content)
            if hasattr(val, "arguments") and val.arguments:
                self._rewrite_values(val.arguments)

    def _rewrite_url_token(self, token) -> None:
        """重写 url token"""
        url = token.value.strip()
        absolute = normalize_url(url, self.css_url)
        if absolute in self.resource_map:
            local = self._get_local_ref(self.resource_map[absolute])
            token.value = local
            token.representation = f"url({local})"

    def _rewrite_url_function_token(self, token) -> None:
        """重写 url() 函数 token"""
        if not token.arguments:
            return

        inner = (
            "".join(
                v.value if hasattr(v, "value") else v.serialize()
                for v in token.arguments
            )
            .strip()
            .strip("'\"")
        )
        absolute = normalize_url(inner, self.css_url)
        if absolute not in self.resource_map:
            return

        local = self._get_local_ref(self.resource_map[absolute])
        new_token = StringToken(
            token.arguments[0].source_line if token.arguments else 0,
            token.arguments[0].source_column if token.arguments else 0,
            local,
            f"'{local}'",
        )
        token.arguments[:] = [new_token]

    def _get_local_ref(self, local_target: str) -> str:
        """获取本地引用路径（相对路径或 ./ 前缀）"""
        if self.current_css_local_path:
            return make_relative_path(self.current_css_local_path, local_target)
        return f"./{local_target}"


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
        current_css_local_path: 当前 CSS 文件的本地路径

    Returns:
        (重写后的 CSS, 新发现的资源映射, 需要进一步解析的子 CSS URL)
    """
    new_resources: dict[str, str] = {}
    sub_css_urls: set[str] = set()

    try:
        tokens = tinycss2.parse_stylesheet(
            css_text, skip_comments=True, skip_whitespace=False
        )
    except Exception:
        return css_text, new_resources, sub_css_urls

    # 收集资源
    collector = CSSResourceCollector(css_url, base_domain, resource_map)
    collector.collect_from_tokens(tokens)
    new_resources = collector.new_resources
    sub_css_urls = collector.sub_css_urls

    # 重写 URL
    rewriter = CSSRewriter(css_url, resource_map, current_css_local_path)
    rewriter.rewrite_tokens(tokens)

    rewritten_css = tinycss2.serialize(tokens)
    return rewritten_css, new_resources, sub_css_urls
