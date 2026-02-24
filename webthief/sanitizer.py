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

from urllib.parse import urlparse

from bs4 import BeautifulSoup, Comment, Tag, NavigableString

from .config import (
    TRACKER_KEYWORDS,
    TRACKER_DOMAINS,
    SW_KEYWORDS,
    RUNTIME_SHIM_JS,
    SPA_HYDRATION_KEYWORDS,
)


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

    # 新增：SPA 框架启动脚本剥离（无论是否 keep_js 都执行）
    _neutralize_spa_scripts(soup)

    # 新增：JS 中和（除非 --keep-js）
    if not keep_js:
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
    for script in soup.find_all("script", src=True):
        src = script["src"]
        try:
            parsed = urlparse(src)
            if parsed.netloc in TRACKER_DOMAINS:
                script.decompose()
                continue
        except Exception:
            pass

    for script in soup.find_all("script"):
        if script.get("src"):
            continue
        content = script.string or ""
        if any(kw in content for kw in TRACKER_KEYWORDS):
            script.decompose()

    for img in soup.find_all("img"):
        src = img.get("src", "")
        try:
            parsed = urlparse(src)
            if parsed.netloc in TRACKER_DOMAINS:
                img.decompose()
                continue
        except Exception:
            pass
        w = img.get("width", "")
        h = img.get("height", "")
        if w == "1" and h == "1":
            img.decompose()

    for noscript in soup.find_all("noscript"):
        content = str(noscript)
        if any(domain in content for domain in TRACKER_DOMAINS):
            noscript.decompose()


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
