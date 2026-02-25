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
        "qr_data",
        "preserved_scripts",
        "menu_css",
        "status_code",
        "is_login_page",
        "page_links",
    )

    def __init__(self):
        self.html: str = ""
        self.resource_urls: set[str] = set()
        self.cookies: list[dict] = []
        self.base_url: str = ""
        self.final_url: str = ""
        self.response_cache: dict[str, bytes] = {}
        self.qr_data: dict = {}
        self.preserved_scripts: list[str] = []
        self.menu_css: str = ""
        self.status_code: int | None = None
        self.is_login_page: bool = False
        self.page_links: set[str] = set()


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
                intercepted, response_cache = self._attach_network_hooks(page, url)

                await self._navigate(page, url, result)
                await self._wait_after_navigation()

                if not self.disable_js:
                    await self._run_scroll_preload(page)
                    await self._run_hover_preload(page)

                await self._force_lazy_resource_activation(page)

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
        if self.enable_react_intercept and not self.disable_js:
            react_interceptor = ReactInterceptor()
            await react_interceptor.inject_react_unmount_patch(page)
        return qr_interceptor, react_interceptor

    def _attach_network_hooks(
        self,
        page: Page,
        base_url: str,
    ) -> tuple[set[str], dict[str, bytes]]:
        intercepted: set[str] = set()
        response_cache: dict[str, bytes] = {}

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
                content_type = response.headers.get("content-type", "")
                if not any(content_type.startswith(m) for m in CACHEABLE_MIMES):
                    return
                if not (200 <= response.status < 300):
                    return
                body = await response.body()
                if body and len(body) < 50 * 1024 * 1024:
                    normalized = normalize_url(resp_url, base_url)
                    if normalized:
                        response_cache[normalized] = body
            except Exception:
                pass

        page.on("request", on_request)
        page.on("response", on_response)
        return intercepted, response_cache

    async def _navigate(self, page: Page, url: str, result: RenderResult) -> None:
        """导航并记录最终 URL / 状态码"""
        console.print(f"[bold cyan]🌐 正在加载: {url}[/]")
        goto_response = None
        try:
            goto_response = await page.goto(url, wait_until="networkidle", timeout=60000)
        except Exception as e:
            console.print(f"[yellow]  ⚠ 导航警告: {e}[/]")

        result.status_code = goto_response.status if goto_response else None
        result.final_url = page.url

    async def _wait_after_navigation(self) -> None:
        await asyncio.sleep(self.wait_after_load)
        if self.extra_wait > 0:
            await asyncio.sleep(self.extra_wait)

    async def _run_scroll_preload(self, page: Page) -> None:
        try:
            scroll_delay_ms = int(self.scroll_pause * 1000)
            await page.evaluate(SCROLL_SCRIPT % scroll_delay_ms)
            await page.wait_for_load_state("networkidle", timeout=15000)
        except Exception:
            pass

    async def _run_hover_preload(self, page: Page) -> None:
        try:
            await page.evaluate(
                """
                async () => {
                    const selectors = ['.supernav > a', '.nav-item', '.dropdown-toggle', 'nav a', 'header a'];
                    for (const sel of selectors) {
                        const els = document.querySelectorAll(sel);
                        for (const el of els) {
                            el.dispatchEvent(new MouseEvent('mouseover', {bubbles: true}));
                            await new Promise(r => setTimeout(r, 100));
                        }
                    }
                }
                """
            )
        except Exception:
            pass

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
        try:
            return await page.evaluate(
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
        except Exception:
            return await page.content()

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
