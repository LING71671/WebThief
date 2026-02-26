"""
渲染与资源嗅探层：
- Playwright 渲染页面并抓取最终 DOM
- 拦截资源请求并缓存响应体
- 检测登录页（401/403、URL 关键字、DOM 表单特征）
- 支持人工登录暂停（headful）
- 集成网站类型检测和克隆策略选择
"""

from __future__ import annotations

import asyncio
import base64
from typing import TYPE_CHECKING
from urllib.parse import urlparse

from playwright.async_api import Page, Request, Response, async_playwright
from rich.console import Console

from ..config import (
    DEFAULT_SCROLL_PAUSE,
    DEFAULT_WAIT_AFTER_LOAD,
    SCROLL_SCRIPT,
    STEALTH_JS,
    TRACKER_DOMAINS,
    get_random_ua,
)
from ..interceptors import (
    AnimationAnalyzer,
    CanvasRecorder,
    MouseSimulator,
    PointerInterceptor,
    QRInterceptor,
    ReactInterceptor,
    WebGLCapture,
)
from ..scripts import (
    ANIMATION_ANALYSIS_BRIDGE_SCRIPT,
    BLOB_IMAGE_MATERIALIZATION_SCRIPT,
    CANVAS_REPLAY_BRIDGE_SCRIPT,
    CSS_SOLIDIFY_SCRIPT,
    DOM_SETTLE_WAIT_SCRIPT,
    DOM_SNAPSHOT_EXTRACT_SCRIPT,
    DOM_URL_COLLECT_SCRIPT,
    FALLBACK_DOM_EXTRACT_SCRIPT,
    FRAMEWORK_WAIT_SCRIPT,
    HOVER_PRELOAD_SCRIPT,
    INTERACTION_PRELOAD_SCRIPT,
    LAZY_RESOURCE_ACTIVATION_SCRIPT,
    LOGIN_DETECTION_SCRIPT,
    MOUSE_REPLAY_BRIDGE_SCRIPT,
    PAGE_LINKS_EXTRACT_SCRIPT,
    PRECISION_SCROLL_SCRIPT,
    RUNTIME_REPLAY_PREPARE_SCRIPT,
    SCROLL_ANIMATION_SOLIDIFY_SCRIPT,
    SPA_DETECTION_SCRIPT,
    VIEWPORT_ACTIVATION_SCRIPT,
    WEBGL_COMPATIBILITY_SCRIPT,
)
from .spa_prerender import SPAPrerender
from ..extractor import RenderStrategy, TechAnalyzer
from ..utils import normalize_crawl_url, normalize_url, should_skip_url

if TYPE_CHECKING:
    from ..security import SecurityHandler
    from ..session import SessionManager
    from ..api_simulator import APISimulator
    from ..detector import WebsiteTypeDetector, WebsiteTypeResult
    from ..strategy import StrategySelector, StrategyResult

console = Console()

# 需要缓存响应体的 MIME 类型前缀
CACHEABLE_MIMES = (
    "image/",
    "font/",
    "application/font",
    "application/x-font",
    "text/css",
    "application/javascript",
    "text/javascript",
    "application/json",
    "application/xml",
    "text/xml",
    "video/",
    "audio/",
    "application/octet-stream",
)

LOGIN_PATH_KEYWORDS = ("login", "signin", "sign-in", "auth")
AUTH_COOKIE_KEYWORDS = ("session", "auth", "token", "sid", "sso")


class RenderResult:
    """渲染结果容器"""

    __slots__ = (
        "html",
        "resource_urls",
        "cookies",
        "base_url",
        "final_url",
        "response_cache",
        "response_content_types",
        "qr_data",
        "preserved_scripts",
        "menu_css",
        "status_code",
        "is_login_page",
        "page_links",
        "tech_stack",
        "render_strategy",
        "spa_routes",
        "route_htmls",
        "security_analysis",
        "api_records",
        "website_type_result",
        "strategy_result",
    )

    def __init__(self):
        self.html: str = ""
        self.resource_urls: set[str] = set()
        self.cookies: list[dict] = []
        self.base_url: str = ""
        self.final_url: str = ""
        self.response_cache: dict[str, bytes] = {}
        self.response_content_types: dict[str, str] = {}
        self.qr_data: dict = {}
        self.preserved_scripts: list[str] = []
        self.menu_css: str = ""
        self.status_code: int | None = None
        self.is_login_page: bool = False
        self.page_links: set[str] = set()
        self.tech_stack: dict = {}
        self.render_strategy: dict = {}
        self.spa_routes: list[str] = []
        self.route_htmls: dict[str, str] = {}
        self.security_analysis: dict = {}
        self.api_records: list = []
        self.website_type_result: "WebsiteTypeResult | None" = None
        self.strategy_result: "StrategyResult | None" = None


class LoginDetector:
    """登录页面检测工具类"""

    @staticmethod
    def is_login_like(url: str, status_code: int | None, has_login_dom: bool) -> bool:
        """判断当前页面是否表现为登录墙"""
        if status_code in (401, 403):
            return True

        parsed = urlparse(url or "")
        path = parsed.path.lower()
        if any(k in path for k in LOGIN_PATH_KEYWORDS):
            return True

        return has_login_dom

    @staticmethod
    def has_auth_cookie(cookies: list[dict]) -> bool:
        """粗略判断是否存在鉴权相关 cookie"""
        for cookie in cookies:
            name = (cookie.get("name") or "").lower()
            if any(key in name for key in AUTH_COOKIE_KEYWORDS):
                return True
        return False


class ResponseCacheManager:
    """响应缓存管理器"""

    @staticmethod
    def is_cacheable(response: Response, content_type: str) -> bool:
        """
        判断响应是否应缓存到 runtime replay 池：
        - 静态资源（图片/字体/CSS/JS）直接缓存
        - XHR / fetch 响应优先缓存
        - 排除 HTML 页面主文档
        """
        ct = (content_type or "").lower()

        # 排除 HTML 主文档
        if ct.startswith("text/html"):
            return False

        if any(ct.startswith(m) for m in CACHEABLE_MIMES):
            return True
        if "json" in ct or "javascript" in ct or ct.startswith("text/"):
            return True

        try:
            request_type = (response.request.resource_type or "").lower()
        except Exception:
            request_type = ""
        return request_type in {"fetch", "xhr"}


class Renderer:
    """
    浏览器渲染引擎
    
    集成网站类型检测和克隆策略选择，在渲染前自动分析网站特征。
    """

    def __init__(
        self,
        wait_after_load: int = DEFAULT_WAIT_AFTER_LOAD,
        scroll_pause: float = DEFAULT_SCROLL_PAUSE,
        user_agent: str | None = None,
        extra_wait: int = 0,
        disable_js: bool = False,
        enable_qr_intercept: bool = True,
        enable_react_intercept: bool = True,
        freeze_animations: bool = True,
        prepare_runtime_replay: bool = False,
        enable_tech_analysis: bool = True,
        enable_spa_prerender: bool = True,
        security_handler: "SecurityHandler | None" = None,
        session_manager: "SessionManager | None" = None,
        api_simulator: "APISimulator | None" = None,
        website_detector: "WebsiteTypeDetector | None" = None,
        strategy_selector: "StrategySelector | None" = None,
        # 动画相关选项
        enable_mouse_simulation: bool = False,
        enable_scroll_precision: bool = False,
        enable_canvas_recording: bool = False,
        enable_webgl_capture: bool = False,
        enable_animation_analyze: bool = False,
        enable_pointer_intercept: bool = False,
    ):
        self.wait_after_load = wait_after_load
        self.scroll_pause = scroll_pause
        self.user_agent = user_agent or get_random_ua()
        self.extra_wait = extra_wait
        self.disable_js = disable_js
        self.enable_qr_intercept = enable_qr_intercept
        self.enable_react_intercept = enable_react_intercept
        self.freeze_animations = freeze_animations
        self.prepare_runtime_replay = prepare_runtime_replay
        self.enable_tech_analysis = enable_tech_analysis
        self.enable_spa_prerender = enable_spa_prerender
        self.security_handler = security_handler
        self.session_manager = session_manager
        self.api_simulator = api_simulator
        self.website_detector = website_detector
        self.strategy_selector = strategy_selector
        # 动画相关选项
        self.enable_mouse_simulation = enable_mouse_simulation
        self.enable_scroll_precision = enable_scroll_precision
        self.enable_canvas_recording = enable_canvas_recording
        self.enable_webgl_capture = enable_webgl_capture
        self.enable_animation_analyze = enable_animation_analyze
        self.enable_pointer_intercept = enable_pointer_intercept

        # 初始化拦截器实例
        self._mouse_simulator: MouseSimulator | None = None
        self._pointer_interceptor: PointerInterceptor | None = None
        self._canvas_recorder: CanvasRecorder | None = None
        self._webgl_capture: WebGLCapture | None = None
        self._animation_analyzer: AnimationAnalyzer | None = None

    async def render(
        self,
        url: str,
        storage_state: dict | None = None,
        headless: bool = True,
    ) -> RenderResult:
        """
        渲染单页并返回资源嗅探结果
        """
        result = RenderResult()
        result.base_url = url

        console.print("[bold cyan]🚀 启动浏览器渲染...[/]")

        tech_analyzer = TechAnalyzer() if self.enable_tech_analysis else None

        async with async_playwright() as pw:
            browser = await self._launch_browser(pw, headless)
            try:
                context = await self._create_browser_context(browser, storage_state)
                page = await context.new_page()

                qr_interceptor, react_interceptor = await self._setup_interceptors(page)
                intercepted, response_cache, response_content_types = self._attach_network_hooks(
                    page, url, tech_analyzer
                )

                await self._navigate_to_page(page, url, result)
                await self._wait_after_navigation()

                # 网站类型检测
                await self._run_website_detection(page, result)

                # 技术栈分析
                render_strategy = await self._analyze_tech_stack(page, tech_analyzer, result)

                # 策略选择
                await self._select_strategy(page, url, tech_analyzer, render_strategy, result)

                # 执行预加载操作
                if not self.disable_js:
                    await self._run_preload_operations(page, render_strategy, result)

                # 强制激活懒加载资源
                await self._force_lazy_resource_activation(page)

                # 执行动画相关操作
                await self._run_animation_operations(page, result)

                # 等待 DOM 稳定
                await self._wait_for_dom_settle(page)

                # React 菜单处理
                if react_interceptor:
                    await self._process_react_menus(page, react_interceptor, result)

                # 运行时回放准备
                if self.prepare_runtime_replay:
                    await self._prepare_runtime_replay(page)

                # CSS 固化
                await self._solidify_css(page)

                # Canvas 冻结
                if not self.prepare_runtime_replay:
                    await self._freeze_canvas(page)

                # QR 码处理
                if qr_interceptor:
                    await self._process_qr_codes(page, qr_interceptor, result)

                # Blob 图片固化
                await self._materialize_blob_images(page)

                # 安全分析
                await self._run_security_analysis(page, result)

                # 登录检测
                await self._detect_login_page(page, result)

                # 提取最终结果
                await self._extract_final_results(
                    page, context, url, result, intercepted, response_cache, response_content_types
                )

                # SPA 预渲染
                await self._run_spa_prerender(page, result)

            finally:
                await browser.close()

        return result

    async def _launch_browser(self, pw, headless: bool):
        """启动浏览器"""
        return await pw.chromium.launch(
            headless=headless,
            args=[
                "--no-sandbox",
                "--disable-blink-features=AutomationControlled",
                "--disable-features=IsolateOrigins,site-per-process",
                "--disable-web-security",
                "--disable-site-isolation-trials",
            ],
        )

    async def _create_browser_context(self, browser, storage_state: dict | None):
        """创建浏览器上下文"""
        context_kwargs = dict(
            user_agent=self.user_agent,
            viewport={"width": 1920, "height": 1080},
            locale="zh-CN",
            java_script_enabled=not self.disable_js,
            ignore_https_errors=True,
            service_workers="block",
        )
        if storage_state:
            context_kwargs["storage_state"] = storage_state

        context = await browser.new_context(**context_kwargs)
        await context.add_init_script(STEALTH_JS)

        if self.security_handler:
            await self.security_handler.setup_browser_context(context)

        return context

    async def _setup_interceptors(self, page: Page) -> tuple:
        """设置拦截器"""
        qr_interceptor = None
        if self.enable_qr_intercept and not self.disable_js:
            qr_interceptor = QRInterceptor()
            await qr_interceptor.inject_qr_proxy(page)

        react_interceptor = None
        if (
            self.enable_react_intercept
            and not self.disable_js
            and not self.prepare_runtime_replay
        ):
            react_interceptor = ReactInterceptor()
            await react_interceptor.inject_react_unmount_patch(page)

        return qr_interceptor, react_interceptor

    def _attach_network_hooks(
        self,
        page: Page,
        base_url: str,
        tech_analyzer: TechAnalyzer | None = None,
    ) -> tuple[set[str], dict[str, bytes], dict[str, str]]:
        """附加网络钩子"""
        intercepted: set[str] = set()
        response_cache: dict[str, bytes] = {}
        response_content_types: dict[str, str] = {}

        def on_request(request: Request) -> None:
            req_url = request.url
            if should_skip_url(req_url):
                return
            parsed = urlparse(req_url)
            if parsed.netloc in TRACKER_DOMAINS:
                return
            normalized = normalize_url(req_url, base_url)
            if normalized:
                intercepted.add(normalized)

        async def on_response(response: Response) -> None:
            try:
                resp_url = response.url
                if should_skip_url(resp_url):
                    return

                if tech_analyzer:
                    tech_analyzer.analyze_response(response)

                content_type = response.headers.get("content-type", "")
                if not ResponseCacheManager.is_cacheable(response, content_type):
                    return
                if not (200 <= response.status < 300):
                    return
                body = await response.body()
                if body and len(body) < 50 * 1024 * 1024:
                    normalized = normalize_url(resp_url, base_url)
                    if normalized:
                        response_cache[normalized] = body
                        response_content_types[normalized] = content_type
            except Exception:
                pass

        page.on("request", on_request)
        page.on("response", on_response)
        return intercepted, response_cache, response_content_types

    async def _navigate_to_page(self, page: Page, url: str, result: RenderResult) -> None:
        """导航到页面"""
        console.print(f"[bold cyan]🌐 正在加载: {url}[/]")
        goto_response = None
        try:
            goto_response = await page.goto(url, wait_until="networkidle", timeout=60000)
        except Exception as e:
            console.print(f"[yellow]  ⚠ 导航警告: {e}[/]")

        # 等待框架完成渲染
        try:
            await page.wait_for_function(
                "() => document.readyState === 'complete'", timeout=10000
            )
            await page.evaluate(FRAMEWORK_WAIT_SCRIPT)
        except Exception:
            pass

        result.status_code = goto_response.status if goto_response else None
        result.final_url = page.url

    async def _wait_after_navigation(self) -> None:
        """导航后等待"""
        await asyncio.sleep(self.wait_after_load)
        if self.extra_wait > 0:
            await asyncio.sleep(self.extra_wait)

    async def _run_website_detection(self, page: Page, result: RenderResult) -> None:
        """执行网站类型检测"""
        if not self.website_detector:
            return

        console.print("[bold cyan]🔍 执行网站类型检测...[/]")
        try:
            website_type_result = await self.website_detector.detect(page)
            result.website_type_result = website_type_result
            self.website_detector.print_summary(website_type_result)
        except Exception as e:
            console.print(f"[yellow]  ⚠ 网站类型检测失败: {e}[/]")

    async def _analyze_tech_stack(
        self, page: Page, tech_analyzer: TechAnalyzer | None, result: RenderResult
    ) -> RenderStrategy | None:
        """分析技术栈"""
        if not tech_analyzer:
            return None

        console.print("[bold cyan]🔍 分析网站技术栈...[/]")
        try:
            await tech_analyzer.analyze_dom(page)
            tech_analyzer.print_summary()

            strategy = tech_analyzer.get_render_strategy()
            result.tech_stack = tech_analyzer.to_dict()
            result.render_strategy = {
                "wait_after_load": strategy.wait_after_load,
                "scroll_enabled": strategy.scroll_enabled,
                "scroll_pause": strategy.scroll_pause,
                "aggressive_interactions": strategy.aggressive_interactions,
                "hydration_wait": strategy.hydration_wait,
                "recommendations": strategy.recommendations,
            }
            return strategy
        except Exception as e:
            console.print(f"[yellow]  ⚠ 技术栈分析失败: {e}[/]")
            return None

    async def _select_strategy(
        self,
        page: Page,
        url: str,
        tech_analyzer: TechAnalyzer | None,
        render_strategy: RenderStrategy | None,
        result: RenderResult,
    ) -> None:
        """选择克隆策略"""
        if not self.strategy_selector or not result.website_type_result:
            return

        console.print("[bold cyan]📋 选择克隆策略...[/]")
        try:
            detected_features = {
                "has_login_form": result.website_type_result.auth_info.has_login_form,
                "has_webgl": result.website_type_result.webgl_info.has_webgl,
                "has_canvas": result.website_type_result.webgl_info.has_canvas,
            }

            tech_stack_obj = None
            if tech_analyzer:
                tech_stack_obj = getattr(tech_analyzer, "_tech_stack", None)

            strategy_result = self.strategy_selector.select(
                tech_stack=tech_stack_obj,
                render_strategy=render_strategy,
                detected_features=detected_features,
                url=url,
            )
            result.strategy_result = strategy_result
            self.strategy_selector.print_result(strategy_result)
        except Exception as e:
            console.print(f"[yellow]  ⚠ 策略选择失败: {e}[/]")

    async def _run_preload_operations(
        self,
        page: Page,
        strategy: RenderStrategy | None,
        result: RenderResult
    ) -> None:
        """执行预加载操作"""
        # 根据策略选择滚动方式
        if result.strategy_result and result.strategy_result.enable_scroll_precision:
            await self._run_precision_scroll_preload(page)
        else:
            await self._run_scroll_preload(page, strategy)

        await self._run_viewport_activation_preload(page)
        await self._run_hover_preload(page)

        if await self._should_run_aggressive_interactions(page, strategy):
            await self._run_interaction_preload(page)

        # 鼠标模拟预加载
        if result.strategy_result and result.strategy_result.enable_mouse_simulation:
            await self._run_mouse_simulation_preload(page)

    async def _run_scroll_preload(self, page: Page, strategy: RenderStrategy | None) -> None:
        """执行滚动预加载"""
        scroll_pause = strategy.scroll_pause if strategy and strategy.scroll_pause else self.scroll_pause
        scroll_enabled = strategy.scroll_enabled if strategy else True

        if not scroll_enabled:
            return

        try:
            scroll_delay_ms = int(scroll_pause * 1000)
            await page.evaluate(SCROLL_SCRIPT % scroll_delay_ms)
            await page.wait_for_load_state("networkidle", timeout=15000)
        except Exception:
            pass

    async def _run_viewport_activation_preload(self, page: Page) -> None:
        """执行视口激活预热"""
        try:
            await page.evaluate(VIEWPORT_ACTIVATION_SCRIPT)
            await page.wait_for_load_state("networkidle", timeout=8000)
        except Exception:
            pass

    async def _run_hover_preload(self, page: Page) -> None:
        """执行 Hover 预热"""
        try:
            await page.evaluate(HOVER_PRELOAD_SCRIPT)
            await page.wait_for_load_state("networkidle", timeout=8000)
        except Exception:
            pass

    async def _run_interaction_preload(self, page: Page) -> None:
        """执行交互预热"""
        try:
            await page.evaluate(INTERACTION_PRELOAD_SCRIPT)
            await page.wait_for_load_state("networkidle", timeout=8000)
        except Exception:
            pass

    async def _should_run_aggressive_interactions(
        self, page: Page, strategy: RenderStrategy | None
    ) -> bool:
        """判断是否应执行激进交互"""
        if strategy is not None:
            return strategy.aggressive_interactions

        try:
            score = await page.evaluate(SPA_DETECTION_SCRIPT)
            return isinstance(score, int) and score >= 2
        except Exception:
            return False

    async def _force_lazy_resource_activation(self, page: Page) -> None:
        """强制激活懒加载资源"""
        try:
            await page.evaluate(LAZY_RESOURCE_ACTIVATION_SCRIPT)
        except Exception:
            pass

    async def _wait_for_dom_settle(
        self, page: Page, timeout_ms: int = 12000, quiet_ms: int = 1200
    ) -> None:
        """等待 DOM 稳定"""
        try:
            await page.evaluate(
                DOM_SETTLE_WAIT_SCRIPT,
                {"timeoutMs": timeout_ms, "quietMs": quiet_ms},
            )
        except Exception:
            pass

    async def _process_react_menus(
        self, page: Page, react_interceptor: ReactInterceptor, result: RenderResult
    ) -> None:
        """处理 React 菜单"""
        await react_interceptor.trigger_all_menus(page)
        await react_interceptor.freeze_menu_states(page)
        result.menu_css = await react_interceptor.convert_js_interactions_to_css(page)

    async def _prepare_runtime_replay(self, page: Page) -> None:
        """准备运行时回放"""
        try:
            await page.evaluate(RUNTIME_REPLAY_PREPARE_SCRIPT)
        except Exception:
            pass

    async def _solidify_css(self, page: Page) -> None:
        """固化 CSS"""
        try:
            await page.evaluate(CSS_SOLIDIFY_SCRIPT)
        except Exception:
            pass

    async def _freeze_canvas(self, page: Page) -> None:
        """冻结 Canvas"""
        try:
            canvases = await page.query_selector_all("canvas")
        except Exception:
            return

        for i, canvas in enumerate(canvases):
            try:
                box = await canvas.bounding_box()
                if not (box and box["width"] > 5 and box["height"] > 5):
                    continue
                shot = await canvas.screenshot(type="png")
                b64 = base64.b64encode(shot).decode("ascii")
                await page.evaluate(
                    """
                    (args) => {
                        const c = document.querySelectorAll('canvas')[args.i];
                        const img = document.createElement('img');
                        img.src = 'data:image/png;base64,' + args.data;
                        img.style.cssText = getComputedStyle(c).cssText;
                        c.replaceWith(img);
                    }
                    """,
                    {"i": i, "data": b64},
                )
            except Exception:
                continue

    async def _process_qr_codes(
        self, page: Page, qr_interceptor: QRInterceptor, result: RenderResult
    ) -> None:
        """处理 QR 码"""
        result.qr_data = await qr_interceptor.capture_qr_lifecycle(page)
        result.preserved_scripts = await qr_interceptor.preserve_qr_scripts(page)

    async def _materialize_blob_images(self, page: Page, max_images: int = 8) -> None:
        """固化 Blob 图片"""
        try:
            await page.evaluate(BLOB_IMAGE_MATERIALIZATION_SCRIPT, max_images)
        except Exception:
            pass

    async def _run_security_analysis(self, page: Page, result: RenderResult) -> None:
        """执行安全分析"""
        if not self.security_handler:
            return

        security_result = await self.security_handler.analyze_page_security(page, html="")
        result.security_analysis = self.security_handler.to_dict(security_result)
        if self.security_handler.should_rotate_fingerprint():
            self.security_handler.rotate_fingerprint()

    async def _detect_login_page(self, page: Page, result: RenderResult) -> None:
        """检测登录页面"""
        has_login_dom = await self._detect_login_dom(page)
        result.is_login_page = LoginDetector.is_login_like(
            result.final_url, result.status_code, has_login_dom
        )

    async def _detect_login_dom(self, page: Page) -> bool:
        """检测登录 DOM"""
        try:
            return await page.evaluate(LOGIN_DETECTION_SCRIPT)
        except Exception:
            return False

    async def _extract_final_results(
        self,
        page: Page,
        context,
        url: str,
        result: RenderResult,
        intercepted: set[str],
        response_cache: dict[str, bytes],
        response_content_types: dict[str, str],
    ) -> None:
        """提取最终结果"""
        result.html = await self._extract_dom_snapshot(page)
        intercepted |= await self._collect_dom_urls(page, result.final_url)

        result.page_links = await self._extract_page_links(page, result.final_url)
        result.cookies = await context.cookies()
        result.resource_urls = intercepted
        result.response_cache = response_cache
        result.response_content_types = response_content_types

        # 导入 API 模拟器
        if self.api_simulator and response_cache:
            imported_count = self.api_simulator.import_from_renderer(
                response_cache, response_content_types
            )
            if imported_count > 0:
                console.print(f"[dim]  ✓ 已导入 {imported_count} 个 API 响应到模拟器[/]")

        # 保存会话
        if self.session_manager and result.cookies:
            try:
                await self.session_manager.save_session(
                    context=context,
                    name=urlparse(url).netloc,
                    origin=url,
                )
            except Exception:
                pass

    async def _extract_dom_snapshot(self, page: Page) -> str:
        """提取 DOM 快照"""
        html_content = ""

        # 策略 1: page.content()
        try:
            html_content = await page.content()
            if self._is_valid_html(html_content):
                return self._process_html_content(html_content)
        except Exception as e:
            console.print(f"[dim]  ⚠ page.content() 失败: {e}[/]")

        # 策略 2: page.evaluate
        try:
            html_content = await page.evaluate(
                DOM_SNAPSHOT_EXTRACT_SCRIPT,
                self.freeze_animations,
            )
            if self._is_valid_html(html_content):
                return self._process_html_content(html_content)
        except Exception as e:
            console.print(f"[dim]  ⚠ page.evaluate 提取失败: {e}[/]")

        # 策略 3: 备用提取
        try:
            html_content = await page.evaluate(FALLBACK_DOM_EXTRACT_SCRIPT)
            if self._is_valid_html(html_content):
                return self._process_html_content(html_content)
        except Exception as e:
            console.print(f"[dim]  ⚠ 备用提取失败: {e}[/]")

        return html_content if html_content else "<!DOCTYPE html><html><body>提取失败</body></html>"

    @staticmethod
    def _is_valid_html(content: str) -> bool:
        """验证内容是否为有效的 HTML"""
        if not content or len(content) < 100:
            return False

        content_lower = content.lower().strip()

        # 检查 JSON 格式
        if content_lower.startswith('{"') or content_lower.startswith("{'"):
            return False
        if '"body":' in content and "\\n" in content[:500]:
            return False

        # 检查基本 HTML 标签
        has_html_tag = "<html" in content_lower or "<!doctype html>" in content_lower
        has_body_tag = "<body" in content_lower

        return has_html_tag or has_body_tag

    def _process_html_content(self, html: str) -> str:
        """处理提取的 HTML 内容"""
        if not html:
            return html

        html = html.strip()

        if not html.lower().startswith("<!doctype html>"):
            html = "<!DOCTYPE html>\n" + html

        if self.freeze_animations and "<head>" in html:
            freeze_style = '<style>*, *::before, *::after { animation-play-state: paused !important; transition: none !important; }</style>'
            html = html.replace("<head>", f"<head>{freeze_style}", 1)

        return html

    async def _collect_dom_urls(self, page: Page, base_url: str) -> set[str]:
        """从最终 DOM 收集资源 URL"""
        collected: set[str] = set()
        try:
            urls = await page.evaluate(DOM_URL_COLLECT_SCRIPT)
        except Exception:
            return collected

        for raw_url in urls:
            if not raw_url or should_skip_url(raw_url):
                continue
            normalized = normalize_url(raw_url, base_url)
            if normalized:
                collected.add(normalized)
        return collected

    async def _extract_page_links(self, page: Page, base_url: str) -> set[str]:
        """提取页面链接"""
        links = set()
        try:
            hrefs = await page.evaluate(PAGE_LINKS_EXTRACT_SCRIPT)
            for href in hrefs:
                if not href or should_skip_url(href):
                    continue
                norm = normalize_crawl_url(href, base_url)
                if norm:
                    links.add(norm)
        except Exception:
            pass
        return links

    async def _run_spa_prerender(self, page: Page, result: RenderResult) -> None:
        """执行 SPA 预渲染"""
        if not self.enable_spa_prerender or not result.tech_stack:
            return

        is_spa = result.tech_stack.get("is_spa", False)
        if not is_spa:
            return

        console.print("[bold cyan]🔄 SPA 检测，启动路由预渲染...[/]")
        spa_prerender = SPAPrerender()
        route_htmls = await spa_prerender.analyze_and_prerender(
            page, result.final_url, result.tech_stack
        )
        result.route_htmls = route_htmls
        result.spa_routes = list(route_htmls.keys())
        console.print(f"[dim]  ✓ 预渲染完成: {len(route_htmls)} 个路由[/]")

    async def manual_auth(
        self,
        url: str,
        storage_state: dict | None = None,
        prompt: str | None = None,
    ) -> dict:
        """打开可视浏览器等待人工登录，返回最新 storage_state"""
        console.print("[bold yellow]🔐 进入人工认证模式（可视浏览器）[/]")

        async with async_playwright() as pw:
            browser = await pw.chromium.launch(
                headless=False,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--disable-features=IsolateOrigins,site-per-process",
                ],
            )

            context_kwargs = dict(
                user_agent=self.user_agent,
                viewport={"width": 1280, "height": 900},
                locale="zh-CN",
                java_script_enabled=True,
                ignore_https_errors=True,
            )
            if storage_state:
                context_kwargs["storage_state"] = storage_state

            context = await browser.new_context(**context_kwargs)
            await context.add_init_script(STEALTH_JS)
            page = await context.new_page()

            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            except Exception as e:
                console.print(f"[yellow]  ⚠ 打开认证页警告: {e}[/]")

            message = prompt or "登录完成后按回车继续抓取..."
            await asyncio.to_thread(input, f"\n{message}\n")

            final_url = page.url
            cookies = await context.cookies()
            state = await context.storage_state()
            await browser.close()

        if LoginDetector.has_auth_cookie(cookies) or not LoginDetector.is_login_like(final_url, None, False):
            console.print("[green]  ✓ 已获取可复用会话[/]")
        else:
            console.print("[yellow]  ⚠ 未检测到明显登录态，后续抓取可能再次触发认证[/]")

        return state

    # ━━━ 动画相关新方法 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    async def _run_precision_scroll_preload(self, page: Page) -> None:
        """执行高精度滚动预加载"""
        console.print("[cyan]  📜 执行高精度滚动...[/]")
        try:
            result = await page.evaluate(PRECISION_SCROLL_SCRIPT)
            if result:
                console.print(f"[green]  ✓ 高精度滚动完成: {result.get('totalSteps', 0)} 步[/]")
        except Exception as e:
            console.print(f"[dim]  ⚠ 高精度滚动失败: {e}[/]")

    async def _run_mouse_simulation_preload(self, page: Page) -> None:
        """执行鼠标模拟预加载"""
        if not self._mouse_simulator:
            self._mouse_simulator = MouseSimulator()

        console.print("[cyan]  🖱️ 执行鼠标轨迹模拟...[/]")
        try:
            # 生成并执行自然鼠标移动
            from ..interceptors import Point, TrajectoryType

            viewport = page.viewport_size or {"width": 1920, "height": 1080}

            # 生成多个轨迹
            trajectories = [
                # 从左上到右下
                (Point(100, 100), Point(viewport["width"] - 100, viewport["height"] - 100)),
                # 从右下到中间
                (Point(viewport["width"] - 100, viewport["height"] - 100), Point(viewport["width"] / 2, viewport["height"] / 2)),
                # 水平扫描
                (Point(100, viewport["height"] / 2), Point(viewport["width"] - 100, viewport["height"] / 2)),
            ]

            for start, end in trajectories:
                trajectory = self._mouse_simulator.generate_trajectory(
                    start, end, TrajectoryType.HUMAN_LIKE
                )
                replay_script = self._mouse_simulator.generate_trajectory_replay_script(
                    trajectory, show_cursor=False
                )
                await page.evaluate(replay_script)
                await asyncio.sleep(0.5)

            console.print("[green]  ✓ 鼠标轨迹模拟完成[/]")
        except Exception as e:
            console.print(f"[dim]  ⚠ 鼠标模拟失败: {e}[/]")

    async def _run_animation_operations(self, page: Page, result: RenderResult) -> None:
        """执行动画相关操作"""
        if not result.strategy_result:
            return

        strategy_result = result.strategy_result

        # 注入 Pointer 事件拦截器
        if self.enable_pointer_intercept or strategy_result.enable_mouse_simulation:
            await self._setup_pointer_interceptor(page)

        # 设置 Canvas 录制
        if self.enable_canvas_recording or strategy_result.enable_canvas_recording:
            await self._setup_canvas_recorder(page)

        # 设置 WebGL 捕获
        if self.enable_webgl_capture:
            await self._setup_webgl_capture(page)

        # 执行动画分析
        if self.enable_animation_analyze or strategy_result.enable_animation_analyze:
            await self._run_animation_analysis(page, result)

    async def _setup_pointer_interceptor(self, page: Page) -> None:
        """设置 Pointer 事件拦截器"""
        if not self._pointer_interceptor:
            self._pointer_interceptor = PointerInterceptor()

        console.print("[cyan]  🖱️ 设置 Pointer 事件拦截器...[/]")
        try:
            await self._pointer_interceptor.inject_pointer_tracker(page)
            # 捕获一段时间的 pointer 事件
            await self._pointer_interceptor.capture_pointer_events(page, duration_ms=3000)
            console.print("[green]  ✓ Pointer 事件拦截器已设置[/]")
        except Exception as e:
            console.print(f"[dim]  ⚠ Pointer 拦截器设置失败: {e}[/]")

    async def _setup_canvas_recorder(self, page: Page) -> None:
        """设置 Canvas 录制器"""
        if not self._canvas_recorder:
            self._canvas_recorder = CanvasRecorder()

        console.print("[cyan]  🎨 设置 Canvas 录制器...[/]")
        try:
            # 注入 Canvas 追踪脚本
            await self._canvas_recorder.inject_canvas_tracker(page)
            # 开始录制
            await self._canvas_recorder.start_recording(page)
            # 等待一段时间捕获绘制操作
            await asyncio.sleep(2)
            # 停止录制
            recording_data = await self._canvas_recorder.stop_recording(page)
            console.print(f"[green]  ✓ Canvas 录制完成: {len(recording_data)} 条记录[/]")

            # 捕获 Canvas 截图作为 fallback
            await self._canvas_recorder.capture_canvas_screenshot(page)
        except Exception as e:
            console.print(f"[dim]  ⚠ Canvas 录制失败: {e}[/]")

    async def _setup_webgl_capture(self, page: Page) -> None:
        """设置 WebGL 捕获器"""
        if not self._webgl_capture:
            self._webgl_capture = WebGLCapture()

        console.print("[cyan]  🎮 设置 WebGL 捕获器...[/]")
        try:
            # 注入 WebGL 追踪层
            await self._webgl_capture.inject_webgl_tracker(page)
            # 获取 WebGL 信息
            await self._webgl_capture.get_webgl_info(page)
            # 捕获 WebGL 资源
            await self._webgl_capture.capture_webgl_resources(page)
            # 捕获 WebGL 截图
            await self._webgl_capture.capture_webgl_screenshot(page)
            console.print("[green]  ✓ WebGL 捕获完成[/]")
        except Exception as e:
            console.print(f"[dim]  ⚠ WebGL 捕获失败: {e}[/]")

    async def _run_animation_analysis(self, page: Page, result: RenderResult) -> None:
        """执行 CSS 动画分析"""
        if not self._animation_analyzer:
            self._animation_analyzer = AnimationAnalyzer()

        console.print("[cyan]  🎬 执行 CSS 动画分析...[/]")
        try:
            # 分析 CSS 动画
            animations = await self._animation_analyzer.analyze_css_animations(page)

            # 选择性保留关键动画
            preserved = self._animation_analyzer.preserve_critical_animations(animations)

            # 生成保留的 CSS
            preserved_css = self._animation_analyzer.generate_preserved_css(preserved)

            # 注入动画冻结脚本
            await self._animation_analyzer.inject_animation_freeze_script(page)

            # 获取分析报告
            report = self._animation_analyzer.get_animation_report()
            self._animation_analyzer.print_report(report)

            # 将 CSS 添加到结果
            if preserved_css:
                result.menu_css = result.menu_css + "\n" + preserved_css if result.menu_css else preserved_css

            console.print("[green]  ✓ CSS 动画分析完成[/]")
        except Exception as e:
            console.print(f"[dim]  ⚠ 动画分析失败: {e}[/]")
