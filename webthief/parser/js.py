"""
JS 解析模块

从 JS 文本中提取静态资源 URL（字符串字面量）。
"""

from __future__ import annotations

import re
from urllib.parse import urlparse

from ..utils import normalize_url, should_skip_url, url_to_local_path

# JS 字符串中常见的静态资源引用（用于补抓 script 里硬编码图片/字体/JS模块）
JS_ASSET_LITERAL_RE = re.compile(
    r"""(?P<q>['"])(?P<url>(?:(?:https?:)?//|/|\.{1,2}/|[A-Za-z0-9_-]+/)[^'"]+?\.(?:png|jpe?g|gif|webp|svg|ico|mp4|webm|mp3|ogg|wav|woff2?|ttf|otf|eot)(?:\?[^'"]*)?)(?P=q)""",
    re.IGNORECASE,
)

# JS 动态导入模块（Vue/React 懒加载组件）
JS_DYNAMIC_IMPORT_RE = re.compile(
    r"""import\s*\(\s*['"](?P<url>\.?\.?/[^'"]+\.js(?:\?[^'"]*)?)['"]\s*\)""",
    re.IGNORECASE,
)

# JS 字符串中的接口端点（用于补抓运行时请求的数据资源）
JS_ENDPOINT_LITERAL_RE = re.compile(
    r"""(?P<q>['"])(?P<url>(?:(?:https?:)?//|/|\.{1,2}/|[A-Za-z0-9_-]+/)[A-Za-z0-9/_\-.?=&%:+~#]{2,260}(?:api|ajax|dynamic|content|auth|login|qrcode|qr|session|token)[A-Za-z0-9/_\-.?=&%:+~#]*)(?P=q)""",
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

    Args:
        js_text: JS 文件内容
        js_url: 该 JS 文件的原始 URL
        resource_map: 现有的资源映射（会被更新）
        base_domain: 站点主域名

    Returns:
        新发现的资源映射
    """
    new_resources: dict[str, str] = {}
    if not js_text:
        return new_resources

    parsed_js = urlparse(js_url)
    site_origin = ""
    if parsed_js.scheme and parsed_js.netloc:
        site_origin = f"{parsed_js.scheme}://{parsed_js.netloc}"

    def register_js_literal_url(raw_url: str) -> None:
        """注册 JS 字面量中的 URL"""
        if not raw_url or should_skip_url(raw_url):
            return

        candidates: list[str] = []
        # JS 字面量里的资源路径，绝大多数是相对于站点根目录
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

    for match in JS_ASSET_LITERAL_RE.finditer(js_text):
        register_js_literal_url((match.group("url") or "").strip())

    for match in JS_DYNAMIC_IMPORT_RE.finditer(js_text):
        register_js_literal_url((match.group("url") or "").strip())

    for match in JS_ENDPOINT_LITERAL_RE.finditer(js_text):
        register_js_literal_url((match.group("url") or "").strip())

    return new_resources
