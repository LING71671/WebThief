"""
工具函数：URL 规范化、MIME 检测、路径安全处理
"""

import hashlib
from urllib.parse import (
    parse_qsl,
    urlencode,
    urljoin,
    urlparse,
    urlunparse,
    unquote,
)

from .config import SKIP_PROTOCOLS


def should_skip_url(url: str) -> bool:
    """判断是否应跳过此 URL（data:、blob: 等特殊协议）"""
    if not url or not url.strip():
        return True
    url_stripped = url.strip()
    for proto in SKIP_PROTOCOLS:
        if url_stripped.startswith(proto):
            return True
    return False


def normalize_url(url: str, base_url: str = "") -> str:
    """
    规范化 URL：
    - 补全协议（// → https://）
    - 解析相对路径为绝对路径
    - 去除锚点 (#fragment)
    - 规范化编码
    """
    if not url or not url.strip():
        return ""

    url = url.strip()

    # 跳过特殊协议
    if should_skip_url(url):
        return url

    # 处理协议相对 URL
    if url.startswith("//"):
        url = "https:" + url

    # 处理相对 URL
    if not url.startswith(("http://", "https://")):
        if base_url:
            url = urljoin(base_url, url)
        else:
            return url

    # 解析并规范化
    parsed = urlparse(url)

    # 去除锚点
    normalized = urlunparse((
        parsed.scheme,
        parsed.netloc,
        parsed.path or "/",
        parsed.params,
        parsed.query,
        "",  # 去掉 fragment
    ))

    return normalized


def normalize_crawl_url(url: str, base_url: str = "") -> str:
    """
    用于站点递归的 URL 规范化：
    - 补全相对路径
    - 去掉 fragment
    - 保留 query，但剔除追踪参数
    """
    normalized = normalize_url(url, base_url)
    if not normalized or should_skip_url(normalized):
        return ""

    parsed = urlparse(normalized)
    kept_qs = []
    for key, value in parse_qsl(parsed.query, keep_blank_values=True):
        key_lower = key.lower()
        if key_lower.startswith("utm_") or key_lower in {"fbclid", "gclid"}:
            continue
        kept_qs.append((key, value))

    query = urlencode(kept_qs, doseq=True)
    return urlunparse(
        (
            parsed.scheme,
            parsed.netloc,
            parsed.path or "/",
            parsed.params,
            query,
            "",
        )
    )


def is_same_host(url: str, host: str) -> bool:
    """判断 URL 是否属于指定 host（精确匹配）"""
    try:
        return urlparse(url).netloc.lower() == host.lower()
    except Exception:
        return False


def url_to_local_path(url: str, base_domain: str = "") -> str:
    """
    将远程 URL 转换为本地相对路径
    https://cdn.example.com/js/app.js → assets/cdn.example.com/js/app.js
    /static/img/logo.png → assets/{base_domain}/static/img/logo.png
    """
    if should_skip_url(url):
        return url

    # 补全协议
    if url.startswith("//"):
        url = "https:" + url

    parsed = urlparse(url)
    domain = parsed.netloc or base_domain

    if not domain:
        return url

    # 构建路径
    path = parsed.path
    if not path or path == "/":
        path = "/index.html"

    # 处理查询参数 —— 转换到文件名中
    if parsed.query:
        # 将查询参数编码到文件名
        query_hash = hashlib.md5(parsed.query.encode()).hexdigest()[:8]
        # 获取文件名和扩展名
        if "." in path.split("/")[-1]:
            name, ext = path.rsplit(".", 1)
            path = f"{name}_{query_hash}.{ext}"
        else:
            path = f"{path}_{query_hash}"

    # 清理路径中的不安全字符
    path = sanitize_path(path)

    # 确保路径不以 / 开头
    path = path.lstrip("/")

    return f"assets/{domain}/{path}"


def url_to_local_page_path(url: str, base_domain: str = "") -> str:
    """
    将页面 URL 映射到本地页面路径：
    - / -> index.html
    - /a/b -> a/b/index.html
    - 带 query 时在文件名追加哈希
    """
    absolute = normalize_crawl_url(url)
    if not absolute:
        return "index.html"

    parsed = urlparse(absolute)
    domain = parsed.netloc or base_domain
    if base_domain and domain and domain != base_domain:
        # 外域页面默认不映射（调用方应提前过滤）
        return "index.html"

    path = parsed.path or "/"
    if path.endswith("/"):
        local = f"{path}index.html"
    else:
        tail = path.rsplit("/", 1)[-1]
        if "." in tail:
            local = path
        else:
            local = f"{path}/index.html"

    local = sanitize_path(local).lstrip("/")
    if not local:
        local = "index.html"

    if parsed.query:
        qhash = hashlib.md5(parsed.query.encode("utf-8")).hexdigest()[:8]
        if local.endswith(".html"):
            local = local[:-5] + f"_{qhash}.html"
        else:
            local = f"{local}_{qhash}"

    return local


def sanitize_path(path: str) -> str:
    """
    清理文件路径中的不安全字符
    - 替换 Windows 不允许的字符
    - 防止目录穿越
    - 处理超长路径
    """
    # 解码 URL 编码
    path = unquote(path)

    # 替换 Windows 不允许的文件名字符
    unsafe_chars = '<>"|?*'
    for ch in unsafe_chars:
        path = path.replace(ch, "_")

    # 替换冒号（但保留盘符格式，这里不会有盘符）
    path = path.replace(":", "_")

    # 防止目录穿越
    parts = path.split("/")
    safe_parts = []
    for part in parts:
        if part in ("..", "."):
            continue
        if not part:
            continue
        # 截断过长的文件名（单个组件最长 200 字符）
        if len(part) > 200:
            name_hash = hashlib.md5(part.encode()).hexdigest()[:8]
            part = part[:190] + "_" + name_hash
        safe_parts.append(part)

    return "/".join(safe_parts)


def compute_sha256(data: bytes) -> str:
    """计算数据的 SHA256 哈希"""
    return hashlib.sha256(data).hexdigest()


def guess_extension(content_type: str, url: str = "") -> str:
    """
    根据 Content-Type 或 URL 猜测文件扩展名
    """
    # 先尝试从 URL 获取
    if url:
        parsed = urlparse(url)
        path = parsed.path
        if "." in path.split("/")[-1]:
            ext = path.rsplit(".", 1)[-1].lower()
            # 过滤掉不合理的扩展名
            if len(ext) <= 10 and ext.isalnum():
                return f".{ext}"

    # 从 Content-Type 映射
    ct_map = {
        "text/html": ".html",
        "text/css": ".css",
        "text/javascript": ".js",
        "application/javascript": ".js",
        "application/x-javascript": ".js",
        "text/plain": ".txt",
        "application/json": ".json",
        "application/xml": ".xml",
        "text/xml": ".xml",
        "image/png": ".png",
        "image/jpeg": ".jpg",
        "image/jpg": ".jpg",
        "image/gif": ".gif",
        "image/webp": ".webp",
        "image/svg+xml": ".svg",
        "image/x-icon": ".ico",
        "image/vnd.microsoft.icon": ".ico",
        "font/woff": ".woff",
        "font/woff2": ".woff2",
        "application/font-woff": ".woff",
        "application/font-woff2": ".woff2",
        "font/ttf": ".ttf",
        "font/otf": ".otf",
        "application/x-font-ttf": ".ttf",
        "application/vnd.ms-fontobject": ".eot",
        "video/mp4": ".mp4",
        "video/webm": ".webm",
        "audio/mpeg": ".mp3",
        "audio/ogg": ".ogg",
        "application/pdf": ".pdf",
        "application/wasm": ".wasm",
    }

    if content_type:
        # 去掉 charset 等参数
        ct = content_type.split(";")[0].strip().lower()
        if ct in ct_map:
            return ct_map[ct]

    return ""


def parse_srcset(srcset: str) -> list[str]:
    """
    解析 srcset 属性，提取所有 URL
    格式: "url1 1x, url2 2x" 或 "url1 300w, url2 600w"
    """
    urls = []
    if not srcset:
        return urls

    for entry in srcset.split(","):
        entry = entry.strip()
        if not entry:
            continue
        # srcset 格式：URL [descriptor]
        parts = entry.split()
        if parts:
            url = parts[0].strip()
            if url and not should_skip_url(url):
                urls.append(url)

    return urls


def make_relative_path(from_file: str, to_file: str) -> str:
    """
    计算从 from_file 到 to_file 的相对路径
    两个路径都是相对于输出根目录的
    """
    from pathlib import PurePosixPath

    from_parts = PurePosixPath(from_file).parent.parts
    to_parts = PurePosixPath(to_file).parts

    # 找到公共前缀
    common_len = 0
    for a, b in zip(from_parts, to_parts):
        if a == b:
            common_len += 1
        else:
            break

    # 向上走的层数
    up_count = len(from_parts) - common_len
    # 向下走的路径
    down_parts = to_parts[common_len:]

    rel_parts = [".."] * up_count + list(down_parts)
    return "/".join(rel_parts) if rel_parts else to_parts[-1]
