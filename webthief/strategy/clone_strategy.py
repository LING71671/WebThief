"""
克隆策略模块

定义网站克隆的策略枚举、策略选择器和降级处理逻辑。
根据网站特征自动选择最优克隆策略，并在无法完整复刻时生成限制说明文档。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..tech_analyzer import TechStack, RenderStrategy

from rich.console import Console
from rich.table import Table

console = Console()


class CloneStrategy(Enum):
    """
    克隆策略枚举

    定义不同场景下的克隆方式：
    - FULL: 完整克隆，适用于静态网站和传统服务端渲染站点
    - PARTIAL: 部分克隆（降级），适用于包含 WebGL/复杂交互的站点
    - STATIC_ONLY: 仅静态资源，适用于高度动态化的站点
    - SCREENSHOT: 仅截图，作为最后的降级手段
    """

    FULL = "full"
    PARTIAL = "partial"
    STATIC_ONLY = "static_only"
    SCREENSHOT = "screenshot"

    @property
    def display_name(self) -> str:
        """获取策略的中文显示名称"""
        names = {
            CloneStrategy.FULL: "完整克隆",
            CloneStrategy.PARTIAL: "部分克隆（降级）",
            CloneStrategy.STATIC_ONLY: "仅静态资源",
            CloneStrategy.SCREENSHOT: "仅截图",
        }
        return names.get(self, "未知策略")

    @property
    def description(self) -> str:
        """获取策略的详细描述"""
        descriptions = {
            CloneStrategy.FULL: "完整克隆网站的所有资源，包括 HTML、CSS、JS、图片、字体等，支持离线浏览。",
            CloneStrategy.PARTIAL: "克隆网站的主要静态资源，对于 WebGL、复杂动画等特性进行降级处理，可能需要本地服务器支持。",
            CloneStrategy.STATIC_ONLY: "仅下载静态资源（HTML、CSS、图片），放弃 JavaScript 动态功能，适合内容型网站。",
            CloneStrategy.SCREENSHOT: "仅生成页面截图，作为最后的降级手段，适用于无法克隆的复杂站点。",
        }
        return descriptions.get(self, "")


class LimitationType(Enum):
    """
    限制类型枚举

    定义克隆过程中可能遇到的各种限制类型
    """

    WEBGL = "webgl"
    WEBSOCKET = "websocket"
    AUTH_REQUIRED = "auth_required"
    DYNAMIC_CONTENT = "dynamic_content"
    THIRD_PARTY_EMBED = "third_party_embed"
    SERVICE_WORKER = "service_worker"
    CORS_RESTRICTION = "cors_restriction"
    DRM_PROTECTED = "drm_protected"
    CANVAS_FINGERPRINT = "canvas_fingerprint"
    GEO_RESTRICTION = "geo_restriction"
    RATE_LIMITED = "rate_limited"
    COMPLEX_ANIMATION = "complex_animation"
    REAL_TIME_DATA = "real_time_data"
    PAYWALL = "paywall"
    OTHER = "other"

    @property
    def display_name(self) -> str:
        """获取限制类型的中文显示名称"""
        names = {
            LimitationType.WEBGL: "WebGL 3D 内容",
            LimitationType.WEBSOCKET: "WebSocket 实时通信",
            LimitationType.AUTH_REQUIRED: "需要认证登录",
            LimitationType.DYNAMIC_CONTENT: "动态内容加载",
            LimitationType.THIRD_PARTY_EMBED: "第三方嵌入式内容",
            LimitationType.SERVICE_WORKER: "Service Worker 缓存",
            LimitationType.CORS_RESTRICTION: "CORS 跨域限制",
            LimitationType.DRM_PROTECTED: "DRM 保护内容",
            LimitationType.CANVAS_FINGERPRINT: "Canvas 指纹检测",
            LimitationType.GEO_RESTRICTION: "地理位置限制",
            LimitationType.RATE_LIMITED: "请求频率限制",
            LimitationType.COMPLEX_ANIMATION: "复杂动画效果",
            LimitationType.REAL_TIME_DATA: "实时数据更新",
            LimitationType.PAYWALL: "付费墙限制",
            LimitationType.OTHER: "其他限制",
        }
        return names.get(self, "未知限制")

    @property
    def severity(self) -> str:
        """获取限制的严重程度"""
        severity_map = {
            LimitationType.WEBGL: "medium",
            LimitationType.WEBSOCKET: "high",
            LimitationType.AUTH_REQUIRED: "critical",
            LimitationType.DYNAMIC_CONTENT: "medium",
            LimitationType.THIRD_PARTY_EMBED: "low",
            LimitationType.SERVICE_WORKER: "low",
            LimitationType.CORS_RESTRICTION: "medium",
            LimitationType.DRM_PROTECTED: "critical",
            LimitationType.CANVAS_FINGERPRINT: "low",
            LimitationType.GEO_RESTRICTION: "high",
            LimitationType.RATE_LIMITED: "medium",
            LimitationType.COMPLEX_ANIMATION: "low",
            LimitationType.REAL_TIME_DATA: "high",
            LimitationType.PAYWALL: "critical",
            LimitationType.OTHER: "medium",
        }
        return severity_map.get(self, "medium")


@dataclass
class LimitationRecord:
    """
    限制记录

    记录克隆过程中遇到的限制及其详细信息
    """

    limitation_type: LimitationType
    description: str
    affected_elements: list[str] = field(default_factory=list)
    workaround: str | None = None
    url: str | None = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_markdown(self) -> str:
        """转换为 Markdown 格式的字符串"""
        lines = [
            f"### {self.limitation_type.display_name}",
            "",
            f"**严重程度**: {self.limitation_type.severity.upper()}",
            "",
            f"**描述**: {self.description}",
            "",
        ]

        if self.affected_elements:
            lines.append("**受影响的元素**:")
            lines.append("")
            for element in self.affected_elements:
                lines.append(f"- {element}")
            lines.append("")

        if self.workaround:
            lines.append(f"**建议解决方案**: {self.workaround}")
            lines.append("")

        if self.url:
            lines.append(f"**相关 URL**: `{self.url}`")
            lines.append("")

        lines.append(f"**记录时间**: {self.timestamp}")
        lines.append("")

        return "\n".join(lines)


@dataclass
class StrategyResult:
    """
    策略选择结果

    包含选择的策略、推荐的渲染参数、检测到的限制等
    """

    strategy: CloneStrategy
    confidence: int = 100
    reasons: list[str] = field(default_factory=list)
    limitations: list[LimitationRecord] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    requires_local_server: bool = False
    requires_prerender: bool = False
    requires_auth: bool = False
    auth_instructions: str | None = None

    # 动画相关策略标志
    enable_mouse_simulation: bool = False
    enable_scroll_precision: bool = False
    enable_canvas_recording: bool = False
    enable_physics_capture: bool = False
    enable_animation_analyze: bool = False

    @property
    def has_limitations(self) -> bool:
        """是否存在限制"""
        return len(self.limitations) > 0

    @property
    def has_critical_limitations(self) -> bool:
        """是否存在严重限制"""
        return any(
            limitation.limitation_type.severity == "critical"
            for limitation in self.limitations
        )

    def add_limitation(
        self,
        limitation_type: LimitationType,
        description: str,
        affected_elements: list[str] | None = None,
        workaround: str | None = None,
        url: str | None = None,
    ) -> None:
        """添加限制记录"""
        self.limitations.append(
            LimitationRecord(
                limitation_type=limitation_type,
                description=description,
                affected_elements=affected_elements or [],
                workaround=workaround,
                url=url,
            )
        )

    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            "strategy": self.strategy.value,
            "strategy_display": self.strategy.display_name,
            "confidence": self.confidence,
            "reasons": self.reasons,
            "recommendations": self.recommendations,
            "requires_local_server": self.requires_local_server,
            "requires_prerender": self.requires_prerender,
            "requires_auth": self.requires_auth,
            "limitations": [
                {
                    "type": lim.limitation_type.value,
                    "type_display": lim.limitation_type.display_name,
                    "severity": lim.limitation_type.severity,
                    "description": lim.description,
                    "affected_elements": lim.affected_elements,
                    "workaround": lim.workaround,
                    "url": lim.url,
                    "timestamp": lim.timestamp,
                }
                for lim in self.limitations
            ],
            # 动画相关策略
            "enable_mouse_simulation": self.enable_mouse_simulation,
            "enable_scroll_precision": self.enable_scroll_precision,
            "enable_canvas_recording": self.enable_canvas_recording,
            "enable_physics_capture": self.enable_physics_capture,
            "enable_animation_analyze": self.enable_animation_analyze,
        }


class StrategySelector:
    """
    策略选择器

    根据网站的技术栈特征和检测结果，自动选择最优的克隆策略。
    """

    # SPA 框架列表
    SPA_FRAMEWORKS = frozenset({
        "React", "Vue.js", "Angular", "Svelte", "Next.js", "Nuxt.js",
        "Gatsby", "Astro", "Remix", "Alpine.js",
    })

    # SSR 框架列表
    SSR_FRAMEWORKS = frozenset({
        "Next.js", "Nuxt.js", "Gatsby", "Astro", "Remix",
    })

    # WebGL 相关库
    WEBGL_LIBRARIES = frozenset({
        "Three.js", "Babylon.js", "A-Frame", "PlayCanvas", "PixiJS",
    })

    # 动画库
    ANIMATION_LIBRARIES = frozenset({
        "GSAP", "Lottie", "Anime.js", "Motion One", "Framer Motion", "AOS",
    })

    # 需要认证的特征
    AUTH_INDICATORS = frozenset({
        "login", "signin", "auth", "oauth", "sso", "account",
    })

    def __init__(self) -> None:
        self._detected_features: dict[str, bool] = {}
        self._detected_technologies: set[str] = set()

    def select(
        self,
        tech_stack: TechStack | None = None,
        render_strategy: RenderStrategy | None = None,
        detected_features: dict[str, bool] | None = None,
        url: str | None = None,
    ) -> StrategyResult:
        """
        根据检测结果选择克隆策略

        Args:
            tech_stack: 技术栈分析结果
            render_strategy: 渲染策略建议
            detected_features: 检测到的特性字典
            url: 目标 URL

        Returns:
            StrategyResult: 策略选择结果
        """
        result = StrategyResult(strategy=CloneStrategy.FULL)

        # 合并检测到的特性
        if detected_features:
            self._detected_features.update(detected_features)

        # 提取技术栈信息
        if tech_stack:
            self._detected_technologies = {
                tech.name for tech in tech_stack.technologies
            }

        # 按优先级检测各种特征
        self._check_auth_requirements(result, url)
        self._check_webgl_content(result, tech_stack)
        self._check_websocket_usage(result)
        self._check_spa_framework(result, tech_stack)
        self._check_animation_complexity(result, tech_stack)
        self._check_third_party_embeds(result)
        self._check_service_worker(result)
        self._check_dynamic_content(result)

        # 根据限制调整策略
        self._adjust_strategy(result)

        # 生成推荐
        self._generate_recommendations(result, tech_stack, render_strategy)

        return result

    def _check_auth_requirements(self, result: StrategyResult, url: str | None) -> None:
        """检测认证需求"""
        # 检查 URL 是否包含认证关键词
        if url:
            url_lower = url.lower()
            for indicator in self.AUTH_INDICATORS:
                if indicator in url_lower:
                    result.requires_auth = True
                    result.add_limitation(
                        limitation_type=LimitationType.AUTH_REQUIRED,
                        description="目标页面可能需要认证登录才能访问完整内容。",
                        workaround="请使用 --auth-mode=manual-pause 参数，在浏览器中手动登录后再继续克隆。",
                        url=url,
                    )
                    result.reasons.append("检测到认证相关 URL 特征")
                    break

        # 检查特性标志
        if self._detected_features.get("has_login_form"):
            result.requires_auth = True
            result.add_limitation(
                limitation_type=LimitationType.AUTH_REQUIRED,
                description="页面包含登录表单，部分内容可能需要认证后才能访问。",
                affected_elements=["登录表单"],
                workaround="使用 --auth-mode=manual-pause 进行交互式登录。",
            )
            result.reasons.append("检测到登录表单")

        if self._detected_features.get("has_paywall"):
            result.add_limitation(
                limitation_type=LimitationType.PAYWALL,
                description="页面包含付费墙，部分内容需要付费订阅才能访问。",
                workaround="付费内容无法通过克隆获取，请考虑订阅后使用会话导入功能。",
            )
            result.reasons.append("检测到付费墙")

    def _check_webgl_content(self, result: StrategyResult, tech_stack: TechStack | None) -> None:
        """检测 WebGL 内容"""
        has_webgl = False
        webgl_libs: list[str] = []

        # 检查技术栈中的 WebGL 库
        if tech_stack:
            for tech in tech_stack.technologies:
                if tech.name in self.WEBGL_LIBRARIES:
                    has_webgl = True
                    webgl_libs.append(tech.name)

        # 检查特性标志
        if self._detected_features.get("has_webgl"):
            has_webgl = True

        if has_webgl:
            result.requires_local_server = True
            result.add_limitation(
                limitation_type=LimitationType.WEBGL,
                description="页面包含 WebGL 3D 内容，在 file:// 协议下可能无法正常渲染。",
                affected_elements=webgl_libs if webgl_libs else ["WebGL Canvas"],
                workaround="使用 --local-server 参数启动本地服务器，通过 http:// 协议访问克隆结果。",
            )
            result.reasons.append(f"检测到 WebGL 库: {', '.join(webgl_libs) if webgl_libs else 'WebGL'}")

    def _check_websocket_usage(self, result: StrategyResult) -> None:
        """检测 WebSocket 使用"""
        if self._detected_features.get("has_websocket"):
            result.add_limitation(
                limitation_type=LimitationType.WEBSOCKET,
                description="页面使用 WebSocket 进行实时通信，克隆后实时功能将无法工作。",
                affected_elements=["WebSocket 连接"],
                workaround="实时数据无法在离线环境中复刻，建议使用 --websocket-proxy 参数记录 WebSocket 消息。",
            )
            result.reasons.append("检测到 WebSocket 连接")

    def _check_spa_framework(self, result: StrategyResult, tech_stack: TechStack | None) -> None:
        """检测 SPA 框架"""
        is_spa = False
        is_ssr = False
        spa_frameworks: list[str] = []

        if tech_stack:
            is_spa = tech_stack.is_spa
            is_ssr = tech_stack.is_ssr

            for tech in tech_stack.technologies:
                if tech.name in self.SPA_FRAMEWORKS:
                    spa_frameworks.append(tech.name)

        if is_spa:
            result.requires_prerender = True
            result.reasons.append(f"检测到 SPA 框架: {', '.join(spa_frameworks)}")

            if is_ssr:
                result.reasons.append("检测到 SSR 框架，将进行预渲染处理")
            else:
                result.add_limitation(
                    limitation_type=LimitationType.DYNAMIC_CONTENT,
                    description="SPA 应用依赖 JavaScript 动态渲染内容，需要预渲染处理。",
                    affected_elements=spa_frameworks,
                    workaround="启用 SPA 预渲染功能，在克隆时等待内容加载完成。",
                )

    def _check_animation_complexity(self, result: StrategyResult, tech_stack: TechStack | None) -> None:
        """检测动画复杂度"""
        animation_libs: list[str] = []

        if tech_stack:
            for tech in tech_stack.technologies:
                if tech.name in self.ANIMATION_LIBRARIES:
                    animation_libs.append(tech.name)

        if animation_libs:
            result.add_limitation(
                limitation_type=LimitationType.COMPLEX_ANIMATION,
                description="页面使用复杂动画库，部分动画效果可能无法在离线环境完美复刻。",
                affected_elements=animation_libs,
                workaround="动画效果已尽可能保留，但某些交互触发的动画可能需要用户手动触发。",
            )
            result.reasons.append(f"检测到动画库: {', '.join(animation_libs)}")

            # 根据动画库启用相应策略
            self._configure_animation_strategies(result, animation_libs, tech_stack)

    def _configure_animation_strategies(
        self,
        result: StrategyResult,
        animation_libs: list[str],
        tech_stack: TechStack | None
    ) -> None:
        """
        根据检测到的动画库配置动画策略
        
        Args:
            result: 策略结果对象
            animation_libs: 检测到的动画库列表
            tech_stack: 技术栈信息
        """
        # 启用动画分析
        if len(animation_libs) > 0:
            result.enable_animation_analyze = True
            result.reasons.append("启用 CSS 动画分析以优化动画保留")

        # 检测 Canvas/WebGL 使用
        has_canvas = False
        has_webgl = False

        if tech_stack:
            for tech in tech_stack.technologies:
                if tech.name in self.WEBGL_LIBRARIES:
                    has_webgl = True
                if tech.name in ["Canvas", "Fabric.js", "Konva.js"]:
                    has_canvas = True

        # 启用 Canvas 录制
        if has_canvas or self._detected_features.get("has_canvas"):
            result.enable_canvas_recording = True
            result.reasons.append("启用 Canvas 录制以捕获动态绘制内容")

        # 启用 WebGL 捕获
        if has_webgl or self._detected_features.get("has_webgl"):
            result.enable_canvas_recording = True
            result.reasons.append("启用 WebGL 捕获以保存 3D 渲染结果")

        # 检测物理引擎
        physics_engines = ["Matter.js", "Box2D", "Cannon.js", "Ammo.js", "PhysX"]
        has_physics = False

        if tech_stack:
            for tech in tech_stack.technologies:
                if tech.name in physics_engines:
                    has_physics = True
                    break

        if has_physics:
            result.enable_physics_capture = True
            result.reasons.append("启用物理引擎捕获以保存物理模拟状态")

        # 检测交互密集型网站
        interactive_libs = ["GSAP", "Framer Motion", "Lottie", "Three.js"]
        has_interactive = any(lib in animation_libs for lib in interactive_libs)

        if has_interactive:
            result.enable_mouse_simulation = True
            result.reasons.append("启用鼠标轨迹模拟以触发交互式动画")

        # 检测滚动动画库
        scroll_libs = ["AOS", "ScrollTrigger", "ScrollMagic", "LocomotiveScroll", "Lenis"]
        has_scroll = any(lib in animation_libs for lib in scroll_libs)

        if has_scroll:
            result.enable_scroll_precision = True
            result.reasons.append("启用高精度滚动以捕获滚动触发动画")

    def _check_third_party_embeds(self, result: StrategyResult) -> None:
        """检测第三方嵌入式内容"""
        embeds: list[str] = []

        if self._detected_features.get("has_youtube_embed"):
            embeds.append("YouTube 视频")
        if self._detected_features.get("has_google_maps"):
            embeds.append("Google Maps")
        if self._detected_features.get("has_iframe_ads"):
            embeds.append("广告 iframe")
        if self._detected_features.get("has_social_widgets"):
            embeds.append("社交网络组件")

        if embeds:
            result.add_limitation(
                limitation_type=LimitationType.THIRD_PARTY_EMBED,
                description="页面包含第三方嵌入式内容，这些内容可能无法在离线环境正常显示。",
                affected_elements=embeds,
                workaround="第三方嵌入式内容需要联网访问，已保留嵌入代码但可能显示为空白或占位符。",
            )
            result.reasons.append(f"检测到第三方嵌入: {', '.join(embeds)}")

    def _check_service_worker(self, result: StrategyResult) -> None:
        """检测 Service Worker"""
        if self._detected_features.get("has_service_worker"):
            result.add_limitation(
                limitation_type=LimitationType.SERVICE_WORKER,
                description="页面注册了 Service Worker，离线缓存逻辑已被移除以避免冲突。",
                affected_elements=["Service Worker"],
                workaround="Service Worker 已被禁用，缓存策略由运行时兼容层处理。",
            )
            result.reasons.append("检测到 Service Worker")

    def _check_dynamic_content(self, result: StrategyResult) -> None:
        """检测动态内容"""
        if self._detected_features.get("has_infinite_scroll"):
            result.add_limitation(
                limitation_type=LimitationType.DYNAMIC_CONTENT,
                description="页面使用无限滚动加载内容，已尝试加载初始内容但可能不完整。",
                affected_elements=["无限滚动列表"],
                workaround="已执行滚动操作触发内容加载，但动态加载的内容可能有限。",
            )
            result.reasons.append("检测到无限滚动")

        if self._detected_features.get("has_lazy_load"):
            result.reasons.append("检测到懒加载图片")

    def _adjust_strategy(self, result: StrategyResult) -> None:
        """根据检测到的限制调整策略"""

        # 存在严重限制时的策略调整
        if result.has_critical_limitations:
            # 如果需要认证且没有其他可降级的内容
            if result.requires_auth and not result.limitations:
                result.strategy = CloneStrategy.SCREENSHOT
                result.confidence = 90
                return

            # 如果有付费墙
            has_paywall = any(
                lim.limitation_type == LimitationType.PAYWALL
                for lim in result.limitations
            )
            if has_paywall:
                result.strategy = CloneStrategy.STATIC_ONLY
                result.confidence = 85
                return

        # WebGL + WebSocket 组合 -> 部分克隆
        has_webgl = any(
            lim.limitation_type == LimitationType.WEBGL
            for lim in result.limitations
        )
        has_websocket = any(
            lim.limitation_type == LimitationType.WEBSOCKET
            for lim in result.limitations
        )

        if has_webgl:
            result.strategy = CloneStrategy.PARTIAL
            result.confidence = 90
            return

        if has_websocket:
            result.strategy = CloneStrategy.STATIC_ONLY
            result.confidence = 85
            return

        # 默认保持完整克隆
        result.strategy = CloneStrategy.FULL
        result.confidence = 95

    def _generate_recommendations(
        self,
        result: StrategyResult,
        tech_stack: TechStack | None,
        render_strategy: RenderStrategy | None,
    ) -> None:
        """生成推荐建议"""

        # 基于策略的推荐
        if result.strategy == CloneStrategy.PARTIAL:
            result.recommendations.append("建议使用 --local-server 参数启动本地服务器以获得最佳体验")

        if result.strategy == CloneStrategy.STATIC_ONLY:
            result.recommendations.append("已跳过 JavaScript 动态功能，如需完整体验请使用 --keep-js 参数")

        # 基于技术栈的推荐
        if tech_stack:
            if tech_stack.is_spa and not tech_stack.is_ssr:
                result.recommendations.append("SPA 应用已启用预渲染，建议增加 --extra-wait 参数确保内容加载完成")

            if tech_stack.has_animation_lib:
                result.recommendations.append("检测到动画库，建议增加滚动等待时间以触发所有动画效果")

        # 基于渲染策略的推荐
        if render_strategy and render_strategy.recommendations:
            result.recommendations.extend(render_strategy.recommendations)

        # 基于限制的推荐
        if result.requires_auth:
            result.recommendations.append("请使用 --auth-mode=manual-pause 进行交互式认证")

        if result.requires_local_server:
            result.recommendations.append("克隆结果需要通过本地服务器访问，请使用 --local-server 参数")

    def print_result(self, result: StrategyResult) -> None:
        """打印策略选择结果"""
        # 策略信息表
        table = Table(title="🎯 克隆策略分析", show_header=True, header_style="bold cyan")
        table.add_column("项目", style="yellow", width=25)
        table.add_column("值", style="green", width=45)

        table.add_row("选择策略", f"{result.strategy.display_name} ({result.strategy.value})")
        table.add_row("置信度", f"{result.confidence}%")
        table.add_row("需要本地服务器", "是" if result.requires_local_server else "否")
        table.add_row("需要预渲染", "是" if result.requires_prerender else "否")
        table.add_row("需要认证", "是" if result.requires_auth else "否")

        # 动画策略
        if any([
            result.enable_mouse_simulation,
            result.enable_scroll_precision,
            result.enable_canvas_recording,
            result.enable_physics_capture,
            result.enable_animation_analyze
        ]):
            table.add_row("", "")
            table.add_row("[bold cyan]动画增强策略", "")
            if result.enable_mouse_simulation:
                table.add_row("  🖱️ 鼠标轨迹模拟", "已启用")
            if result.enable_scroll_precision:
                table.add_row("  📜 高精度滚动", "已启用")
            if result.enable_canvas_recording:
                table.add_row("  🎨 Canvas 录制", "已启用")
            if result.enable_physics_capture:
                table.add_row("  ⚛️ 物理引擎捕获", "已启用")
            if result.enable_animation_analyze:
                table.add_row("  🎬 动画分析", "已启用")

        console.print(table)

        # 原因列表
        if result.reasons:
            console.print("\n[bold cyan]📋 检测依据:[/]")
            for reason in result.reasons:
                console.print(f"  • {reason}")

        # 推荐列表
        if result.recommendations:
            console.print("\n[bold cyan]💡 推荐操作:[/]")
            for rec in result.recommendations:
                console.print(f"  • {rec}")

        # 限制列表
        if result.has_limitations:
            console.print("\n[bold yellow]⚠️  已知限制:[/]")
            for lim in result.limitations:
                severity_color = {
                    "critical": "red",
                    "high": "yellow",
                    "medium": "cyan",
                    "low": "dim",
                }.get(lim.limitation_type.severity, "white")

                console.print(
                    f"  [{severity_color}]• {lim.limitation_type.display_name}: {lim.description}[/{severity_color}]"
                )


class LimitationsWriter:
    """
    限制说明文档生成器

    在输出目录生成 LIMITATIONS.md 文件，记录克隆过程中遇到的所有限制。
    """

    def __init__(self, output_dir: Path | str) -> None:
        self.output_dir = Path(output_dir)

    def write(self, result: StrategyResult, source_url: str) -> Path:
        """
        生成 LIMITATIONS.md 文件

        Args:
            result: 策略选择结果
            source_url: 源网站 URL

        Returns:
            生成的文件路径
        """
        content = self._generate_content(result, source_url)
        output_path = self.output_dir / "LIMITATIONS.md"
        output_path.write_text(content, encoding="utf-8")
        return output_path

    def _generate_content(self, result: StrategyResult, source_url: str) -> str:
        """生成 Markdown 内容"""
        lines = [
            "# 克隆限制说明",
            "",
            f"> 本文档由 WebThief 自动生成",
            f"> 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"> 源网站: {source_url}",
            "",
            "---",
            "",
            "## 克隆策略",
            "",
            f"**{result.strategy.display_name}**",
            "",
            f"{result.strategy.description}",
            "",
            f"- **置信度**: {result.confidence}%",
            f"- **需要本地服务器**: {'是' if result.requires_local_server else '否'}",
            f"- **需要预渲染**: {'是' if result.requires_prerender else '否'}",
            f"- **需要认证**: {'是' if result.requires_auth else '否'}",
            "",
        ]

        # 检测依据
        if result.reasons:
            lines.extend([
                "## 检测依据",
                "",
            ])
            for reason in result.reasons:
                lines.append(f"- {reason}")
            lines.append("")

        # 推荐操作
        if result.recommendations:
            lines.extend([
                "## 推荐操作",
                "",
            ])
            for rec in result.recommendations:
                lines.append(f"- {rec}")
            lines.append("")

        # 已知限制
        if result.has_limitations:
            lines.extend([
                "## 已知限制",
                "",
                "以下是克隆过程中检测到的限制，可能影响克隆结果的完整性：",
                "",
            ])

            # 按严重程度排序
            severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
            sorted_limitations = sorted(
                result.limitations,
                key=lambda x: severity_order.get(x.limitation_type.severity, 2),
            )

            for limitation in sorted_limitations:
                lines.append(limitation.to_markdown())
                lines.append("---")
                lines.append("")

        # 使用说明
        lines.extend([
            "## 使用说明",
            "",
        ])

        if result.requires_local_server:
            lines.extend([
                "### 启动本地服务器",
                "",
                "由于克隆结果包含需要 HTTP 协议才能正常工作的内容，请使用以下命令启动本地服务器：",
                "",
                "```bash",
                "cd " + str(self.output_dir),
                "python -m http.server 8080",
                "```",
                "",
                "然后在浏览器中访问 `http://localhost:8080`",
                "",
            ])

        if result.requires_auth:
            lines.extend([
                "### 认证说明",
                "",
                "部分内容需要认证后才能访问。如果已拥有账户，可以使用以下方式导入会话：",
                "",
                "```bash",
                "webthief clone <url> --auth-mode=manual-pause",
                "```",
                "",
            ])

        # 免责声明
        lines.extend([
            "## 免责声明",
            "",
            "本克隆结果仅供学习和研究目的使用。请遵守原网站的使用条款和版权规定。",
            "未经授权复制或分发受版权保护的内容可能违反法律。",
            "",
        ])

        return "\n".join(lines)

    def append_limitation(
        self,
        limitation: LimitationRecord,
        source_url: str,
    ) -> Path | None:
        """
        向现有的 LIMITATIONS.md 文件追加新的限制记录

        Args:
            limitation: 要追加的限制记录
            source_url: 源网站 URL

        Returns:
            更新后的文件路径，如果文件不存在则返回 None
        """
        output_path = self.output_dir / "LIMITATIONS.md"

        if not output_path.exists():
            return None

        existing_content = output_path.read_text(encoding="utf-8")

        # 在文件末尾追加新限制
        new_section = [
            "",
            "---",
            "",
            "## 新增限制",
            "",
            limitation.to_markdown(),
        ]

        updated_content = existing_content + "\n".join(new_section)
        output_path.write_text(updated_content, encoding="utf-8")

        return output_path
