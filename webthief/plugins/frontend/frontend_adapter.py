"""
前端架构适配器：
- 统一的前端架构检测入口
- 整合微前端、Server Components、依赖解析
- 提供渲染策略建议
- 与 Playwright 深度集成
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from playwright.async_api import Page, Response

from rich.console import Console
from rich.table import Table

from .dependency_resolver import DependencyResolver, DependencyGraph
from .micro_frontend_handler import (
    MicroFrontendHandler,
    MicroFrontendAnalysis,
    MicroFrontendType,
)
from .server_component_handler import (
    ServerComponentHandler,
    ServerComponentAnalysis,
    ServerComponentType,
)

console = Console()


class FrontendArchitecture(Enum):
    """前端架构类型"""
    TRADITIONAL = "传统多页应用"
    SPA = "单页应用 (SPA)"
    SSR = "服务端渲染 (SSR)"
    SSG = "静态站点生成 (SSG)"
    ISR = "增量静态再生 (ISR)"
    MICRO_FRONTEND = "微前端架构"
    SERVER_COMPONENTS = "服务端组件架构"
    HYBRID = "混合架构"
    UNKNOWN = "未知架构"


@dataclass
class FrontendConfig:
    """前端配置"""
    # 基础配置
    wait_after_load: int = 3
    scroll_enabled: bool = True
    scroll_pause: float = 0.5

    # SPA/SSR 配置
    hydration_wait: int = 0
    aggressive_interactions: bool = False
    lazy_load_activation: bool = True
    animation_freeze: bool = True

    # 微前端配置
    wait_for_sub_apps: bool = False
    sub_app_timeout: int = 5000
    isolate_sandbox: bool = False

    # Server Components 配置
    wait_for_hydration: bool = False
    hydration_timeout: int = 5000
    wait_for_flight_data: bool = False
    streaming_support: bool = False

    # 依赖加载配置
    preload_critical_deps: bool = True
    parallel_load_limit: int = 6

    # 网络配置
    extra_network_wait: int = 0

    # 建议列表
    recommendations: list[str] = field(default_factory=list)


@dataclass
class FrontendAnalysisResult:
    """前端分析结果"""
    architecture: FrontendArchitecture = FrontendArchitecture.UNKNOWN
    confidence: int = 0

    # 子分析结果
    micro_frontend_analysis: MicroFrontendAnalysis | None = None
    server_component_analysis: ServerComponentAnalysis | None = None
    dependency_graph: DependencyGraph | None = None

    # 检测到的特征
    is_spa: bool = False
    is_ssr: bool = False
    is_micro_frontend: bool = False
    has_server_components: bool = False
    has_animation: bool = False

    # 框架信息
    detected_frameworks: list[str] = field(default_factory=list)
    build_tools: list[str] = field(default_factory=list)

    # 配置
    config: FrontendConfig = field(default_factory=FrontendConfig)


class FrontendAdapter:
    """
    前端架构适配器
    统一检测和分析前端架构，提供渲染策略
    """

    def __init__(self, base_url: str):
        """
        初始化前端适配器

        Args:
            base_url: 页面基础 URL
        """
        self.base_url = base_url
        self.result = FrontendAnalysisResult()

        # 初始化子处理器
        self.micro_frontend_handler = MicroFrontendHandler(base_url)
        self.server_component_handler = ServerComponentHandler(base_url)
        self.dependency_resolver = DependencyResolver(base_url)

        # 分析状态
        self._analyzed = False
        self._response_analyzed_urls: set[str] = set()

    async def analyze(self, page: Page) -> FrontendAnalysisResult:
        """
        执行完整的前端架构分析

        Args:
            page: Playwright Page 对象

        Returns:
            FrontendAnalysisResult: 完整的分析结果
        """
        console.print("[bold cyan]🔍 开始前端架构分析...[/]")

        # 1. 基础架构检测
        await self._detect_basic_architecture(page)

        # 2. 微前端检测
        await self._analyze_micro_frontend(page)

        # 3. Server Components 检测
        await self._analyze_server_components(page)

        # 4. 依赖分析
        await self._analyze_dependencies(page)

        # 5. 综合判断架构类型
        self._determine_architecture()

        # 6. 生成渲染配置
        self._generate_config()

        self._analyzed = True
        return self.result

    async def _detect_basic_architecture(self, page: Page) -> None:
        """检测基础架构特征"""
        try:
            basic_info = await page.evaluate("""
                () => {
                    const info = {
                        // SPA 特征
                        hasReact: !!(window.React || window.__REACT_DEVTOOLS_GLOBAL_HOOK__),
                        hasVue: !!(window.Vue || window.__VUE__ || window.__vue_app__),
                        hasAngular: !!(window.ng || window.angular),
                        hasSvelte: !!document.querySelector('[class*="svelte-"]'),

                        // SSR 特征
                        hasNext: !!(window.__NEXT_DATA__ || document.getElementById('__next')),
                        hasNuxt: !!(window.__NUXT__ || document.getElementById('__nuxt')),
                        hasGatsby: !!(window.___loader || document.getElementById('___gatsby')),
                        hasRemix: !!(window.__remixContext || window.__remixManifest),
                        hasAstro: !!document.querySelector('[data-astro-root]'),

                        // 构建工具
                        hasWebpack: !!(window.__webpack_require__ || window.webpackChunk),
                        hasVite: !!window.__vite__,

                        // 动画库
                        hasGSAP: !!(window.gsap || window.TweenMax),
                        hasFramerMotion: false,
                        hasAOS: !!window.AOS,
                        hasLottie: !!window.lottie,

                        // 其他特征
                        isHydrated: false,
                        hasLazyImages: document.querySelectorAll('img[loading="lazy"], img[data-src]').length > 0,
                    };

                    // 检测 hydration 状态
                    if (info.hasReact) {
                        const root = document.getElementById('root') || document.getElementById('__next');
                        info.isHydrated = root && root._reactRootContainer !== undefined;
                    }

                    return info;
                }
            """)

            self._update_framework_detection(basic_info)
            self._update_build_tools(basic_info)
            self._update_animation_detection(basic_info)
            self._update_spa_status()

        except Exception as e:
            console.print(f"[yellow]  ⚠ 基础架构检测失败: {e}[/]")

    def _update_framework_detection(self, basic_info: dict) -> None:
        """更新框架检测结果"""
        frameworks = []

        framework_checks = [
            ('hasReact', 'React'),
            ('hasVue', 'Vue.js'),
            ('hasAngular', 'Angular'),
            ('hasSvelte', 'Svelte'),
        ]

        for check_key, framework_name in framework_checks:
            if basic_info.get(check_key):
                frameworks.append(framework_name)

        # SSR 框架
        ssr_checks = [
            ('hasNext', 'Next.js'),
            ('hasNuxt', 'Nuxt.js'),
            ('hasGatsby', 'Gatsby'),
            ('hasRemix', 'Remix'),
            ('hasAstro', 'Astro'),
        ]

        for check_key, framework_name in ssr_checks:
            if basic_info.get(check_key):
                frameworks.append(framework_name)
                if check_key in ('hasNext', 'hasNuxt', 'hasRemix'):
                    self.result.is_ssr = True

        self.result.detected_frameworks = list(set(frameworks))

    def _update_build_tools(self, basic_info: dict) -> None:
        """更新构建工具检测"""
        build_tools = []
        if basic_info.get('hasWebpack'):
            build_tools.append('Webpack')
        if basic_info.get('hasVite'):
            build_tools.append('Vite')
        self.result.build_tools = build_tools

    def _update_animation_detection(self, basic_info: dict) -> None:
        """更新动画检测"""
        self.result.has_animation = (
            basic_info.get('hasGSAP') or
            basic_info.get('hasAOS') or
            basic_info.get('hasLottie')
        )

    def _update_spa_status(self) -> None:
        """更新 SPA 状态"""
        self.result.is_spa = bool(self.result.detected_frameworks) and not self.result.is_ssr

    async def _analyze_micro_frontend(self, page: Page) -> None:
        """分析微前端架构"""
        try:
            self.result.micro_frontend_analysis = await self.micro_frontend_handler.detect(page)
            self.result.is_micro_frontend = self.result.micro_frontend_analysis.is_micro_frontend

            if self.result.is_micro_frontend:
                console.print(f"[green]  ✓ 检测到微前端: {self.result.micro_frontend_analysis.framework_type.value}[/]")

        except Exception as e:
            console.print(f"[yellow]  ⚠ 微前端分析失败: {e}[/]")

    async def _analyze_server_components(self, page: Page) -> None:
        """分析 Server Components"""
        try:
            self.result.server_component_analysis = await self.server_component_handler.detect(page)
            self.result.has_server_components = self.result.server_component_analysis.has_server_components

            if self.result.has_server_components:
                console.print(f"[green]  ✓ 检测到 Server Components: {self.result.server_component_analysis.component_type.value}[/]")

        except Exception as e:
            console.print(f"[yellow]  ⚠ Server Components 分析失败: {e}[/]")

    async def _analyze_dependencies(self, page: Page) -> None:
        """分析模块依赖"""
        try:
            self.result.dependency_graph = await self.dependency_resolver.analyze_page(page)

            if self.result.dependency_graph.modules:
                console.print(f"[green]  ✓ 分析了 {len(self.result.dependency_graph.modules)} 个模块依赖[/]")

                if self.result.dependency_graph.circular_dependencies:
                    console.print(f"[yellow]  ⚠ 检测到 {len(self.result.dependency_graph.circular_dependencies)} 个循环依赖[/]")

        except Exception as e:
            console.print(f"[yellow]  ⚠ 依赖分析失败: {e}[/]")

    def _determine_architecture(self) -> None:
        """综合判断前端架构类型"""
        # 优先级：微前端 > Server Components > SSR > SPA > 传统

        if self.result.is_micro_frontend:
            self.result.architecture = FrontendArchitecture.MICRO_FRONTEND
            self.result.confidence = self.result.micro_frontend_analysis.confidence if self.result.micro_frontend_analysis else 80
            return

        if self.result.has_server_components:
            self.result.architecture = FrontendArchitecture.SERVER_COMPONENTS
            self.result.confidence = self.result.server_component_analysis.confidence if self.result.server_component_analysis else 80
            return

        if self.result.is_ssr:
            # 判断是 SSR 还是混合架构
            if self.result.is_spa:
                self.result.architecture = FrontendArchitecture.HYBRID
            else:
                self.result.architecture = FrontendArchitecture.SSR
            self.result.confidence = 85
            return

        if self.result.is_spa:
            self.result.architecture = FrontendArchitecture.SPA
            self.result.confidence = 80
            return

        # 检查是否是传统网站
        if not self.result.detected_frameworks:
            self.result.architecture = FrontendArchitecture.TRADITIONAL
            self.result.confidence = 70
            return

        self.result.architecture = FrontendArchitecture.UNKNOWN

    def _generate_config(self) -> None:
        """生成渲染配置"""
        config = FrontendConfig()

        self._apply_animation_config(config)
        self._apply_spa_config(config)
        self._apply_ssr_config(config)
        self._apply_micro_frontend_config(config)
        self._apply_server_components_config(config)
        self._apply_dependency_config(config)
        self._apply_framework_specific_config(config)

        self.result.config = config

    def _apply_animation_config(self, config: FrontendConfig) -> None:
        """应用动画相关配置"""
        if self.result.has_animation:
            config.scroll_enabled = True
            config.scroll_pause = 0.8
            config.animation_freeze = False
            config.recommendations.append("动画库检测到，启用滚动触发动画")

    def _apply_spa_config(self, config: FrontendConfig) -> None:
        """应用 SPA 相关配置"""
        if self.result.is_spa:
            config.hydration_wait = 2
            config.aggressive_interactions = True
            config.lazy_load_activation = True
            config.recommendations.append("SPA 应用，等待 hydration 完成")

    def _apply_ssr_config(self, config: FrontendConfig) -> None:
        """应用 SSR 相关配置"""
        if self.result.is_ssr:
            config.hydration_wait = 3
            config.extra_network_wait = 2
            config.recommendations.append("SSR 应用，等待客户端水合")

    def _apply_micro_frontend_config(self, config: FrontendConfig) -> None:
        """应用微前端相关配置"""
        if not self.result.is_micro_frontend or not self.result.micro_frontend_analysis:
            return

        mf_strategy = self.micro_frontend_handler.get_render_strategy()
        config.wait_for_sub_apps = mf_strategy.get('wait_for_sub_apps', False)
        config.sub_app_timeout = mf_strategy.get('sub_app_timeout', 5000)
        config.isolate_sandbox = mf_strategy.get('isolate_sandbox', False)
        config.recommendations.extend(mf_strategy.get('recommendations', []))

    def _apply_server_components_config(self, config: FrontendConfig) -> None:
        """应用 Server Components 相关配置"""
        if not self.result.has_server_components or not self.result.server_component_analysis:
            return

        sc_strategy = self.server_component_handler.get_render_strategy()
        config.wait_for_hydration = sc_strategy.get('wait_for_hydration', False)
        config.hydration_timeout = sc_strategy.get('hydration_timeout', 5000)
        config.wait_for_flight_data = sc_strategy.get('wait_for_flight_data', False)
        config.streaming_support = sc_strategy.get('streaming_support', False)
        config.recommendations.extend(sc_strategy.get('recommendations', []))

    def _apply_dependency_config(self, config: FrontendConfig) -> None:
        """应用依赖优化配置"""
        if not self.result.dependency_graph or not self.result.dependency_graph.modules:
            return

        critical_path = self.result.dependency_graph.get_critical_path()
        if len(critical_path) > 5:
            config.extra_network_wait += 2
            config.recommendations.append(f"关键依赖路径较长 ({len(critical_path)} 层)，增加等待时间")

        if self.result.dependency_graph.circular_dependencies:
            config.recommendations.append(
                f"检测到 {len(self.result.dependency_graph.circular_dependencies)} 个循环依赖，可能影响加载"
            )

    def _apply_framework_specific_config(self, config: FrontendConfig) -> None:
        """应用框架特定配置"""
        framework_configs = {
            'Next.js': {'hydration_wait': 3, 'extra_network_wait': 2},
            'Nuxt.js': {'hydration_wait': 3},
            'Gatsby': {'hydration_wait': 2},
        }

        for framework, settings in framework_configs.items():
            if framework in self.result.detected_frameworks:
                if 'hydration_wait' in settings:
                    config.hydration_wait = max(config.hydration_wait, settings['hydration_wait'])
                if 'extra_network_wait' in settings:
                    config.extra_network_wait = max(config.extra_network_wait, settings['extra_network_wait'])

    def analyze_response(self, response: Response) -> None:
        """
        分析网络响应（在页面加载过程中调用）

        Args:
            response: Playwright Response 对象
        """
        url = response.url
        if url in self._response_analyzed_urls:
            return
        self._response_analyzed_urls.add(url)

        # 分发到子处理器
        self.micro_frontend_handler.analyze_response(response)
        self.server_component_handler.analyze_response(response)

    def get_config(self) -> FrontendConfig:
        """
        获取渲染配置

        Returns:
            FrontendConfig: 渲染配置对象
        """
        if not self._analyzed:
            console.print("[yellow]⚠ 尚未执行分析，返回默认配置[/]")

        return self.result.config

    def get_load_order(self) -> list[list[str]]:
        """
        获取优化后的模块加载顺序

        Returns:
            分层的模块 URL 列表
        """
        if not self.result.dependency_graph:
            return []

        return self.dependency_resolver.get_optimized_load_order()

    def print_summary(self) -> None:
        """打印分析摘要"""
        console.print("\n" + "=" * 60)
        console.print("[bold cyan]📊 前端架构分析报告[/]")
        console.print("=" * 60)

        self._print_architecture_info()
        self._print_detected_frameworks()
        self._print_build_tools()
        self._print_feature_flags()
        self._print_sub_analysis()
        self._print_render_config()
        self._print_recommendations()

        console.print("\n" + "=" * 60)

    def _print_architecture_info(self) -> None:
        """打印架构信息"""
        console.print(f"\n[bold]架构类型:[/] [green]{self.result.architecture.value}[/]")
        console.print(f"[bold]置信度:[/] [yellow]{self.result.confidence}%[/]")

    def _print_detected_frameworks(self) -> None:
        """打印检测到的框架"""
        if not self.result.detected_frameworks:
            return

        console.print(f"\n[bold]检测到的框架:[/]")
        for fw in self.result.detected_frameworks:
            console.print(f"  • {fw}")

    def _print_build_tools(self) -> None:
        """打印构建工具"""
        if not self.result.build_tools:
            return

        console.print(f"\n[bold]构建工具:[/]")
        for tool in self.result.build_tools:
            console.print(f"  • {tool}")

    def _print_feature_flags(self) -> None:
        """打印特征标记"""
        features = []
        if self.result.is_spa:
            features.append("SPA")
        if self.result.is_ssr:
            features.append("SSR")
        if self.result.is_micro_frontend:
            features.append("微前端")
        if self.result.has_server_components:
            features.append("Server Components")
        if self.result.has_animation:
            features.append("动画库")

        if features:
            console.print(f"\n[bold]特征标记:[/] {', '.join(features)}")

    def _print_sub_analysis(self) -> None:
        """打印子分析结果"""
        if self.result.is_micro_frontend:
            self.micro_frontend_handler.print_summary()

        if self.result.has_server_components:
            self.server_component_handler.print_summary()

        if self.result.dependency_graph and self.result.dependency_graph.modules:
            self.dependency_resolver.print_summary()

    def _print_render_config(self) -> None:
        """打印渲染配置"""
        config = self.result.config
        console.print(f"\n[bold cyan]⚙ 渲染配置:[/]")
        console.print(f"  加载后等待: {config.wait_after_load}s")
        console.print(f"  Hydration 等待: {config.hydration_wait}s")
        console.print(f"  额外网络等待: {config.extra_network_wait}s")
        console.print(f"  滚动启用: {'是' if config.scroll_enabled else '否'}")
        console.print(f"  懒加载激活: {'是' if config.lazy_load_activation else '否'}")

    def _print_recommendations(self) -> None:
        """打印建议"""
        if not self.result.config.recommendations:
            return

        console.print(f"\n[bold cyan]📋 渲染策略建议:[/]")
        for rec in self.result.config.recommendations:
            console.print(f"  • {rec}")

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式"""
        return {
            "architecture": self.result.architecture.value,
            "confidence": self.result.confidence,
            "is_spa": self.result.is_spa,
            "is_ssr": self.result.is_ssr,
            "is_micro_frontend": self.result.is_micro_frontend,
            "has_server_components": self.result.has_server_components,
            "has_animation": self.result.has_animation,
            "detected_frameworks": self.result.detected_frameworks,
            "build_tools": self.result.build_tools,
            "micro_frontend": self.micro_frontend_handler.to_dict() if self.result.is_micro_frontend else None,
            "server_components": self.server_component_handler.to_dict() if self.result.has_server_components else None,
            "dependencies": self.dependency_resolver.to_dict() if self.result.dependency_graph else None,
            "config": {
                "wait_after_load": self.result.config.wait_after_load,
                "hydration_wait": self.result.config.hydration_wait,
                "extra_network_wait": self.result.config.extra_network_wait,
                "scroll_enabled": self.result.config.scroll_enabled,
                "recommendations": self.result.config.recommendations,
            },
        }
