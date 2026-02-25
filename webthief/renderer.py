"""
渲染与资源嗅探层：
- Playwright 渲染页面并抓取最终 DOM
- 拦截资源请求并缓存响应体
- 检测登录页（401/403、URL 关键字、DOM 表单特征）
- 支持人工登录暂停（headful）
"""

from __future__ import annotations

import asyncio
import base64
from urllib.parse import urlparse

from playwright.async_api import Page, Request, Response, async_playwright
from rich.console import Console

from .config import (
    DEFAULT_SCROLL_PAUSE,
    DEFAULT_WAIT_AFTER_LOAD,
    SCROLL_SCRIPT,
    STEALTH_JS,
    TRACKER_DOMAINS,
    get_random_ua,
)
from .qr_interceptor import QRInterceptor
from .react_interceptor import ReactInterceptor
from .spa_prerender import SPAPrerender
from .tech_analyzer import RenderStrategy, TechAnalyzer
from .utils import normalize_crawl_url, normalize_url, should_skip_url

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


class Renderer:
    """
    浏览器渲染引擎
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

    @staticmethod
    def _is_cacheable_response(response: Response, content_type: str, base_url: str = "") -> bool:
        """
        判断响应是否应缓存到 runtime replay 池：
        - 静态资源（图片/字体/CSS/JS）直接缓存
        - XHR / fetch 响应优先缓存（即便 content-type 非标准）
        - 兼容 +json / javascript / text/* 等常见动态接口 MIME
        - 排除 HTML 页面主文档（避免将页面本身缓存为 API 响应）
        """
        ct = (content_type or "").lower()

        # 排除 HTML 主文档 - 不应该缓存页面本身
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
            browser = await pw.chromium.launch(
                headless=headless,
                args=[
                    "--no-sandbox",
                    "--disable-blink-features=AutomationControlled",
                    "--disable-features=IsolateOrigins,site-per-process",
                    "--disable-web-security",
                    "--disable-site-isolation-trials",
                ],
            )
            try:
                context = await browser.new_context(
                    **self._build_context_kwargs(storage_state)
                )
                await context.add_init_script(STEALTH_JS)
                page = await context.new_page()

                qr_interceptor, react_interceptor = await self._setup_interceptors(page)
                intercepted, response_cache, response_content_types = self._attach_network_hooks(page, url, tech_analyzer)

                await self._navigate(page, url, result)
                await self._wait_after_navigation()

                render_strategy = None
                if tech_analyzer:
                    render_strategy = await self._analyze_and_get_strategy(page, tech_analyzer, result)

                if not self.disable_js:
                    await self._run_scroll_preload(page, render_strategy)
                    await self._run_viewport_activation_preload(page)
                    await self._run_hover_preload(page)
                    if await self._should_run_aggressive_interactions(page, render_strategy):
                        await self._run_interaction_preload(page)

                await self._force_lazy_resource_activation(page)
                await self._wait_for_dom_settle(page)

                if react_interceptor:
                    await react_interceptor.trigger_all_menus(page)
                    await react_interceptor.freeze_menu_states(page)
                    result.menu_css = await react_interceptor.convert_js_interactions_to_css(
                        page
                    )

                if self.prepare_runtime_replay:
                    await self._prepare_runtime_replay(page)

                await self._solidify_css(page)
                
                if not self.prepare_runtime_replay:
                    await self._freeze_canvas(page)

                if qr_interceptor:
                    result.qr_data = await qr_interceptor.capture_qr_lifecycle(page)
                    result.preserved_scripts = await qr_interceptor.preserve_qr_scripts(page)

                await self._materialize_blob_images(page)

                has_login_dom = await self._detect_login_dom(page)
                result.is_login_page = self.is_login_like(
                    result.final_url, result.status_code, has_login_dom
                )

                result.html = await self._extract_dom_snapshot(page)
                intercepted |= await self._collect_dom_urls(page, result.final_url)

                result.page_links = await self._extract_page_links(page, result.final_url)
                result.cookies = await context.cookies()
                result.resource_urls = intercepted
                result.response_cache = response_cache
                result.response_content_types = response_content_types
                
                # SPA 预渲染：如果检测到 SPA 框架，预渲染所有路由
                if self.enable_spa_prerender and result.tech_stack:
                    is_spa = result.tech_stack.get("is_spa", False)
                    if is_spa:
                        console.print("[bold cyan]🔄 SPA 检测，启动路由预渲染...[/]")
                        spa_prerender = SPAPrerender()
                        route_htmls = await spa_prerender.analyze_and_prerender(
                            page, result.final_url, result.tech_stack
                        )
                        result.route_htmls = route_htmls
                        result.spa_routes = list(route_htmls.keys())
                        console.print(f"[dim]  ✓ 预渲染完成: {len(route_htmls)} 个路由[/]")
            finally:
                await browser.close()

        return result

    def _build_context_kwargs(self, storage_state: dict | None) -> dict:
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
        return context_kwargs

    async def _setup_interceptors(
        self, page: Page
    ) -> tuple[QRInterceptor | None, ReactInterceptor | None]:
        qr_interceptor = None
        if self.enable_qr_intercept and not self.disable_js:
            qr_interceptor = QRInterceptor()
            await qr_interceptor.inject_qr_proxy(page)

        react_interceptor = None
        # keep-js 模式优先保留站点原生运行时，不注入高侵入的 React 补丁
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
                if not self._is_cacheable_response(response, content_type):
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

    async def _navigate(self, page: Page, url: str, result: RenderResult) -> None:
        """导航并记录最终 URL / 状态码，增强对现代框架的兼容性"""
        console.print(f"[bold cyan]🌐 正在加载: {url}[/]")
        goto_response = None
        try:
            # 使用 networkidle 等待网络空闲
            goto_response = await page.goto(url, wait_until="networkidle", timeout=60000)
        except Exception as e:
            console.print(f"[yellow]  ⚠ 导航警告: {e}[/]")

        # 额外等待以确保 JavaScript 框架完成 hydration
        try:
            # 等待 document.readyState 为 complete
            await page.wait_for_function("() => document.readyState === 'complete'", timeout=10000)

            # 对于现代框架，等待关键元素出现
            await page.evaluate(
                """
                async () => {
                    // 等待最多 3 秒让框架完成渲染
                    const maxWait = 3000;
                    const start = Date.now();

                    while (Date.now() - start < maxWait) {
                        // 检查是否有内容渲染
                        const hasContent = document.body && (
                            document.body.innerText.length > 100 ||
                            document.querySelectorAll('img').length > 0 ||
                            document.querySelectorAll('div').length > 5
                        );

                        // 检查常见的框架加载指示器
                        const frameworksReady = !document.querySelector('#__next[data-reactroot]') ||
                                                document.querySelector('#__next > *');

                        if (hasContent && frameworksReady) {
                            break;
                        }

                        await new Promise(r => setTimeout(r, 100));
                    }
                }
                """
            )
        except Exception:
            pass

        result.status_code = goto_response.status if goto_response else None
        result.final_url = page.url

    async def _wait_after_navigation(self) -> None:
        await asyncio.sleep(self.wait_after_load)
        if self.extra_wait > 0:
            await asyncio.sleep(self.extra_wait)

    async def _analyze_and_get_strategy(
        self,
        page: Page,
        tech_analyzer: TechAnalyzer,
        result: RenderResult,
    ) -> RenderStrategy | None:
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

    async def _run_scroll_preload(self, page: Page, strategy: RenderStrategy | None = None) -> None:
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
        """
        通用视口激活预热：
        - 按区块逐段滚动，触发 IntersectionObserver / scroll 监听逻辑
        - 对老站影响较小，对现代滚动动效站点更有效
        """
        try:
            await page.evaluate(
                """
                async () => {
                    const wait = (ms) => new Promise((r) => setTimeout(r, ms));
                    const targets = [];
                    const seen = new Set();

                    const selectors = [
                        'section',
                        'article',
                        'main > div',
                        '[data-aos]',
                        '[data-animate]',
                        '[data-scroll]',
                        '[data-parallax]',
                        '[class*="reveal"]',
                        '[class*="timeline"]',
                        '.swiper',
                        '.carousel',
                        '[role="tablist"]'
                    ];

                    for (const sel of selectors) {
                        for (const el of document.querySelectorAll(sel)) {
                            if (seen.has(el)) continue;
                            const rect = el.getBoundingClientRect();
                            if (!rect || rect.height < 6) continue;
                            seen.add(el);
                            const top = Math.max(
                                0,
                                rect.top + window.scrollY - Math.floor(window.innerHeight * 0.35)
                            );
                            targets.push(top);
                            if (targets.length >= 40) break;
                        }
                        if (targets.length >= 40) break;
                    }

                    if (!targets.length) {
                        const scrollHeight = Math.max(
                            document.body ? document.body.scrollHeight : 0,
                            document.documentElement ? document.documentElement.scrollHeight : 0
                        );
                        const stops = 12;
                        for (let i = 0; i <= stops; i++) {
                            targets.push(Math.floor((scrollHeight * i) / stops));
                        }
                    } else {
                        targets.sort((a, b) => a - b);
                    }

                    for (const y of targets) {
                        window.scrollTo(0, y);
                        window.dispatchEvent(new Event('scroll'));
                        window.dispatchEvent(new Event('resize'));
                        window.dispatchEvent(new WheelEvent('wheel', { deltaY: 120, bubbles: true }));
                        await wait(170);
                    }

                    window.scrollTo(0, 0);
                    window.dispatchEvent(new Event('scroll'));
                    await wait(450);
                }
                """
            )
            try:
                await page.wait_for_load_state("networkidle", timeout=8000)
            except Exception:
                pass
        except Exception:
            pass

    async def _run_hover_preload(self, page: Page) -> None:
        try:
            await page.evaluate(
                """
                async () => {
                    const selectors = [
                        '.supernav > a',
                        '.nav-item',
                        '.dropdown-toggle',
                        'nav a',
                        'header a',
                        '[aria-haspopup="true"]',
                        '[role="menuitem"]',
                        'button[aria-expanded]',
                        '[data-featuretarget] button',
                        '[data-featuretarget] a'
                    ];
                    const touched = new Set();
                    const maxElements = 180;
                    let total = 0;

                    function fire(el, eventType) {
                        try {
                            if (eventType === 'focus') {
                                el.dispatchEvent(new Event('focus', { bubbles: true, cancelable: true }));
                                return;
                            }
                            el.dispatchEvent(new MouseEvent(eventType, {
                                bubbles: true,
                                cancelable: true,
                                view: window
                            }));
                        } catch (e) {}
                    }

                    for (const sel of selectors) {
                        const els = document.querySelectorAll(sel);
                        for (const el of els) {
                            if (touched.has(el)) continue;
                            if (total >= maxElements) break;
                            const rect = el.getBoundingClientRect();
                            if (!rect || rect.width < 2 || rect.height < 2) continue;
                            el.scrollIntoView({ behavior: 'instant', block: 'center', inline: 'nearest' });

                            fire(el, 'pointerenter');
                            fire(el, 'mouseenter');
                            fire(el, 'mouseover');
                            fire(el, 'mousemove');
                            fire(el, 'focus');

                            touched.add(el);
                            total += 1;
                            await new Promise(r => setTimeout(r, 140));
                        }
                        if (total >= maxElements) break;
                    }

                    await new Promise(r => setTimeout(r, 900));
                }
                """
            )
            try:
                await page.wait_for_load_state("networkidle", timeout=8000)
            except Exception:
                pass
        except Exception:
            pass

    async def _run_interaction_preload(self, page: Page) -> None:
        """
        通用交互预热：
        - 触发 tabs / carousel bullets / accordion 等常见控件
        - 仅点击“低导航风险”元素，避免离开当前页面
        """
        try:
            await page.evaluate(
                """
                async () => {
                    const selectors = [
                        '[role="tab"]',
                        '[aria-controls]',
                        '[data-tab]',
                        '[data-target]',
                        '[data-bs-target]',
                        '.tab',
                        '.tabs li',
                        '.swiper-pagination-bullet',
                        '.slick-dots button',
                        '.carousel-indicators button',
                        '.accordion-button',
                        '.collapse-toggle',
                        'button'
                    ];

                    const seen = new Set();
                    const maxActions = 70;
                    let actions = 0;

                    function isVisible(el) {
                        const rect = el.getBoundingClientRect();
                        if (!rect) return false;
                        if (rect.width < 2 || rect.height < 2) return false;
                        const style = getComputedStyle(el);
                        return style.visibility !== 'hidden' && style.display !== 'none';
                    }

                    function isLowRiskTarget(el) {
                        const tag = (el.tagName || '').toLowerCase();
                        if (tag === 'button') {
                            const type = (el.getAttribute('type') || '').toLowerCase();
                            const form = el.closest('form');
                            // 默认 submit 按钮风险高，避免触发表单跳转
                            if (!type || type === 'submit') {
                                if (form) return false;
                            }
                            return true;
                        }
                        if (tag === 'a') {
                            const href = (el.getAttribute('href') || '').trim().toLowerCase();
                            if (!href || href === '#') return true;
                            if (href.startsWith('javascript:')) return true;
                            return false;
                        }
                        if (el.getAttribute('role') === 'tab') return true;
                        if (el.hasAttribute('aria-controls')) return true;
                        if (el.hasAttribute('data-tab') || el.hasAttribute('data-target') || el.hasAttribute('data-bs-target')) return true;
                        const cls = (el.className || '').toLowerCase();
                        return cls.includes('tab') || cls.includes('bullet') || cls.includes('dot');
                    }

                    function safeClick(el) {
                        try {
                            if (typeof el.click === 'function') {
                                el.click();
                            } else {
                                el.dispatchEvent(new MouseEvent('click', {
                                    bubbles: true,
                                    cancelable: true,
                                    view: window
                                }));
                            }
                        } catch (e) {}
                    }

                    for (const sel of selectors) {
                        const elements = document.querySelectorAll(sel);
                        for (const el of elements) {
                            if (actions >= maxActions) break;
                            if (seen.has(el)) continue;
                            if (!isVisible(el)) continue;
                            if (!isLowRiskTarget(el)) continue;

                            seen.add(el);
                            el.scrollIntoView({ behavior: 'instant', block: 'center', inline: 'nearest' });
                            el.dispatchEvent(new MouseEvent('mouseenter', { bubbles: true }));
                            el.dispatchEvent(new MouseEvent('mouseover', { bubbles: true }));
                            safeClick(el);
                            actions += 1;
                            await new Promise(r => setTimeout(r, 160));
                        }
                        if (actions >= maxActions) break;
                    }

                    await new Promise(r => setTimeout(r, 900));
                    return actions;
                }
                """
            )
            try:
                await page.wait_for_load_state("networkidle", timeout=8000)
            except Exception:
                pass
        except Exception:
            pass

    async def _should_run_aggressive_interactions(self, page: Page, strategy: RenderStrategy | None = None) -> bool:
        if strategy is not None:
            return strategy.aggressive_interactions
        
        try:
            score = await page.evaluate(
                """
                () => {
                    let score = 0;

                    if (document.querySelector('#__next, #__nuxt, [data-reactroot], [data-reactid], [data-v-app], [ng-version]')) {
                        score += 2;
                    }

                    if (window.__NEXT_DATA__ || window.__NUXT__) {
                        score += 2;
                    }

                    if (document.querySelectorAll('script[type="module"]').length >= 3) {
                        score += 1;
                    }

                    if (document.querySelector('[data-aos], [data-wow-duration], [data-scroll], [data-parallax]')) {
                        score += 1;
                    }

                    if (document.querySelector('.swiper, .swiper-container, .slick-slider, .carousel, [class*="swiper"], [class*="carousel"]')) {
                        score += 1;
                    }

                    if (document.querySelector('[role="tab"], [aria-controls], [data-tab], .tabs, .accordion')) {
                        score += 1;
                    }

                    return score;
                }
                """
            )
            return isinstance(score, int) and score >= 2
        except Exception:
            return False

    async def _force_lazy_resource_activation(self, page: Page) -> None:
        """强制激活常见懒加载资源，确保快照包含真实图片/背景图"""
        try:
            await page.evaluate(
                """
                () => {
                    const srcAttrs = [
                        'data-src', 'data-original', 'data-lazy-src',
                        'data-actualsrc', 'data-url'
                    ];
                    const srcsetAttrs = ['data-srcset', 'data-lazy-srcset'];
                    const bgAttrs = ['data-bg', 'data-bg-src', 'data-background'];

                    const isPlaceholder = (val) => {
                        if (!val) return true;
                        const s = String(val).trim().toLowerCase();
                        if (!s) return true;
                        if (s.startsWith('data:image')) return s.length < 256 || s.includes('r0lgodh');
                        return ['placeholder', 'spacer', 'blank', 'loading', 'pixel'].some(k => s.includes(k));
                    };

                    document.querySelectorAll('img').forEach((img) => {
                        for (const attr of srcAttrs) {
                            const candidate = img.getAttribute(attr);
                            if (!candidate) continue;
                            if (isPlaceholder(img.getAttribute('src'))) {
                                img.setAttribute('src', candidate);
                            }
                        }
                        for (const attr of srcsetAttrs) {
                            const candidate = img.getAttribute(attr);
                            if (candidate && !img.getAttribute('srcset')) {
                                img.setAttribute('srcset', candidate);
                            }
                        }
                        if (img.getAttribute('loading') === 'lazy') {
                            img.setAttribute('loading', 'eager');
                        }
                    });

                    document.querySelectorAll('source').forEach((source) => {
                        for (const attr of srcsetAttrs) {
                            const candidate = source.getAttribute(attr);
                            if (candidate) {
                                source.setAttribute('srcset', candidate);
                            }
                        }
                        for (const attr of srcAttrs) {
                            const candidate = source.getAttribute(attr);
                            if (candidate && !source.getAttribute('src')) {
                                source.setAttribute('src', candidate);
                            }
                        }
                    });

                    document.querySelectorAll('*').forEach((el) => {
                        for (const attr of bgAttrs) {
                            const candidate = el.getAttribute(attr);
                            if (!candidate) continue;
                            if (!el.style.backgroundImage || el.style.backgroundImage === 'none') {
                                el.style.backgroundImage = `url("${candidate}")`;
                            }
                        }
                    });
                }
                """
            )
        except Exception:
            pass

    async def _materialize_blob_images(self, page: Page, max_images: int = 8) -> None:
        """
        将页面中的 blob: 图片地址固化为 data URL。
        目的：离线重放时，blob 对象 URL 已失效，直接导致图片（含二维码）裂图。
        """
        try:
            await page.evaluate(
                """
                async (limit) => {
                    const candidates = Array.from(
                        document.querySelectorAll('img[src^="blob:"]')
                    );
                    if (!candidates.length) {
                        return 0;
                    }

                    async function blobUrlToDataUrl(blobUrl) {
                        try {
                            const response = await fetch(blobUrl);
                            if (!response || !response.ok) return '';
                            const blob = await response.blob();
                            if (!blob || !blob.size) return '';
                            if (blob.size > 2 * 1024 * 1024) return '';
                            return await new Promise((resolve) => {
                                const reader = new FileReader();
                                reader.onload = () => {
                                    resolve(typeof reader.result === 'string' ? reader.result : '');
                                };
                                reader.onerror = () => resolve('');
                                reader.readAsDataURL(blob);
                            });
                        } catch (e) {
                            return '';
                        }
                    }

                    let converted = 0;
                    for (const img of candidates) {
                        if (converted >= limit) break;
                        const src = (img.getAttribute('src') || '').trim();
                        if (!src.startsWith('blob:')) continue;
                        const dataUrl = await blobUrlToDataUrl(src);
                        if (!dataUrl) continue;
                        img.setAttribute('data-webthief-blob-src', src);
                        img.setAttribute('src', dataUrl);
                        converted += 1;
                    }
                    return converted;
                }
                """,
                max_images,
            )
        except Exception:
            pass

    async def _wait_for_dom_settle(
        self,
        page: Page,
        timeout_ms: int = 12000,
        quiet_ms: int = 1200,
    ) -> None:
        """
        等待 DOM 稳定，给异步渲染/数据注入留时间，减少快照截断导致的空白块。
        """
        try:
            await page.evaluate(
                """
                (args) => new Promise((resolve) => {
                    const timeoutMs = Math.max(1000, Number(args.timeoutMs) || 12000);
                    const quietMs = Math.max(200, Number(args.quietMs) || 1200);

                    let settled = false;
                    let quietTimer = null;
                    let timeoutTimer = null;

                    function done() {
                        if (settled) return;
                        settled = true;
                        if (quietTimer) clearTimeout(quietTimer);
                        if (timeoutTimer) clearTimeout(timeoutTimer);
                        if (observer) observer.disconnect();
                        resolve(true);
                    }

                    function resetQuietTimer() {
                        if (quietTimer) clearTimeout(quietTimer);
                        quietTimer = setTimeout(done, quietMs);
                    }

                    const observer = new MutationObserver(() => {
                        resetQuietTimer();
                    });
                    observer.observe(document.documentElement || document.body, {
                        childList: true,
                        subtree: true,
                        attributes: true,
                        characterData: true
                    });

                    timeoutTimer = setTimeout(done, timeoutMs);
                    resetQuietTimer();
                })
                """,
                {"timeoutMs": timeout_ms, "quietMs": quiet_ms},
            )
        except Exception:
            pass

    async def _prepare_runtime_replay(self, page: Page) -> None:
        """
        在保留 JS 的场景下，尽量回退已初始化组件，避免快照态阻断二次初始化。
        典型场景：slick/swiper 在克隆页重新执行时因 "initialized" 状态失效。
        """
        try:
            await page.evaluate(
                """
                () => {
                    try {
                        if (window.jQuery && window.jQuery.fn && window.jQuery.fn.slick) {
                            window.jQuery('.slick-initialized').each(function() {
                                try { window.jQuery(this).slick('unslick'); } catch (e) {}
                            });
                        }
                    } catch (e) {}

                    try {
                        document.querySelectorAll('.swiper, .swiper-container').forEach((el) => {
                            const inst = el.swiper || el.__swiper__ || null;
                            if (inst && typeof inst.destroy === 'function') {
                                try { inst.destroy(true, true); } catch (e) {}
                            }
                        });
                    } catch (e) {}
                }
                """
            )
        except Exception:
            pass

    async def _solidify_scroll_animations(self, page: Page) -> None:
        """
        固化滚动驱动动画的状态（GSAP ScrollTrigger等）。
        将当前滚动位置的计算样式写入元素，使首屏内容可见。
        注意：不处理菜单、导航等交互元素。
        """
        try:
            console.print("[cyan]  🎬 固化滚动动画状态...[/]")
            await page.evaluate(
                """() => {
                    // 滚动到首屏位置
                    window.scrollTo(0, 0);
                    window.dispatchEvent(new Event('scroll'));
                    
                    // 需要排除的选择器（菜单、导航、弹窗等）
                    const excludeSelectors = [
                        'nav.menu',
                        'nav[class*="menu"]',
                        '.menu-overlay',
                        '.nav-overlay',
                        '.mobile-menu',
                        '[class*="navList"]',
                        '.appNavList',
                        '.shape-overlays',
                        '#menu',
                        '.modal',
                        '.popup',
                        '.overlay'
                    ];
                    
                    // 检查元素是否应该被排除
                    function shouldExclude(el) {
                        // 检查是否在排除列表中
                        for (const selector of excludeSelectors) {
                            try {
                                if (el.matches && el.matches(selector)) return true;
                                if (el.closest && el.closest(selector)) return true;
                            } catch(e) {}
                        }
                        // 检查是否是导航链接
                        const tag = el.tagName ? el.tagName.toLowerCase() : '';
                        if (tag === 'nav') return true;
                        // 检查父元素是否是nav
                        if (el.parentElement && el.parentElement.tagName.toLowerCase() === 'nav') {
                            // 但保留main里面的内容
                            let parent = el.parentElement;
                            while (parent) {
                                if (parent.tagName.toLowerCase() === 'main') return false;
                                if (parent.tagName.toLowerCase() === 'nav') return true;
                                parent = parent.parentElement;
                            }
                        }
                        return false;
                    }
                    
                    // 只处理首屏区域内的元素
                    const viewportHeight = window.innerHeight;
                    
                    // 强制首屏内容可见 - 处理GSAP等动画库的初始隐藏
                    document.querySelectorAll('*').forEach(function(el) {
                        // 排除菜单和导航元素
                        if (shouldExclude(el)) return;
                        
                        const rect = el.getBoundingClientRect();
                        // 只处理首屏区域内的元素
                        if (rect.bottom < 0 || rect.top > viewportHeight) return;
                        
                        const computed = getComputedStyle(el);
                        const opacity = parseFloat(computed.opacity);
                        
                        // 如果元素被隐藏（opacity为0或接近0），尝试显示它
                        if (opacity < 0.01 && rect.height > 0) {
                            // 检查是否是动画元素
                            const transform = computed.transform;
                            const hasTransform = transform && transform !== 'none';
                            
                            // 将当前计算样式写入内联style
                            el.style.opacity = '1';
                            if (hasTransform) {
                                el.style.transform = transform;
                            }
                            el.style.visibility = 'visible';
                        }
                    });
                    
                    // 特别处理常见的GSAP动画类（但排除导航相关）
                    const gsapSelectors = [
                        '[class*="alan"]',  // 南孚网站使用的动画类
                        '[class*="gsap"]',
                        '[data-speed]',
                        '.fn1_alan',
                        '.fn2_alan',
                        '#firstMv',
                        '#firstMedia',
                        '.banner',
                        '.group.active',
                        'h1',
                        '.note',
                        '.col.half'
                    ];
                    
                    gsapSelectors.forEach(function(selector) {
                        try {
                            document.querySelectorAll(selector).forEach(function(el) {
                                if (shouldExclude(el)) return;
                                const rect = el.getBoundingClientRect();
                                if (rect.bottom < 0 || rect.top > viewportHeight) return;
                                
                                // 强制设置为可见 - 覆盖GSAP的内联样式
                                el.style.setProperty('opacity', '1', 'important');
                                el.style.setProperty('visibility', 'visible', 'important');
                                // 清除GSAP的transform
                                el.style.setProperty('transform', 'none', 'important');
                            });
                        } catch(e) {}
                    });
                    
                    // 处理video元素的父容器（首屏内）
                    document.querySelectorAll('video').forEach(function(v) {
                        const rect = v.getBoundingClientRect();
                        if (rect.bottom < 0 || rect.top > viewportHeight) return;
                        
                        v.style.opacity = '1';
                        v.style.display = 'block';
                        const parent = v.parentElement;
                        if (parent && !shouldExclude(parent)) {
                            parent.style.opacity = '1';
                        }
                    });
                    
                    console.log('[WebThief] 滚动动画状态已固化');
                }"""
            )
            console.print("[green]  ✓ 滚动动画状态已固化[/]")
        except Exception as e:
            console.print(f"[yellow]  ⚠ 滚动动画固化警告: {e}[/]")

    async def _solidify_css(self, page: Page) -> None:
        try:
            await page.evaluate(
                """
                () => {
                    const rootStyles = getComputedStyle(document.documentElement);
                    let cssVars = ':root {\\n';
                    for (let i = 0; i < rootStyles.length; i++) {
                        const prop = rootStyles[i];
                        if (prop.startsWith('--')) {
                            cssVars += `  ${prop}: ${rootStyles.getPropertyValue(prop)};\\n`;
                        }
                    }
                    cssVars += '}';
                    const style = document.createElement('style');
                    style.textContent = cssVars;
                    document.head.appendChild(style);

                    document.querySelectorAll('*').forEach(el => {
                        const bg = getComputedStyle(el).backgroundImage;
                        if (bg && bg !== 'none' && !el.style.backgroundImage) {
                            el.style.backgroundImage = bg;
                        }
                    });
                }
                """
            )
        except Exception:
            pass

    async def _freeze_canvas(self, page: Page) -> None:
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

    async def _extract_dom_snapshot(self, page: Page) -> str:
        """
        提取页面 DOM 快照，使用多种策略确保获取完整渲染后的 HTML。
        优先使用 page.content()，因为它能更好地处理现代框架（React/Vue/Next.js）渲染的页面。
        """
        html_content = ""

        # 策略 1: 优先使用 page.content() - 对现代框架更可靠
        try:
            html_content = await page.content()
            if self._is_valid_html(html_content):
                return self._process_html_content(html_content)
        except Exception as e:
            console.print(f"[dim]  ⚠ page.content() 失败: {e}[/]")

        # 策略 2: 使用 page.evaluate 提取 DOM
        try:
            html_content = await page.evaluate(
                """
                (freezeAnimations) => {
                    function expand(root) {
                        root.querySelectorAll('*').forEach(el => {
                            if (el.shadowRoot) {
                                const wrapper = document.createElement('div');
                                wrapper.innerHTML = el.shadowRoot.innerHTML;
                                el.appendChild(wrapper);
                                expand(wrapper);
                            }
                        });
                    }
                    expand(document);

                    if (freezeAnimations) {
                        const s = document.createElement('style');
                        s.textContent = '*, *::before, *::after { animation-play-state: paused !important; transition: none !important; }';
                        document.head.appendChild(s);
                    }

                    return '<!DOCTYPE html>\\n' + document.documentElement.outerHTML;
                }
                """,
                self.freeze_animations,
            )
            if self._is_valid_html(html_content):
                return self._process_html_content(html_content)
        except Exception as e:
            console.print(f"[dim]  ⚠ page.evaluate 提取失败: {e}[/]")

        # 策略 3: 尝试获取 document.body 的 HTML
        try:
            html_content = await page.evaluate(
                """
                () => {
                    const html = document.documentElement ? document.documentElement.outerHTML : '';
                    const body = document.body ? document.body.outerHTML : '';
                    return html || body || document.documentElement.innerHTML || '';
                }
                """
            )
            if self._is_valid_html(html_content):
                return self._process_html_content(html_content)
        except Exception as e:
            console.print(f"[dim]  ⚠ 备用提取失败: {e}[/]")

        # 如果所有策略都失败，返回最后一次获取的内容
        return html_content if html_content else "<!DOCTYPE html><html><body>提取失败</body></html>"

    @staticmethod
    def _is_valid_html(content: str) -> bool:
        """验证内容是否为有效的 HTML"""
        if not content or len(content) < 100:
            return False

        content_lower = content.lower().strip()

        # 检查是否包含 JSON 格式的响应（错误情况）
        if content_lower.startswith('{"') or content_lower.startswith("{'"):
            return False
        if '"body":' in content and '\\n' in content[:500]:
            return False

        # 检查是否包含基本的 HTML 标签
        has_html_tag = '<html' in content_lower or '<!doctype html>' in content_lower
        has_body_tag = '<body' in content_lower
        has_doctype = content_lower.startswith('<!doctype html>')

        # 至少要有 HTML 标签或 body 标签
        return has_html_tag or has_body_tag

    def _process_html_content(self, html: str) -> str:
        """处理提取的 HTML 内容，确保格式正确"""
        if not html:
            return html

        html = html.strip()

        # 确保有 DOCTYPE
        if not html.lower().startswith('<!doctype html>'):
            html = '<!DOCTYPE html>\n' + html

        # 冻结动画（如果启用）
        if self.freeze_animations and '<head>' in html:
            freeze_style = '<style>*, *::before, *::after { animation-play-state: paused !important; transition: none !important; }</style>'
            html = html.replace('<head>', f'<head>{freeze_style}', 1)

        return html

    async def _collect_dom_urls(self, page: Page, base_url: str) -> set[str]:
        """从最终 DOM 收集 src/href 资源引用"""
        collected: set[str] = set()
        try:
            urls = await page.evaluate(
                """
                () => Array.from(new Set([
                    ...Array.from(document.querySelectorAll('[src]')).map(e => e.src),
                    ...Array.from(document.querySelectorAll('link[href]')).map(e => e.href)
                ]))
                """
            )
        except Exception:
            return collected

        for raw_url in urls:
            if not raw_url or should_skip_url(raw_url):
                continue
            normalized = normalize_url(raw_url, base_url)
            if normalized:
                collected.add(normalized)
        return collected

    async def manual_auth(
        self,
        url: str,
        storage_state: dict | None = None,
        prompt: str | None = None,
    ) -> dict:
        """
        打开可视浏览器等待人工登录，返回最新 storage_state
        """
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

        if self.has_auth_cookie(cookies) or not self.is_login_like(final_url, None, False):
            console.print("[green]  ✓ 已获取可复用会话[/]")
        else:
            console.print("[yellow]  ⚠ 未检测到明显登录态，后续抓取可能再次触发认证[/]")

        return state

    async def _detect_login_dom(self, page: Page) -> bool:
        """检测页面是否包含典型登录表单"""
        try:
            return await page.evaluate(
                """
                () => {
                    const selectors = [
                        'input[type="password"]',
                        'input[name*="pass" i]',
                        'form[action*="login" i]',
                        'form[id*="login" i]',
                        'form[class*="login" i]',
                        '[data-testid*="login" i]'
                    ];
                    return selectors.some(sel => !!document.querySelector(sel));
                }
                """
            )
        except Exception:
            return False

    async def _extract_page_links(self, page: Page, base_url: str) -> set[str]:
        """提取页面中的 a[href] 并规范化为可抓取 URL"""
        links = set()
        try:
            hrefs = await page.evaluate(
                """
                () => Array.from(
                    new Set(
                        Array.from(document.querySelectorAll('a[href]'))
                            .map(a => a.getAttribute('href') || '')
                    )
                )
                """
            )
            for href in hrefs:
                if not href or should_skip_url(href):
                    continue
                norm = normalize_crawl_url(href, base_url)
                if norm:
                    links.add(norm)
        except Exception:
            pass
        return links
