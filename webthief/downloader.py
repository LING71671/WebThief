"""
高并发下载与去重引擎：
- aiohttp 异步并发下载
- SHA256 哈希去重
- User-Agent 伪装 + Referer 设置
- 指数退避重试
- rich 进度条
"""

from __future__ import annotations

import asyncio
import time
from pathlib import Path
from urllib.parse import urlparse

import aiohttp
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

from .config import DEFAULT_CONCURRENCY, DEFAULT_TIMEOUT, DEFAULT_RETRIES, DEFAULT_DELAY, get_random_ua
from .utils import compute_sha256, guess_extension

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
    ):
        self.concurrency = concurrency
        self.timeout = timeout
        self.retries = retries
        self.delay = delay
        self.cookies = cookies or []
        self.referer = referer
        self.response_cache = response_cache or {}

        # 全局哈希去重表: SHA256 → 本地路径
        self.hash_map: dict[str, str] = {}
        # URL → 下载结果
        self.results: dict[str, DownloadResult] = {}
        # 统计
        self.total_downloaded = 0
        self.total_skipped = 0
        self.total_failed = 0
        self.total_bytes = 0

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

        total = len(resource_map)
        console.print(f"\n[bold blue]📥 开始下载 {total} 个资源（并发: {self.concurrency}）[/]")

        # 构建 cookie jar
        jar = aiohttp.CookieJar(unsafe=True)

        # 构建 connector
        connector = aiohttp.TCPConnector(
            limit=self.concurrency,
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
            semaphore = asyncio.Semaphore(self.concurrency)

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

        async with semaphore:
            # 【改造四】缓存优先：检查渲染阶段是否已缓存此资源
            if url in self.response_cache:
                content = self.response_cache[url]
                sha = compute_sha256(content)

                if sha in self.hash_map:
                    result.success = True
                    result.local_path = self.hash_map[sha]
                    result.sha256 = sha
                    self.total_skipped += 1
                else:
                    file_path = output_dir / local_path
                    file_path.parent.mkdir(parents=True, exist_ok=True)
                    file_path.write_bytes(content)
                    self.hash_map[sha] = local_path
                    result.success = True
                    result.content = content
                    result.sha256 = sha
                    self.total_downloaded += 1
                    self.total_bytes += len(content)

                self.results[url] = result
                progress.advance(task)
                return

            # 缓存未命中，走网络下载
            for attempt in range(1, self.retries + 1):
                try:
                    headers = {
                        "User-Agent": get_random_ua(),
                        "Accept": "*/*",
                        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                        "Accept-Encoding": "gzip, deflate",
                    }
                    if self.referer:
                        headers["Referer"] = self.referer

                    async with session.get(url, headers=headers, allow_redirects=True) as resp:
                        if resp.status == 200:
                            content = await resp.read()
                            content_type = resp.headers.get("Content-Type", "")

                            # SHA256 去重
                            sha = compute_sha256(content)
                            if sha in self.hash_map:
                                # 已经下载过相同内容
                                result.success = True
                                result.local_path = self.hash_map[sha]
                                result.sha256 = sha
                                result.content_type = content_type
                                self.total_skipped += 1
                                break

                            # 检查并修复扩展名
                            file_path = output_dir / local_path
                            if not file_path.suffix:
                                ext = guess_extension(content_type, url)
                                if ext:
                                    local_path += ext
                                    file_path = output_dir / local_path
                                    result.local_path = local_path

                            # 保存文件
                            file_path.parent.mkdir(parents=True, exist_ok=True)
                            file_path.write_bytes(content)

                            # 注册哈希
                            self.hash_map[sha] = local_path

                            result.success = True
                            result.content = content
                            result.content_type = content_type
                            result.sha256 = sha
                            self.total_downloaded += 1
                            self.total_bytes += len(content)
                            break

                        elif resp.status in (301, 302, 307, 308):
                            # 重定向已由 allow_redirects 处理
                            pass
                        elif resp.status == 404:
                            result.error = f"HTTP 404 Not Found"
                            self.total_failed += 1
                            break
                        else:
                            result.error = f"HTTP {resp.status}"
                            if attempt == self.retries:
                                self.total_failed += 1

                except asyncio.TimeoutError:
                    result.error = "超时"
                    if attempt == self.retries:
                        self.total_failed += 1
                except aiohttp.ClientError as e:
                    result.error = str(e)
                    if attempt == self.retries:
                        self.total_failed += 1
                except Exception as e:
                    result.error = str(e)
                    if attempt == self.retries:
                        self.total_failed += 1

                # 指数退避
                if attempt < self.retries:
                    await asyncio.sleep(self.delay * (2 ** (attempt - 1)))

            # 请求间微延迟（反检测）
            if self.delay > 0:
                await asyncio.sleep(self.delay * 0.1)

        self.results[url] = result
        progress.advance(task)

    @staticmethod
    def _format_size(size_bytes: int) -> str:
        """格式化文件大小"""
        for unit in ("B", "KB", "MB", "GB"):
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} TB"
