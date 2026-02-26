"""
站点递归抓取器：
- 同 host BFS 递归抓取
- 登录墙检测 + 人工认证暂停
- 会话缓存（加密）
- 页面链接本地重写与落盘
"""

from __future__ import annotations

import json
from collections import deque
from pathlib import Path
from urllib.parse import urlparse

from rich.console import Console

from .downloader import Downloader
from ..parser import Parser, ParseResult, parse_external_css, parse_external_js_assets
from ..interceptors import QRInterceptor, ReactInterceptor
from ..core.renderer import Renderer
from .sanitizer import sanitize, inject_runtime_resource_map
from ..session import SessionStore
from .storage import Storage
from ..utils import is_same_host, normalize_crawl_url, url_to_local_page_path

console = Console()


class SiteCrawler:
    """全站递归抓取协调器"""

    def __init__(
        self,
        start_url: str,
        storage: Storage,
        renderer: Renderer,
        concurrency: int = 20,
        timeout: int = 30,
        delay: float = 0.1,
        max_pages: int = 5000,
        keep_js: bool = False,
        verbose: bool = False,
        enable_qr_intercept: bool = True,
        enable_react_intercept: bool = True,
        auth_mode: str = "manual-pause",
        session_cache: bool = True,
        session_file: str | None = None,
        headful_auth: bool = True,
    ):
        self.start_url = normalize_crawl_url(start_url, start_url) or start_url
        self.storage = storage
        self.renderer = renderer
        self.concurrency = concurrency
        self.timeout = timeout
        self.delay = delay
        self.max_pages = max_pages
        self.keep_js = keep_js
        self.verbose = verbose
        self.enable_qr_intercept = enable_qr_intercept
        self.enable_react_intercept = enable_react_intercept
        self.auth_mode = auth_mode
        self.session_cache = session_cache
        self.session_file = session_file
        self.headful_auth = headful_auth

        self.start_host = urlparse(self.start_url).netloc
        self.session_store = SessionStore()

        self.queue: deque[str] = deque([self.start_url])
        self.queued: set[str] = {self.start_url}
        self.visited: set[str] = set()
        self.failed: dict[str, str] = {}
        self.url_to_local_page: dict[str, str] = {
            self.start_url: url_to_local_page_path(self.start_url, self.start_host)
        }
        self.auth_pauses = 0
        self.tech_stack_cache: dict[str, dict] = {}

        self.storage_state: dict | None = None
        self.downloader = Downloader(
            concurrency=self.concurrency,
            timeout=self.timeout,
            delay=self.delay,
            referer=self.start_url,
        )

    async def run(self) -> Path:
        """执行站点递归抓取"""
        console.print(
            f"[bold yellow]━━━ 站点递归抓取模式（同 host: {self.start_host}） ━━━[/]"
        )
        self.storage_state = self._load_storage_state()

        while self.queue and len(self.visited) < self.max_pages:
            current_url = self.queue.popleft()
            self.queued.discard(current_url)

            if self._skip_page(current_url):
                continue

            current_local_path = self._ensure_local_page_path(current_url)
            self._print_page_header(current_url)

            try:
                status, info = await self._process_page(current_url, current_local_path)
                if status == "skip":
                    self.failed[current_url] = info
                elif self.verbose:
                    console.print(
                        f"[dim]  ↳ 页面链接: +{info} | 队列: {len(self.queue)}[/]"
                    )
            except Exception as e:
                self.failed[current_url] = str(e)
                console.print(f"[red]  ✗ 页面抓取失败: {e}[/]")
            finally:
                self.visited.add(current_url)

        report = self._build_report()
        self.storage.save_text(
            json.dumps(report, ensure_ascii=False, indent=2),
            "crawl_report.json",
        )
        console.print("[green]  ✓ 已生成 crawl_report.json[/]")
        self.storage.print_tree()
        return self.storage.get_output_path()

    def _skip_page(self, url: str) -> bool:
        """判断 URL 是否应在当前轮次跳过"""
        if url in self.visited:
            return True
        if not is_same_host(url, self.start_host):
            return True
        return False

    def _ensure_local_page_path(self, url: str) -> str:
        """确保 URL 已映射本地 HTML 路径"""
        return self.url_to_local_page.setdefault(
            url,
            url_to_local_page_path(url, self.start_host),
        )

    def _print_page_header(self, current_url: str) -> None:
        console.print(
            f"\n[bold cyan]🌐 页面 {len(self.visited)+1}/{self.max_pages}: {current_url}[/]"
        )

    async def _process_page(
        self,
        current_url: str,
        current_local_path: str,
    ) -> tuple[str, str | int]:
        """处理单个页面并返回 (status, info)"""
        render_result, skip_reason = await self._render_with_auth(current_url)
        if not render_result:
            return "skip", skip_reason or "登录墙，已按策略跳过"

        base_url = render_result.final_url or current_url
        clean_html = self._sanitize_rendered_html(current_url, render_result)
        parse_result = self._parse_page(
            clean_html=clean_html,
            base_url=base_url,
            current_local_path=current_local_path,
            intercepted_urls=render_result.resource_urls,
        )

        download_results = await self._download_page_resources(
            parse_result=parse_result,
            render_result=render_result,
            base_url=base_url,
        )
        self._sync_resource_map_with_download_results(
            parse_result.resource_map, download_results
        )
        await self._deep_parse_css(parse_result, base_url)
        await self._deep_parse_js(parse_result, base_url)

        final_html = self._fix_dedup_paths(
            parse_result.html,
            download_results,
            parse_result.resource_map,
        )
        final_html = inject_runtime_resource_map(
            final_html,
            original_url=base_url,
            resource_map=parse_result.resource_map,
            response_cache=render_result.response_cache,
            response_content_types=render_result.response_content_types,
        )
        self.storage.save_html(final_html, filename=current_local_path)

        discovered_links = set(parse_result.page_links) | set(render_result.page_links)
        self._enqueue_links(discovered_links, base_url)
        
        if render_result.tech_stack:
            self.tech_stack_cache[current_url] = render_result.tech_stack
        
        return "ok", len(discovered_links)

    async def _render_with_auth(self, current_url: str):
        """渲染页面并处理登录墙策略"""
        render_result = await self.renderer.render(
            current_url,
            storage_state=self.storage_state,
            headless=True,
        )
        if not render_result.is_login_page:
            return render_result, ""

        action = await self._handle_auth(current_url, render_result)
        if action == "skip":
            return None, "登录墙，已按策略跳过"

        render_result = await self.renderer.render(
            current_url,
            storage_state=self.storage_state,
            headless=True,
        )
        if render_result.is_login_page:
            return None, "登录后仍处于登录页"
        return render_result, ""

    def _sanitize_rendered_html(self, current_url: str, render_result) -> str:
        """净化 HTML 并注入兼容脚本"""
        qr_bridge_script, menu_script = self._build_injected_scripts(
            current_url=current_url,
            render_result=render_result,
        )
        return sanitize(
            render_result.html,
            original_url=render_result.final_url or current_url,
            keep_js=self.keep_js,
            qr_bridge_script=qr_bridge_script,
            menu_script=menu_script,
        )

    def _build_injected_scripts(self, current_url: str, render_result) -> tuple[str, str]:
        """根据渲染结果构造可选注入脚本"""
        qr_bridge_script = ""
        if render_result.qr_data and self.enable_qr_intercept:
            parsed = urlparse(render_result.final_url or current_url)
            original_domain = f"{parsed.scheme}://{parsed.netloc}"
            qr_bridge_script = QRInterceptor().generate_qr_bridge_script(original_domain)

        menu_script = ""
        if render_result.menu_css and self.enable_react_intercept:
            menu_script = ReactInterceptor().generate_menu_preservation_script()
        return qr_bridge_script, menu_script

    def _parse_page(
        self,
        clean_html: str,
        base_url: str,
        current_local_path: str,
        intercepted_urls: set[str],
    ) -> ParseResult:
        parser = Parser(
            base_url=base_url,
            intercepted_urls=intercepted_urls,
            page_link_mode="local",
        )
        parse_result = parser.parse(
            clean_html,
            current_page_local_path=current_local_path,
        )
        return parse_result

    async def _download_page_resources(
        self,
        parse_result: ParseResult,
        render_result,
        base_url: str,
    ) -> dict:
        """下载页面及其主资源"""
        self.downloader.cookies = render_result.cookies
        self.downloader.referer = base_url
        self.downloader.response_cache = render_result.response_cache
        return await self.downloader.download_all(
            parse_result.resource_map,
            Path(self.storage.output_dir),
        )

    def _enqueue_links(self, discovered_links: set[str], base_url: str) -> None:
        """将页面发现的新链接加入 BFS 队列"""
        for link in discovered_links:
            normalized = normalize_crawl_url(link, base_url)
            if not normalized or not is_same_host(normalized, self.start_host):
                continue
            if normalized in self.visited or normalized in self.queued:
                continue

            self.url_to_local_page.setdefault(
                normalized,
                url_to_local_page_path(normalized, self.start_host),
            )
            self.queue.append(normalized)
            self.queued.add(normalized)

    async def _handle_auth(self, current_url: str, render_result) -> str:
        """处理登录墙，返回 skip/retry"""
        if self.auth_mode == "skip":
            console.print("[yellow]  ⚠ 检测到登录墙，按 --auth-mode=skip 跳过[/]")
            return "skip"

        if self.auth_mode == "import-session":
            console.print("[yellow]  ⚠ 已导入会话但仍需登录，按策略跳过[/]")
            return "skip"

        # manual-pause
        if not self.headful_auth:
            console.print("[yellow]  ⚠ 未启用 headful 认证，无法人工登录，已跳过[/]")
            return "skip"

        self.auth_pauses += 1
        console.print(
            "[bold yellow]⏸ 检测到登录墙，已暂停抓取。请在弹出的浏览器中完成登录。[/]"
        )
        self.storage_state = await self.renderer.manual_auth(
            current_url,
            storage_state=self.storage_state,
            prompt="登录/扫码完成后按回车继续...",
        )

        if self.session_cache and self.storage_state:
            self._save_storage_state(self.storage_state)

        # 二次检查：若当前渲染已明确 401/403，提示并重试一次
        if render_result.status_code in (401, 403):
            console.print("[dim]  ↳ 已完成人工认证，正在重新验证页面访问...[/]")
        return "retry"

    def _load_storage_state(self) -> dict | None:
        """加载会话状态（import-session 或 encrypted cache）"""
        if self.auth_mode == "import-session":
            if not self.session_file:
                console.print("[yellow]⚠ --auth-mode=import-session 但未提供 --session-file[/]")
                return None
            try:
                data = json.loads(Path(self.session_file).read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    console.print(f"[dim]📥 已导入会话文件: {self.session_file}[/]")
                    return data
            except Exception as e:
                console.print(f"[yellow]⚠ 导入会话失败: {e}[/]")
            return None

        if not self.session_cache:
            return None

        state = self.session_store.load(self.start_host, custom_path=self.session_file)
        if state:
            console.print("[dim]📥 已加载加密会话缓存[/]")
        return state

    def _save_storage_state(self, state: dict) -> None:
        """保存会话状态（加密缓存）"""
        self.session_store.save(self.start_host, state, custom_path=self.session_file)

    async def _deep_parse_css(self, parse_result: ParseResult, base_url: str) -> None:
        """
        深度解析已下载的 CSS 文件，提取并下载其中的子资源（字体、图片等）
        """
        base_domain = urlparse(base_url).netloc
        css_urls = set(parse_result.css_sub_resources.keys())
        processed_css = set()
        iteration = 0
        max_iterations = 5

        while css_urls - processed_css and iteration < max_iterations:
            iteration += 1
            new_css_urls = set()

            for css_url in css_urls - processed_css:
                processed_css.add(css_url)
                local_path = parse_result.resource_map.get(css_url) or parse_result.css_sub_resources.get(css_url)
                if not local_path:
                    continue

                css_file = Path(self.storage.output_dir) / local_path
                if not css_file.exists():
                    continue

                try:
                    css_text = css_file.read_text(encoding="utf-8", errors="replace")
                except Exception:
                    continue

                _, new_resources, sub_css = parse_external_css(
                    css_text,
                    css_url,
                    parse_result.resource_map,
                    base_domain,
                    current_css_local_path=local_path,
                )

                if new_resources:
                    if self.verbose:
                        console.print(
                            f"[dim]  🔗 CSS 子资源: {css_url} → {len(new_resources)} 个新资源[/]"
                        )
                    css_download_results = await self.downloader.download_all(
                        new_resources, Path(self.storage.output_dir)
                    )
                    self._sync_resource_map_with_download_results(
                        parse_result.resource_map, css_download_results
                    )

                rewritten_css, _, _ = parse_external_css(
                    css_text,
                    css_url,
                    parse_result.resource_map,
                    base_domain,
                    current_css_local_path=local_path,
                )

                self.storage.save_text(rewritten_css, local_path)
                new_css_urls |= sub_css

            css_urls = new_css_urls

    async def _deep_parse_js(self, parse_result: ParseResult, base_url: str) -> None:
        """
        深度解析已下载 JS 文件，补抓硬编码静态资源（图片/字体/媒体）。
        """
        base_domain = urlparse(base_url).netloc
        pending_js_urls = {
            url
            for url, local_path in parse_result.resource_map.items()
            if isinstance(local_path, str) and local_path.lower().endswith(".js")
        }
        processed_js_urls = set()

        while pending_js_urls - processed_js_urls:
            current_batch = list(pending_js_urls - processed_js_urls)
            for js_url in current_batch:
                processed_js_urls.add(js_url)
                local_path = parse_result.resource_map.get(js_url)
                if not local_path:
                    continue

                js_file = Path(self.storage.output_dir) / local_path
                if not js_file.exists():
                    continue

                try:
                    js_text = js_file.read_text(encoding="utf-8", errors="replace")
                except Exception:
                    continue

                new_resources = parse_external_js_assets(
                    js_text,
                    js_url,
                    parse_result.resource_map,
                    base_domain,
                )
                if not new_resources:
                    continue

                if self.verbose:
                    console.print(
                        f"[dim]  🔗 JS 子资源: {js_url} → {len(new_resources)} 个新资源[/]"
                    )
                js_download_results = await self.downloader.download_all(
                    new_resources, Path(self.storage.output_dir)
                )
                self._sync_resource_map_with_download_results(
                    parse_result.resource_map, js_download_results
                )

            pending_js_urls = {
                url
                for url, local_path in parse_result.resource_map.items()
                if isinstance(local_path, str) and local_path.lower().endswith(".js")
            }

    def _fix_dedup_paths(
        self,
        html: str,
        download_results: dict,
        resource_map: dict[str, str],
    ) -> str:
        """修复去重导致的路径变化"""
        for url, result in download_results.items():
            if result.success and result.local_path != resource_map.get(url):
                old = f"./{resource_map.get(url, '')}"
                new = f"./{result.local_path}"
                if old and new and old != new:
                    html = html.replace(old, new)
        return html

    def _build_report(self) -> dict:
        aggregated_tech: dict[str, dict] = {}
        for url, tech_data in self.tech_stack_cache.items():
            for tech in tech_data.get("technologies", []):
                name = tech.get("name", "")
                if name and name not in aggregated_tech:
                    aggregated_tech[name] = tech
        
        return {
            "start_url": self.start_url,
            "host": self.start_host,
            "pages_crawled": len(self.visited),
            "pages_failed": len(self.failed),
            "failed_urls": self.failed,
            "queued_remaining": len(self.queue),
            "max_pages": self.max_pages,
            "auth_mode": self.auth_mode,
            "auth_pauses": self.auth_pauses,
            "session_cache": self.session_cache,
            "resource_stats": {
                "downloaded": self.downloader.total_downloaded,
                "deduplicated": self.downloader.total_skipped,
                "failed": self.downloader.total_failed,
                "bytes": self.downloader.total_bytes,
            },
            "tech_stack": {
                "technologies": list(aggregated_tech.values()),
                "is_spa": any(t.get("is_spa", False) for t in self.tech_stack_cache.values()),
                "is_ssr": any(t.get("is_ssr", False) for t in self.tech_stack_cache.values()),
                "has_animation": any(t.get("has_animation", False) for t in self.tech_stack_cache.values()),
            },
        }

    @staticmethod
    def _sync_resource_map_with_download_results(
        resource_map: dict[str, str],
        download_results: dict,
    ) -> None:
        """将下载去重后的真实落盘路径回写到资源映射表"""
        for url, result in download_results.items():
            if getattr(result, "success", False) and getattr(result, "local_path", ""):
                resource_map[url] = result.local_path
            else:
                resource_map.pop(url, None)
