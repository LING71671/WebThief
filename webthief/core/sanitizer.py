"""
页面净化层：
- 移除 CSP (Content-Security-Policy)
- 剥离 Service Worker 注册脚本
- 清洗第三方追踪器/分析脚本
- 移除 integrity / crossorigin 属性
- 清理无用的预连接提示
- 【新增】注入运行时兼容层 Shim
- 【新增】中和 JS 脚本（防止 SPA Hydration 闪退）
- 【新增】剥离 SPA 框架启动脚本
"""

import json
from urllib.parse import urlparse, urlunparse

from bs4 import BeautifulSoup, Comment, Tag, NavigableString

from ..config import (
    TRACKER_KEYWORDS,
    TRACKER_DOMAINS,
    SW_KEYWORDS,
    RUNTIME_SHIM_JS,
    SPA_HYDRATION_KEYWORDS,
)
from ..utils import normalize_url, should_skip_url


def sanitize(html: str, original_url: str = "", keep_js: bool = False,
             qr_bridge_script: str = "", menu_script: str = "") -> str:
    """
    对 HTML 字符串进行全面净化，返回清洗后的 HTML。

    Args:
        html: 原始 HTML 字符串
        original_url: 原始页面 URL（用于 Shim 伪造 location）
        keep_js: 是否保留 JS 执行能力（默认 False = 中和所有 JS）
        qr_bridge_script: 二维码桥接脚本（可选）
        menu_script: 菜单保留脚本（可选）

    执行步骤：
    1. 移除 CSP meta 标签
    2. 移除 Service Worker 脚本
    3. 清洗追踪器脚本（内联 + 外部）
    4. 移除 integrity / crossorigin / nonce 属性
    5. 清理预连接 / DNS 预取提示
    6. 【新增】中和 JS 脚本 / 剥离 SPA 框架启动脚本
    7. 【新增】注入运行时兼容层 Shim
    8. 【新增】注入二维码桥接脚本
    9. 【新增】注入菜单保留脚本
    """
    soup = BeautifulSoup(html, "lxml")

    _remove_csp(soup)
    _remove_service_workers(soup)
    _remove_trackers(soup)
    _remove_integrity_attrs(soup)
    _remove_preconnect(soup)
    _remove_nonce_attrs(soup)

    # keep-js 模式下要保留运行时链路，否则会导致整站交互/动效失效。
    # 仅在 neutralize-js 模式执行 SPA 启动脚本剥离与脚本中和。
    if not keep_js:
        _neutralize_spa_scripts(soup)
        _neutralize_scripts(soup)

    # 新增：注入运行时兼容层
    _inject_runtime_shim(soup, original_url)

    # 新增：注入二维码桥接脚本
    if qr_bridge_script:
        _inject_custom_script(soup, qr_bridge_script, "qr-bridge")

    # 新增：注入菜单保留脚本
    if menu_script:
        _inject_custom_script(soup, menu_script, "menu-preservation")

    return str(soup)


def inject_runtime_resource_map(
    html: str,
    original_url: str,
    resource_map: dict[str, str],
    response_cache: dict[str, bytes] | None = None,
    response_content_types: dict[str, str] | None = None,
) -> str:
    """
    注入资源映射脚本，供运行时 fetch/XHR 使用本地镜像资源。

    Args:
        html: 已完成 sanitize + parse 的 HTML
        original_url: 原始页面 URL
        resource_map: 远程 URL -> 本地路径
    """
    if not resource_map:
        return html

    soup = BeautifulSoup(html, "lxml")
    _inject_resource_map_script(
        soup,
        original_url,
        resource_map,
        response_cache=response_cache or {},
        response_content_types=response_content_types or {},
    )
    return str(soup)


def _remove_csp(soup: BeautifulSoup) -> None:
    """移除 Content-Security-Policy meta 标签"""
    for meta in soup.find_all("meta", attrs={"http-equiv": True}):
        if meta.get("http-equiv", "").lower() in (
            "content-security-policy",
            "content-security-policy-report-only",
            "x-content-security-policy",
            "x-frame-options",
        ):
            meta.decompose()


def _remove_service_workers(soup: BeautifulSoup) -> None:
    """移除所有包含 Service Worker 注册的 script 块"""
    for script in soup.find_all("script"):
        content = script.string or ""
        src = script.get("src", "")
        if src and any(kw in src.lower() for kw in ("sw.js", "service-worker", "serviceworker")):
            script.decompose()
            continue
        if any(kw in content for kw in SW_KEYWORDS):
            script.decompose()


def _remove_trackers(soup: BeautifulSoup) -> None:
    """
    清洗追踪器：
    1. 移除引用已知追踪域名的外部脚本
    2. 移除内联脚本中包含追踪器关键字的代码
    3. 移除追踪用的 <img> 像素 (1x1)
    4. 移除 <noscript> 中的追踪内容
    """
    _remove_tracker_scripts(soup)
    _remove_tracker_images(soup)
    _remove_tracker_noscript_blocks(soup)


def _remove_tracker_scripts(soup: BeautifulSoup) -> None:
    for script in soup.find_all("script"):
        src = script.get("src", "")
        if src and _is_tracker_domain_url(src):
            script.decompose()
            continue
        if src:
            continue
        content = script.string or ""
        if any(keyword in content for keyword in TRACKER_KEYWORDS):
            script.decompose()


def _remove_tracker_images(soup: BeautifulSoup) -> None:
    for img in soup.find_all("img"):
        src = img.get("src", "")
        if (src and _is_tracker_domain_url(src)) or _is_tracker_pixel(img):
            img.decompose()


def _remove_tracker_noscript_blocks(soup: BeautifulSoup) -> None:
    for noscript in soup.find_all("noscript"):
        content = str(noscript)
        if any(domain in content for domain in TRACKER_DOMAINS):
            noscript.decompose()


def _is_tracker_domain_url(url: str) -> bool:
    try:
        return urlparse(url).netloc in TRACKER_DOMAINS
    except Exception:
        return False


def _is_tracker_pixel(img: Tag) -> bool:
    width = str(img.get("width", "")).strip()
    height = str(img.get("height", "")).strip()
    return width == "1" and height == "1"


def _remove_integrity_attrs(soup: BeautifulSoup) -> None:
    """移除 integrity 和 crossorigin 属性（本地 SRI 校验必失败）"""
    for tag in soup.find_all(True):
        if tag.has_attr("integrity"):
            del tag["integrity"]
        if tag.has_attr("crossorigin"):
            del tag["crossorigin"]


def _remove_preconnect(soup: BeautifulSoup) -> None:
    """移除 preconnect / dns-prefetch 提示（离线无意义）"""
    useless_rels = {"preconnect", "dns-prefetch"}
    for link in soup.find_all("link", rel=True):
        rel_values = link.get("rel", [])
        if isinstance(rel_values, list):
            rel_set = set(r.lower() for r in rel_values)
        else:
            rel_set = {rel_values.lower()}
        if rel_set & useless_rels:
            link.decompose()


def _remove_nonce_attrs(soup: BeautifulSoup) -> None:
    """移除 nonce 属性（CSP 相关）"""
    for tag in soup.find_all(True):
        if tag.has_attr("nonce"):
            del tag["nonce"]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  以下为 v1.1 新增：JS 中和 + SPA 剥离 + Shim 注入
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def _neutralize_scripts(soup: BeautifulSoup) -> None:
    """
    中和所有 <script> 标签 —— 将 type 改为 text/disabled
    浏览器会跳过非 text/javascript 类型的 script，但 DOM 结构完整保留

    保护性排除：
    - type="application/ld+json" (SEO 结构化数据)
    - type="application/json" (内嵌数据)
    - data-webthief="shim" (我们自己注入的 Shim)
    """
    SAFE_TYPES = {"application/ld+json", "application/json"}

    for script in soup.find_all("script"):
        # 跳过我们自己的 Shim
        if script.get("data-webthief") == "shim":
            continue

        # 跳过安全类型
        script_type = (script.get("type") or "").lower().strip()
        if script_type in SAFE_TYPES:
            continue

        # 中和：将 type 改为 text/disabled
        script["type"] = "text/disabled"
        # 保留原始 type 以供调试
        if script_type and script_type not in ("text/javascript", "module", ""):
            script["data-original-type"] = script_type


def _neutralize_spa_scripts(soup: BeautifulSoup) -> None:
    """
    物理剔除 SPA 框架的 Hydration 启动脚本

    这些框架在客户端会重新渲染（Hydration），如果执行，
    反而会覆盖我们已经渲染好的静态 HTML → 白屏/闪退

    即使在 --keep-js 模式下也要执行此步骤
    """
    for script in soup.find_all("script"):
        content = script.string or ""
        src = script.get("src", "") or ""

        # 检查内联脚本
        if content:
            for keyword in SPA_HYDRATION_KEYWORDS:
                if keyword in content:
                    script.decompose()
                    break

        # 检查外部脚本（框架 chunk 加载器）
        elif src:
            # Gatsby / Next.js / Nuxt 的 chunk 加载器
            loader_patterns = [
                "webpack-runtime",
                "framework-",
                "app-",       # Gatsby: app-{hash}.js
                "_next/",     # Next.js
                "_nuxt/",     # Nuxt
                "chunk-",
                "polyfills-",
                "commons-",
            ]
            src_lower = src.lower()
            if any(pat in src_lower for pat in loader_patterns):
                script.decompose()


def _inject_runtime_shim(soup: BeautifulSoup, original_url: str) -> None:
    """
    在 <head> 的最顶部注入运行时兼容层脚本
    确保它在所有其他脚本之前执行
    """
    # 解析原站信息
    if original_url:
        parsed = urlparse(original_url)
        origin = f"{parsed.scheme}://{parsed.netloc}"
        hostname = parsed.netloc
        protocol = f"{parsed.scheme}:"
    else:
        origin = "https://localhost"
        hostname = "localhost"
        protocol = "https:"

    # 生成 Shim 脚本内容
    shim_content = RUNTIME_SHIM_JS % (origin, hostname, protocol)

    # 创建 script 标签
    shim_tag = soup.new_tag(
        "script",
        attrs={"data-webthief": "shim"}
    )
    shim_tag.string = shim_content

    # 插入到 <head> 的最前面
    head = soup.find("head")
    if head:
        head.insert(0, shim_tag)
    else:
        # 如果没有 <head>，创建一个
        html_tag = soup.find("html")
        if html_tag:
            new_head = soup.new_tag("head")
            new_head.insert(0, shim_tag)
            html_tag.insert(0, new_head)


def _inject_custom_script(soup: BeautifulSoup, script_content: str, script_id: str) -> None:
    """
    注入自定义脚本到 <head> 末尾

    Args:
        soup: BeautifulSoup 对象
        script_content: 脚本内容
        script_id: 脚本标识符
    """
    if not script_content:
        return

    script_tag = soup.new_tag(
        "script",
        attrs={"data-webthief": script_id}
    )
    script_tag.string = script_content

    head = soup.find("head")
    if head:
        head.append(script_tag)
    else:
        html_tag = soup.find("html")
        if html_tag:
            new_head = soup.new_tag("head")
            new_head.append(script_tag)
            html_tag.insert(0, new_head)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  资源映射脚本注入 - 策略模式重构
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class ResourceMapBuilder:
    """资源映射构建器 - 负责构建 URL 到本地资源的映射"""

    def __init__(self, original_url: str):
        self.original_url = original_url
        self.normalized_map: dict[str, str] = {}

    def build(self, resource_map: dict[str, str]) -> dict[str, str]:
        """构建标准化的资源映射"""
        for raw_url, local_path in resource_map.items():
            if not isinstance(raw_url, str) or not isinstance(local_path, str):
                continue

            absolute = normalize_url(raw_url, self.original_url)
            if not absolute or should_skip_url(absolute):
                continue

            local_ref = f"./{local_path}"
            self._add_aliases(absolute, local_ref)

        return self.normalized_map

    def _add_aliases(self, absolute: str, value: str) -> None:
        """为 URL 添加多种别名形式"""
        self.normalized_map[absolute] = value

        parsed = urlparse(absolute)
        path = parsed.path or "/"
        if path:
            self._add_path_aliases(path, value)

        if parsed.query and path:
            self._add_query_aliases(parsed, path, value)

    def _add_path_aliases(self, path: str, value: str) -> None:
        """添加路径相关的别名"""
        self.normalized_map.setdefault(path, value)
        if path.startswith("/"):
            rel_path = path.lstrip("/")
            if rel_path:
                self.normalized_map.setdefault(rel_path, value)
                self.normalized_map.setdefault(f"./{rel_path}", value)

    def _add_query_aliases(self, parsed, path: str, value: str) -> None:
        """添加带查询参数的别名"""
        with_query = f"{path}?{parsed.query}"
        self.normalized_map.setdefault(with_query, value)
        if with_query.startswith("/"):
            rel_query = with_query.lstrip("/")
            if rel_query:
                self.normalized_map.setdefault(rel_query, value)
                self.normalized_map.setdefault(f"./{rel_query}", value)

        without_query = urlunparse(
            (parsed.scheme, parsed.netloc, parsed.path or "/", parsed.params, "", "")
        )
        self.normalized_map.setdefault(without_query, value)


class ResponseCacheBuilder:
    """响应缓存构建器 - 负责处理 API 响应缓存"""

    MAX_ENTRIES = 120
    MAX_TOTAL_CHARS = 2_000_000
    MAX_BODY_SIZE = 200 * 1024

    def __init__(self, original_url: str, content_types: dict[str, str]):
        self.original_url = original_url
        self.content_types = content_types
        self.response_map: dict[str, dict[str, str]] = {}
        self.payload_entries = 0
        self.total_chars = 0

    def build(self, response_cache: dict[str, bytes]) -> dict[str, dict[str, str]]:
        """构建响应缓存映射"""
        for raw_url, body in response_cache.items():
            if self._should_stop():
                break
            if not self._is_valid_entry(raw_url, body):
                continue

            absolute = normalize_url(raw_url, self.original_url)
            if not absolute or should_skip_url(absolute):
                continue

            text = self._decode_body(body)
            if not text or not text.strip():
                continue
            if self._would_exceed_limit(text):
                continue

            content_type = self._get_content_type(absolute)
            if not self._should_cache_content(text, content_type):
                continue

            self._add_response(absolute, text, content_type)

        return self.response_map

    def _should_stop(self) -> bool:
        """检查是否达到条目上限"""
        return self.payload_entries >= self.MAX_ENTRIES

    def _is_valid_entry(self, raw_url, body) -> bool:
        """验证条目有效性"""
        if not isinstance(raw_url, str) or not isinstance(body, (bytes, bytearray)):
            return False
        if len(body) > self.MAX_BODY_SIZE:
            return False
        return True

    def _decode_body(self, body: bytes) -> str | None:
        """解码响应体为文本"""
        try:
            return body.decode("utf-8")
        except Exception:
            try:
                return body.decode("utf-8", errors="ignore")
            except Exception:
                return None

    def _would_exceed_limit(self, text: str) -> bool:
        """检查是否超出字符限制"""
        return self.total_chars + len(text) > self.MAX_TOTAL_CHARS

    def _get_content_type(self, absolute: str) -> str:
        """获取内容类型"""
        return (self.content_types.get(absolute) or "").split(";")[0].strip().lower()

    def _should_cache_content(self, text: str, content_type: str) -> bool:
        """判断是否应该缓存此内容"""
        stripped = text.lstrip()
        is_json_like = stripped.startswith("{") or stripped.startswith("[")

        # 排除 HTML 页面内容
        if content_type.startswith("text/html"):
            return False
        if stripped.startswith("<!doctype html>") or stripped.startswith("<html"):
            return False

        return (
            content_type.startswith("application/json")
            or "json" in content_type
            or content_type.startswith("text/")
            or "javascript" in content_type
            or is_json_like
        )

    def _add_response(self, absolute: str, text: str, content_type: str) -> None:
        """添加响应到映射"""
        stripped = text.lstrip()
        is_json_like = stripped.startswith("{") or stripped.startswith("[")

        payload = {
            "body": text,
            "contentType": content_type or ("application/json" if is_json_like else "text/plain"),
        }
        self._add_aliases(absolute, payload)
        self.payload_entries += 1
        self.total_chars += len(text)

    def _add_aliases(self, absolute: str, payload: dict[str, str]) -> None:
        """为 URL 添加多种别名形式"""
        self.response_map[absolute] = payload

        parsed = urlparse(absolute)
        path = parsed.path or "/"
        if path:
            self.response_map.setdefault(path, payload)
            if path.startswith("/"):
                rel_path = path.lstrip("/")
                if rel_path:
                    self.response_map.setdefault(rel_path, payload)
                    self.response_map.setdefault(f"./{rel_path}", payload)

        if parsed.query and path:
            with_query = f"{path}?{parsed.query}"
            self.response_map.setdefault(with_query, payload)
            if with_query.startswith("/"):
                rel_query = with_query.lstrip("/")
                if rel_query:
                    self.response_map.setdefault(rel_query, payload)
                    self.response_map.setdefault(f"./{rel_query}", payload)

            without_query = urlunparse(
                (parsed.scheme, parsed.netloc, parsed.path or "/", parsed.params, "", "")
            )
            self.response_map.setdefault(without_query, payload)


class ResourceMapScriptGenerator:
    """资源映射脚本生成器 - 负责生成最终的 JavaScript 代码"""

    def __init__(self, original_url: str):
        self.original_url = original_url

    def generate(
        self,
        normalized_map: dict[str, str],
        response_map: dict[str, dict[str, str]]
    ) -> str:
        """生成资源映射脚本内容"""
        origin = self._extract_origin()

        script_lines = [
            "(function(){",
            f"  window.__WEBTHIEF_ORIGIN__ = {json.dumps(origin, ensure_ascii=False)};",
            "  var existing = window.__WEBTHIEF_RESOURCE_MAP__ || {};",
            f"  var incoming = {json.dumps(normalized_map, ensure_ascii=False, separators=(',', ':'))};",
            "  for (var k in incoming) { existing[k] = incoming[k]; }",
            "  window.__WEBTHIEF_RESOURCE_MAP__ = existing;",
        ]

        if response_map:
            script_lines.extend(self._generate_response_map_lines(response_map))

        script_lines.append("})();")
        return "\n".join(script_lines)

    def _extract_origin(self) -> str:
        """提取原始 URL 的 origin"""
        parsed = urlparse(self.original_url or "")
        if parsed.scheme and parsed.netloc:
            return f"{parsed.scheme}://{parsed.netloc}"
        return ""

    def _generate_response_map_lines(self, response_map: dict[str, dict[str, str]]) -> list[str]:
        """生成响应映射相关的代码行"""
        return [
            "  var existingResp = window.__WEBTHIEF_RESPONSE_MAP__ || {};",
            f"  var incomingResp = {json.dumps(response_map, ensure_ascii=False, separators=(',', ':'))};",
            "  for (var rk in incomingResp) { existingResp[rk] = incomingResp[rk]; }",
            "  window.__WEBTHIEF_RESPONSE_MAP__ = existingResp;",
        ]


def _inject_resource_map_script(
    soup: BeautifulSoup,
    original_url: str,
    resource_map: dict[str, str],
    response_cache: dict[str, bytes] | None = None,
    response_content_types: dict[str, str] | None = None,
) -> None:
    """注入运行时资源映射（供 shim 的 fetch/XHR 代理使用本地镜像资源）"""
    if not resource_map:
        return

    # 步骤1: 构建资源映射
    map_builder = ResourceMapBuilder(original_url)
    normalized_map = map_builder.build(resource_map)

    if not normalized_map:
        return

    # 步骤2: 构建响应缓存映射
    cache_builder = ResponseCacheBuilder(
        original_url,
        response_content_types or {}
    )
    response_map = cache_builder.build(response_cache or {})

    # 步骤3: 生成脚本内容
    script_generator = ResourceMapScriptGenerator(original_url)
    script_content = script_generator.generate(normalized_map, response_map)

    # 步骤4: 注入脚本到 DOM
    _insert_resource_map_script(soup, script_content)


def _insert_resource_map_script(soup: BeautifulSoup, script_content: str) -> None:
    """将资源映射脚本插入到 DOM 中"""
    script_tag = soup.new_tag(
        "script",
        attrs={"data-webthief": "resource-map"},
    )
    script_tag.string = script_content

    head = soup.find("head")
    if not head:
        html_tag = soup.find("html")
        if not html_tag:
            return
        head = soup.new_tag("head")
        html_tag.insert(0, head)

    # 移除旧的映射脚本
    old_map = head.find("script", attrs={"data-webthief": "resource-map"})
    if old_map:
        old_map.decompose()

    # 插入到 shim 脚本之后，或头部最前面
    shim = head.find("script", attrs={"data-webthief": "shim"})
    if shim:
        shim.insert_after(script_tag)
    else:
        head.insert(0, script_tag)
