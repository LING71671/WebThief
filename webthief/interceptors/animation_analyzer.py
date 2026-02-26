"""
CSS 动画分析与保留模块
目标：分析页面中的 CSS 动画，识别关键动画类型，计算最优冻结点，选择性保留关键动画
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from playwright.async_api import Page
from rich.console import Console

console = Console()


class AnimationType(Enum):
    """动画类型枚举"""
    ENTRANCE = "entrance"      # 入场动画
    HOVER = "hover"            # 悬停动画
    SCROLL = "scroll"          # 滚动动画
    LOOP = "loop"              # 循环动画
    EXIT = "exit"              # 退出动画
    TRANSITION = "transition"  # 过渡动画
    UNKNOWN = "unknown"        # 未知类型


@dataclass
class KeyframeRule:
    """关键帧规则数据类"""
    name: str
    raw_css: str
    selectors: list[str] = field(default_factory=list)
    properties: dict[str, list[tuple[float, str]]] = field(default_factory=dict)


@dataclass
class AnimationInfo:
    """动画信息数据类"""
    name: str
    animation_type: AnimationType
    target_selector: str
    duration: float
    delay: float
    timing_function: str
    iteration_count: str
    direction: str
    fill_mode: str
    keyframes: KeyframeRule | None = None
    importance_score: float = 0.0
    freeze_point: float = 0.0
    should_preserve: bool = False


@dataclass
class AnimationReport:
    """动画分析报告数据类"""
    total_animations: int = 0
    animations_by_type: dict[str, int] = field(default_factory=dict)
    preserved_animations: list[AnimationInfo] = field(default_factory=list)
    removed_animations: list[AnimationInfo] = field(default_factory=list)
    css_output: str = ""
    recommendations: list[str] = field(default_factory=list)


class AnimationAnalyzer:
    """
    CSS 动画分析器
    负责：
    1. 分析页面中的 CSS 动画关键帧（@keyframes）
    2. 识别关键动画类型：入场、悬停、滚动、循环
    3. 计算最优动画冻结点
    4. 选择性保留关键动画
    5. 生成动画保留的 CSS 样式
    6. 提供动画分析报告
    """

    # 动画类型识别关键字
    ENTRANCE_KEYWORDS = [
        'fadein', 'slidein', 'zoomin', 'bouncein', 'fade-in', 'slide-in',
        'zoom-in', 'bounce-in', 'enter', 'appear', 'show', 'intro',
        'reveal', 'dropin', 'grow', 'expand', 'popin', 'flyin'
    ]

    HOVER_KEYWORDS = [
        'hover', 'mouseover', 'mouseenter', 'mouseleave', 'onhover',
        'hoverin', 'hoverout', 'focus', 'active'
    ]

    SCROLL_KEYWORDS = [
        'scroll', 'parallax', 'scrolltrigger', 'scroll-trigger',
        'aos', 'scrollreveal', 'waypoint', 'sticky'
    ]

    LOOP_KEYWORDS = [
        'infinite', 'loop', 'rotate', 'spin', 'pulse', 'shake',
        'bounce', 'flash', 'swing', 'tada', 'wobble', 'jello',
        'heartbeat', 'breathing', 'ripple', 'loading', 'spinner'
    ]

    EXIT_KEYWORDS = [
        'fadeout', 'slideout', 'zoomout', 'bounceout', 'fade-out',
        'slide-out', 'zoom-out', 'bounce-out', 'exit', 'disappear',
        'hide', 'outro', 'collapse', 'shrink', 'popout', 'flyout'
    ]

    # 关键动画属性
    CRITICAL_PROPERTIES = [
        'opacity', 'transform', 'visibility', 'display',
        'width', 'height', 'top', 'left', 'right', 'bottom'
    ]

    def __init__(self):
        self.keyframe_rules: dict[str, KeyframeRule] = {}
        self.animation_declarations: list[AnimationInfo] = []
        self.css_text: str = ""
        self.preserved_styles: list[str] = []

    async def analyze_css_animations(self, page: Page) -> list[AnimationInfo]:
        """
        分析页面中的 CSS 动画关键帧
        返回识别到的所有动画信息列表
        """
        console.print("[cyan]  🎬 分析 CSS 动画...[/]")

        # 提取页面所有 CSS 规则和动画信息
        css_data = await page.evaluate("""
            () => {
                const results = {
                    keyframes: [],
                    animations: [],
                    stylesheets: []
                };
                
                // 提取所有样式表中的关键帧
                for (const sheet of document.styleSheets) {
                    try {
                        for (const rule of sheet.cssRules || []) {
                            // 提取 @keyframes 规则
                            if (rule.type === CSSRule.KEYFRAMES_RULE) {
                                results.keyframes.push({
                                    name: rule.name,
                                    cssText: rule.cssText,
                                    cssRules: Array.from(rule.cssRules).map(r => ({
                                        keyText: r.keyText,
                                        cssText: r.cssText
                                    }))
                                });
                            }
                            // 提取动画相关样式
                            else if (rule.type === CSSRule.STYLE_RULE) {
                                const style = rule.style;
                                const animationName = style.animationName || style.webkitAnimationName;
                                if (animationName && animationName !== 'none') {
                                    results.animations.push({
                                        selector: rule.selectorText,
                                        animationName: animationName,
                                        animationDuration: style.animationDuration || style.webkitAnimationDuration || '0s',
                                        animationDelay: style.animationDelay || style.webkitAnimationDelay || '0s',
                                        animationTimingFunction: style.animationTimingFunction || style.webkitAnimationTimingFunction || 'ease',
                                        animationIterationCount: style.animationIterationCount || style.webkitAnimationIterationCount || '1',
                                        animationDirection: style.animationDirection || style.webkitAnimationDirection || 'normal',
                                        animationFillMode: style.animationFillMode || style.webkitAnimationFillMode || 'none',
                                        transition: style.transition || ''
                                    });
                                }
                            }
                        }
                    } catch (e) {
                        // 跨域样式表可能无法访问
                    }
                }
                
                // 提取内联样式中的动画
                document.querySelectorAll('[style*="animation"]').forEach(el => {
                    results.animations.push({
                        selector: el.tagName.toLowerCase() + (el.id ? '#' + el.id : '') + (el.className ? '.' + el.className.split(' ').join('.') : ''),
                        inline: true,
                        style: el.getAttribute('style')
                    });
                });
                
                return results;
            }
        """)

        # 解析关键帧规则
        for keyframe_data in css_data.get('keyframes', []):
            keyframe = self._parse_keyframe_rule(keyframe_data)
            self.keyframe_rules[keyframe.name] = keyframe

        # 解析动画声明
        for anim_data in css_data.get('animations', []):
            animation_info = self._parse_animation_declaration(anim_data)
            if animation_info:
                self.animation_declarations.append(animation_info)

        console.print(f"[green]  ✓ 发现 {len(self.keyframe_rules)} 个关键帧规则[/]")
        console.print(f"[green]  ✓ 发现 {len(self.animation_declarations)} 个动画声明[/]")

        return self.animation_declarations

    def _parse_keyframe_rule(self, data: dict[str, Any]) -> KeyframeRule:
        """解析关键帧规则"""
        keyframe = KeyframeRule(
            name=data.get('name', ''),
            raw_css=data.get('cssText', '')
        )

        # 解析选择器和属性
        for rule in data.get('cssRules', []):
            selector = rule.get('keyText', '')
            keyframe.selectors.append(selector)

            # 解析 CSS 属性
            css_text = rule.get('cssText', '')
            properties = self._extract_css_properties(css_text)
            for prop, value in properties.items():
                percentage = self._selector_to_percentage(selector)
                if prop not in keyframe.properties:
                    keyframe.properties[prop] = []
                keyframe.properties[prop].append((percentage, value))

        return keyframe

    def _parse_animation_declaration(self, data: dict[str, Any]) -> AnimationInfo | None:
        """解析动画声明"""
        animation_name = data.get('animationName', '')
        if not animation_name or animation_name == 'none':
            return None

        # 确定动画类型
        animation_type = self._detect_animation_type(animation_name, data)

        # 解析时间值
        duration = self._parse_time_value(data.get('animationDuration', '0s'))
        delay = self._parse_time_value(data.get('animationDelay', '0s'))

        # 关联关键帧
        keyframes = self.keyframe_rules.get(animation_name)

        # 创建动画信息
        animation_info = AnimationInfo(
            name=animation_name,
            animation_type=animation_type,
            target_selector=data.get('selector', ''),
            duration=duration,
            delay=delay,
            timing_function=data.get('animationTimingFunction', 'ease'),
            iteration_count=data.get('animationIterationCount', '1'),
            direction=data.get('animationDirection', 'normal'),
            fill_mode=data.get('animationFillMode', 'none'),
            keyframes=keyframes
        )

        # 计算重要性和冻结点
        animation_info.importance_score = self._calculate_importance_score(animation_info)
        animation_info.freeze_point = self.calculate_optimal_freeze_point(animation_info)
        animation_info.should_preserve = self._should_preserve_animation(animation_info)

        return animation_info

    def _detect_animation_type(self, name: str, data: dict[str, Any]) -> AnimationType:
        """检测动画类型"""
        name_lower = name.lower()

        # 按优先级检查各种关键字
        animation_type = self._detect_type_by_keywords(name_lower)
        if animation_type != AnimationType.UNKNOWN:
            return animation_type

        # 检查选择器中的悬停关键字
        if self._has_hover_selector(data):
            return AnimationType.HOVER

        # 检查迭代次数
        if self._is_infinite_animation(data):
            return AnimationType.LOOP

        # 检查过渡属性
        if self._has_transition(data):
            return AnimationType.TRANSITION

        return AnimationType.UNKNOWN

    def _detect_type_by_keywords(self, name_lower: str) -> AnimationType:
        """根据关键字检测动画类型"""
        keyword_map = [
            (self.ENTRANCE_KEYWORDS, AnimationType.ENTRANCE),
            (self.EXIT_KEYWORDS, AnimationType.EXIT),
            (self.LOOP_KEYWORDS, AnimationType.LOOP),
            (self.SCROLL_KEYWORDS, AnimationType.SCROLL),
        ]

        for keywords, anim_type in keyword_map:
            if any(kw in name_lower for kw in keywords):
                return anim_type

        return AnimationType.UNKNOWN

    def _has_hover_selector(self, data: dict[str, Any]) -> bool:
        """检查选择器中是否包含悬停关键字"""
        selector = data.get('selector', '').lower()
        return any(kw in selector for kw in self.HOVER_KEYWORDS)

    def _is_infinite_animation(self, data: dict[str, Any]) -> bool:
        """检查是否为无限循环动画"""
        iteration_count = data.get('animationIterationCount', '1')
        return iteration_count in ['infinite', 'infinite ']

    def _has_transition(self, data: dict[str, Any]) -> bool:
        """检查是否有过渡属性"""
        return bool(data.get('transition', ''))

    def _parse_time_value(self, time_str: str) -> float:
        """解析时间值为毫秒"""
        if not time_str:
            return 0.0

        time_str = str(time_str).strip().lower()

        # 处理多个值的情况，取第一个
        if ',' in time_str:
            time_str = time_str.split(',')[0].strip()

        try:
            if time_str.endswith('ms'):
                return float(time_str[:-2])
            elif time_str.endswith('s'):
                return float(time_str[:-1]) * 1000
            else:
                return float(time_str)
        except ValueError:
            return 0.0

    def _selector_to_percentage(self, selector: str) -> float:
        """将选择器转换为百分比值"""
        selector = selector.strip()

        if selector == 'from' or selector == '0%':
            return 0.0
        if selector == 'to' or selector == '100%':
            return 100.0

        try:
            if selector.endswith('%'):
                return float(selector[:-1])
        except ValueError:
            pass

        return 0.0

    def _extract_css_properties(self, css_text: str) -> dict[str, str]:
        """从 CSS 文本中提取属性"""
        properties = {}

        # 移除选择器部分
        if '{' in css_text and '}' in css_text:
            content = css_text[css_text.find('{') + 1:css_text.rfind('}')]
        else:
            content = css_text

        # 解析属性
        for match in re.finditer(r'([\w-]+)\s*:\s*([^;]+)', content):
            prop_name = match.group(1).strip()
            prop_value = match.group(2).strip()
            properties[prop_name] = prop_value

        return properties

    def _calculate_importance_score(self, animation: AnimationInfo) -> float:
        """计算动画重要性分数（0-100）"""
        score = 0.0

        # 入场动画通常很重要
        if animation.animation_type == AnimationType.ENTRANCE:
            score += 30.0

        # 悬停动画对交互很重要
        if animation.animation_type == AnimationType.HOVER:
            score += 25.0

        # 循环动画可能是装饰性的，分数较低
        if animation.animation_type == AnimationType.LOOP:
            score += 10.0

        # 包含关键属性的动画更重要
        if animation.keyframes:
            for prop in animation.keyframes.properties.keys():
                if any(cp in prop.lower() for cp in self.CRITICAL_PROPERTIES):
                    score += 15.0
                    break

        # 持续时间短的动画可能是重要的微交互
        if animation.duration < 300:
            score += 10.0

        # 无限循环的动画可能是装饰性的
        if animation.iteration_count in ['infinite', 'infinite ']:
            score -= 10.0

        return min(100.0, max(0.0, score))

    def _should_preserve_animation(self, animation: AnimationInfo) -> bool:
        """判断是否应该保留动画"""
        # 重要性高的动画保留
        if animation.importance_score >= 40.0:
            return True

        # 入场动画通常需要保留
        if animation.animation_type == AnimationType.ENTRANCE:
            return True

        # 悬停动画保留
        if animation.animation_type == AnimationType.HOVER:
            return True

        # 滚动触发动画保留
        if animation.animation_type == AnimationType.SCROLL:
            return True

        return False

    def calculate_optimal_freeze_point(self, animation: AnimationInfo) -> float:
        """
        计算最优动画冻结点
        返回动画进度百分比（0-100）
        """
        if not animation.keyframes or not animation.keyframes.properties:
            return 100.0

        freeze_point = self._get_default_freeze_point(animation.animation_type)
        freeze_point = self._adjust_freeze_point_by_properties(
            freeze_point, animation.keyframes.properties
        )

        return freeze_point

    def _get_default_freeze_point(self, animation_type: AnimationType) -> float:
        """根据动画类型获取默认冻结点"""
        freeze_point_map = {
            AnimationType.ENTRANCE: 100.0,
            AnimationType.EXIT: 0.0,
            AnimationType.HOVER: 0.0,
            AnimationType.LOOP: 50.0,
            AnimationType.SCROLL: 50.0,
        }
        return freeze_point_map.get(animation_type, 100.0)

    def _adjust_freeze_point_by_properties(
        self, freeze_point: float, properties: dict[str, list[tuple[float, str]]]
    ) -> float:
        """根据关键属性调整冻结点"""
        for prop, values in properties.items():
            prop_lower = prop.lower()

            if 'opacity' in prop_lower:
                freeze_point = self._find_opacity_optimal_point(freeze_point, values)
            elif 'transform' in prop_lower and 'scale' in str(values).lower():
                freeze_point = self._find_scale_optimal_point(freeze_point, values)

        return freeze_point

    def _find_opacity_optimal_point(
        self, current_point: float, values: list[tuple[float, str]]
    ) -> float:
        """找到 opacity 接近 1 的最优点"""
        for percentage, value in values:
            if '1' in value or value == '1':
                return min(current_point, percentage)
        return current_point

    def _find_scale_optimal_point(
        self, current_point: float, values: list[tuple[float, str]]
    ) -> float:
        """找到 scale 接近 1 的最优点"""
        for percentage, value in values:
            if 'scale(1)' in value or 'scale3d(1' in value:
                return min(current_point, percentage)
        return current_point

    def preserve_critical_animations(self, animations: list[AnimationInfo] | None = None) -> list[AnimationInfo]:
        """
        选择性保留关键动画
        返回需要保留的动画列表
        """
        console.print("[cyan]  💾 选择性保留关键动画...[/]")

        if animations is None:
            animations = self.animation_declarations

        preserved = []
        removed = []

        for animation in animations:
            if animation.should_preserve:
                preserved.append(animation)
                console.print(f"[green]  ✓ 保留动画: {animation.name} ({animation.animation_type.value})[/]")
            else:
                removed.append(animation)
                console.print(f"[dim]  ✗ 移除动画: {animation.name} ({animation.animation_type.value})[/]")

        console.print(f"[green]  ✓ 保留 {len(preserved)} 个关键动画，移除 {len(removed)} 个动画[/]")

        return preserved

    def generate_preserved_css(self, animations: list[AnimationInfo] | None = None) -> str:
        """
        生成动画保留的 CSS 样式
        返回生成的 CSS 文本
        """
        if animations is None:
            animations = [a for a in self.animation_declarations if a.should_preserve]

        css_parts = []
        css_parts.append("/* ━━━ WebThief 保留的关键动画样式 ━━━ */")
        css_parts.append("")

        # 生成关键帧保留样式
        processed_keyframes: set[str] = set()

        for animation in animations:
            if animation.name in processed_keyframes:
                continue
            processed_keyframes.add(animation.name)

            # 生成冻结状态的 CSS
            freeze_css = self._generate_freeze_css(animation)
            if freeze_css:
                css_parts.append(f"/* 动画: {animation.name} - 冻结在 {animation.freeze_point}% */")
                css_parts.append(f"{animation.target_selector} {{")
                css_parts.append(f"    animation: none !important;")
                css_parts.extend(f"    {line}" for line in freeze_css)
                css_parts.append("}")
                css_parts.append("")

        # 添加通用动画重置
        css_parts.append("/* 通用动画重置 */")
        css_parts.append(".webthief-no-animation, .webthief-no-animation * {")
        css_parts.append("    animation: none !important;")
        css_parts.append("    transition: none !important;")
        css_parts.append("}")
        css_parts.append("")

        self.css_text = "\n".join(css_parts)
        return self.css_text

    def _generate_freeze_css(self, animation: AnimationInfo) -> list[str]:
        """生成冻结状态的 CSS 属性"""
        css_lines = []

        if not animation.keyframes:
            return css_lines

        # 找到最接近冻结点的关键帧
        freeze_percentage = animation.freeze_point
        closest_frame = None
        closest_distance = float('inf')

        for selector in animation.keyframes.selectors:
            percentage = self._selector_to_percentage(selector)
            distance = abs(percentage - freeze_percentage)
            if distance < closest_distance:
                closest_distance = distance
                closest_frame = selector

        if closest_frame and animation.keyframes.raw_css:
            # 提取该关键帧的属性
            properties = self._extract_properties_at_selector(
                animation.keyframes.raw_css,
                closest_frame
            )
            for prop, value in properties.items():
                css_lines.append(f"{prop}: {value} !important;")

        return css_lines

    def _extract_properties_at_selector(self, raw_css: str, target_selector: str) -> dict[str, str]:
        """提取特定选择器的 CSS 属性"""
        properties = {}

        # 构建正则表达式匹配目标选择器的内容
        pattern = rf'{re.escape(target_selector)}\s*\{{([^}}]+)\}}'
        match = re.search(pattern, raw_css, re.IGNORECASE)

        if match:
            content = match.group(1)
            for prop_match in re.finditer(r'([\w-]+)\s*:\s*([^;]+)', content):
                prop_name = prop_match.group(1).strip()
                prop_value = prop_match.group(2).strip()
                properties[prop_name] = prop_value

        return properties

    def get_animation_report(self) -> AnimationReport:
        """
        获取动画分析报告
        返回详细的动画分析报告
        """
        report = AnimationReport()

        # 统计总数
        report.total_animations = len(self.animation_declarations)

        # 按类型统计
        for animation in self.animation_declarations:
            type_name = animation.animation_type.value
            report.animations_by_type[type_name] = report.animations_by_type.get(type_name, 0) + 1

        # 分类保留和移除的动画
        for animation in self.animation_declarations:
            if animation.should_preserve:
                report.preserved_animations.append(animation)
            else:
                report.removed_animations.append(animation)

        # 生成 CSS 输出
        report.css_output = self.generate_preserved_css(report.preserved_animations)

        # 生成建议
        report.recommendations = self._generate_recommendations()

        return report

    def _generate_recommendations(self) -> list[str]:
        """生成动画处理建议"""
        recommendations = []

        # 统计各类动画数量
        type_counts: dict[str, int] = {}
        for animation in self.animation_declarations:
            type_name = animation.animation_type.value
            type_counts[type_name] = type_counts.get(type_name, 0) + 1

        # 基于统计生成建议
        if type_counts.get('loop', 0) > 5:
            recommendations.append(
                f"检测到 {type_counts['loop']} 个循环动画，建议保留核心加载动画，"
                "移除装饰性动画以提升性能"
            )

        if type_counts.get('entrance', 0) > 0:
            recommendations.append(
                f"检测到 {type_counts['entrance']} 个入场动画，已自动保留关键入场效果"
            )

        if type_counts.get('scroll', 0) > 3:
            recommendations.append(
                f"检测到 {type_counts['scroll']} 个滚动动画，建议在静态页面中冻结为默认状态"
            )

        long_animations = [a for a in self.animation_declarations if a.duration > 3000]
        if long_animations:
            recommendations.append(
                f"检测到 {len(long_animations)} 个长时长动画 (>3s)，"
                "建议检查是否需要完整保留"
            )

        return recommendations

    def print_report(self, report: AnimationReport | None = None) -> None:
        """打印动画分析报告到控制台"""
        if report is None:
            report = self.get_animation_report()

        console.print("\n[bold cyan]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/]")
        console.print("[bold cyan]         CSS 动画分析报告[/]")
        console.print("[bold cyan]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/]")

        console.print(f"\n[bold]总动画数量:[/] {report.total_animations}")

        console.print("\n[bold]动画类型分布:[/]")
        for anim_type, count in sorted(report.animations_by_type.items()):
            console.print(f"  • {anim_type}: {count}")

        console.print(f"\n[bold]保留动画:[/] {len(report.preserved_animations)}")
        for anim in report.preserved_animations:
            console.print(
                f"  [green]✓[/] {anim.name} "
                f"([dim]{anim.animation_type.value}[/], "
                f"重要性: {anim.importance_score:.1f})"
            )

        console.print(f"\n[bold]移除动画:[/] {len(report.removed_animations)}")
        for anim in report.removed_animations:
            console.print(
                f"  [red]✗[/] {anim.name} "
                f"([dim]{anim.animation_type.value}[/])"
            )

        if report.recommendations:
            console.print("\n[bold]处理建议:[/]")
            for i, rec in enumerate(report.recommendations, 1):
                console.print(f"  {i}. {rec}")

        console.print("\n[bold cyan]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/]\n")

    async def inject_animation_freeze_script(self, page: Page) -> None:
        """
        注入动画冻结脚本到页面
        用于在克隆页面中冻结非关键动画
        """
        console.print("[cyan]  ❄️ 注入动画冻结脚本...[/]")

        freeze_script = """
        (function() {
            'use strict';
            // ━━━ WebThief Animation Freeze Layer ━━━
            
            // 需要保留的动画名称列表
            const PRESERVED_ANIMATIONS = window.__webthief_preserved_animations || [];
            
            // 冻结所有非关键动画
            function freezeNonCriticalAnimations() {
                const allElements = document.querySelectorAll('*');
                
                allElements.forEach(el => {
                    const computedStyle = window.getComputedStyle(el);
                    const animationName = computedStyle.animationName;
                    
                    // 如果动画不在保留列表中，则冻结
                    if (animationName && animationName !== 'none') {
                        const shouldPreserve = PRESERVED_ANIMATIONS.some(
                            name => animationName.includes(name)
                        );
                        
                        if (!shouldPreserve) {
                            el.style.animation = 'none !important';
                            el.style.transition = 'none !important';
                            el.classList.add('webthief-animation-frozen');
                        }
                    }
                });
                
                console.log('[WebThief Animation] 已冻结非关键动画');
            }
            
            // 页面加载完成后执行
            if (document.readyState === 'loading') {
                document.addEventListener('DOMContentLoaded', freezeNonCriticalAnimations);
            } else {
                freezeNonCriticalAnimations();
            }
            
            // 监听动态添加的元素
            const observer = new MutationObserver((mutations) => {
                mutations.forEach((mutation) => {
                    mutation.addedNodes.forEach((node) => {
                        if (node.nodeType === Node.ELEMENT_NODE) {
                            const el = node;
                            const computedStyle = window.getComputedStyle(el);
                            const animationName = computedStyle.animationName;
                            
                            if (animationName && animationName !== 'none') {
                                const shouldPreserve = PRESERVED_ANIMATIONS.some(
                                    name => animationName.includes(name)
                                );
                                
                                if (!shouldPreserve) {
                                    el.style.animation = 'none !important';
                                    el.classList.add('webthief-animation-frozen');
                                }
                            }
                        }
                    });
                });
            });
            
            observer.observe(document.body, {
                childList: true,
                subtree: true
            });
            
            console.log('[WebThief Animation] 动画冻结层已激活');
        })();
        """

        # 先注入保留的动画列表
        preserved_names = [a.name for a in self.animation_declarations if a.should_preserve]
        await page.evaluate(f"""
            window.__webthief_preserved_animations = {preserved_names!r};
        """)

        # 注入冻结脚本
        await page.add_init_script(freeze_script)

        console.print("[green]  ✓ 动画冻结脚本已注入[/]")
