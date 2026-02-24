"""
五层流水线编排器：
串联 渲染 → 净化 → 解析重写 → 下载 → 存储
并在站点模式下协调 BFS 递归抓取
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from urllib.parse import urlparse

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from .downloader import Downloader
from .parser import ParseResult, Parser, parse_external_css
from .qr_interceptor import QRInterceptor
from .react_interceptor import ReactInterceptor
from .renderer import RenderResult, Renderer
from .sanitizer import sanitize
from .session_store import SessionStore
from .site_crawler import SiteCrawler
from .storage import Storage

console = Console()


class Orchestrator:
    """
    克隆流水线编排器

    流程：
    1. 渲染层 — Playwright 渲染页面，嗅探资源
    2. 净化层 — 清洗 CSP / Service Worker / 追踪器
    3. 解析重写层 — AST 级提取资源引用并重写路径
    4. 下载引擎 — 异步并发下载资源
    5. 存储层 — 保存 HTML 和资源到本地目录
    """

    def __init__(
        self,
        url: str,
        output_dir: str = "./webthief_output",
        concurrency: int = 20,
        timeout: int = 30,
        delay: float = 0.1,
        user_agent: str | None = None,
        extra_wait: int = 0,
        disable_js: bool = False,
        keep_js: bool = False,
        verbose: bool = False,
        enable_qr_intercept: bool = True,
        enable_react_intercept: bool = True,
        crawl_site: bool = True,
        max_pages: int = 5000,
        auth_mode: str = "manual-pause",
        session_cache: bool = True,
        session_file: str | None = None,
        headful_auth: bool = True,
    ):
        self.url = url
        self.output_dir = output_dir
        self.concurrency = concurrency
        self.timeout = timeout
        self.delay = delay
        self.user_agent = user_agent
        self.extra_wait = extra_wait
        self.disable_js = disable_js
        self.keep_js = keep_js
        self.verbose = verbose
        self.enable_qr_intercept = enable_qr_intercept
        self.enable_react_intercept = enable_react_intercept
        self.crawl_site = crawl_site
        self.max_pages = max_pages
        self.auth_mode = auth_mode
        self.session_cache = session_cache
        self.session_file = session_file
        self.headful_auth = headful_auth

    async def run(self) -> Path:
        """执行克隆流程"""
        start_time = time.time()
        self._print_banner()

        storage = Storage(self.output_dir)
        storage.initialize()

        renderer = Renderer(
            extra_wait=self.extra_wait,
            user_agent=self.user_agent,
            disable_js=self.disable_js,
            enable_qr_intercept=self.enable_qr_intercept,
            enable_react_intercept=self.enable_react_intercept,
        )

        if self.crawl_site:
            crawler = SiteCrawler(
                start_url=self.url,
                storage=storage,
                renderer=renderer,
                concurrency=self.concurrency,
                timeout=self.timeout,
                delay=self.delay,
                max_pages=self.max_pages,
                keep_js=self.keep_js,
                verbose=self.verbose,
                enable_qr_intercept=self.enable_qr_intercept,
                enable_react_intercept=self.enable_react_intercept,
                auth_mode=self.auth_mode,
                session_cache=self.session_cache,
                session_file=self.session_file,
                headful_auth=self.headful_auth,
            )
            output_path = await crawler.run()
            elapsed = time.time() - start_time
            self._print_site_summary(elapsed)
            return output_path

        output_path = await self._run_single_page(storage, renderer, start_time)
        return output_path

    async def _run_single_page(
        self,
        storage: Storage,
        renderer: Renderer,
        start_time: float,
    ) -> Path:
        """单页克隆流程（保留旧行为兼容）"""
        storage_state = self._load_storage_state()

        console.print("\n[bold yellow]━━━ 阶段 1/5: 渲染与资源嗅探 ━━━[/]")
        render_result = await renderer.render(
            self.url,
            storage_state=storage_state,
            headless=True,
        )

        if render_result.is_login_page:
            render_result = await self._handle_single_page_auth(renderer, render_result)

        console.print("\n[bold yellow]━━━ 阶段 2/5: HTML 净化 + JS 中和 ━━━[/]")
        clean_html = self._sanitize_html(render_result)
        console.print("[green]  ✓ HTML 净化 + 兼容层注入完成[/]")

        console.print("\n[bold yellow]━━━ 阶段 3/5: AST 解析与路径重写 ━━━[/]")
        base_url = render_result.final_url or self.url
        parser = Parser(
            base_url=base_url,
            intercepted_urls=render_result.resource_urls,
        )
        parse_result = parser.parse(clean_html, current_page_local_path="index.html")

        console.print("\n[bold yellow]━━━ 阶段 4/5: 高并发资源下载 ━━━[/]")
        downloader = Downloader(
            concurrency=self.concurrency,
            timeout=self.timeout,
            delay=self.delay,
            cookies=render_result.cookies,
            referer=base_url,
            response_cache=render_result.response_cache,
        )
        download_results = await downloader.download_all(
            parse_result.resource_map,
            Path(self.output_dir),
        )

        await self._deep_parse_css(parse_result, downloader, storage, base_url)

        console.print("\n[bold yellow]━━━ 阶段 5/5: 镜像存储 ━━━[/]")
        final_html = self._fix_dedup_paths(
            parse_result.html, download_results, parse_result.resource_map
        )
        storage.save_html(final_html, filename="index.html")
        storage.print_tree()

        elapsed = time.time() - start_time
        self._print_summary(elapsed, downloader, storage)
        return storage.get_output_path()

    async def _handle_single_page_auth(
        self,
        renderer: Renderer,
        render_result: RenderResult,
    ) -> RenderResult:
        """单页模式下的认证处理"""
        if self.auth_mode == "skip":
            console.print("[yellow]⚠ 检测到登录墙，按 --auth-mode=skip 继续输出当前页面[/]")
            return render_result

        if self.auth_mode == "import-session":
            console.print("[yellow]⚠ 导入会话后仍检测到登录墙，继续输出当前页面[/]")
            return render_result

        if not self.headful_auth:
            console.print("[yellow]⚠ 未启用 headful 认证，继续输出当前页面[/]")
            return render_result

        console.print("[bold yellow]⏸ 检测到登录墙，切换人工认证...[/]")
        state = await renderer.manual_auth(self.url, storage_state=self._load_storage_state())
        if state and self.session_cache:
            self._save_storage_state(state)

        return await renderer.render(
            self.url,
            storage_state=state,
            headless=True,
        )

    def _sanitize_html(self, render_result: RenderResult) -> str:
        qr_bridge_script = ""
        if render_result.qr_data and self.enable_qr_intercept:
            parsed = urlparse(render_result.final_url or self.url)
            original_domain = f"{parsed.scheme}://{parsed.netloc}"
            qr_bridge_script = QRInterceptor().generate_qr_bridge_script(original_domain)
            console.print("[cyan]  🔐 生成二维码桥接脚本[/]")

        menu_script = ""
        if render_result.menu_css and self.enable_react_intercept:
            menu_script = ReactInterceptor().generate_menu_preservation_script()
            console.print("[cyan]  ⚛️  生成菜单保留脚本[/]")

        js_mode = "保留" if self.keep_js else "中和"
        console.print(f"[magenta]🧹 清洗 CSP / SW / 追踪器 | JS 模式: {js_mode}[/]")
        return sanitize(
            render_result.html,
            original_url=render_result.final_url or self.url,
            keep_js=self.keep_js,
            qr_bridge_script=qr_bridge_script,
            menu_script=menu_script,
        )

    def _load_storage_state(self) -> dict | None:
        """加载会话状态"""
        host = urlparse(self.url).netloc
        if self.auth_mode == "import-session":
            if not self.session_file:
                return None
            try:
                data = json.loads(Path(self.session_file).read_text(encoding="utf-8"))
                return data if isinstance(data, dict) else None
            except Exception as e:
                console.print(f"[yellow]⚠ 导入会话失败: {e}[/]")
                return None

        if not self.session_cache:
            return None
        return SessionStore().load(host, custom_path=self.session_file)

    def _save_storage_state(self, state: dict) -> None:
        host = urlparse(self.url).netloc
        SessionStore().save(host, state, custom_path=self.session_file)

    async def _deep_parse_css(
        self,
        parse_result: ParseResult,
        downloader: Downloader,
        storage: Storage,
        base_url: str,
    ) -> None:
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

                css_file = Path(self.output_dir) / local_path
                if not css_file.exists():
                    continue

                try:
                    css_text = css_file.read_text(encoding="utf-8", errors="replace")
                except Exception:
                    continue

                rewritten_css, new_resources, sub_css = parse_external_css(
                    css_text, css_url, parse_result.resource_map, base_domain
                )

                if new_resources:
                    if self.verbose:
                        console.print(
                            f"[dim]  🔗 CSS 子资源: {css_url} → {len(new_resources)} 个新资源[/]"
                        )
                    await downloader.download_all(new_resources, Path(self.output_dir))

                storage.save_text(rewritten_css, local_path)
                new_css_urls |= sub_css

            css_urls = new_css_urls

    def _fix_dedup_paths(
        self,
        html: str,
        download_results: dict,
        resource_map: dict[str, str],
    ) -> str:
        """修复因哈希去重导致的路径变化"""
        for url, result in download_results.items():
            if result.success and result.local_path != resource_map.get(url):
                original_path = f"./{resource_map.get(url, '')}"
                new_path = f"./{result.local_path}"

                if original_path and new_path and original_path != new_path:
                    html = html.replace(original_path, new_path)
        return html

    def _print_banner(self) -> None:
        banner = Text()
        banner.append("🕷️  WebThief", style="bold white")
        banner.append(" v1.0.0\n", style="dim")
        banner.append("   高保真网站克隆工具", style="cyan")

        panel = Panel(
            banner,
            border_style="bright_blue",
            padding=(1, 2),
        )
        console.print(panel)
        console.print(f"[bold]🎯 目标: [cyan]{self.url}[/][/]")

    def _print_summary(self, elapsed: float, downloader: Downloader, storage: Storage) -> None:
        summary = Text()
        summary.append("\n🎉 克隆完成!\n\n", style="bold green")
        summary.append(f"  ⏱  耗时: {elapsed:.1f} 秒\n", style="white")
        summary.append(f"  📥 下载: {downloader.total_downloaded} 文件\n", style="white")
        summary.append(f"  ⏭  去重: {downloader.total_skipped} 文件\n", style="cyan")
        if downloader.total_failed:
            summary.append(f"  ✗  失败: {downloader.total_failed} 文件\n", style="red")
        summary.append(f"  📦 总量: {downloader._format_size(downloader.total_bytes)}\n", style="white")
        summary.append(f"  📂 输出: {storage.get_output_path()}\n", style="white")
        summary.append("\n  💡 打开 index.html 即可离线浏览", style="dim")

        panel = Panel(
            summary,
            title="[bold green]✅ 完成[/]",
            border_style="green",
            padding=(0, 2),
        )
        console.print(panel)

    def _print_site_summary(self, elapsed: float) -> None:
        summary = Text()
        summary.append("\n🎉 站点抓取完成!\n\n", style="bold green")
        summary.append(f"  ⏱  耗时: {elapsed:.1f} 秒\n", style="white")
        summary.append(f"  📂 输出: {Path(self.output_dir).resolve()}\n", style="white")
        summary.append("  📄 报告: crawl_report.json\n", style="white")
        summary.append("\n  💡 从 index.html 开始本地浏览", style="dim")
        panel = Panel(
            summary,
            title="[bold green]✅ 完成[/]",
            border_style="green",
            padding=(0, 2),
        )
        console.print(panel)

