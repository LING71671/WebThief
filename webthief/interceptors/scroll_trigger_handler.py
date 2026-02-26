"""
ScrollTrigger 动画处理模块
目标：检测和捕获 GSAP ScrollTrigger 和 ScrollMagic 动画，生成静态兼容样式
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from playwright.async_api import Page
from rich.console import Console

console = Console()


@dataclass
class ScrollTriggerConfig:
    """ScrollTrigger 配置数据类"""

    trigger: str | None = None
    start: str = "top bottom"
    end: str = "bottom top"
    scrub: bool | float = False
    pin: bool = False
    markers: bool = False
    toggle_actions: str = "play none none none"
    animation_properties: dict[str, Any] = field(default_factory=dict)


@dataclass
class AnimationState:
    """动画状态数据类"""

    progress: float = 0.0
    css_styles: dict[str, str] = field(default_factory=dict)
    transform: str = ""
    opacity: float = 1.0


class ScrollTriggerHandler:
    """
    ScrollTrigger 动画处理器
    负责：
    1. 检测页面使用的滚动触发库（GSAP ScrollTrigger / ScrollMagic）
    2. 解析 ScrollTrigger 配置（scrub、pin、trigger、start、end）
    3. 捕获不同滚动位置的动画状态
    4. 生成 ScrollTrigger 兼容的静态 CSS 样式
    5. 通过 Playwright 注入跟踪代码
    """

    # 滚动触发库检测关键字
    SCROLL_TRIGGER_KEYWORDS = [
        "scrolltrigger",
        "gsap",
        "scrollmagic",
        "scrollmagic",
        "scrollreveal",
        "aos",
        "locomotive-scroll",
        "lenis",
        "skrollr",
    ]

    # GSAP ScrollTrigger 特定关键字
    GSAP_KEYWORDS = [
        "gsap",
        "scrolltrigger",
        "gsap.registerplugin",
        "scrolltrigger.create",
        "scrolltrigger.batch",
    ]

    # ScrollMagic 特定关键字
    SCROLL_MAGIC_KEYWORDS = [
        "scrollmagic",
        "scrollmagic.controller",
        "scrollmagic.scene",
        "addto",
        "setpin",
        "settween",
    ]

    def __init__(self):
        self.detected_library: str | None = None
        self.scroll_trigger_configs: list[ScrollTriggerConfig] = []
        self.animation_states: dict[str, list[AnimationState]] = {}
        self.pinned_elements: list[dict[str, Any]] = []
        self.captured_snapshots: list[dict[str, Any]] = []

    async def detect_scroll_trigger_library(self, page: Page) -> str | None:
        """
        检测页面使用的滚动触发库
        返回检测到的库名称或 None
        """
        console.print("[cyan]  🔍 检测滚动触发库...[/]")

        detection_script = """
        () => {
            const libraries = {
                gsap: !!window.gsap,
                scrollTrigger: !!(window.gsap && window.gsap.plugins && window.gsap.plugins.scrollTrigger),
                scrollMagic: !!window.ScrollMagic,
                scrollReveal: !!window.ScrollReveal,
                aos: !!window.AOS,
                locomotiveScroll: !!window.LocomotiveScroll,
                lenis: !!window.Lenis,
                skrollr: !!window.skrollr
            };
            
            // 检测 GSAP ScrollTrigger 插件
            if (window.gsap) {
                const gsapVersion = window.gsap.version || 'unknown';
                libraries.gsapVersion = gsapVersion;
                
                // 检查是否注册了 ScrollTrigger
                if (window.gsap.registerPlugin) {
                    const plugins = window.gsap.core && window.gsap.core.globals || {};
                    libraries.registeredPlugins = Object.keys(plugins);
                }
            }
            
            // 检测 ScrollMagic Controller
            if (window.ScrollMagic) {
                libraries.scrollMagicVersion = window.ScrollMagic.version || 'unknown';
            }
            
            return libraries;
        }
        """

        try:
            detection_result = await page.evaluate(detection_script)

            if detection_result.get("scrollTrigger"):
                self.detected_library = "gsap_scrolltrigger"
                version = detection_result.get("gsapVersion", "unknown")
                console.print(f"[green]  ✓ 检测到 GSAP ScrollTrigger (v{version})[/]")
            elif detection_result.get("scrollMagic"):
                self.detected_library = "scrollmagic"
                version = detection_result.get("scrollMagicVersion", "unknown")
                console.print(f"[green]  ✓ 检测到 ScrollMagic (v{version})[/]")
            elif detection_result.get("scrollReveal"):
                self.detected_library = "scrollreveal"
                console.print("[green]  ✓ 检测到 ScrollReveal[/]")
            elif detection_result.get("aos"):
                self.detected_library = "aos"
                console.print("[green]  ✓ 检测到 AOS (Animate On Scroll)[/]")
            elif detection_result.get("locomotiveScroll"):
                self.detected_library = "locomotive_scroll"
                console.print("[green]  ✓ 检测到 Locomotive Scroll[/]")
            elif detection_result.get("lenis"):
                self.detected_library = "lenis"
                console.print("[green]  ✓ 检测到 Lenis[/]")
            elif detection_result.get("skrollr"):
                self.detected_library = "skrollr"
                console.print("[green]  ✓ 检测到 Skrollr[/]")
            else:
                console.print("[yellow]  ⚠ 未检测到已知的滚动触发库[/]")
                return None

            return self.detected_library

        except Exception as e:
            console.print(f"[red]  ✗ 检测失败: {e}[/]")
            return None

    async def parse_scroll_trigger_config(self, page: Page) -> list[ScrollTriggerConfig]:
        """
        解析 ScrollTrigger 配置
        提取 scrub、pin、trigger、start、end 等配置
        """
        console.print("[cyan]  📋 解析 ScrollTrigger 配置...[/]")

        if not self.detected_library:
            await self.detect_scroll_trigger_library(page)

        parse_script = """
        () => {
            const configs = [];
            
            // GSAP ScrollTrigger 配置提取
            if (window.ScrollTrigger) {
                // 获取所有 ScrollTrigger 实例
                const triggers = window.ScrollTrigger.getAll ? window.ScrollTrigger.getAll() : [];
                
                triggers.forEach((trigger, index) => {
                    const config = {
                        type: 'gsap_scrolltrigger',
                        index: index,
                        trigger: trigger.trigger ? trigger.trigger.tagName + (trigger.trigger.className ? '.' + trigger.trigger.className.split(' ')[0] : '') : null,
                        triggerSelector: trigger.trigger ? (trigger.trigger.id ? '#' + trigger.trigger.id : trigger.trigger.className ? '.' + trigger.trigger.className.split(' ').join('.') : trigger.trigger.tagName.toLowerCase()) : null,
                        start: trigger.start,
                        end: trigger.end,
                        scrub: trigger.scrub,
                        pin: trigger.pin,
                        markers: trigger.markers,
                        toggleActions: trigger.toggleActions,
                        animation: trigger.animation ? {
                            duration: trigger.animation.duration(),
                            vars: trigger.animation.vars
                        } : null
                    };
                    configs.push(config);
                });
            }
            
            // ScrollMagic 配置提取
            if (window.ScrollMagic && window.ScrollMagic._instances) {
                window.ScrollMagic._instances.forEach((controller, cIndex) => {
                    if (controller._scenes) {
                        controller._scenes.forEach((scene, sIndex) => {
                            const config = {
                                type: 'scrollmagic',
                                controllerIndex: cIndex,
                                sceneIndex: sIndex,
                                trigger: scene.triggerElement() ? scene.triggerElement().tagName : null,
                                triggerSelector: scene.triggerElement() ? (scene.triggerElement().id ? '#' + scene.triggerElement().id : scene.triggerElement().className ? '.' + scene.triggerElement().className.split(' ')[0] : scene.triggerElement().tagName.toLowerCase()) : null,
                                start: scene.triggerHook(),
                                duration: scene.duration(),
                                offset: scene.offset(),
                                pin: scene.pin() !== null,
                                reverse: scene.reverse()
                            };
                            configs.push(config);
                        });
                    }
                });
            }
            
            // 通过 DOM 属性检测 ScrollTrigger 标记
            document.querySelectorAll('[data-scroll-trigger]').forEach(el => {
                configs.push({
                    type: 'dom_marker',
                    trigger: el.tagName,
                    triggerSelector: el.id ? '#' + el.id : el.className ? '.' + el.className.split(' ')[0] : el.tagName.toLowerCase(),
                    dataset: el.dataset
                });
            });
            
            return configs;
        }
        """

        try:
            raw_configs = await page.evaluate(parse_script)

            self.scroll_trigger_configs = []
            for raw_config in raw_configs:
                config = ScrollTriggerConfig(
                    trigger=raw_config.get("triggerSelector") or raw_config.get("trigger"),
                    start=str(raw_config.get("start", "top bottom")),
                    end=str(raw_config.get("end", "bottom top")),
                    scrub=raw_config.get("scrub", False),
                    pin=raw_config.get("pin", False),
                    markers=raw_config.get("markers", False),
                    toggle_actions=raw_config.get("toggleActions", "play none none none"),
                    animation_properties=raw_config.get("animation") or {},
                )
                self.scroll_trigger_configs.append(config)

            console.print(f"[green]  ✓ 解析到 {len(self.scroll_trigger_configs)} 个 ScrollTrigger 配置[/]")
            return self.scroll_trigger_configs

        except Exception as e:
            console.print(f"[red]  ✗ 配置解析失败: {e}[/]")
            return []

    async def capture_scroll_trigger_states(self, page: Page, scroll_positions: list[float] | None = None) -> dict[str, list[AnimationState]]:
        """
        捕获不同滚动位置的动画状态
        在指定滚动位置采样动画状态
        """
        console.print("[cyan]  📸 捕获滚动动画状态...[/]")

        if scroll_positions is None:
            # 默认采样位置：0%, 25%, 50%, 75%, 100%
            scroll_positions = [0.0, 0.25, 0.5, 0.75, 1.0]

        self.animation_states = {}

        try:
            # 获取页面总高度
            page_height = await page.evaluate("() => document.body.scrollHeight - window.innerHeight")

            for progress in scroll_positions:
                scroll_y = int(page_height * progress)

                # 滚动到指定位置
                await page.evaluate(f"window.scrollTo(0, {scroll_y})")
                await page.wait_for_timeout(100)  # 等待动画稳定

                # 捕获当前状态的脚本
                capture_script = """
                (progress) => {
                    const states = [];
                    
                    // 获取所有带有动画的元素
                    const animatedElements = document.querySelectorAll(
                        '[data-scroll-trigger], [data-aos], [data-sr], .gsap-marker, .scrollmagic-pin-spacer'
                    );
                    
                    // 如果没有特定标记，尝试获取 transform 不为 none 的元素
                    if (animatedElements.length === 0) {
                        document.querySelectorAll('*').forEach(el => {
                            const style = window.getComputedStyle(el);
                            if (style.transform !== 'none' || style.opacity !== '1' || style.filter !== 'none') {
                                const rect = el.getBoundingClientRect();
                                states.push({
                                    selector: el.id ? '#' + el.id : el.className ? '.' + el.className.split(' ')[0] : el.tagName.toLowerCase(),
                                    tagName: el.tagName,
                                    rect: {
                                        top: rect.top,
                                        left: rect.left,
                                        width: rect.width,
                                        height: rect.height
                                    },
                                    computedStyle: {
                                        transform: style.transform,
                                        opacity: style.opacity,
                                        filter: style.filter,
                                        translate: style.translate,
                                        scale: style.scale,
                                        rotate: style.rotate
                                    },
                                    inlineStyle: el.style.cssText
                                });
                            }
                        });
                    } else {
                        animatedElements.forEach(el => {
                            const style = window.getComputedStyle(el);
                            const rect = el.getBoundingClientRect();
                            
                            states.push({
                                selector: el.id ? '#' + el.id : el.className ? '.' + el.className.split(' ')[0] : el.tagName.toLowerCase(),
                                tagName: el.tagName,
                                dataset: el.dataset,
                                rect: {
                                    top: rect.top,
                                    left: rect.left,
                                    width: rect.width,
                                    height: rect.height
                                },
                                computedStyle: {
                                    transform: style.transform,
                                    opacity: style.opacity,
                                    filter: style.filter,
                                    translate: style.translate,
                                    scale: style.scale,
                                    rotate: style.rotate
                                },
                                inlineStyle: el.style.cssText
                            });
                        });
                    }
                    
                    // 获取 ScrollTrigger 进度信息
                    const scrollTriggerProgress = [];
                    if (window.ScrollTrigger && window.ScrollTrigger.getAll) {
                        window.ScrollTrigger.getAll().forEach(st => {
                            scrollTriggerProgress.push({
                                trigger: st.trigger ? (st.trigger.id || st.trigger.className || st.trigger.tagName) : null,
                                progress: st.progress,
                                isActive: st.isActive
                            });
                        });
                    }
                    
                    return {
                        elementStates: states,
                        scrollTriggerProgress: scrollTriggerProgress,
                        scrollY: window.scrollY,
                        maxScroll: document.body.scrollHeight - window.innerHeight
                    };
                }
                """

                result = await page.evaluate(capture_script, progress)

                # 转换为 AnimationState 对象
                states = []
                for elem_state in result.get("elementStates", []):
                    computed = elem_state.get("computedStyle", {})
                    state = AnimationState(
                        progress=progress,
                        css_styles=computed,
                        transform=computed.get("transform", ""),
                        opacity=float(computed.get("opacity", 1.0)),
                    )
                    states.append(state)

                self.animation_states[f"progress_{int(progress * 100)}"] = states

                # 保存快照
                self.captured_snapshots.append({
                    "progress": progress,
                    "scroll_y": result.get("scrollY", 0),
                    "element_states": result.get("elementStates", []),
                    "scroll_trigger_progress": result.get("scrollTriggerProgress", []),
                })

            console.print(f"[green]  ✓ 已捕获 {len(scroll_positions)} 个滚动位置的动画状态[/]")
            return self.animation_states

        except Exception as e:
            console.print(f"[red]  ✗ 状态捕获失败: {e}[/]")
            return {}

    def generate_static_styles(self) -> str:
        """
        生成 ScrollTrigger 兼容的静态 CSS 样式
        将动态动画转换为静态 CSS
        """
        console.print("[cyan]  🎨 生成静态 CSS 样式...[/]")

        css_builder = CssRuleBuilder()
        self._add_snapshot_styles(css_builder)
        self._add_utility_styles(css_builder)

        css_content = css_builder.build()
        console.print(f"[green]  ✓ 生成 {css_builder.line_count} 行 CSS 样式[/]")

        return css_content

    def _add_snapshot_styles(self, builder: "CssRuleBuilder") -> None:
        """为每个捕获的快照添加 CSS 样式。"""
        for snapshot in self.captured_snapshots:
            self._process_single_snapshot(builder, snapshot)

    def _process_single_snapshot(self, builder: "CssRuleBuilder", snapshot: dict) -> None:
        """处理单个快照并添加其样式规则。"""
        progress = snapshot.get("progress", 0)
        percentage = int(progress * 100)

        builder.add_comment(f"Scroll Progress: {percentage}%")

        for elem_state in snapshot.get("element_states", []):
            self._add_element_styles(builder, elem_state, percentage)

    def _add_element_styles(
        self, builder: "CssRuleBuilder", elem_state: dict, percentage: int
    ) -> None:
        """为单个元素添加样式规则。"""
        selector = elem_state.get("selector", "")
        computed = elem_state.get("computedStyle", {})

        if not selector or selector == "html":
            return

        styles = self._extract_applicable_styles(computed)
        if styles:
            safe_selector = self._escape_css_selector(selector)
            rule_selector = f'[data-scroll-progress="{percentage}"] {safe_selector}'
            builder.add_rule(rule_selector, styles)

    def _extract_applicable_styles(self, computed: dict) -> list[str]:
        """提取适用的 CSS 样式。"""
        styles = []

        if computed.get("transform") and computed["transform"] != "none":
            styles.append(f"transform: {computed['transform']};")

        if computed.get("opacity"):
            styles.append(f"opacity: {computed['opacity']};")

        if computed.get("filter") and computed["filter"] != "none":
            styles.append(f"filter: {computed['filter']};")

        return styles

    def _escape_css_selector(self, selector: str) -> str:
        """转义 CSS 选择器中的特殊字符。"""
        return selector.replace(".", "\\.").replace("#", "\\#")

    def _add_utility_styles(self, builder: "CssRuleBuilder") -> None:
        """添加通用工具样式。"""
        self._add_css_variables(builder)
        self._add_animation_classes(builder)
        self._add_pin_styles(builder)

    def _add_css_variables(self, builder: "CssRuleBuilder") -> None:
        """添加 CSS 变量定义。"""
        builder.add_comment("Scroll-driven CSS Variables")
        builder.add_rule(":root", [
            "--scroll-progress: 0;",
            "--viewport-height: 100vh;",
        ])

    def _add_animation_classes(self, builder: "CssRuleBuilder") -> None:
        """添加 Intersection Observer 动画类。"""
        builder.add_comment("Intersection Observer Animation Classes")
        builder.add_rule(".wt-animate-on-scroll", [
            "transition: opacity 0.6s ease, transform 0.6s ease;",
        ])
        builder.add_rule(".wt-animate-on-scroll.wt-hidden", [
            "opacity: 0;",
            "transform: translateY(30px);",
        ])
        builder.add_rule(".wt-animate-on-scroll.wt-visible", [
            "opacity: 1;",
            "transform: translateY(0);",
        ])

    def _add_pin_styles(self, builder: "CssRuleBuilder") -> None:
        """添加 Pin 样式支持。"""
        builder.add_comment("Pin Styles")
        builder.add_rule(".wt-pin-container", [
            "position: relative;",
        ])
        builder.add_rule(".wt-pinned", [
            "position: fixed !important;",
            "top: 0;",
            "left: 0;",
            "width: 100%;",
            "z-index: 100;",
        ])


class CssRuleBuilder:
    """CSS 规则构建器，用于程序化构建 CSS 内容。"""

    def __init__(self):
        self._rules: list[str] = []
        self._add_header()

    def _add_header(self) -> None:
        """添加 CSS 文件头部注释。"""
        self._rules.append("/* WebThief ScrollTrigger Static Styles */")
        self._rules.append("/* Generated from captured animation states */")
        self._rules.append("")

    def add_comment(self, comment: str) -> None:
        """添加注释行。"""
        self._rules.append(f"/* {comment} */")

    def add_rule(self, selector: str, declarations: list[str]) -> None:
        """添加 CSS 规则。"""
        self._rules.append(f"{selector} {{")
        for declaration in declarations:
            self._rules.append(f"    {declaration}")
        self._rules.append("}")
        self._rules.append("")

    def build(self) -> str:
        """构建最终的 CSS 内容。"""
        return "\n".join(self._rules)

    @property
    def line_count(self) -> int:
        """获取当前行数。"""
        return len(self._rules)

    async def inject_scroll_trigger_tracker(self, page: Page) -> None:
        """
        通过 Playwright 注入跟踪代码
        拦截 ScrollTrigger 和 ScrollMagic 的创建和更新
        """
        console.print("[cyan]  📡 注入 ScrollTrigger 跟踪器...[/]")

        tracker_script = """
        (function() {
            'use strict';
            // ━━━ WebThief ScrollTrigger Tracker ━━━
            
            window.__webthief_scroll_trigger = {
                instances: [],
                events: [],
                animations: []
            };
            
            // 拦截 GSAP ScrollTrigger
            if (window.gsap && window.gsap.registerPlugin) {
                const originalRegisterPlugin = window.gsap.registerPlugin;
                window.gsap.registerPlugin = function(...plugins) {
                    plugins.forEach(plugin => {
                        window.__webthief_scroll_trigger.events.push({
                            type: 'plugin_registered',
                            plugin: plugin && plugin.name ? plugin.name : 'unknown',
                            timestamp: Date.now()
                        });
                    });
                    return originalRegisterPlugin.apply(this, arguments);
                };
            }
            
            // 拦截 ScrollTrigger.create
            if (window.ScrollTrigger) {
                const originalCreate = window.ScrollTrigger.create;
                window.ScrollTrigger.create = function(config) {
                    const instance = originalCreate.apply(this, arguments);
                    
                    window.__webthief_scroll_trigger.instances.push({
                        type: 'scrolltrigger',
                        config: {
                            trigger: config.trigger ? (config.trigger.id || config.trigger.className || config.trigger.tagName) : null,
                            start: config.start,
                            end: config.end,
                            scrub: config.scrub,
                            pin: config.pin,
                            markers: config.markers
                        },
                        timestamp: Date.now()
                    });
                    
                    console.log('[WebThief ScrollTrigger Tracker] 创建 ScrollTrigger:', config);
                    return instance;
                };
                
                // 监听 ScrollTrigger 更新
                window.ScrollTrigger.addEventListener('refresh', () => {
                    window.__webthief_scroll_trigger.events.push({
                        type: 'refresh',
                        timestamp: Date.now()
                    });
                });
            }
            
            // 拦截 ScrollMagic Controller
            if (window.ScrollMagic) {
                const OriginalController = window.ScrollMagic.Controller;
                window.ScrollMagic.Controller = function(options) {
                    const controller = new OriginalController(options);
                    
                    window.__webthief_scroll_trigger.instances.push({
                        type: 'scrollmagic_controller',
                        options: options,
                        timestamp: Date.now()
                    });
                    
                    console.log('[WebThief ScrollTrigger Tracker] 创建 ScrollMagic Controller');
                    return controller;
                };
                
                // 拦截 ScrollMagic Scene
                const OriginalScene = window.ScrollMagic.Scene;
                window.ScrollMagic.Scene = function(options) {
                    const scene = new OriginalScene(options);
                    
                    window.__webthief_scroll_trigger.instances.push({
                        type: 'scrollmagic_scene',
                        options: options,
                        timestamp: Date.now()
                    });
                    
                    console.log('[WebThief ScrollTrigger Tracker] 创建 ScrollMagic Scene:', options);
                    return scene;
                };
            }
            
            // 监听滚动事件
            let scrollTimeout;
            window.addEventListener('scroll', function() {
                clearTimeout(scrollTimeout);
                scrollTimeout = setTimeout(() => {
                    window.__webthief_scroll_trigger.events.push({
                        type: 'scroll',
                        scrollY: window.scrollY,
                        maxScroll: document.body.scrollHeight - window.innerHeight,
                        progress: window.scrollY / (document.body.scrollHeight - window.innerHeight),
                        timestamp: Date.now()
                    });
                }, 100);
            }, { passive: true });
            
            // 监听动画开始/结束
            if (window.gsap) {
                const originalTo = window.gsap.to;
                window.gsap.to = function(target, vars) {
                    const tween = originalTo.apply(this, arguments);
                    
                    window.__webthief_scroll_trigger.animations.push({
                        type: 'to',
                        target: typeof target === 'string' ? target : target.id || target.className || target.tagName,
                        vars: vars,
                        timestamp: Date.now()
                    });
                    
                    return tween;
                };
            }
            
            console.log('[WebThief ScrollTrigger Tracker] 跟踪器已激活');
        })();
        """

        try:
            await page.add_init_script(tracker_script)
            console.print("[green]  ✓ ScrollTrigger 跟踪器已注入[/]")

        except Exception as e:
            console.print(f"[red]  ✗ 跟踪器注入失败: {e}[/]")

    def generate_scroll_trigger_bridge_script(self) -> str:
        """
        生成 ScrollTrigger 桥接脚本
        用于在克隆页面中恢复滚动动画功能
        """
        bridge_script = """
        (function() {
            'use strict';
            // ━━━ WebThief ScrollTrigger Bridge ━━━
            
            // 使用 Intersection Observer 替代 ScrollTrigger
            const observerOptions = {
                root: null,
                rootMargin: '0px',
                threshold: [0, 0.25, 0.5, 0.75, 1.0]
            };
            
            const scrollObserver = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    const element = entry.target;
                    const ratio = entry.intersectionRatio;
                    
                    // 更新 CSS 变量
                    element.style.setProperty('--intersection-ratio', ratio);
                    
                    // 触发动画类
                    if (entry.isIntersecting) {
                        element.classList.add('wt-visible');
                        element.classList.remove('wt-hidden');
                        
                        // 触发自定义事件
                        element.dispatchEvent(new CustomEvent('wt-scroll-enter', {
                            detail: { ratio: ratio, boundingClientRect: entry.boundingClientRect }
                        }));
                    } else {
                        element.classList.remove('wt-visible');
                        element.classList.add('wt-hidden');
                        
                        element.dispatchEvent(new CustomEvent('wt-scroll-leave', {
                            detail: { ratio: ratio }
                        }));
                    }
                    
                    // 触发进度事件
                    element.dispatchEvent(new CustomEvent('wt-scroll-progress', {
                        detail: { ratio: ratio, isIntersecting: entry.isIntersecting }
                    }));
                });
            }, observerOptions);
            
            // 自动观察带有 data-scroll-trigger 的元素
            document.querySelectorAll('[data-scroll-trigger]').forEach(el => {
                el.classList.add('wt-animate-on-scroll');
                scrollObserver.observe(el);
            });
            
            // 观察 AOS 元素
            document.querySelectorAll('[data-aos]').forEach(el => {
                el.classList.add('wt-animate-on-scroll');
                scrollObserver.observe(el);
            });
            
            // 提供手动注册方法
            window.WebThiefScrollBridge = {
                observe: function(selector) {
                    document.querySelectorAll(selector).forEach(el => {
                        el.classList.add('wt-animate-on-scroll');
                        scrollObserver.observe(el);
                    });
                },
                
                unobserve: function(selector) {
                    document.querySelectorAll(selector).forEach(el => {
                        scrollObserver.unobserve(el);
                    });
                },
                
                // 模拟 ScrollTrigger.refresh
                refresh: function() {
                    document.querySelectorAll('[data-scroll-trigger], [data-aos]').forEach(el => {
                        scrollObserver.unobserve(el);
                        scrollObserver.observe(el);
                    });
                },
                
                // 获取当前滚动进度
                getScrollProgress: function() {
                    return window.scrollY / (document.body.scrollHeight - window.innerHeight);
                }
            };
            
            // 模拟 GSAP ScrollTrigger API
            window.ScrollTrigger = window.ScrollTrigger || {
                create: function(config) {
                    console.log('[WebThief Bridge] 模拟 ScrollTrigger.create', config);
                    if (config.trigger) {
                        const elements = document.querySelectorAll(config.trigger);
                        elements.forEach(el => {
                            el.setAttribute('data-scroll-trigger', '');
                            scrollObserver.observe(el);
                        });
                    }
                    return {
                        kill: function() {},
                        refresh: function() {},
                        disable: function() {},
                        enable: function() {}
                    };
                },
                
                getAll: function() {
                    return [];
                },
                
                refresh: function() {
                    window.WebThiefScrollBridge.refresh();
                },
                
                addEventListener: function(event, callback) {
                    window.addEventListener('wt-scroll-' + event, callback);
                }
            };
            
            console.log('[WebThief ScrollTrigger Bridge] 桥接脚本已激活');
        })();
        """

        return bridge_script

    async def get_tracking_data(self, page: Page) -> dict[str, Any]:
        """
        获取跟踪器收集的数据
        """
        try:
            tracking_data = await page.evaluate("""
                () => ({
                    instances: window.__webthief_scroll_trigger?.instances || [],
                    events: window.__webthief_scroll_trigger?.events || [],
                    animations: window.__webthief_scroll_trigger?.animations || []
                })
            """)

            console.print(f"[green]  ✓ 获取到 {len(tracking_data.get('instances', []))} 个实例[/]")
            console.print(f"[green]  ✓ 获取到 {len(tracking_data.get('events', []))} 个事件[/]")
            console.print(f"[green]  ✓ 获取到 {len(tracking_data.get('animations', []))} 个动画[/]")

            return tracking_data

        except Exception as e:
            console.print(f"[red]  ✗ 获取跟踪数据失败: {e}[/]")
            return {}
