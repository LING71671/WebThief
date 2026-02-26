"""
微前端架构处理器：
- 检测微前端框架（qiankun、single-spa、Module Federation）
- 分析子应用信息
- 处理模块联邦配置
- 支持沙箱隔离检测
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


class MicroFrontendType(Enum):
    """微前端类型"""
    QIANKUN = "qiankun"
    SINGLE_SPA = "single-spa"
    MODULE_FEDERATION = "Module Federation"
    IFRAME = "iframe"
    WEB_COMPONENTS = "Web Components"
    EMP = "EMP"
    GARFISH = "Garfish"
    WUJIE = "wujie"
    UNKNOWN = "Unknown"


@dataclass
class SubAppInfo:
    """子应用信息"""
    name: str
    entry: str
    active_rule: str | None = None
    container: str | None = None
    props: dict[str, Any] = field(default_factory=dict)
    sandbox: bool = False
    prefetch: bool = False
    status: str = "unknown"


@dataclass
class ModuleFederationConfig:
    """Module Federation 配置"""
    name: str = ""
    filename: str = "remoteEntry.js"
    exposes: dict[str, str] = field(default_factory=dict)
    remotes: dict[str, str] = field(default_factory=dict)
    shared: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ModuleFederationConfig":
        """从字典创建配置对象"""
        return cls(
            name=data.get("name", ""),
            filename=data.get("filename", "remoteEntry.js"),
            exposes=data.get("exposes", {}),
            remotes=data.get("remotes", {}),
            shared=data.get("shared", {}),
        )


@dataclass
class MicroFrontendAnalysis:
    """微前端分析结果"""
    framework_type: MicroFrontendType = MicroFrontendType.UNKNOWN
    is_micro_frontend: bool = False
    main_app_url: str | None = None
    sub_apps: list[SubAppInfo] = field(default_factory=list)
    federation_config: ModuleFederationConfig | None = None
    sandbox_enabled: bool = False
    communication_method: str | None = None
    routing_strategy: str | None = None
    confidence: int = 0


class MicroFrontendHandler:
    """
    微前端架构处理器
    检测并分析各种微前端框架
    """

    # qiankun 检测模式
    QIANKUN_PATTERNS = [
        re.compile(r'qiankun', re.IGNORECASE),
        re.compile(r'__POWERED_BY_QIANKUN__'),
        re.compile(r'__INJECTED_PUBLIC_PATH__'),
        re.compile(r'@qiankun'),
    ]

    # single-spa 检测模式
    SINGLE_SPA_PATTERNS = [
        re.compile(r'single-spa', re.IGNORECASE),
        re.compile(r'__SINGLE_SPA__'),
        re.compile(r'registerApplication'),
        re.compile(r'startApp'),
        re.compile(r'@single-spa'),
    ]

    # Module Federation 检测模式
    MODULE_FEDERATION_PATTERNS = [
        re.compile(r'__webpack_init_sharing__'),
        re.compile(r'__webpack_share_scopes__'),
        re.compile(r'__webpack_container__'),
        re.compile(r'get\s*\(\s*["\']\.\/remoteEntry["\']'),
        re.compile(r'initialize\s*\(\s*["\']remoteEntry["\']'),
        re.compile(r'module-federation', re.IGNORECASE),
    ]

    # Garfish 检测模式
    GARFISH_PATTERNS = [
        re.compile(r'@garfish', re.IGNORECASE),
        re.compile(r'Garfish\s*\('),
        re.compile(r'__GARFISH__'),
    ]

    # wujie 检测模式
    WUJIE_PATTERNS = [
        re.compile(r'wujie', re.IGNORECASE),
        re.compile(r'__WUJIE__'),
        re.compile(r'@wujie'),
        re.compile(r'preloadApp'),
        re.compile(r'destroyApp'),
    ]

    # EMP 检测模式
    EMP_PATTERNS = [
        re.compile(r'@efox', re.IGNORECASE),
        re.compile(r'emp-', re.IGNORECASE),
        re.compile(r'empShare'),
    ]

    def __init__(self, base_url: str):
        """
        初始化微前端处理器

        Args:
            base_url: 页面基础 URL
        """
        self.base_url = base_url
        self.analysis = MicroFrontendAnalysis()
        self._analyzed_urls: set[str] = set()

    async def detect(self, page: Page) -> MicroFrontendAnalysis:
        """
        检测页面是否使用微前端架构

        Args:
            page: Playwright Page 对象

        Returns:
            MicroFrontendAnalysis: 分析结果
        """
        console.print("[bold magenta]🔍 检测微前端架构...[/]")

        # 1. 检测全局对象
        await self._detect_global_objects(page)

        # 2. 检测 DOM 结构
        await self._detect_dom_structure(page)

        # 3. 检测脚本内容
        await self._detect_script_patterns(page)

        # 4. 分析 Module Federation
        await self._analyze_module_federation(page)

        # 5. 分析子应用
        await self._analyze_sub_apps(page)

        # 确定最终结果
        self._finalize_analysis()

        return self.analysis

    async def _detect_global_objects(self, page: Page) -> None:
        """检测微前端相关的全局对象"""
        try:
            global_checks = await page.evaluate("""
                () => {
                    return {
                        // qiankun
                        qiankun: typeof window.__POWERED_BY_QIANKUN__ !== 'undefined',
                        qiankunPublicPath: typeof window.__INJECTED_PUBLIC_PATH__ !== 'undefined',

                        // single-spa
                        singleSpa: typeof window.singleSpa !== 'undefined',
                        singleSpaNavigate: typeof window.singleSpaNavigate !== 'undefined',

                        // Module Federation
                        webpackInitSharing: typeof window.__webpack_init_sharing__ !== 'undefined',
                        webpackShareScopes: typeof window.__webpack_share_scopes__ !== 'undefined',
                        webpackContainer: typeof window.__webpack_container__ !== 'undefined',

                        // Garfish
                        garfish: typeof window.__GARFISH__ !== 'undefined',
                        garfishInstance: typeof window.Garfish !== 'undefined',

                        // wujie
                        wujie: typeof window.__WUJIE__ !== 'undefined',
                        wujieBus: typeof window.$wujie !== 'undefined',

                        // iframe 相关
                        iframeApps: document.querySelectorAll('iframe[data-name], iframe[data-app]').length > 0,

                        // Web Components
                        customElements: window.customElements && window.customElements.get,
                        shadowRoots: document.querySelectorAll('*').length > 0 &&
                            Array.from(document.querySelectorAll('*')).some(el => el.shadowRoot !== null),
                    };
                }
            """)

            self._process_framework_detection(global_checks)
            await self._process_iframe_detection(global_checks, page)

            if global_checks.get('shadowRoots'):
                self.analysis.communication_method = "Web Components"

        except Exception as e:
            console.print(f"[yellow]  ⚠ 全局对象检测失败: {e}[/]")

    def _process_framework_detection(self, global_checks: dict) -> None:
        """处理框架检测结果"""
        framework_checks = [
            ('qiankun', 'qiankunPublicPath', MicroFrontendType.QIANKUN, 95),
            ('singleSpa', 'singleSpaNavigate', MicroFrontendType.SINGLE_SPA, 90),
            ('webpackInitSharing', 'webpackShareScopes', MicroFrontendType.MODULE_FEDERATION, 85),
            ('garfish', 'garfishInstance', MicroFrontendType.GARFISH, 90),
            ('wujie', 'wujieBus', MicroFrontendType.WUJIE, 90),
        ]

        for check1, check2, framework_type, confidence in framework_checks:
            if global_checks.get(check1) or global_checks.get(check2):
                self.analysis.framework_type = framework_type
                self.analysis.confidence = confidence
                return

    async def _process_iframe_detection(self, global_checks: dict, page: Page) -> None:
        """处理 iframe 检测"""
        if not global_checks.get('iframeApps'):
            return

        if self.analysis.framework_type == MicroFrontendType.UNKNOWN:
            self.analysis.framework_type = MicroFrontendType.IFRAME
            self.analysis.confidence = 70

        self.analysis.sub_apps.extend(await self._extract_iframe_apps(page))

    async def _detect_dom_structure(self, page: Page) -> None:
        """检测 DOM 结构中的微前端特征"""
        try:
            dom_info = await page.evaluate("""
                () => {
                    const result = {
                        microAppContainers: [],
                        shadowContainers: [],
                        dynamicContainers: [],
                    };

                    // 检测微前端容器
                    const containerSelectors = [
                        '[data-micro-app]',
                        '[data-app-name]',
                        '[data-single-spa]',
                        '[id*="micro-app"]',
                        '[id*="subapp"]',
                        '[class*="micro-app"]',
                        '[class*="sub-app"]',
                        '#subapp-container',
                        '#micro-app',
                        '#app-container',
                    ];

                    containerSelectors.forEach(selector => {
                        document.querySelectorAll(selector).forEach(el => {
                            result.microAppContainers.push({
                                selector: selector,
                                id: el.id || '',
                                className: el.className || '',
                                name: el.getAttribute('data-name') ||
                                      el.getAttribute('data-app-name') ||
                                      el.getAttribute('data-micro-app') || '',
                            });
                        });
                    });

                    // 检测 Shadow DOM
                    document.querySelectorAll('*').forEach(el => {
                        if (el.shadowRoot) {
                            result.shadowContainers.push({
                                tag: el.tagName.toLowerCase(),
                                id: el.id || '',
                                mode: el.shadowRoot.mode || 'open',
                            });
                        }
                    });

                    return result;
                }
            """)

            containers = dom_info.get('microAppContainers', [])
            if containers:
                for container in containers:
                    if container.get('name'):
                        self.analysis.sub_apps.append(SubAppInfo(
                            name=container['name'],
                            entry='',
                            container=container.get('id') or container.get('className'),
                        ))

                if self.analysis.framework_type == MicroFrontendType.UNKNOWN:
                    self.analysis.framework_type = MicroFrontendType.SINGLE_SPA
                    self.analysis.confidence = max(self.analysis.confidence, 60)

        except Exception as e:
            console.print(f"[yellow]  ⚠ DOM 结构检测失败: {e}[/]")

    async def _detect_script_patterns(self, page: Page) -> None:
        """检测脚本内容中的微前端模式"""
        try:
            script_patterns = await page.evaluate("""
                () => {
                    const scripts = [];
                    const patterns = {
                        qiankun: false,
                        singleSpa: false,
                        moduleFederation: false,
                        garfish: false,
                        wujie: false,
                        emp: false,
                    };

                    // 检查内联脚本
                    document.querySelectorAll('script:not([src])').forEach(script => {
                        const content = script.textContent || '';

                        if (/qiankun/i.test(content) || /__POWERED_BY_QIANKUN__/.test(content)) {
                            patterns.qiankun = true;
                        }
                        if (/single-spa/i.test(content) || /registerApplication/.test(content)) {
                            patterns.singleSpa = true;
                        }
                        if (/__webpack_init_sharing__/.test(content) ||
                            /__webpack_share_scopes__/.test(content)) {
                            patterns.moduleFederation = true;
                        }
                        if (/@garfish/i.test(content) || /Garfish\\s*\\(/.test(content)) {
                            patterns.garfish = true;
                        }
                        if (/wujie/i.test(content) || /__WUJIE__/.test(content)) {
                            patterns.wujie = true;
                        }
                        if (/@efox/i.test(content) || /emp-/i.test(content)) {
                            patterns.emp = true;
                        }
                    });

                    return patterns;
                }
            """)

            if script_patterns.get('qiankun'):
                self.analysis.framework_type = MicroFrontendType.QIANKUN
                self.analysis.confidence = max(self.analysis.confidence, 80)

            if script_patterns.get('singleSpa'):
                if self.analysis.framework_type == MicroFrontendType.UNKNOWN:
                    self.analysis.framework_type = MicroFrontendType.SINGLE_SPA
                self.analysis.confidence = max(self.analysis.confidence, 75)

            if script_patterns.get('moduleFederation'):
                if self.analysis.framework_type == MicroFrontendType.UNKNOWN:
                    self.analysis.framework_type = MicroFrontendType.MODULE_FEDERATION
                self.analysis.confidence = max(self.analysis.confidence, 70)

            if script_patterns.get('garfish'):
                self.analysis.framework_type = MicroFrontendType.GARFISH
                self.analysis.confidence = max(self.analysis.confidence, 80)

            if script_patterns.get('wujie'):
                self.analysis.framework_type = MicroFrontendType.WUJIE
                self.analysis.confidence = max(self.analysis.confidence, 80)

            if script_patterns.get('emp'):
                self.analysis.framework_type = MicroFrontendType.EMP
                self.analysis.confidence = max(self.analysis.confidence, 75)

        except Exception as e:
            console.print(f"[yellow]  ⚠ 脚本模式检测失败: {e}[/]")

    async def _analyze_module_federation(self, page: Page) -> None:
        """分析 Module Federation 配置"""
        try:
            federation_info = await page.evaluate("""
                () => {
                    const info = {
                        hasFederation: false,
                        containers: [],
                        sharedModules: [],
                        remoteEntries: [],
                    };

                    // 检查 webpack 共享作用域
                    if (window.__webpack_share_scopes__) {
                        info.hasFederation = true;
                        const scopes = window.__webpack_share_scopes__;
                        for (const scopeName in scopes) {
                            const scope = scopes[scopeName];
                            for (const moduleName in scope) {
                                info.sharedModules.push({
                                    scope: scopeName,
                                    name: moduleName,
                                    version: scope[moduleName].from || 'unknown',
                                });
                            }
                        }
                    }

                    // 检查远程容器
                    if (window.__webpack_container__) {
                        info.containers.push('main');
                    }

                    // 尝试获取远程入口
                    const scripts = Array.from(document.querySelectorAll('script[src]'));
                    scripts.forEach(script => {
                        const src = script.src;
                        if (src.includes('remoteEntry') || src.includes('remote-entry')) {
                            info.remoteEntries.push(src);
                        }
                    });

                    return info;
                }
            """)

            if federation_info.get('hasFederation'):
                self.analysis.federation_config = ModuleFederationConfig(
                    name="main",
                    shared={
                        item['name']: {'version': item['version']}
                        for item in federation_info.get('sharedModules', [])
                    },
                )

                for remote in federation_info.get('remoteEntries', []):
                    self.analysis.sub_apps.append(SubAppInfo(
                        name=remote.split('/')[-1].replace('.js', ''),
                        entry=remote,
                    ))

                if self.analysis.framework_type == MicroFrontendType.UNKNOWN:
                    self.analysis.framework_type = MicroFrontendType.MODULE_FEDERATION
                    self.analysis.confidence = max(self.analysis.confidence, 80)

        except Exception as e:
            console.print(f"[yellow]  ⚠ Module Federation 分析失败: {e}[/]")

    async def _analyze_sub_apps(self, page: Page) -> None:
        """分析子应用配置"""
        try:
            # 尝试获取 qiankun 配置
            qiankun_apps = await page.evaluate("""
                () => {
                    if (!window.qiankun && typeof window.__QIANKUN_APPS__ === 'undefined') {
                        return [];
                    }

                    const apps = [];

                    // 尝试从全局变量获取
                    if (window.__QIANKUN_APPS__) {
                        return window.__QIANKUN_APPS__;
                    }

                    // 尝试从 DOM 推断
                    document.querySelectorAll('[data-name], [data-app-name]').forEach(el => {
                        apps.push({
                            name: el.getAttribute('data-name') || el.getAttribute('data-app-name'),
                            entry: el.getAttribute('data-entry') || '',
                            container: el.id || el.className,
                        });
                    });

                    return apps;
                }
            """)

            for app in qiankun_apps:
                existing = next(
                    (s for s in self.analysis.sub_apps if s.name == app.get('name')),
                    None
                )
                if existing:
                    existing.entry = app.get('entry', existing.entry)
                    existing.container = app.get('container', existing.container)
                else:
                    self.analysis.sub_apps.append(SubAppInfo(
                        name=app.get('name', ''),
                        entry=app.get('entry', ''),
                        container=app.get('container'),
                    ))

        except Exception as e:
            console.print(f"[yellow]  ⚠ 子应用分析失败: {e}[/]")

    async def _extract_iframe_apps(self, page: Page) -> list[SubAppInfo]:
        """提取 iframe 类型的子应用"""
        try:
            iframes = await page.evaluate("""
                () => {
                    const apps = [];
                    document.querySelectorAll('iframe[data-name], iframe[data-app], iframe[name]').forEach(iframe => {
                        apps.push({
                            name: iframe.getAttribute('data-name') ||
                                  iframe.getAttribute('data-app') ||
                                  iframe.getAttribute('name') ||
                                  'unknown',
                            entry: iframe.src || '',
                            container: iframe.id || iframe.className,
                        });
                    });
                    return apps;
                }
            """)

            return [
                SubAppInfo(
                    name=app.get('name', ''),
                    entry=app.get('entry', ''),
                    container=app.get('container'),
                )
                for app in iframes
            ]

        except Exception:
            return []

    def _finalize_analysis(self) -> None:
        """最终确定分析结果"""
        self.analysis.is_micro_frontend = (
            self.analysis.framework_type != MicroFrontendType.UNKNOWN or
            len(self.analysis.sub_apps) > 0
        )

        if self.analysis.framework_type == MicroFrontendType.QIANKUN:
            self.analysis.sandbox_enabled = True
            self.analysis.routing_strategy = "history"

        elif self.analysis.framework_type == MicroFrontendType.SINGLE_SPA:
            self.analysis.routing_strategy = "history/hash"

        elif self.analysis.framework_type == MicroFrontendType.MODULE_FEDERATION:
            self.analysis.routing_strategy = "application-controlled"

        elif self.analysis.framework_type == MicroFrontendType.WUJIE:
            self.analysis.sandbox_enabled = True
            self.analysis.routing_strategy = "iframe-sandbox"

    def analyze_response(self, response: Response) -> None:
        """
        分析响应内容中的微前端特征

        Args:
            response: Playwright Response 对象
        """
        url = response.url
        if url in self._analyzed_urls:
            return
        self._analyzed_urls.add(url)

        content_type = response.headers.get('content-type', '').lower()
        if 'javascript' not in content_type and not url.endswith('.js'):
            return

        # 这里可以添加对响应内容的分析
        # 由于 Playwright 的 Response 需要异步获取内容，这里只做 URL 分析

        for pattern in self.QIANKUN_PATTERNS:
            if pattern.search(url):
                self.analysis.framework_type = MicroFrontendType.QIANKUN
                self.analysis.confidence = max(self.analysis.confidence, 70)
                break

        for pattern in self.MODULE_FEDERATION_PATTERNS:
            if pattern.search(url):
                self.analysis.framework_type = MicroFrontendType.MODULE_FEDERATION
                self.analysis.confidence = max(self.analysis.confidence, 65)
                break

    def get_render_strategy(self) -> dict[str, Any]:
        """
        根据微前端类型返回渲染策略建议

        Returns:
            渲染策略配置字典
        """
        strategy = {
            "wait_for_sub_apps": False,
            "sub_app_timeout": 5000,
            "isolate_sandbox": False,
            "preload_remotes": [],
            "recommendations": [],
        }

        if not self.analysis.is_micro_frontend:
            return strategy

        if self.analysis.framework_type == MicroFrontendType.QIANKUN:
            strategy.update({
                "wait_for_sub_apps": True,
                "sub_app_timeout": 8000,
                "isolate_sandbox": True,
                "recommendations": [
                    "qiankun: 等待子应用挂载完成",
                    "qiankun: 注意 JS 沙箱隔离",
                    "qiankun: 可能需要等待 prefetch 完成",
                ],
            })

        elif self.analysis.framework_type == MicroFrontendType.SINGLE_SPA:
            strategy.update({
                "wait_for_sub_apps": True,
                "sub_app_timeout": 6000,
                "recommendations": [
                    "single-spa: 等待所有应用 mount 完成",
                    "single-spa: 注意路由事件监听",
                ],
            })

        elif self.analysis.framework_type == MicroFrontendType.MODULE_FEDERATION:
            strategy.update({
                "wait_for_sub_apps": True,
                "sub_app_timeout": 5000,
                "recommendations": [
                    "Module Federation: 等待远程模块加载",
                    "Module Federation: 注意共享依赖版本",
                ],
            })
            if self.analysis.federation_config:
                strategy["preload_remotes"] = list(
                    self.analysis.federation_config.remotes.keys()
                )

        elif self.analysis.framework_type == MicroFrontendType.WUJIE:
            strategy.update({
                "wait_for_sub_apps": True,
                "sub_app_timeout": 10000,
                "isolate_sandbox": True,
                "recommendations": [
                    "wujie: 等待 iframe 沙箱初始化",
                    "wujie: 注意 WebComponent 降级",
                ],
            })

        return strategy

    def print_summary(self) -> None:
        """打印微前端分析摘要"""
        if not self.analysis.is_micro_frontend:
            console.print("[dim]  未检测到微前端架构[/]")
            return

        self._print_framework_info()
        self._print_sub_apps_table()
        self._print_federation_config()
        self._print_render_recommendations()

    def _print_framework_info(self) -> None:
        """打印框架信息"""
        console.print(f"\n[bold cyan]🏗 微前端架构检测[/]")
        console.print(f"  框架类型: [green]{self.analysis.framework_type.value}[/]")
        console.print(f"  置信度: [yellow]{self.analysis.confidence}%[/]")

    def _print_sub_apps_table(self) -> None:
        """打印子应用表格"""
        if not self.analysis.sub_apps:
            return

        table = Table(title="📦 子应用列表", show_header=True, header_style="bold cyan")
        table.add_column("名称", style="green", width=20)
        table.add_column("入口", style="blue", width=40)
        table.add_column("容器", style="yellow", width=20)
        table.add_column("沙箱", width=8)

        for app in self.analysis.sub_apps:
            entry_short = app.entry.split('/')[-1] if app.entry else "-"
            if len(entry_short) > 38:
                entry_short = entry_short[:35] + "..."

            table.add_row(
                app.name[:18] + ("..." if len(app.name) > 18 else ""),
                entry_short,
                app.container[:18] if app.container else "-",
                "✓" if app.sandbox else "-",
            )

        console.print(table)

    def _print_federation_config(self) -> None:
        """打印 Module Federation 配置"""
        if not self.analysis.federation_config:
            return

        fc = self.analysis.federation_config
        console.print(f"\n[bold cyan]🔗 Module Federation 配置:[/]")
        console.print(f"  名称: {fc.name}")
        if fc.shared:
            console.print(f"  共享模块: {', '.join(fc.shared.keys())}")
        if fc.remotes:
            console.print(f"  远程模块: {', '.join(fc.remotes.keys())}")

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
            "is_micro_frontend": self.analysis.is_micro_frontend,
            "framework_type": self.analysis.framework_type.value,
            "confidence": self.analysis.confidence,
            "main_app_url": self.analysis.main_app_url,
            "sub_apps": [
                {
                    "name": app.name,
                    "entry": app.entry,
                    "container": app.container,
                    "sandbox": app.sandbox,
                }
                for app in self.analysis.sub_apps
            ],
            "federation_config": {
                "name": self.analysis.federation_config.name,
                "exposes": self.analysis.federation_config.exposes,
                "remotes": self.analysis.federation_config.remotes,
                "shared": self.analysis.federation_config.shared,
            } if self.analysis.federation_config else None,
            "sandbox_enabled": self.analysis.sandbox_enabled,
            "routing_strategy": self.analysis.routing_strategy,
            "render_strategy": self.get_render_strategy(),
        }
