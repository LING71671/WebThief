"""
网站类型智能检测器

检测网站类型并提供相应的处理建议：
- 静态网站：无需 JavaScript 渲染
- SPA 应用：需要 JavaScript 渲染
- 认证需求：需要登录才能访问
- WebGL/Canvas：需要特殊处理
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from playwright.async_api import Page

from rich.console import Console
from rich.table import Table

console = Console()


class WebsiteType(Enum):
    """网站类型枚举"""
    STATIC = "静态网站"
    SPA_REACT = "React SPA"
    SPA_VUE = "Vue SPA"
    SPA_ANGULAR = "Angular SPA"
    SPA_SVELTE = "Svelte SPA"
    SPA_OTHER = "其他 SPA"
    SSR = "服务端渲染"
    AUTH_REQUIRED = "需要认证"
    WEBGL_APP = "WebGL 应用"
    CANVAS_APP = "Canvas 应用"
    HYBRID = "混合型网站"
    UNKNOWN = "未知类型"


@dataclass
class FrameworkInfo:
    """框架信息"""
    name: str
    version: str | None = None
    confidence: int = 100
    evidence: str | None = None


@dataclass
class AuthInfo:
    """认证信息"""
    has_login_form: bool = False
    login_form_selectors: list[str] = field(default_factory=list)
    has_auth_wall: bool = False
    auth_type: str | None = None  # 'basic', 'oauth', 'form', 'custom'


@dataclass
class WebGLInfo:
    """WebGL 信息"""
    has_webgl: bool = False
    has_canvas: bool = False
    canvas_count: int = 0
    webgl_context_type: str | None = None  # 'webgl', 'webgl2', 'experimental-webgl'
    is_threejs: bool = False
    is_pixijs: bool = False


@dataclass
class WebsiteTypeResult:
    """网站类型检测结果"""
    website_type: WebsiteType
    frameworks: list[FrameworkInfo] = field(default_factory=list)
    auth_info: AuthInfo = field(default_factory=AuthInfo)
    webgl_info: WebGLInfo = field(default_factory=WebGLInfo)
    is_static: bool = False
    requires_js_rendering: bool = False
    confidence: int = 100
    recommendations: list[str] = field(default_factory=list)

    @property
    def is_spa(self) -> bool:
        """是否为 SPA 应用"""
        return self.website_type in {
            WebsiteType.SPA_REACT,
            WebsiteType.SPA_VUE,
            WebsiteType.SPA_ANGULAR,
            WebsiteType.SPA_SVELTE,
            WebsiteType.SPA_OTHER,
        }

    @property
    def needs_authentication(self) -> bool:
        """是否需要认证"""
        return self.auth_info.has_login_form or self.auth_info.has_auth_wall


class WebsiteTypeDetector:
    """
    网站类型智能检测器

    通过多种方式检测网站类型：
    1. HTML 结构分析
    2. JavaScript 框架特征检测
    3. DOM 元素检测
    4. Canvas/WebGL 检测
    5. 登录表单检测
    """

    # SPA 框架检测模式
    SPA_SIGNATURES = {
        "react": {
            "patterns": [
                r"data-reactroot",
                r"data-reactid",
                r"_reactRootContainer",
                r"__REACT_DEVTOOLS_GLOBAL_HOOK__",
            ],
            "dom_check": """
                !!(window.React ||
                   window.__REACT_DEVTOOLS_GLOBAL_HOOK__ ||
                   document.querySelector('[data-reactroot], [data-reactid]') ||
                   Object.keys(document.documentElement).some(k => k.startsWith('__react')))
            """,
            "root_selectors": ["[data-reactroot]", "[data-reactid]", "#root", "#app"],
        },
        "vue": {
            "patterns": [
                r"data-v-[a-f0-9]+",
                r"__VUE__",
                r"__vue_app__",
                r"data-v-app",
            ],
            "dom_check": """
                !!(window.Vue ||
                   window.__VUE__ ||
                   window.__vue_app__ ||
                   document.querySelector('[data-v-]') ||
                   document.querySelector('[data-v-app]'))
            """,
            "root_selectors": ["[data-v-app]", "#app", "#vue-app"],
        },
        "angular": {
            "patterns": [
                r"ng-version",
                r"ng-app",
                r"ng-controller",
                r"_ngcontent-",
                r"_nghost-",
                r"app-root",
            ],
            "dom_check": """
                !!(window.ng ||
                   window.angular ||
                   document.querySelector('[ng-version], [ng-app], [_ngcontent-]') ||
                   document.querySelector('app-root'))
            """,
            "root_selectors": ["app-root", "[ng-app]", "#app"],
        },
        "svelte": {
            "patterns": [
                r"class=\"svelte-[a-z0-9]+\"",
                r"svelte-",
            ],
            "dom_check": """
                !!(document.querySelector('[class*="svelte-"]') ||
                   Array.from(document.querySelectorAll('style')).some(s =>
                       s.textContent.includes('svelte-')))
            """,
            "root_selectors": ["[class*='svelte-']"],
        },
    }

    # 登录表单检测模式
    LOGIN_FORM_PATTERNS = {
        "form_selectors": [
            "form[action*='login']",
            "form[action*='signin']",
            "form[action*='auth']",
            "form[id*='login']",
            "form[id*='signin']",
            "form[class*='login']",
            "form[class*='signin']",
        ],
        "input_patterns": [
            "input[type='password']",
            "input[name*='password']",
            "input[name*='passwd']",
            "input[name*='pwd']",
            "input[placeholder*='密码']",
            "input[placeholder*='Password']",
        ],
        "button_patterns": [
            "button[type='submit'][class*='login']",
            "button[type='submit'][class*='signin']",
            "input[type='submit'][value*='登录']",
            "input[type='submit'][value*='Login']",
            "input[type='submit'][value*='Sign']",
        ],
        "auth_wall_indicators": [
            ".login-required",
            ".auth-required",
            ".signin-required",
            "#login-modal",
            "#auth-modal",
            "[class*='auth-wall']",
            "[class*='paywall']",
        ],
    }

    # WebGL/Canvas 检测模式
    WEBGL_PATTERNS = {
        "threejs": {
            "patterns": [r"three\.min\.js", r"three\.js", r"THREE\."],
            "dom_check": "!!window.THREE",
        },
        "pixijs": {
            "patterns": [r"pixi\.min\.js", r"pixi\.js", r"PIXI\."],
            "dom_check": "!!window.PIXI",
        },
        "babylonjs": {
            "patterns": [r"babylon\.js", r"BABYLON\."],
            "dom_check": "!!window.BABYLON",
        },
    }

    def __init__(self):
        self._detected_frameworks: list[FrameworkInfo] = []
        self._auth_info: AuthInfo = AuthInfo()
        self._webgl_info: WebGLInfo = WebGLInfo()
        self._is_static: bool = False
        self._analyzed_urls: set[str] = set()

    async def detect(self, page: Page) -> WebsiteTypeResult:
        """
        检测网站类型

        Args:
            page: Playwright Page 对象

        Returns:
            WebsiteTypeResult: 检测结果
        """
        # 重置状态
        self._detected_frameworks = []
        self._auth_info = AuthInfo()
        self._webgl_info = WebGLInfo()
        self._is_static = True

        # 执行各项检测
        await self._detect_spa_frameworks(page)
        await self._detect_auth_requirements(page)
        await self._detect_webgl_canvas(page)
        await self._detect_static_indicators(page)

        # 综合判断网站类型
        website_type = self._determine_website_type()
        confidence = self._calculate_confidence()
        recommendations = self._generate_recommendations(website_type)

        return WebsiteTypeResult(
            website_type=website_type,
            frameworks=self._detected_frameworks,
            auth_info=self._auth_info,
            webgl_info=self._webgl_info,
            is_static=self._is_static,
            requires_js_rendering=not self._is_static,
            confidence=confidence,
            recommendations=recommendations,
        )

    async def _detect_spa_frameworks(self, page: Page) -> None:
        """检测 SPA 框架"""
        for framework_name, signatures in self.SPA_SIGNATURES.items():
            detected = False
            evidence_list = []

            # DOM 检测
            dom_check = signatures.get("dom_check")
            if dom_check:
                try:
                    result = await page.evaluate(dom_check)
                    if result:
                        detected = True
                        evidence_list.append("DOM 特征检测")
                except Exception:
                    pass

            # 模式匹配检测
            patterns = signatures.get("patterns", [])
            for pattern in patterns:
                try:
                    html_content = await page.content()
                    if re.search(pattern, html_content, re.IGNORECASE):
                        detected = True
                        evidence_list.append(f"模式匹配: {pattern}")
                        break
                except Exception:
                    pass

            # 根元素检测
            root_selectors = signatures.get("root_selectors", [])
            for selector in root_selectors:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        detected = True
                        evidence_list.append(f"根元素: {selector}")
                        break
                except Exception:
                    pass

            if detected:
                self._detected_frameworks.append(FrameworkInfo(
                    name=framework_name,
                    confidence=95 if len(evidence_list) > 1 else 80,
                    evidence="; ".join(evidence_list),
                ))
                self._is_static = False

    async def _detect_auth_requirements(self, page: Page) -> None:
        """检测认证需求"""
        login_selectors = []

        # 检测登录表单
        for selector in self.LOGIN_FORM_PATTERNS["form_selectors"]:
            try:
                element = await page.query_selector(selector)
                if element:
                    self._auth_info.has_login_form = True
                    login_selectors.append(selector)
            except Exception:
                pass

        # 检测密码输入框
        for selector in self.LOGIN_FORM_PATTERNS["input_patterns"]:
            try:
                element = await page.query_selector(selector)
                if element:
                    self._auth_info.has_login_form = True
                    login_selectors.append(selector)
            except Exception:
                pass

        # 检测登录按钮
        for selector in self.LOGIN_FORM_PATTERNS["button_patterns"]:
            try:
                element = await page.query_selector(selector)
                if element:
                    self._auth_info.has_login_form = True
                    login_selectors.append(selector)
            except Exception:
                pass

        # 检测认证墙
        for selector in self.LOGIN_FORM_PATTERNS["auth_wall_indicators"]:
            try:
                element = await page.query_selector(selector)
                if element:
                    self._auth_info.has_auth_wall = True
                    login_selectors.append(selector)
            except Exception:
                pass

        self._auth_info.login_form_selectors = list(set(login_selectors))

        # 判断认证类型
        if self._auth_info.has_login_form:
            try:
                # 检查是否有 OAuth 标识
                oauth_indicators = await page.evaluate("""
                    () => {
                        const text = document.body.innerText.toLowerCase();
                        return text.includes('oauth') ||
                               text.includes('sign in with') ||
                               text.includes('login with') ||
                               !!document.querySelector('[class*="oauth"]') ||
                               !!document.querySelector('[class*="social-login"]');
                    }
                """)
                if oauth_indicators:
                    self._auth_info.auth_type = "oauth"
                else:
                    self._auth_info.auth_type = "form"
            except Exception:
                self._auth_info.auth_type = "form"

    async def _detect_webgl_canvas(self, page: Page) -> None:
        """检测 WebGL/Canvas 应用"""
        try:
            # 检测 Canvas 元素
            canvas_info = await page.evaluate("""
                () => {
                    const canvases = document.querySelectorAll('canvas');
                    const result = {
                        count: canvases.length,
                        hasWebGL: false,
                        webglType: null
                    };

                    canvases.forEach(canvas => {
                        try {
                            const gl = canvas.getContext('webgl2') ||
                                      canvas.getContext('webgl') ||
                                      canvas.getContext('experimental-webgl');
                            if (gl) {
                                result.hasWebGL = true;
                                if (canvas.getContext('webgl2')) {
                                    result.webglType = 'webgl2';
                                } else if (canvas.getContext('webgl')) {
                                    result.webglType = 'webgl';
                                } else {
                                    result.webglType = 'experimental-webgl';
                                }
                            }
                        } catch (e) {}
                    });

                    return result;
                }
            """)

            self._webgl_info.canvas_count = canvas_info.get("count", 0)
            self._webgl_info.has_canvas = canvas_info.get("count", 0) > 0
            self._webgl_info.has_webgl = canvas_info.get("hasWebGL", False)
            self._webgl_info.webgl_context_type = canvas_info.get("webglType")

            # 检测 WebGL 库
            for lib_name, patterns in self.WEBGL_PATTERNS.items():
                dom_check = patterns.get("dom_check")
                if dom_check:
                    try:
                        result = await page.evaluate(dom_check)
                        if result:
                            if lib_name == "threejs":
                                self._webgl_info.is_threejs = True
                            elif lib_name == "pixijs":
                                self._webgl_info.is_pixijs = True
                            self._is_static = False
                    except Exception:
                        pass

        except Exception:
            pass

    async def _detect_static_indicators(self, page: Page) -> None:
        """检测静态网站特征"""
        if not self._is_static:
            return

        try:
            # 检查是否有大量静态内容
            static_indicators = await page.evaluate("""
                () => {
                    const scripts = document.querySelectorAll('script[src]');
                    const inlineScripts = document.querySelectorAll('script:not([src])');

                    let hasFrameworkScript = false;
                    scripts.forEach(script => {
                        const src = script.src.toLowerCase();
                        if (src.includes('react') ||
                            src.includes('vue') ||
                            src.includes('angular') ||
                            src.includes('svelte')) {
                            hasFrameworkScript = true;
                        }
                    });

                    return {
                        scriptCount: scripts.length,
                        inlineScriptCount: inlineScripts.length,
                        hasFrameworkScript: hasFrameworkScript,
                        hasServerRenderedContent: !!document.querySelector('[data-server-rendered]')
                    };
                }
            """)

            if static_indicators.get("hasFrameworkScript"):
                self._is_static = False

            if static_indicators.get("hasServerRenderedContent"):
                self._is_static = False

        except Exception:
            pass

    def _determine_website_type(self) -> WebsiteType:
        """综合判断网站类型"""
        # 优先级：WebGL > 认证 > SPA 框架 > 静态

        # WebGL 应用
        if self._webgl_info.has_webgl:
            if self._webgl_info.is_threejs:
                return WebsiteType.WEBGL_APP
            return WebsiteType.WEBGL_APP

        # Canvas 应用
        if self._webgl_info.has_canvas and not self._webgl_info.has_webgl:
            return WebsiteType.CANVAS_APP

        # 认证墙
        if self._auth_info.has_auth_wall:
            return WebsiteType.AUTH_REQUIRED

        # SPA 框架
        if self._detected_frameworks:
            framework_name = self._detected_frameworks[0].name
            framework_map = {
                "react": WebsiteType.SPA_REACT,
                "vue": WebsiteType.SPA_VUE,
                "angular": WebsiteType.SPA_ANGULAR,
                "svelte": WebsiteType.SPA_SVELTE,
            }
            return framework_map.get(framework_name, WebsiteType.SPA_OTHER)

        # 静态网站
        if self._is_static:
            return WebsiteType.STATIC

        # 默认
        return WebsiteType.UNKNOWN

    def _calculate_confidence(self) -> int:
        """计算检测置信度"""
        if not self._detected_frameworks and not self._auth_info.has_login_form:
            if self._is_static:
                return 90
            return 50

        confidence = 100

        # 根据证据数量调整置信度
        if self._detected_frameworks:
            avg_framework_confidence = sum(f.confidence for f in self._detected_frameworks) / len(self._detected_frameworks)
            confidence = int((confidence + avg_framework_confidence) / 2)

        # WebGL 检测增加置信度
        if self._webgl_info.has_webgl:
            confidence = min(100, confidence + 10)

        return confidence

    def _generate_recommendations(self, website_type: WebsiteType) -> list[str]:
        """生成处理建议"""
        recommendations = []

        if website_type == WebsiteType.STATIC:
            recommendations.append("静态网站：可直接下载 HTML 和资源，无需 JavaScript 渲染")
            recommendations.append("建议：使用简单的 HTTP 请求获取页面内容")

        elif website_type in {WebsiteType.SPA_REACT, WebsiteType.SPA_VUE, WebsiteType.SPA_ANGULAR, WebsiteType.SPA_SVELTE}:
            framework_name = website_type.value
            recommendations.append(f"{framework_name}：需要完整渲染 JavaScript")
            recommendations.append("建议：使用 Playwright 等浏览器自动化工具等待页面完全加载")
            recommendations.append("建议：等待框架 hydration 完成后再提取内容")

        elif website_type == WebsiteType.AUTH_REQUIRED:
            recommendations.append("认证网站：需要处理登录流程")
            if self._auth_info.auth_type == "oauth":
                recommendations.append("建议：使用 OAuth 认证流程或手动登录后保存会话")
            else:
                recommendations.append("建议：提供登录凭据或使用已认证的会话 Cookie")

        elif website_type == WebsiteType.WEBGL_APP:
            recommendations.append("WebGL 应用：需要特殊处理 3D 渲染内容")
            if self._webgl_info.is_threejs:
                recommendations.append("Three.js 检测到：等待场景加载完成")
            recommendations.append("建议：增加渲染等待时间，确保 WebGL 内容完全加载")

        elif website_type == WebsiteType.CANVAS_APP:
            recommendations.append("Canvas 应用：可能包含动态绑定的内容")
            recommendations.append("建议：检查 Canvas 渲染的内容是否需要提取")

        if self._auth_info.has_login_form and website_type != WebsiteType.AUTH_REQUIRED:
            recommendations.append("注意：检测到登录表单，可能需要认证才能访问完整内容")

        return recommendations

    def print_summary(self, result: WebsiteTypeResult) -> None:
        """打印检测结果摘要"""
        console.print(f"\n[bold cyan]🔍 网站类型检测结果[/]")
        console.print(f"  类型: [green]{result.website_type.value}[/]")
        console.print(f"  置信度: [yellow]{result.confidence}%[/]")
        console.print(f"  需要JS渲染: {'[red]是[/]' if result.requires_js_rendering else '[green]否[/]'}")

        if result.frameworks:
            console.print("\n[bold]检测到的框架:[/]")
            for framework in result.frameworks:
                console.print(f"  • {framework.name} (置信度: {framework.confidence}%)")
                if framework.evidence:
                    console.print(f"    证据: [dim]{framework.evidence}[/]")

        if result.auth_info.has_login_form:
            console.print("\n[bold yellow]⚠ 认证信息:[/]")
            console.print(f"  检测到登录表单: {'是' if result.auth_info.has_login_form else '否'}")
            console.print(f"  认证墙: {'是' if result.auth_info.has_auth_wall else '否'}")
            if result.auth_info.auth_type:
                console.print(f"  认证类型: {result.auth_info.auth_type}")

        if result.webgl_info.has_canvas or result.webgl_info.has_webgl:
            console.print("\n[bold magenta]🎨 WebGL/Canvas 信息:[/]")
            console.print(f"  Canvas 数量: {result.webgl_info.canvas_count}")
            console.print(f"  WebGL 支持: {'是' if result.webgl_info.has_webgl else '否'}")
            if result.webgl_info.webgl_context_type:
                console.print(f"  WebGL 类型: {result.webgl_info.webgl_context_type}")
            if result.webgl_info.is_threejs:
                console.print("  Three.js: [green]检测到[/]")

        if result.recommendations:
            console.print("\n[bold cyan]📋 处理建议:[/]")
            for rec in result.recommendations:
                console.print(f"  • {rec}")

    def to_dict(self, result: WebsiteTypeResult) -> dict:
        """将检测结果转换为字典"""
        return {
            "website_type": result.website_type.value,
            "is_spa": result.is_spa,
            "is_static": result.is_static,
            "requires_js_rendering": result.requires_js_rendering,
            "confidence": result.confidence,
            "frameworks": [
                {
                    "name": f.name,
                    "version": f.version,
                    "confidence": f.confidence,
                    "evidence": f.evidence,
                }
                for f in result.frameworks
            ],
            "auth_info": {
                "has_login_form": result.auth_info.has_login_form,
                "has_auth_wall": result.auth_info.has_auth_wall,
                "auth_type": result.auth_info.auth_type,
                "login_form_selectors": result.auth_info.login_form_selectors,
            },
            "webgl_info": {
                "has_webgl": result.webgl_info.has_webgl,
                "has_canvas": result.webgl_info.has_canvas,
                "canvas_count": result.webgl_info.canvas_count,
                "webgl_context_type": result.webgl_info.webgl_context_type,
                "is_threejs": result.webgl_info.is_threejs,
                "is_pixijs": result.webgl_info.is_pixijs,
            },
            "recommendations": result.recommendations,
        }
