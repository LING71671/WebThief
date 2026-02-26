"""
高并发下载与去重引擎：
- aiohttp 异步并发下载
- SHA256 哈希去重
- User-Agent 伪装 + Referer 设置
- 指数退避重试
- rich 进度条
- 性能优化器集成（动态并发调整）
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import TYPE_CHECKING, Any

from rich.console import Console
from rich.progress import (
    Progress,
    SpinnerColumn,
    BarColumn,
    TextColumn,
    DownloadColumn,
    TransferSpeedColumn,
    TimeRemainingColumn,
)

from ..config import DEFAULT_CONCURRENCY, DEFAULT_TIMEOUT, DEFAULT_RETRIES, DEFAULT_DELAY, get_random_ua
from ..utils import compute_sha256, guess_extension

if TYPE_CHECKING:
    from ..performance import PerformanceOptimizer
    import aiohttp

console = Console()


class DownloadResult:
    """单个文件的下载结果"""
    __slots__ = ("url", "local_path", "success", "content", "content_type", "sha256", "error")

    def __init__(self, url: str, local_path: str):
        self.url = url
        self.local_path = local_path
        self.success: bool = False
        self.content: bytes = b""
        self.content_type: str = ""
        self.sha256: str = ""
        self.error: str = ""


class Downloader:
    """
    异步并发下载引擎
    负责：并发下载 → 哈希去重 → 重试 → 进度报告
    """

    def __init__(
        self,
        concurrency: int = DEFAULT_CONCURRENCY,
        timeout: int = DEFAULT_TIMEOUT,
        retries: int = DEFAULT_RETRIES,
        delay: float = DEFAULT_DELAY,
        cookies: list[dict] | None = None,
        referer: str = "",
        response_cache: dict[str, bytes] | None = None,
        # 新增参数
        performance_optimizer: "PerformanceOptimizer | None" = None,
    ):
        self.concurrency = concurrency
        self.timeout = timeout
        self.retries = retries
        self.delay = delay
        self.cookies = cookies or []
        self.referer = referer
        self.response_cache = response_cache or {}
        
        # 性能优化器
        self.performance_optimizer = performance_optimizer

        # 全局哈希去重表: SHA256 → 本地路径
        self.hash_map: dict[str, str] = {}
        # URL → 下载结果
        self.results: dict[str, DownloadResult] = {}
        # 统计
        self.total_downloaded = 0
        self.total_skipped = 0
        self.total_failed = 0
        self.total_bytes = 0
        
        # 动态并发控制
        self._current_concurrency = concurrency
        self._adjustment_counter = 0

    async def download_all(
        self,
        resource_map: dict[str, str],
        output_dir: Path,
    ) -> dict[str, DownloadResult]:
        """
        并发下载所有资源

        Args:
            resource_map: {原始URL: 本地相对路径} 映射表
            output_dir: 输出根目录

        Returns:
            {URL: DownloadResult} 结果字典
        """
        if not resource_map:
            return {}

        import aiohttp

        total = len(resource_map)

        # 获取最优并发数（如果启用了性能优化器）
        if self.performance_optimizer:
            optimal_concurrency = self.performance_optimizer.get_optimal_concurrency()
            self._current_concurrency = optimal_concurrency
        else:
            self._current_concurrency = self.concurrency

        console.print(f"\n[bold blue]📥 开始下载 {total} 个资源（并发: {self._current_concurrency}）[/]")

        # 构建 cookie jar
        jar = aiohttp.CookieJar(unsafe=True)

        # 构建 connector（使用动态并发数）
        connector = aiohttp.TCPConnector(
            limit=self._current_concurrency,
            limit_per_host=10,
            ttl_dns_cache=300,
            ssl=False,  # 忽略 SSL 错误
        )

        # 准备 cookies dict
        cookie_dict = {}
        for c in self.cookies:
            name = c.get("name", "")
            value = c.get("value", "")
            if name and value:
                cookie_dict[name] = value

        async with aiohttp.ClientSession(
            connector=connector,
            cookie_jar=jar,
            cookies=cookie_dict,
            timeout=aiohttp.ClientTimeout(total=self.timeout * 2, sock_read=self.timeout),
        ) as session:
            semaphore = asyncio.Semaphore(self._current_concurrency)

            with Progress(
                SpinnerColumn(),
                TextColumn("[bold blue]{task.description}"),
                BarColumn(bar_width=40),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                DownloadColumn(),
                TransferSpeedColumn(),
                TimeRemainingColumn(),
                console=console,
            ) as progress:
                task = progress.add_task("下载资源", total=total)

                tasks = []
                for url, local_path in resource_map.items():
                    t = asyncio.create_task(
                        self._download_one(
                            session, semaphore, url, local_path, output_dir, progress, task
                        )
                    )
                    tasks.append(t)

                await asyncio.gather(*tasks) 

        # 打印统计
        console.print(f"\n[bold green]  ✓ 下载完成: {self.total_downloaded} 个文件[/]")
        if self.total_skipped:
            console.print(f"[cyan]  ⏭ 去重跳过: {self.total_skipped} 个[/]")
        if self.total_failed:
            console.print(f"[red]  ✗ 下载失败: {self.total_failed} 个[/]")
        console.print(f"[cyan]  📦 总大小: {self._format_size(self.total_bytes)}[/]")

        return self.results

    async def _download_one(
        self,
        session: aiohttp.ClientSession,
        semaphore: asyncio.Semaphore,
        url: str,
        local_path: str,
        output_dir: Path,
        progress,
        task,
    ) -> None:
        """下载单个文件（缓存优先 + 重试）"""
        result = DownloadResult(url, local_path)
        
        # 记录开始时间（用于性能监控）
        start_time = None
        if self.performance_optimizer:
            import time
            start_time = time.monotonic()

        async with semaphore:
            handled_by_cache = self._try_use_cached_response(
                url=url,
                local_path=local_path,
                output_dir=output_dir,
                result=result,
            )
            if not handled_by_cache:
                await self._download_with_retries(
                    session=session,
                    url=url,
                    local_path=local_path,
                    output_dir=output_dir,
                    result=result,
                )

            # 请求间微延迟（反检测）
            if self.delay > 0:
                await asyncio.sleep(self.delay * 0.1)
        
        # 报告性能指标
        if self.performance_optimizer and start_time:
            import time
            elapsed = time.monotonic() - start_time
            self.performance_optimizer.record_download_metrics(
                url=url,
                success=result.success,
                elapsed=elapsed,
                size=len(result.content) if result.content else 0,
            )
            
            # 定期调整并发数
            self._adjustment_counter += 1
            if self._adjustment_counter % 50 == 0:
                self._adjust_concurrency_dynamically(semaphore)

        self.results[url] = result
        progress.advance(task)
    
    def _adjust_concurrency_dynamically(self, semaphore: asyncio.Semaphore) -> None:
        """动态调整并发数"""
        if not self.performance_optimizer:
            return
        
        new_concurrency = self.performance_optimizer.get_optimal_concurrency()
        if new_concurrency != self._current_concurrency:
            old_concurrency = self._current_concurrency
            self._current_concurrency = new_concurrency
            console.print(
                f"[dim]  ⚡ 并发数调整: {old_concurrency} → {new_concurrency}[/]"
            )

    def _try_use_cached_response(
        self,
        url: str,
        local_path: str,
        output_dir: Path,
        result: DownloadResult,
    ) -> bool:
        """缓存命中则直接写入并返回 True"""
        content = self.response_cache.get(url)
        if content is None:
            return False

        sha = compute_sha256(content)
        if self._apply_dedup_if_exists(result, sha):
            return True

        file_path = output_dir / local_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 如果是 JS 文件，替换动态导入
        if local_path.lower().endswith('.js'):
            content = self._patch_js_dynamic_import(content)
        
        file_path.write_bytes(content)

        self.hash_map[sha] = local_path
        result.success = True
        result.content = content
        result.sha256 = sha
        self.total_downloaded += 1
        self.total_bytes += len(content)
        return True

    async def _download_with_retries(
        self,
        session: aiohttp.ClientSession,
        url: str,
        local_path: str,
        output_dir: Path,
        result: DownloadResult,
    ) -> None:
        """按重试策略下载 URL"""
        for attempt in range(1, self.retries + 1):
            try:
                done = await self._download_once(
                    session=session,
                    url=url,
                    local_path=local_path,
                    output_dir=output_dir,
                    result=result,
                    attempt=attempt,
                )
                if done:
                    return
            except asyncio.TimeoutError:
                self._record_attempt_error(result, "超时", attempt)
            except aiohttp.ClientError as e:
                self._record_attempt_error(result, str(e), attempt)
            except Exception as e:
                self._record_attempt_error(result, str(e), attempt)

            if attempt < self.retries:
                await asyncio.sleep(self.delay * (2 ** (attempt - 1)))

    async def _download_once(
        self,
        session: aiohttp.ClientSession,
        url: str,
        local_path: str,
        output_dir: Path,
        result: DownloadResult,
        attempt: int,
    ) -> bool:
        """执行单次 HTTP 请求，返回是否结束重试"""
        headers = self._build_headers()
        async with session.get(url, headers=headers, allow_redirects=True) as resp:
            if resp.status == 200:
                content = await resp.read()
                content_type = resp.headers.get("Content-Type", "")
                self._save_downloaded_content(
                    url=url,
                    local_path=local_path,
                    output_dir=output_dir,
                    content=content,
                    content_type=content_type,
                    result=result,
                )
                return True

            return self._handle_non_200_status(resp.status, result, attempt)

    def _build_headers(self) -> dict[str, str]:
        headers = {
            "User-Agent": get_random_ua(),
            "Accept": "*/*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate",
        }
        if self.referer:
            headers["Referer"] = self.referer
        return headers

    def _save_downloaded_content(
        self,
        url: str,
        local_path: str,
        output_dir: Path,
        content: bytes,
        content_type: str,
        result: DownloadResult,
    ) -> None:
        sha = compute_sha256(content)
        if self._apply_dedup_if_exists(result, sha, content_type):
            return

        final_local_path = local_path
        file_path = output_dir / final_local_path
        if not file_path.suffix:
            ext = guess_extension(content_type, url)
            if ext:
                final_local_path = f"{local_path}{ext}"
                file_path = output_dir / final_local_path

        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 如果是 JS 文件，替换动态导入
        if final_local_path.lower().endswith('.js'):
            content = self._patch_js_dynamic_import(content)
        
        file_path.write_bytes(content)

        self.hash_map[sha] = final_local_path
        result.local_path = final_local_path
        result.success = True
        result.content = content
        result.content_type = content_type
        result.sha256 = sha
        self.total_downloaded += 1
        self.total_bytes += len(content)

    def _patch_js_dynamic_import(self, content: bytes) -> bytes:
        """将 JS 中的 import() 替换为 __webthief_import__()"""
        try:
            text = content.decode('utf-8', errors='replace')
            # 替换动态导入：import("xxx") -> __webthief_import__("xxx")
            import re
            patched = re.sub(
                r'\bimport\s*\(\s*(["\'])([^"\']+\.js(?:\?[^\'"\s]*)?)\1\s*\)',
                r'__webthief_import__(\1\2\1)',
                text
            )
            return patched.encode('utf-8')
        except Exception:
            return content

    def _apply_dedup_if_exists(
        self,
        result: DownloadResult,
        sha: str,
        content_type: str = "",
    ) -> bool:
        """若哈希已存在，复用本地路径并返回 True"""
        local_path = self.hash_map.get(sha)
        if not local_path:
            return False

        result.success = True
        result.local_path = local_path
        result.sha256 = sha
        result.content_type = content_type
        self.total_skipped += 1
        return True

    def _handle_non_200_status(
        self,
        status: int,
        result: DownloadResult,
        attempt: int,
    ) -> bool:
        """处理非 200 响应，返回是否结束重试"""
        if status in (301, 302, 307, 308):
            # allow_redirects=True 场景下通常不会落到这里，保留兼容
            if attempt == self.retries:
                result.error = f"HTTP {status}"
                self.total_failed += 1
                return True
            return False

        if status == 404:
            result.error = "HTTP 404 Not Found"
            self.total_failed += 1
            return True

        result.error = f"HTTP {status}"
        if attempt == self.retries:
            self.total_failed += 1
            return True
        return False

    def _record_attempt_error(
        self,
        result: DownloadResult,
        error: str,
        attempt: int,
    ) -> None:
        result.error = error
        if attempt == self.retries:
            self.total_failed += 1

    @staticmethod
    def _format_size(size_bytes: int) -> str:
        """格式化文件大小"""
        for unit in ("B", "KB", "MB", "GB"):
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} TB"
