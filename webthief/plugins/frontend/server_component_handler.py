"""
React Server Components 处理器：
- 检测 React Server Components (RSC)
- 分析服务端组件边界
- 识别客户端/服务端组件混合模式
- 处理 RSC payload 解析
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from playwright.async_api import Page, Response

from rich.console import Console
from rich.table import Table

console = Console()


class ServerComponentType(Enum):
    """服务端组件类型"""
    REACT_SERVER_COMPONENT = "React Server Component"
    NEXTJS_SERVER_COMPONENT = "Next.js Server Component"
    REMIX_SERVER_COMPONENT = "Remix Server Component"
    ASTRO_COMPONENT = "Astro Component"
    FRESH_ISLAND = "Fresh Island"
    SOLID_START = "Solid Start"
    UNKNOWN = "Unknown"


@dataclass
class ReactServerComponent:
    """React Server Component 信息"""
    component_id: str
    module_path: str
    is_client_boundary: bool = False
    is_server_boundary: bool = False
    exported_functions: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    chunk_files: list[str] = field(default_factory=list)
    props: dict[str, Any] = field(default_factory=dict)


@dataclass
class ServerComponentAnalysis:
    """Server Components 分析结果"""
    has_server_components: bool = False
    component_type: ServerComponentType = ServerComponentType.UNKNOWN
    total_components: int = 0
    server_components: list[ReactServerComponent] = field(default_factory=list)
    client_components: list[ReactServerComponent] = field(default_factory=list)
    rsc_payloads: list[str] = field(default_factory=list)
    flight_data: dict[str, Any] = field(default_factory=dict)
    streaming_enabled: bool = False
    confidence: int = 0


class ServerComponentHandler:
    """
    React Server Components 处理器
    检测和分析服务端组件架构
    """

    # Next.js RSC 检测模式
    NEXTJS_RSC_PATTERNS = [
        re.compile(r'__NEXT_DATA__'),
        re.compile(r'_rsc='),
        re.compile(r'/_next/data/'),
        re.compile(r'__next_f'),
        re.compile(r'next/dist'),
        re.compile(r'@next/font'),
    ]

    # React Flight 模式
    REACT_FLIGHT_PATTERNS = [
        re.compile(r'__flight__'),
        re.compile(r'__react_fiber'),
        re.compile(r'RSC_PAYLOAD'),
        re.compile(r'FlightData'),
        re.compile(r'SSRManifest'),
    ]

    # Remix 检测模式
    REMIX_PATTERNS = [
        re.compile(r'__remixContext'),
        re.compile(r'__remixManifest'),
        re.compile(r'@remix-run'),
        re.compile(r'/build/manifest-'),
    ]

    # Astro 检测模式
    ASTRO_PATTERNS = [
        re.compile(r'_astro/'),
        re.compile(r'astro\.runtime'),
        re.compile(r'data-astro-'),
        re.compile(r'astro-[a-z0-9]+'),
    ]

    # Fresh 检测模式
    FRESH_PATTERNS = [
        re.compile(r'fresh'),
        re.compile(r'/_frsh/'),
        re.compile(r'island-'),
        re.compile(r'data-island'),
    ]

    # Solid Start 检测模式
    SOLID_START_PATTERNS = [
        re.compile(r'solid-start'),
        re.compile(r'solid-js'),
        re.compile(r'/_solid/'),
    ]

    # RSC Payload 标记
    RSC_PAYLOAD_MARKERS = [
        b'$L',  # 模块引用
        b'$rsc',  # RSC 标记
        b'$I',  # 客户端引用
        b'$S',  # 服务端引用
        b'M1:',  # Flight 模块
        b'J0:',  # Flight JSON
        b'S0:',  # Flight Symbol
    ]

    def __init__(self, base_url: str):
        """
        初始化 Server Components 处理器

        Args:
            base_url: 页面基础 URL
        """
        self.base_url = base_url
        self.analysis = ServerComponentAnalysis()
        self._analyzed_urls: set[str] = set()
        self._rsc_chunks: dict[str, bytes] = {}

    async def detect(self, page: Page) -> ServerComponentAnalysis:
        """
        检测页面是否使用 Server Components

        Args:
            page: Playwright Page 对象

        Returns:
            ServerComponentAnalysis: 分析结果
        """
        console.print("[bold magenta]🔍 检测 Server Components...[/]")

        # 1. 检测全局对象和元数据
        await self._detect_global_objects(page)

        # 2. 检测 DOM 特征
        await self._detect_dom_features(page)

        # 3. 分析网络请求
        await self._analyze_network_requests(page)

        # 4. 检测 RSC Payload
        await self._detect_rsc_payloads(page)

        # 5. 分析组件边界
        await self._analyze_component_boundaries(page)

        # 最终确定分析结果
        self._finalize_analysis()

        return self.analysis

    async def _detect_global_objects(self, page: Page) -> None:
        """检测 Server Components 相关的全局对象"""
        try:
            global_checks = await page.evaluate("""
                () => {
                    return {
                        // Next.js
                        nextData: typeof window.__NEXT_DATA__ !== 'undefined',
                        nextRouter: typeof window.__nextRouter !== 'undefined',
                        nextF: typeof window.__next_f !== 'undefined',

                        // Remix
                        remixContext: typeof window.__remixContext !== 'undefined',
                        remixManifest: typeof window.__remixManifest !== 'undefined',
                        remixRouteModules: typeof window.__remixRouteModules !== 'undefined',

                        // React Flight
                        reactFlight: typeof window.__flight__ !== 'undefined',
                        reactFiber: typeof window.__react_fiber$ !== 'undefined',

                        // Astro
                        astro: typeof window.Astro !== 'undefined',

                        // Fresh
                        fresh: typeof window.fresh !== 'undefined',
                    };
                }
            """)

            if global_checks.get('nextData'):
                self.analysis.component_type = ServerComponentType.NEXTJS_SERVER_COMPONENT
                self.analysis.confidence = 85

                # 检查是否启用 RSC
                if global_checks.get('nextF'):
                    self.analysis.streaming_enabled = True

            if global_checks.get('remixContext') or global_checks.get('remixManifest'):
                self.analysis.component_type = ServerComponentType.REMIX_SERVER_COMPONENT
                self.analysis.confidence = max(self.analysis.confidence, 80)

            if global_checks.get('reactFlight'):
                self.analysis.component_type = ServerComponentType.REACT_SERVER_COMPONENT
                self.analysis.confidence = max(self.analysis.confidence, 90)

            if global_checks.get('astro'):
                self.analysis.component_type = ServerComponentType.ASTRO_COMPONENT
                self.analysis.confidence = max(self.analysis.confidence, 85)

            if global_checks.get('fresh'):
                self.analysis.component_type = ServerComponentType.FRESH_ISLAND
                self.analysis.confidence = max(self.analysis.confidence, 80)

        except Exception as e:
            console.print(f"[yellow]  ⚠ 全局对象检测失败: {e}[/]")

    async def _detect_dom_features(self, page: Page) -> None:
        """检测 DOM 中的 Server Components 特征"""
        try:
            dom_info = await page.evaluate("""
                () => {
                    const result = {
                        nextRoot: false,
                        rscMarkers: [],
                        clientHints: [],
                        preloadLinks: [],
                    };

                    // Next.js root
                    const nextRoot = document.getElementById('__next');
                    if (nextRoot) {
                        result.nextRoot = true;
                    }

                    // RSC 相关的 script 标签
                    document.querySelectorAll('script').forEach(script => {
                        const type = script.type || '';
                        const src = script.src || '';
                        const id = script.id || '';

                        if (type.includes('json') || id.includes('__NEXT_DATA__')) {
                            result.rscMarkers.push({
                                type: type,
                                id: id,
                                src: src,
                            });
                        }
                    });

                    // 预加载链接
                    document.querySelectorAll('link[rel="preload"], link[rel="modulepreload"]').forEach(link => {
                        const href = link.href || '';
                        if (href.includes('_rsc') || href.includes('flight') ||
                            href.includes('chunks') || href.includes('app-build-manifest')) {
                            result.preloadLinks.push(href);
                        }
                    });

                    return result;
                }
            """)

            if dom_info.get('nextRoot'):
                if self.analysis.component_type == ServerComponentType.UNKNOWN:
                    self.analysis.component_type = ServerComponentType.NEXTJS_SERVER_COMPONENT
                    self.analysis.confidence = max(self.analysis.confidence, 60)

            for link in dom_info.get('preloadLinks', []):
                if '_rsc' in link:
                    self.analysis.rsc_payloads.append(link)
                    self.analysis.streaming_enabled = True

        except Exception as e:
            console.print(f"[yellow]  ⚠ DOM 特征检测失败: {e}[/]")

    async def _analyze_network_requests(self, page: Page) -> None:
        """分析网络请求中的 RSC 特征"""
        try:
            # 获取页面加载的资源列表
            resources = await page.evaluate("""
                () => {
                    return performance.getEntriesByType('resource')
                        .filter(r => r.initiatorType === 'script' || r.initiatorType === 'fetch')
                        .map(r => ({
                            name: r.name,
                            type: r.initiatorType,
                            duration: r.duration,
                        }));
                }
            """)

            for resource in resources:
                url = resource.get('name', '')

                # 检测 RSC 相关请求
                if '_rsc=' in url:
                    self.analysis.rsc_payloads.append(url)
                    self.analysis.streaming_enabled = True

                if '/_next/data/' in url:
                    self.analysis.confidence = max(self.analysis.confidence, 70)

                if 'flight-data' in url or 'manifest' in url:
                    self.analysis.rsc_payloads.append(url)

        except Exception as e:
            console.print(f"[yellow]  ⚠ 网络请求分析失败: {e}[/]")

    async def _detect_rsc_payloads(self, page: Page) -> None:
        """检测和解析 RSC Payload"""
        try:
            # 尝试获取 __NEXT_DATA__ 中的 RSC 信息
            next_data = await page.evaluate("""
                () => {
                    const script = document.getElementById('__NEXT_DATA__');
                    if (script) {
                        try {
                            return JSON.parse(script.textContent);
                        } catch (e) {
                            return null;
                        }
                    }
                    return null;
                }
            """)

            if next_data:
                self.analysis.flight_data = next_data

                # 分析 buildId 和页面信息
                build_id = next_data.get('buildId')
                if build_id:
                    self.analysis.confidence = max(self.analysis.confidence, 75)

                # 分析页面组件
                page_props = next_data.get('props', {}).get('pageProps', {})
                if page_props:
                    self._extract_components_from_props(page_props)

            # 尝试获取 Remix manifest
            remix_manifest = await page.evaluate("""
                () => {
                    if (window.__remixManifest) {
                        return window.__remixManifest;
                    }
                    return null;
                }
            """)

            if remix_manifest:
                self._parse_remix_manifest(remix_manifest)

        except Exception as e:
            console.print(f"[yellow]  ⚠ RSC Payload 检测失败: {e}[/]")

    def _extract_components_from_props(self, props: dict[str, Any]) -> None:
        """从页面 props 中提取组件信息"""
        # 检查是否有服务端组件特有的属性
        if '__rsc' in props or '__flight__' in props:
            self.analysis.has_server_components = True

        # 提取可能的组件 ID
        for key, value in props.items():
            if isinstance(value, dict):
                if 'componentId' in value or 'moduleId' in value:
                    component = ReactServerComponent(
                        component_id=value.get('componentId', str(hash(key))),
                        module_path=value.get('moduleId', ''),
                    )
                    self.analysis.server_components.append(component)

    def _parse_remix_manifest(self, manifest: dict[str, Any]) -> None:
        """解析 Remix manifest"""
        routes = manifest.get('routes', {})

        for route_id, route_info in routes.items():
            if isinstance(route_info, dict):
                component = ReactServerComponent(
                    component_id=route_id,
                    module_path=route_info.get('module', ''),
                    chunk_files=route_info.get('imports', []),
                )

                # Remix 中所有路由组件默认是服务端渲染的
                self.analysis.server_components.append(component)

        self.analysis.total_components = len(self.analysis.server_components)

    async def _analyze_component_boundaries(self, page: Page) -> None:
        """分析客户端/服务端组件边界"""
        try:
            # 检测客户端组件标记
            client_components = await page.evaluate("""
                () => {
                    const components = [];

                    // 检查 React DevTools 可见的组件
                    const rootElements = document.querySelectorAll('[data-reactroot], [data-reactid]');

                    // 检查使用 "use client" 指令的组件特征
                    document.querySelectorAll('script[src]').forEach(script => {
                        const src = script.src;
                        if (src.includes('client-') || src.includes('client.') ||
                            src.includes('chunks/app/') || src.includes('pages/')) {
                            components.push({
                                src: src,
                                type: 'client',
                            });
                        }
                    });

                    return components;
                }
            """)

            for comp in client_components:
                src = comp.get('src', '')
                component = ReactServerComponent(
                    component_id=src.split('/')[-1].replace('.js', ''),
                    module_path=src,
                    is_client_boundary=True,
                )
                self.analysis.client_components.append(component)

            self.analysis.total_components = (
                len(self.analysis.server_components) +
                len(self.analysis.client_components)
            )

        except Exception as e:
            console.print(f"[yellow]  ⚠ 组件边界分析失败: {e}[/]")

    def _finalize_analysis(self) -> None:
        """最终确定分析结果"""
        self.analysis.has_server_components = (
            self.analysis.component_type != ServerComponentType.UNKNOWN or
            len(self.analysis.server_components) > 0 or
            len(self.analysis.rsc_payloads) > 0
        )

        # 如果检测到 RSC payloads 但置信度较低，提升置信度
        if self.analysis.rsc_payloads and self.analysis.confidence < 70:
            self.analysis.confidence = 70

    def analyze_response(self, response: Response) -> None:
        """
        分析响应内容中的 Server Components 特征

        Args:
            response: Playwright Response 对象
        """
        url = response.url
        if url in self._analyzed_urls:
            return
        self._analyzed_urls.add(url)

        self._check_url_patterns(url)
        self._check_response_headers(response.headers)

    def _check_url_patterns(self, url: str) -> None:
        """检查 URL 模式"""
        pattern_groups = [
            (self.NEXTJS_RSC_PATTERNS, ServerComponentType.NEXTJS_SERVER_COMPONENT),
            (self.REMIX_PATTERNS, ServerComponentType.REMIX_SERVER_COMPONENT),
        ]

        for patterns, component_type in pattern_groups:
            for pattern in patterns:
                if pattern.search(url):
                    if self.analysis.component_type == ServerComponentType.UNKNOWN:
                        self.analysis.component_type = component_type
                    self.analysis.confidence = max(self.analysis.confidence, 60)
                    return

    def _check_response_headers(self, headers: dict) -> None:
        """检查响应头"""
        accept = headers.get('accept', '').lower()
        content_type = headers.get('content-type', '').lower()

        # RSC 请求通常有特定的 Accept 头
        if 'text/x-component' in accept or 'rsc' in accept:
            self.analysis.has_server_components = True
            self.analysis.confidence = max(self.analysis.confidence, 85)

        # 检查响应头
        if 'text/x-component' in content_type or 'rsc' in content_type:
            self.analysis.has_server_components = True
            self.analysis.streaming_enabled = True
            self.analysis.confidence = max(self.analysis.confidence, 95)

    def get_render_strategy(self) -> dict[str, Any]:
        """
        根据 Server Components 类型返回渲染策略建议

        Returns:
            渲染策略配置字典
        """
        strategy = {
            "wait_for_hydration": False,
            "hydration_timeout": 5000,
            "wait_for_flight_data": False,
            "streaming_support": False,
            "recommendations": [],
        }

        if not self.analysis.has_server_components:
            return strategy

        if self.analysis.component_type == ServerComponentType.NEXTJS_SERVER_COMPONENT:
            strategy.update({
                "wait_for_hydration": True,
                "hydration_timeout": 8000,
                "wait_for_flight_data": True,
                "streaming_support": self.analysis.streaming_enabled,
                "recommendations": [
                    "Next.js RSC: 等待 React hydration 完成",
                    "Next.js RSC: 注意服务端组件的数据加载",
                    "Next.js RSC: 检查 __NEXT_DATA__ 完整性",
                ],
            })

            if self.analysis.streaming_enabled:
                strategy["recommendations"].append(
                    "Next.js: 启用流式渲染支持"
                )

        elif self.analysis.component_type == ServerComponentType.REMIX_SERVER_COMPONENT:
            strategy.update({
                "wait_for_hydration": True,
                "hydration_timeout": 6000,
                "recommendations": [
                    "Remix: 等待 loader 数据加载",
                    "Remix: 注意路由过渡动画",
                ],
            })

        elif self.analysis.component_type == ServerComponentType.ASTRO_COMPONENT:
            strategy.update({
                "wait_for_hydration": True,
                "hydration_timeout": 4000,
                "recommendations": [
                    "Astro: 等待岛屿组件水合",
                    "Astro: 注意 client:* 指令组件",
                ],
            })

        elif self.analysis.component_type == ServerComponentType.FRESH_ISLAND:
            strategy.update({
                "wait_for_hydration": True,
                "hydration_timeout": 5000,
                "recommendations": [
                    "Fresh: 等待 Islands 交互激活",
                    "Fresh: 注意部分水合行为",
                ],
            })

        return strategy

    def print_summary(self) -> None:
        """打印 Server Components 分析摘要"""
        if not self.analysis.has_server_components:
            console.print("[dim]  未检测到 Server Components[/]")
            return

        self._print_component_info()
        self._print_server_components()
        self._print_client_components()
        self._print_rsc_payloads()
        self._print_render_recommendations()

    def _print_component_info(self) -> None:
        """打印组件信息"""
        console.print(f"\n[bold cyan]⚛ Server Components 检测[/]")
        console.print(f"  组件类型: [green]{self.analysis.component_type.value}[/]")
        console.print(f"  置信度: [yellow]{self.analysis.confidence}%[/]")
        console.print(f"  流式渲染: {'[green]✓[/]' if self.analysis.streaming_enabled else '[dim]-[/]'}")

    def _print_server_components(self) -> None:
        """打印服务端组件"""
        if not self.analysis.server_components:
            return

        console.print(f"\n[bold]服务端组件 ({len(self.analysis.server_components)}):[/]")
        for comp in self.analysis.server_components[:5]:
            console.print(f"  • {comp.component_id}")
        if len(self.analysis.server_components) > 5:
            console.print(f"  ... 还有 {len(self.analysis.server_components) - 5} 个")

    def _print_client_components(self) -> None:
        """打印客户端组件"""
        if not self.analysis.client_components:
            return

        console.print(f"\n[bold]客户端组件 ({len(self.analysis.client_components)}):[/]")
        for comp in self.analysis.client_components[:5]:
            console.print(f"  • {comp.component_id}")
        if len(self.analysis.client_components) > 5:
            console.print(f"  ... 还有 {len(self.analysis.client_components) - 5} 个")

    def _print_rsc_payloads(self) -> None:
        """打印 RSC Payloads"""
        if not self.analysis.rsc_payloads:
            return

        console.print(f"\n[bold]RSC Payloads:[/]")
        for payload in self.analysis.rsc_payloads[:3]:
            short = payload.split('/')[-1] if '/' in payload else payload
            console.print(f"  • {short}")

    def _print_render_recommendations(self) -> None:
        """打印渲染策略建议"""
        strategy = self.get_render_strategy()
        if not strategy.get("recommendations"):
            return

        console.print("\n[bold cyan]📋 渲染策略建议:[/]")
        for rec in strategy["recommendations"]:
            console.print(f"  • {rec}")

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式"""
        return {
            "has_server_components": self.analysis.has_server_components,
            "component_type": self.analysis.component_type.value,
            "confidence": self.analysis.confidence,
            "total_components": self.analysis.total_components,
            "server_components": [
                {
                    "component_id": comp.component_id,
                    "module_path": comp.module_path,
                    "is_server_boundary": comp.is_server_boundary,
                }
                for comp in self.analysis.server_components
            ],
            "client_components": [
                {
                    "component_id": comp.component_id,
                    "module_path": comp.module_path,
                    "is_client_boundary": comp.is_client_boundary,
                }
                for comp in self.analysis.client_components
            ],
            "rsc_payloads": self.analysis.rsc_payloads,
            "streaming_enabled": self.analysis.streaming_enabled,
            "render_strategy": self.get_render_strategy(),
        }
