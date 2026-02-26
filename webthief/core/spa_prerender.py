"""
SPA 路由预渲染模块：
- 检测 SPA 框架（Angular、React Router、Vue Router）
- 提取路由配置
- 预渲染所有路由状态
- 生成静态多页版本
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from playwright.async_api import Page


@dataclass
class RouteInfo:
    """路由信息"""
    path: str
    component: str | None = None
    is_lazy: bool = False
    chunk_name: str | None = None


@dataclass
class SPARoutes:
    """SPA 路由集合"""
    framework: str = "unknown"
    routes: list[RouteInfo] = field(default_factory=list)
    base_href: str = "/"

    def get_all_paths(self) -> list[str]:
        """获取所有路由路径"""
        paths = []
        for route in self.routes:
            if route.path and route.path != "**" and not route.path.startswith(":"):
                paths.append(route.path)
        return paths


class SPAPrerender:
    """
    SPA 预渲染器
    支持 Angular、React Router、Vue Router
    """

    def __init__(self):
        self.routes = SPARoutes()

    async def analyze_and_prerender(
        self,
        page: Page,
        base_url: str,
        tech_stack: dict,
    ) -> dict[str, str]:
        """
        分析 SPA 路由并预渲染所有状态

        Returns:
            路由路径 -> HTML 内容的映射
        """
        # 检测框架类型
        framework = self._detect_framework(tech_stack)
        self.routes.framework = framework

        if framework == "angular":
            return await self._prerender_angular(page, base_url)
        elif framework == "react":
            return await self._prerender_react(page, base_url)
        elif framework == "vue":
            return await self._prerender_vue(page, base_url)
        else:
            # 通用方案：尝试通过 URL hash 或 history 操作切换路由
            return await self._prerender_generic(page, base_url)

    def _detect_framework(self, tech_stack: dict) -> str:
        """根据技术栈检测框架"""
        technologies = tech_stack.get("technologies", [])
        tech_names = [t.get("name", "").lower() for t in technologies]

        if "angular" in tech_names:
            return "angular"
        elif "react" in tech_names or "next.js" in tech_names or "gatsby" in tech_names:
            return "react"
        elif "vue.js" in tech_names or "nuxt.js" in tech_names:
            return "vue"

        return "unknown"

    async def _prerender_angular(
        self,
        page: Page,
        base_url: str,
    ) -> dict[str, str]:
        """预渲染 Angular 应用的所有路由"""
        results = {}

        # 尝试从 window 对象获取路由配置
        routes = await page.evaluate("""
            () => {
                // 尝试获取 Angular 路由
                if (window.ng && window.ng.getRouter) {
                    try {
                        const router = window.ng.getRouter();
                        return router.config.map(r => ({
                            path: r.path || '',
                            component: r.component?.name || null,
                            loadComponent: !!r.loadComponent
                        }));
                    } catch(e) {}
                }

                // 尝试从 DOM 查找路由链接
                const links = Array.from(document.querySelectorAll('a[href^="/"]'));
                const paths = links.map(a => a.getAttribute('href'))
                    .filter(href => href && href.startsWith('/') && !href.includes('#'));
                return [...new Set(paths)].map(p => ({ path: p }));
            }
        """)

        if not routes:
            # 如果无法获取路由，尝试常见的 Angular 路由
            routes = [
                {"path": "/"},
                {"path": "/home"},
                {"path": "/about"},
                {"path": "/product"},
                {"path": "/pricing"},
            ]

        console = __import__('rich.console', fromlist=['Console']).Console()
        console.print(f"[dim]  🔍 检测到 {len(routes)} 个 Angular 路由[/]")

        # 预渲染每个路由
        for route_info in routes:
            path = route_info.get("path", "")
            if not path or path == "**":
                continue

            try:
                # 导航到路由
                full_url = base_url.rstrip("/") + path
                await page.goto(full_url, wait_until="networkidle", timeout=30000)
                await page.wait_for_timeout(2000)  # 等待路由切换动画

                # 获取渲染后的 HTML
                html = await page.content()
                results[path] = html

                console.print(f"[dim]    ✓ 预渲染路由: {path}[/]")
            except Exception as e:
                console.print(f"[dim]    ✗ 路由渲染失败: {path} - {e}[/]")

        return results

    async def _prerender_react(
        self,
        page: Page,
        base_url: str,
    ) -> dict[str, str]:
        """预渲染 React Router 应用"""
        results = {}

        # 尝试从 React Router 获取路由
        routes = await page.evaluate("""
            () => {
                // 尝试查找 React Router 的 routes
                if (window.__REACT_ROUTER_CONTEXT__ || window.__reactRouterContext) {
                    // React Router v6
                    const context = window.__REACT_ROUTER_CONTEXT__ || window.__reactRouterContext;
                    return context?.matches?.map(m => ({ path: m.pathname })) || [];
                }

                // 尝试从 DOM 查找路由链接
                const links = Array.from(document.querySelectorAll('a[href^="/"]'));
                const paths = links.map(a => a.getAttribute('href'))
                    .filter(href => href && href.startsWith('/') && href.length > 1);
                return [...new Set(paths)].map(p => ({ path: p }));
            }
        """)

        if not routes:
            routes = [{"path": "/"}]

        console = __import__('rich.console', fromlist=['Console']).Console()
        console.print(f"[dim]  🔍 检测到 {len(routes)} 个 React 路由[/]")

        for route_info in routes[:10]:  # 限制最多 10 个路由
            path = route_info.get("path", "")
            if not path:
                continue

            try:
                full_url = base_url.rstrip("/") + path
                await page.goto(full_url, wait_until="networkidle", timeout=30000)
                await page.wait_for_timeout(1500)

                html = await page.content()
                results[path] = html

                console.print(f"[dim]    ✓ 预渲染路由: {path}[/]")
            except Exception as e:
                console.print(f"[dim]    ✗ 路由渲染失败: {path}[/]")

        return results

    async def _prerender_vue(
        self,
        page: Page,
        base_url: str,
    ) -> dict[str, str]:
        """预渲染 Vue Router 应用"""
        results = {}

        # 尝试从 Vue Router 获取路由
        routes = await page.evaluate("""
            () => {
                // 尝试访问 Vue Router
                if (window.__VUE__ && window.__VUE__.config) {
                    // Vue 3
                    const app = window.__VUE__;
                    // 尝试获取 router
                }

                if (window.Vue && window.Vue.prototype) {
                    // Vue 2
                    const router = window.Vue.prototype.$router;
                    if (router && router.options && router.options.routes) {
                        return router.options.routes.map(r => ({
                            path: r.path,
                            name: r.name
                        }));
                    }
                }

                // 从 DOM 查找
                const links = Array.from(document.querySelectorAll('a[href^="/"], a[href^="#"]'));
                const paths = links.map(a => {
                    const href = a.getAttribute('href');
                    if (href && href.startsWith('/')) return href;
                    if (href && href.startsWith('#/')) return href.slice(1);
                    return null;
                }).filter(Boolean);

                return [...new Set(paths)].map(p => ({ path: p }));
            }
        """)

        if not routes:
            routes = [{"path": "/"}]

        console = __import__('rich.console', fromlist=['Console']).Console()
        console.print(f"[dim]  🔍 检测到 {len(routes)} 个 Vue 路由[/]")

        for route_info in routes[:10]:
            path = route_info.get("path", "")
            if not path:
                continue

            try:
                full_url = base_url.rstrip("/") + path
                await page.goto(full_url, wait_until="networkidle", timeout=30000)
                await page.wait_for_timeout(1500)

                html = await page.content()
                results[path] = html

                console.print(f"[dim]    ✓ 预渲染路由: {path}[/]")
            except Exception as e:
                console.print(f"[dim]    ✗ 路由渲染失败: {path}[/]")

        return results

    async def _prerender_generic(
        self,
        page: Page,
        base_url: str,
    ) -> dict[str, str]:
        """通用预渲染方案"""
        results = {"/": await page.content()}

        # 尝试从页面链接发现路由
        links = await page.evaluate("""
            () => {
                const links = Array.from(document.querySelectorAll('a[href^="/"]'));
                return links.map(a => a.getAttribute('href'))
                    .filter(href => href && href.startsWith('/') && href.length > 1 && !href.includes('.'));
            }
        """)

        unique_paths = list(set(links))[:5]  # 限制数量

        console = __import__('rich.console', fromlist=['Console']).Console()
        console.print(f"[dim]  🔍 从页面链接发现 {len(unique_paths)} 个可能的路由[/]")

        for path in unique_paths:
            try:
                full_url = base_url.rstrip("/") + path
                await page.goto(full_url, wait_until="networkidle", timeout=30000)
                await page.wait_for_timeout(1500)

                html = await page.content()
                results[path] = html

                console.print(f"[dim]    ✓ 预渲染路由: {path}[/]")
            except Exception:
                pass

        return results
