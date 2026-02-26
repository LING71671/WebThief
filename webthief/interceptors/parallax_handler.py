"""
视差滚动效果处理模块
目标：检测、计算和转换视差滚动效果为静态 CSS
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from playwright.async_api import Page
from rich.console import Console

console = Console()


@dataclass
class ParallaxElement:
    """视差元素数据结构"""

    selector: str
    speed: float
    direction: str = "vertical"  # vertical, horizontal, both
    element_type: str = "div"  # div, img, section, etc.
    original_transform: str = ""
    is_background: bool = False


@dataclass
class ParallaxConfig:
    """视差效果配置"""

    speed: float
    start_offset: int = 0
    end_offset: int | None = None
    direction: str = "vertical"
    invert: bool = False
    scale_effect: bool = False
    opacity_effect: bool = False


class ParallaxHandler:
    """
    视差滚动效果处理器
    负责：
    1. 检测视差滚动元素（支持 data-speed、data-parallax、data-parallax-speed 属性）
    2. 计算不同滚动位置的视差层位置
    3. 将视差效果转换为 CSS transform
    4. 生成视差效果的静态 CSS 样式
    5. 通过 Playwright 注入跟踪代码
    """

    # 视差属性检测关键字
    PARALLAX_ATTRIBUTES = [
        "data-speed",
        "data-parallax",
        "data-parallax-speed",
        "data-parallax-x",
        "data-parallax-y",
        "data-parallax-direction",
    ]

    # 视差相关 CSS 类名
    PARALLAX_CLASS_NAMES = [
        "parallax",
        "parallax-bg",
        "parallax-element",
        "parallax-layer",
        "js-parallax",
    ]

    def __init__(self):
        self.parallax_elements: list[ParallaxElement] = []
        self.parallax_scripts: list[str] = []
        self.detected_configs: dict[str, ParallaxConfig] = {}
        self.css_output: str = ""

    async def detect_parallax_elements(self, page: Page) -> list[ParallaxElement]:
        """
        检测页面中的视差滚动元素
        支持 data-speed、data-parallax、data-parallax-speed 等属性
        """
        console.print("[cyan]  🔍 检测视差滚动元素...[/]")

        detection_script = """
            () => {
                const elements = [];
                const parallaxAttrs = [
                    'data-speed', 'data-parallax', 'data-parallax-speed',
                    'data-parallax-x', 'data-parallax-y', 'data-parallax-direction'
                ];
                const parallaxClasses = [
                    'parallax', 'parallax-bg', 'parallax-element',
                    'parallax-layer', 'js-parallax'
                ];

                // 通过属性检测
                parallaxAttrs.forEach(attr => {
                    document.querySelectorAll(`[${attr}]`).forEach((el, index) => {
                        const speed = parseFloat(el.getAttribute('data-speed') ||
                                                el.getAttribute('data-parallax-speed') ||
                                                el.getAttribute('data-parallax') || '0.5');
                        const direction = el.getAttribute('data-parallax-direction') || 'vertical';
                        const isBg = el.classList.contains('parallax-bg') ||
                                    el.getAttribute('data-parallax') === 'background';

                        elements.push({
                            selector: el.id ? `#${el.id}` :
                                     el.className ? `.${el.className.split(' ')[0]}:nth-of-type(${index + 1})` :
                                     `${el.tagName.toLowerCase()}[${attr}]:nth-of-type(${index + 1})`,
                            speed: speed,
                            direction: direction,
                            element_type: el.tagName.toLowerCase(),
                            original_transform: el.style.transform || '',
                            is_background: isBg,
                            source: 'attribute',
                            attr_name: attr,
                            attr_value: el.getAttribute(attr)
                        });
                    });
                });

                // 通过类名检测
                parallaxClasses.forEach(cls => {
                    document.querySelectorAll(`.${cls}`).forEach((el, index) => {
                        // 避免重复检测
                        if (!elements.some(e => e.element === el)) {
                            elements.push({
                                selector: el.id ? `#${el.id}` :
                                         `.${cls}:nth-of-type(${index + 1})`,
                                speed: 0.5,
                                direction: 'vertical',
                                element_type: el.tagName.toLowerCase(),
                                original_transform: el.style.transform || '',
                                is_background: cls.includes('bg') || cls.includes('background'),
                                source: 'class',
                                class_name: cls
                            });
                        }
                    });
                });

                // 检测常见的视差库
                const hasParallaxLib = !!(window.parallax ||
                                         window.Parallax ||
                                         window.rellax ||
                                         window.Rellax ||
                                         window.skrollr ||
                                         window.simpleParallax);

                return {
                    elements: elements,
                    has_library: hasParallaxLib,
                    library_name: window.rellax ? 'rellax' :
                                  window.Rellax ? 'rellax' :
                                  window.skrollr ? 'skrollr' :
                                  window.simpleParallax ? 'simpleParallax' :
                                  window.parallax ? 'parallax' :
                                  window.Parallax ? 'Parallax' : null
                };
            }
        """

        result = await page.evaluate(detection_script)

        # 转换为 ParallaxElement 对象
        self.parallax_elements = []
        for elem_data in result.get("elements", []):
            element = ParallaxElement(
                selector=elem_data["selector"],
                speed=elem_data["speed"],
                direction=elem_data["direction"],
                element_type=elem_data["element_type"],
                original_transform=elem_data.get("original_transform", ""),
                is_background=elem_data.get("is_background", False),
            )
            self.parallax_elements.append(element)

        console.print(f"[green]  ✓ 检测到 {len(self.parallax_elements)} 个视差元素[/]")
        if result.get("has_library"):
            console.print(f"[blue]  📚 检测到视差库: {result.get('library_name')}[/]")

        return self.parallax_elements

    def calculate_parallax_positions(
        self,
        element: ParallaxElement,
        scroll_positions: list[int] | None = None,
    ) -> dict[int, dict[str, float]]:
        """
        计算不同滚动位置的视差层位置

        Args:
            element: 视差元素
            scroll_positions: 滚动位置列表，默认 [0, 25, 50, 75, 100] 百分比

        Returns:
            滚动位置到位置信息的映射
        """
        if scroll_positions is None:
            scroll_positions = [0, 25, 50, 75, 100]

        positions: dict[int, dict[str, float]] = {}

        for scroll_pct in scroll_positions:
            # 计算视差偏移量
            # speed > 1 表示移动比滚动快，speed < 1 表示移动比滚动慢
            # speed < 0 表示反向移动
            offset = scroll_pct * element.speed

            if element.direction in ("vertical", "both"):
                translate_y = offset
            else:
                translate_y = 0

            if element.direction in ("horizontal", "both"):
                translate_x = offset
            else:
                translate_x = 0

            positions[scroll_pct] = {
                "translate_x": translate_x,
                "translate_y": translate_y,
                "scroll_percentage": scroll_pct,
            }

        return positions

    def convert_to_css_transform(
        self,
        element: ParallaxElement,
        scroll_percentage: float,
    ) -> str:
        """
        将视差效果转换为 CSS transform 字符串

        Args:
            element: 视差元素
            scroll_percentage: 当前滚动百分比 (0-100)

        Returns:
            CSS transform 字符串
        """
        positions = self.calculate_parallax_positions(
            element, [int(scroll_percentage)]
        )
        pos = positions.get(int(scroll_percentage), {"translate_x": 0, "translate_y": 0})

        transforms: list[str] = []

        # 添加视差位移
        if pos["translate_x"] != 0 or pos["translate_y"] != 0:
            transforms.append(f"translate3d({pos['translate_x']}px, {pos['translate_y']}px, 0)")

        # 保留原始 transform
        if element.original_transform:
            # 提取原始 transform 中非 translate 的部分
            original = element.original_transform
            # 移除已有的 translate 避免冲突
            original = re.sub(r"translate3d\([^)]+\)", "", original)
            original = re.sub(r"translate\([^)]+\)", "", original)
            original = re.sub(r"translateX\([^)]+\)", "", original)
            original = re.sub(r"translateY\([^)]+\)", "", original)
            original = original.strip()
            if original:
                transforms.append(original)

        return " ".join(transforms) if transforms else "none"

    def generate_static_css(self, elements: list[ParallaxElement] | None = None) -> str:
        """
        生成视差效果的静态 CSS 样式
        使用 CSS scroll-timeline 或 keyframes 实现

        Args:
            elements: 视差元素列表，默认使用已检测到的元素

        Returns:
            生成的 CSS 字符串
        """
        if elements is None:
            elements = self.parallax_elements

        css_lines: list[str] = []
        css_lines.append("/* ━━━ WebThief Parallax Static CSS ━━━ */")
        css_lines.append("")

        # 添加基础视差容器样式
        css_lines.append("/* 视差容器基础样式 */")
        css_lines.append(".parallax-container,")
        css_lines.append("[data-parallax],")
        css_lines.append("[data-speed],")
        css_lines.append("[data-parallax-speed] {")
        css_lines.append("    position: relative;")
        css_lines.append("    overflow: hidden;")
        css_lines.append("}")
        css_lines.append("")

        # 为背景视差元素添加特定样式
        css_lines.append("/* 背景视差元素 */")
        css_lines.append(".parallax-bg,")
        css_lines.append("[data-parallax=\"background\"] {")
        css_lines.append("    position: absolute;")
        css_lines.append("    top: -20%;")
        css_lines.append("    left: 0;")
        css_lines.append("    width: 100%;")
        css_lines.append("    height: 140%;")
        css_lines.append("    will-change: transform;")
        css_lines.append("    pointer-events: none;")
        css_lines.append("}")
        css_lines.append("")

        # 为每个元素生成 CSS
        for index, element in enumerate(elements):
            class_name = f"webthief-parallax-{index + 1}"

            css_lines.append(f"/* 视差元素 {index + 1}: {element.selector} */")
            css_lines.append(f"{element.selector},")
            css_lines.append(f".{class_name} {{")
            css_lines.append("    will-change: transform;")
            css_lines.append("    transform-style: preserve-3d;")

            if element.is_background:
                css_lines.append("    position: absolute;")
                css_lines.append("    top: -20%;")
                css_lines.append("    left: 0;")
                css_lines.append("    width: 100%;")
                css_lines.append("    height: 140%;")
                css_lines.append("    pointer-events: none;")

            css_lines.append("}")
            css_lines.append("")

            # 生成 keyframes 动画
            keyframe_name = f"parallax-move-{index + 1}"
            css_lines.append(f"@keyframes {keyframe_name} {{")
            css_lines.append("    0% {")

            # 计算起始位置
            start_transform = self.convert_to_css_transform(element, 0)
            css_lines.append(f"        transform: {start_transform};")
            css_lines.append("    }")

            # 50% 位置
            css_lines.append("    50% {")
            mid_transform = self.convert_to_css_transform(element, 50)
            css_lines.append(f"        transform: {mid_transform};")
            css_lines.append("    }")

            # 100% 位置
            css_lines.append("    100% {")
            end_transform = self.convert_to_css_transform(element, 100)
            css_lines.append(f"        transform: {end_transform};")
            css_lines.append("    }")
            css_lines.append("}")
            css_lines.append("")

            # 应用动画
            css_lines.append(f"{element.selector}.parallax-active,")
            css_lines.append(f".{class_name}.parallax-active {{")
            css_lines.append(f"    animation: {keyframe_name} linear;")
            css_lines.append("    animation-timeline: scroll();")
            css_lines.append("    animation-range: entry exit;")
            css_lines.append("}")
            css_lines.append("")

        # 添加降级方案（不支持 scroll-timeline 的浏览器）
        css_lines.append("/* 降级方案：使用 sticky 定位 */")
        css_lines.append("@supports not (animation-timeline: scroll()) {")
        for index, element in enumerate(elements):
            css_lines.append(f"    {element.selector},")
            css_lines.append(f"    .webthief-parallax-{index + 1} {{")
            css_lines.append("        position: sticky;")
            css_lines.append("        top: 0;")
            css_lines.append("    }")
        css_lines.append("}")
        css_lines.append("")

        self.css_output = "\n".join(css_lines)
        return self.css_output

    async def inject_parallax_tracker(self, page: Page) -> None:
        """
        通过 Playwright 注入视差跟踪代码
        用于监控和记录视差效果
        """
        console.print("[cyan]  📡 注入视差跟踪代码...[/]")

        tracker_script = """
        (function() {
            'use strict';
            // ━━━ WebThief Parallax Tracker ━━━

            window.__webthief_parallax = {
                elements: [],
                scroll_positions: [],
                is_tracking: false,
                library_detected: null
            };

            // 检测视差库
            function detectParallaxLibrary() {
                if (window.rellax || window.Rellax) {
                    return 'rellax';
                }
                if (window.skrollr) {
                    return 'skrollr';
                }
                if (window.simpleParallax) {
                    return 'simpleParallax';
                }
                if (window.parallax || window.Parallax) {
                    return 'parallax.js';
                }
                return null;
            }

            // 收集视差元素信息
            function collectParallaxElements() {
                const elements = [];
                const attrs = [
                    'data-speed', 'data-parallax', 'data-parallax-speed',
                    'data-parallax-x', 'data-parallax-y'
                ];

                attrs.forEach(attr => {
                    document.querySelectorAll(`[${attr}]`).forEach((el, idx) => {
                        const rect = el.getBoundingClientRect();
                        elements.push({
                            selector: el.id ? `#${el.id}` :
                                     el.className ? `.${el.className.split(' ')[0]}` :
                                     `${el.tagName.toLowerCase()}[${attr}]`,
                            speed: parseFloat(el.getAttribute('data-speed') ||
                                            el.getAttribute('data-parallax-speed') || '0.5'),
                            direction: el.getAttribute('data-parallax-direction') || 'vertical',
                            rect: {
                                top: rect.top + window.scrollY,
                                left: rect.left + window.scrollX,
                                width: rect.width,
                                height: rect.height
                            },
                            is_background: el.classList.contains('parallax-bg'),
                            original_transform: el.style.transform || ''
                        });
                    });
                });

                return elements;
            }

            // 跟踪滚动位置
            function trackScrollPosition() {
                if (!window.__webthief_parallax.is_tracking) return;

                const scroll_y = window.scrollY;
                const max_scroll = document.documentElement.scrollHeight - window.innerHeight;
                const scroll_pct = max_scroll > 0 ? (scroll_y / max_scroll) * 100 : 0;

                window.__webthief_parallax.scroll_positions.push({
                    y: scroll_y,
                    percentage: scroll_pct,
                    timestamp: Date.now()
                });

                // 限制记录数量
                if (window.__webthief_parallax.scroll_positions.length > 1000) {
                    window.__webthief_parallax.scroll_positions.shift();
                }
            }

            // 初始化
            window.__webthief_parallax.library_detected = detectParallaxLibrary();
            window.__webthief_parallax.elements = collectParallaxElements();

            // 监听滚动
            let ticking = false;
            window.addEventListener('scroll', function() {
                if (!ticking) {
                    window.requestAnimationFrame(function() {
                        trackScrollPosition();
                        ticking = false;
                    });
                    ticking = true;
                }
            }, { passive: true });

            // 开始跟踪
            window.__webthief_parallax.start_tracking = function() {
                window.__webthief_parallax.is_tracking = true;
                console.log('[WebThief Parallax] 开始跟踪视差效果');
            };

            window.__webthief_parallax.stop_tracking = function() {
                window.__webthief_parallax.is_tracking = false;
                console.log('[WebThief Parallax] 停止跟踪视差效果');
            };

            window.__webthief_parallax.get_report = function() {
                return {
                    elements: window.__webthief_parallax.elements,
                    library: window.__webthief_parallax.library_detected,
                    scroll_samples: window.__webthief_parallax.scroll_positions.length,
                    tracked_positions: window.__webthief_parallax.scroll_positions.slice(-10)
                };
            };

            console.log('[WebThief Parallax] 视差跟踪器已激活');
            console.log('[WebThief Parallax] 检测到', window.__webthief_parallax.elements.length, '个视差元素');
            if (window.__webthief_parallax.library_detected) {
                console.log('[WebThief Parallax] 检测到视差库:', window.__webthief_parallax.library_detected);
            }
        })();
        """

        await page.add_init_script(tracker_script)
        console.print("[green]  ✓ 视差跟踪代码已注入[/]")

    async def get_tracking_report(self, page: Page) -> dict[str, Any]:
        """
        获取视差跟踪报告
        """
        report = await page.evaluate("""
            () => {
                if (window.__webthief_parallax && window.__webthief_parallax.get_report) {
                    return window.__webthief_parallax.get_report();
                }
                return { error: 'Tracker not initialized' };
            }
        """)
        return report

    def generate_parallax_bridge_script(self) -> str:
        """
        生成视差桥接脚本
        用于在克隆页面中模拟视差效果
        """
        bridge_script = """
        (function() {
            'use strict';
            // ━━━ WebThief Parallax Bridge Script ━━━

            // 简单的视差实现（作为库的降级方案）
            window.WebThiefParallax = {
                elements: [],
                initialized: false,

                init: function(selector) {
                    const elements = document.querySelectorAll(selector || '[data-speed], [data-parallax], [data-parallax-speed]');

                    elements.forEach(el => {
                        const speed = parseFloat(
                            el.getAttribute('data-speed') ||
                            el.getAttribute('data-parallax-speed') ||
                            el.getAttribute('data-parallax') ||
                            '0.5'
                        );

                        this.elements.push({
                            element: el,
                            speed: speed,
                            direction: el.getAttribute('data-parallax-direction') || 'vertical',
                            original_transform: el.style.transform || ''
                        });
                    });

                    this.initialized = true;
                    this.bindEvents();
                    console.log('[WebThief Parallax Bridge] 初始化完成，', this.elements.length, '个元素');
                },

                bindEvents: function() {
                    let ticking = false;

                    window.addEventListener('scroll', function() {
                        if (!ticking) {
                            window.requestAnimationFrame(function() {
                                window.WebThiefParallax.update();
                                ticking = false;
                            });
                            ticking = true;
                        }
                    }, { passive: true });
                },

                update: function() {
                    const scroll_y = window.scrollY;

                    this.elements.forEach(item => {
                        const el = item.element;
                        const speed = item.speed;

                        // 计算视差偏移
                        let translate_x = 0;
                        let translate_y = 0;

                        if (item.direction === 'vertical' || item.direction === 'both') {
                            translate_y = scroll_y * speed * 0.1;
                        }
                        if (item.direction === 'horizontal' || item.direction === 'both') {
                            translate_x = scroll_y * speed * 0.1;
                        }

                        // 应用 transform
                        const transform = `translate3d(${translate_x}px, ${translate_y}px, 0) ${item.original_transform}`;
                        el.style.transform = transform;
                    });
                },

                destroy: function() {
                    this.elements.forEach(item => {
                        item.element.style.transform = item.original_transform;
                    });
                    this.elements = [];
                    this.initialized = false;
                }
            };

            // 自动初始化
            if (document.readyState === 'loading') {
                document.addEventListener('DOMContentLoaded', function() {
                    window.WebThiefParallax.init();
                });
            } else {
                window.WebThiefParallax.init();
            }

            console.log('[WebThief Parallax Bridge] 视差桥接脚本已激活');
        })();
        """
        return bridge_script

    async def preserve_parallax_scripts(self, page: Page) -> list[str]:
        """
        识别并保留视差相关的脚本
        """
        console.print("[cyan]  🔍 识别视差相关脚本...[/]")

        scripts = await page.evaluate("""
            () => {
                const scripts = [];
                document.querySelectorAll('script[src]').forEach(script => {
                    scripts.push({
                        src: script.src,
                        async: script.async,
                        defer: script.defer
                    });
                });
                return scripts;
            }
        """)

        parallax_keywords = [
            'parallax', 'rellax', 'skrollr', 'scroll', 'stellar',
            'jarallax', 'simpleparallax', 'rellax'
        ]
        preserved_scripts = []

        for script in scripts:
            src = script['src'].lower()
            if any(kw in src for kw in parallax_keywords):
                preserved_scripts.append(script['src'])
                console.print(f"[dim]  📦 保留视差脚本: {script['src']}[/]")

        return preserved_scripts
