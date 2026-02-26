"""
API 响应缓存模块

提供 API 响应的持久化缓存功能，支持：
- JSON 格式存储缓存数据
- 缓存过期管理
- 简单的 URL -> 响应映射
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from rich.console import Console

console = Console()


@dataclass
class CachedResponse:
    """缓存的 API 响应数据结构"""

    url: str
    method: str = "GET"
    status_code: int = 200
    headers: dict[str, str] = field(default_factory=dict)
    body: Any = None
    content_type: str = "application/json"
    created_at: float = field(default_factory=time.time)
    expires_at: Optional[float] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def is_expired(self) -> bool:
        """检查缓存是否已过期"""
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式"""
        return {
            "url": self.url,
            "method": self.method,
            "status_code": self.status_code,
            "headers": self.headers,
            "body": self.body,
            "content_type": self.content_type,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CachedResponse":
        """从字典创建实例"""
        return cls(
            url=data.get("url", ""),
            method=data.get("method", "GET"),
            status_code=data.get("status_code", 200),
            headers=data.get("headers", {}),
            body=data.get("body"),
            content_type=data.get("content_type", "application/json"),
            created_at=data.get("created_at", time.time()),
            expires_at=data.get("expires_at"),
            metadata=data.get("metadata", {}),
        )


class APICache:
    """
    API 响应缓存管理器

    功能特性：
    - 持久化存储到本地 JSON 文件
    - 支持缓存过期时间设置
    - URL 规范化处理
    - 简单的 URL -> 响应映射
    """

    DEFAULT_TTL = 86400  # 默认缓存 24 小时
    CACHE_FILE_NAME = "api_cache.json"

    # 追踪参数列表
    TRACKING_PARAMS = frozenset({
        "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
        "fbclid", "gclid", "msclkid", "_ga", "_gid", "ref", "source",
    })

    def __init__(
        self,
        cache_dir: str | Path,
        ttl: int = DEFAULT_TTL,
        normalize_query: bool = True,
        ignore_tracking_params: bool = True,
    ):
        """
        初始化缓存管理器

        Args:
            cache_dir: 缓存目录路径
            ttl: 缓存默认过期时间（秒）
            normalize_query: 是否规范化查询参数
            ignore_tracking_params: 是否忽略追踪参数
        """
        self.cache_dir = Path(cache_dir)
        self.ttl = ttl
        self.normalize_query = normalize_query
        self.ignore_tracking_params = ignore_tracking_params
        self._cache: dict[str, CachedResponse] = {}
        self._loaded = False

    def _ensure_cache_dir(self) -> None:
        """确保缓存目录存在"""
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_cache_file_path(self) -> Path:
        """获取缓存文件路径"""
        return self.cache_dir / self.CACHE_FILE_NAME

    def _normalize_url(self, url: str, method: str = "GET") -> str:
        """
        规范化 URL 作为缓存键

        - 去除 fragment
        - 排序查询参数
        - 移除追踪参数
        """
        if not url:
            return ""

        parsed = urlparse(url)

        # 处理查询参数
        if self.normalize_query and parsed.query:
            params = parse_qsl(parsed.query, keep_blank_values=True)
            # 过滤追踪参数
            if self.ignore_tracking_params:
                params = [
                    (key, value)
                    for key, value in params
                    if key.lower() not in self.TRACKING_PARAMS
                ]
            # 排序参数
            params.sort(key=lambda x: x[0].lower())
            query = urlencode(params, doseq=True)
        else:
            query = parsed.query

        # 重建 URL（不含 fragment）
        normalized = urlunparse(
            (
                parsed.scheme,
                parsed.netloc.lower(),
                parsed.path,
                parsed.params,
                query,
                "",  # 移除 fragment
            )
        )

        # 包含请求方法作为键的一部分
        return f"{method.upper()}:{normalized}"

    def _generate_cache_key(self, url: str, method: str = "GET", body: Any = None) -> str:
        """
        生成缓存键

        对于 POST 等带 body 的请求，将 body 也纳入键计算
        """
        base_key = self._normalize_url(url, method)

        if body is not None and method.upper() in ("POST", "PUT", "PATCH"):
            try:
                if isinstance(body, (dict, list)):
                    body_str = json.dumps(body, sort_keys=True)
                else:
                    body_str = str(body)
                body_hash = hashlib.md5(body_str.encode()).hexdigest()[:8]
                return f"{base_key}:{body_hash}"
            except Exception:
                pass

        return base_key

    def load(self) -> None:
        """从文件加载缓存"""
        if self._loaded:
            return

        cache_file = self._get_cache_file_path()
        if not cache_file.exists():
            self._loaded = True
            return

        try:
            with open(cache_file, "r", encoding="utf-8") as file_handle:
                data = json.load(file_handle)

            for key, item in data.items():
                try:
                    self._cache[key] = CachedResponse.from_dict(item)
                except Exception as error:
                    console.print(f"[yellow]  ⚠ 加载缓存项失败: {key}, {error}[/]")

            self._loaded = True
            console.print(f"[dim]  ✓ 已加载 {len(self._cache)} 个缓存响应[/]")
        except Exception as error:
            console.print(f"[yellow]  ⚠ 加载缓存文件失败: {error}[/]")
            self._loaded = True

    def save(self) -> None:
        """保存缓存到文件"""
        self._ensure_cache_dir()
        cache_file = self._get_cache_file_path()

        try:
            data = {key: item.to_dict() for key, item in self._cache.items()}
            with open(cache_file, "w", encoding="utf-8") as file_handle:
                json.dump(data, file_handle, ensure_ascii=False, indent=2)
            console.print(f"[dim]  ✓ 已保存 {len(self._cache)} 个缓存响应[/]")
        except Exception as error:
            console.print(f"[red]  ✗ 保存缓存文件失败: {error}[/]")

    def get(
        self,
        url: str,
        method: str = "GET",
        body: Any = None,
    ) -> Optional[CachedResponse]:
        """
        获取缓存的响应

        Args:
            url: 请求 URL
            method: HTTP 方法
            body: 请求体（用于 POST/PUT/PATCH）

        Returns:
            缓存的响应，如果不存在或已过期则返回 None
        """
        self.load()

        key = self._generate_cache_key(url, method, body)
        cached = self._cache.get(key)

        if cached is None:
            return None

        if cached.is_expired():
            del self._cache[key]
            return None

        return cached

    def set(
        self,
        url: str,
        response: Any,
        method: str = "GET",
        status_code: int = 200,
        headers: Optional[dict[str, str]] = None,
        content_type: str = "application/json",
        ttl: Optional[int] = None,
        metadata: Optional[dict[str, Any]] = None,
        body: Any = None,
    ) -> CachedResponse:
        """
        设置缓存响应

        Args:
            url: 请求 URL
            response: 响应内容
            method: HTTP 方法
            status_code: HTTP 状态码
            headers: 响应头
            content_type: 内容类型
            ttl: 过期时间（秒），None 表示使用默认值
            metadata: 额外元数据
            body: 请求体（用于生成缓存键）

        Returns:
            创建的缓存响应对象
        """
        self.load()

        key = self._generate_cache_key(url, method, body)
        now = time.time()
        expires_at = now + (ttl if ttl is not None else self.ttl)

        cached = CachedResponse(
            url=url,
            method=method.upper(),
            status_code=status_code,
            headers=headers or {},
            body=response,
            content_type=content_type,
            created_at=now,
            expires_at=expires_at,
            metadata=metadata or {},
        )

        self._cache[key] = cached
        return cached

    def delete(self, url: str, method: str = "GET", body: Any = None) -> bool:
        """
        删除指定的缓存

        Returns:
            是否成功删除
        """
        self.load()
        key = self._generate_cache_key(url, method, body)

        if key in self._cache:
            del self._cache[key]
            return True
        return False

    def clear(self) -> None:
        """清空所有缓存"""
        self._cache.clear()
        console.print("[dim]  ✓ 已清空缓存[/]")

    def clear_expired(self) -> int:
        """
        清理过期缓存

        Returns:
            清理的缓存数量
        """
        self.load()
        expired_keys = [key for key, value in self._cache.items() if value.is_expired()]

        for key in expired_keys:
            del self._cache[key]

        if expired_keys:
            console.print(f"[dim]  ✓ 已清理 {len(expired_keys)} 个过期缓存[/]")

        return len(expired_keys)

    def get_all_urls(self) -> list[str]:
        """获取所有缓存的 URL 列表"""
        self.load()
        return list(set(item.url for item in self._cache.values()))

    def get_stats(self) -> dict[str, Any]:
        """获取缓存统计信息"""
        self.load()

        total = len(self._cache)
        expired = sum(1 for item in self._cache.values() if item.is_expired())

        methods: dict[str, int] = {}
        content_types: dict[str, int] = {}

        for item in self._cache.values():
            method = item.method
            methods[method] = methods.get(method, 0) + 1

            content_type = item.content_type.split(";")[0].strip()
            content_types[content_type] = content_types.get(content_type, 0) + 1

        return {
            "total": total,
            "expired": expired,
            "active": total - expired,
            "methods": methods,
            "content_types": content_types,
        }

    def export_to_runtime_map(self) -> dict[str, dict[str, str]]:
        """
        导出为运行时兼容层使用的响应映射格式

        Returns:
            适合注入到 __WEBTHIEF_RESPONSE_MAP__ 的字典
        """
        self.load()

        result: dict[str, dict[str, str]] = {}

        for cached in self._cache.values():
            if cached.is_expired():
                continue

            # 生成多个候选键
            candidates = self._generate_lookup_candidates(cached.url)

            body_str = ""
            if cached.body is not None:
                if isinstance(cached.body, str):
                    body_str = cached.body
                else:
                    try:
                        body_str = json.dumps(cached.body, ensure_ascii=False)
                    except Exception:
                        body_str = str(cached.body)

            value = {
                "body": body_str,
                "contentType": cached.content_type,
                "statusCode": cached.status_code,
            }

            for candidate in candidates:
                if candidate:
                    result[candidate] = value

        return result

    def _generate_lookup_candidates(self, url: str) -> list[str]:
        """生成 URL 的多种查找候选"""
        candidates = []

        if not url:
            return candidates

        url = url.strip()
        candidates.append(url)

        # 去除 hash
        no_hash = url.split("#")[0]
        if no_hash != url:
            candidates.append(no_hash)

        # 去除 query
        no_query = no_hash.split("?")[0]
        if no_query != no_hash:
            candidates.append(no_query)

        try:
            parsed = urlparse(url)
            candidates.append(url)

            # 路径形式
            path = parsed.path or "/"
            candidates.append(path)

            if path.startswith("/"):
                rel_path = path[1:]
                candidates.append(rel_path)
                candidates.append("./" + rel_path)
        except Exception:
            pass

        return candidates

    def import_from_renderer_cache(
        self,
        response_cache: dict[str, bytes],
        response_content_types: dict[str, str],
    ) -> int:
        """
        从 Renderer 的响应缓存导入数据

        Args:
            response_cache: Renderer 捕获的响应体字典
            response_content_types: Renderer 捕获的内容类型字典

        Returns:
            导入的缓存数量
        """
        self.load()
        imported = 0

        for url, body in response_cache.items():
            if not body:
                continue

            content_type = response_content_types.get(url, "application/octet-stream")

            # 尝试解析为 JSON
            parsed_body: Any = body
            if "json" in content_type.lower():
                try:
                    parsed_body = json.loads(body.decode("utf-8"))
                except Exception:
                    parsed_body = body.decode("utf-8", errors="replace")
            elif content_type.startswith("text/"):
                try:
                    parsed_body = body.decode("utf-8")
                except Exception:
                    parsed_body = body.decode("utf-8", errors="replace")

            # 检查是否已存在
            existing = self.get(url)
            if existing is None:
                self.set(
                    url=url,
                    response=parsed_body,
                    content_type=content_type,
                )
                imported += 1

        if imported > 0:
            console.print(f"[dim]  ✓ 从渲染器缓存导入 {imported} 个响应[/]")

        return imported
