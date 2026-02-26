"""
Hover 效果分析与处理模块
目标：分析复杂 Hover 效果，评估视觉重要性，并转换为静态 CSS
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from playwright.async_api import Page
from rich.console import Console

console = Console()


class PseudoClass(Enum):
    """CSS 伪类类型"""
    HOVER = "hover"
    FOCUS = "focus"
    ACTIVE = "active"


@dataclass
class HoverEffect:
    """Hover 效果数据类"""
    selector: str
    pseudo_class: PseudoClass
    styles: dict[str, str] = field(default_factory=dict)
    original_styles: dict[str, str] = field(default_factory=dict)
    transition_duration: float = 0.0
    transition_easing: str = "ease"
    visual_importance_score: float = 0.0
    is_animated: bool = False


@dataclass
class HoverReport:
    """Hover 分析报告"""
    total_effects: int = 0
    hover_effects: int = 0
    focus_effects: int = 0
    active_effects: int = 0
    animated_effects: int = 0
    high_importance_effects: int = 0
    css_output: str = ""
    recommendations: list[str] = field(default_factory=list)


class HoverAnalyzer:
    """
    Hover 效果分析器
    负责：
    1. 检测 :hover、:focus、:active 伪类触发的样式变化
    2. 评估 hover 效果的视觉重要性
    3. 应用最优 hover 状态
    4. 将 hover 效果转换为静态 CSS
    5. 生成 hover 分析报告
    """

    # 需要检测的 CSS 属性
    TRACKED_PROPERTIES = [
        "transform",
        "filter",
        "opacity",
        "background-color",
        "background",
        "color",
        "border-color",
        "box-shadow",
        "text-shadow",
        "scale",
        "rotate",
        "translate",
        "width",
        "height",
        "margin",
        "padding",
        "border-width",
        "font-size",
        "letter-spacing",
        "z-index",
    ]

    # 高视觉重要性属性权重
    VISUAL_IMPORTANCE_WEIGHTS = {
        "transform": 1.5,
        "filter": 1.3,
        "opacity": 1.2,
        "background-color": 1.0,
        "background": 1.0,
        "color": 0.8,
        "box-shadow": 1.1,
        "text-shadow": 0.7,
        "border-color": 0.6,
        "scale": 1.4,
        "rotate": 1.3,
        "translate": 1.2,
    }

    def __init__(self):
        self.detected_effects: list[HoverEffect] = []
        self.processed_elements: set[str] = set()
        self.report: HoverReport = HoverReport()

    async def analyze_hover_effects(self, page: Page) -> list[HoverEffect]:
        """
        分析页面中的 hover 效果
        检测 :hover、:focus、:active 伪类触发的样式变化
        """
        console.print("[cyan]  🔍 分析页面 Hover 效果...[/]")

        self.detected_effects = []

        # 注入分析脚本
        analysis_script = """
        () => {
            const results = [];
            const TRACKED_PROPERTIES = [
                'transform', 'filter', 'opacity', 'background-color', 'background',
                'color', 'border-color', 'box-shadow', 'text-shadow', 'scale',
                'rotate', 'translate', 'width', 'height', 'margin', 'padding',
                'border-width', 'font-size', 'letter-spacing', 'z-index'
            ];
            
            // 获取所有元素
            const allElements = document.querySelectorAll('*');
            
            for (const element of allElements) {
                const computedStyle = window.getComputedStyle(element);
                const selector = element.tagName.toLowerCase() + 
                    (element.id ? '#' + element.id : '') +
                    (element.className ? '.' + element.className.split(' ').join('.') : '');
                
                // 检查是否有 hover 相关的样式规则
                const sheets = document.styleSheets;
                for (const sheet of sheets) {
                    try {
                        const rules = sheet.cssRules || sheet.rules;
                        for (const rule of rules) {
                            if (rule.selectorText) {
                                const selectorText = rule.selectorText.toLowerCase();
                                
                                // 检测 :hover
                                if (selectorText.includes(':hover')) {
                                    const styles = {};
                                    const style = rule.style;
                                    for (let i = 0; i < style.length; i++) {
                                        const prop = style[i];
                                        if (TRACKED_PROPERTIES.some(p => prop.includes(p))) {
                                            styles[prop] = style.getPropertyValue(prop);
                                        }
                                    }
                                    
                                    if (Object.keys(styles).length > 0) {
                                        results.push({
                                            selector: rule.selectorText,
                                            pseudoClass: 'hover',
                                            styles: styles,
                                            elementTag: element.tagName,
                                            elementClasses: element.className
                                        });
                                    }
                                }
                                
                                // 检测 :focus
                                if (selectorText.includes(':focus')) {
                                    const styles = {};
                                    const style = rule.style;
                                    for (let i = 0; i < style.length; i++) {
                                        const prop = style[i];
                                        if (TRACKED_PROPERTIES.some(p => prop.includes(p))) {
                                            styles[prop] = style.getPropertyValue(prop);
                                        }
                                    }
                                    
                                    if (Object.keys(styles).length > 0) {
                                        results.push({
                                            selector: rule.selectorText,
                                            pseudoClass: 'focus',
                                            styles: styles,
                                            elementTag: element.tagName,
                                            elementClasses: element.className
                                        });
                                    }
                                }
                                
                                // 检测 :active
                                if (selectorText.includes(':active')) {
                                    const styles = {};
                                    const style = rule.style;
                                    for (let i = 0; i < style.length; i++) {
                                        const prop = style[i];
                                        if (TRACKED_PROPERTIES.some(p => prop.includes(p))) {
                                            styles[prop] = style.getPropertyValue(prop);
                                        }
                                    }
                                    
                                    if (Object.keys(styles).length > 0) {
                                        results.push({
                                            selector: rule.selectorText,
                                            pseudoClass: 'active',
                                            styles: styles,
                                            elementTag: element.tagName,
                                            elementClasses: element.className
                                        });
                                    }
                                }
                            }
                        }
                    } catch (e) {
                        // 跨域样式表可能无法访问
                    }
                }
            }
            
            return results;
        }
        """

        raw_effects = await page.evaluate(analysis_script)

        # 转换为 HoverEffect 对象
        for effect_data in raw_effects:
            pseudo_class = PseudoClass.HOVER
            if effect_data["pseudoClass"] == "focus":
                pseudo_class = PseudoClass.FOCUS
            elif effect_data["pseudoClass"] == "active":
                pseudo_class = PseudoClass.ACTIVE

            effect = HoverEffect(
                selector=effect_data["selector"],
                pseudo_class=pseudo_class,
                styles=effect_data["styles"],
            )
            self.detected_effects.append(effect)

        # 去重
        unique_effects = {}
        for effect in self.detected_effects:
            key = f"{effect.selector}:{effect.pseudo_class.value}"
            if key not in unique_effects:
                unique_effects[key] = effect

        self.detected_effects = list(unique_effects.values())

        console.print(f"[green]  ✓ 检测到 {len(self.detected_effects)} 个 Hover 效果[/]")

        return self.detected_effects

    def evaluate_visual_importance(self, effect: HoverEffect) -> float:
        """
        评估 hover 效果的视觉重要性
        返回 0-1 之间的分数，越高表示越重要
        """
        score = 0.0
        max_possible_score = 0.0

        for prop, value in effect.styles.items():
            # 获取属性权重
            weight = 0.5  # 默认权重
            for tracked_prop, tracked_weight in self.VISUAL_IMPORTANCE_WEIGHTS.items():
                if tracked_prop in prop.lower():
                    weight = tracked_weight
                    break

            max_possible_score += weight * 2  # 假设最大变化值为 2

            # 根据变化幅度计算分数
            change_magnitude = self._calculate_change_magnitude(prop, value)
            score += weight * min(change_magnitude, 2.0)

        # 检查是否有动画
        if "transition" in effect.styles or "animation" in effect.styles:
            effect.is_animated = True
            score += 0.5
            max_possible_score += 0.5

        # 归一化到 0-1
        if max_possible_score > 0:
            normalized_score = min(score / max_possible_score, 1.0)
        else:
            normalized_score = 0.0

        effect.visual_importance_score = normalized_score

        return normalized_score

    def _calculate_change_magnitude(self, property_name: str, value: str) -> float:
        """计算样式变化的幅度"""
        # 提取数值
        numeric_match = re.search(r'(-?\d+\.?\d*)', value)
        if numeric_match:
            try:
                numeric_value = float(numeric_match.group(1))
                # 根据属性类型归一化
                if 'opacity' in property_name:
                    return abs(numeric_value)  # opacity 范围 0-1
                elif 'scale' in property_name or 'rotate' in property_name:
                    return abs(numeric_value) / 360  # 旋转角度归一化
                elif 'translate' in property_name or 'width' in property_name or 'height' in property_name:
                    return abs(numeric_value) / 100  # 像素值归一化
                else:
                    return abs(numeric_value) / 50
            except ValueError:
                return 0.5
        return 0.5  # 非数值属性默认中等变化

    async def apply_optimal_hover_state(self, page: Page, threshold: float = 0.5) -> None:
        """
        应用最优 hover 状态
        将视觉重要性高于阈值的 hover 效果应用到元素上
        """
        console.print(f"[cyan]  🎨 应用最优 Hover 状态 (阈值: {threshold})...[/]")

        # 先评估所有效果的视觉重要性
        for effect in self.detected_effects:
            self.evaluate_visual_importance(effect)

        # 筛选高重要性效果
        high_importance_effects = [
            e for e in self.detected_effects
            if e.visual_importance_score >= threshold
        ]

        # 生成并应用样式
        apply_script = """
        (effects) => {
            effects.forEach(effect => {
                try {
                    const elements = document.querySelectorAll(effect.selector.replace(/:hover|:focus|:active/g, ''));
                    elements.forEach(el => {
                        // 应用 hover 样式到元素
                        Object.entries(effect.styles).forEach(([prop, value]) => {
                            el.style.setProperty(prop, value, 'important');
                        });
                        
                        // 添加标记
                        el.setAttribute('data-webthief-hover-applied', effect.pseudoClass);
                    });
                } catch (e) {
                    console.error('应用 hover 样式失败:', effect.selector, e);
                }
            });
        }
        """

        effects_data = [
            {
                "selector": e.selector,
                "pseudoClass": e.pseudo_class.value,
                "styles": e.styles
            }
            for e in high_importance_effects
        ]

        await page.evaluate(apply_script, effects_data)

        console.print(f"[green]  ✓ 已应用 {len(high_importance_effects)} 个高重要性 Hover 效果[/]")

    def convert_to_static_css(self, effects: list[HoverEffect] | None = None) -> str:
        """
        将 hover 效果转换为静态 CSS
        生成可直接使用的 CSS 代码
        """
        if effects is None:
            effects = self.detected_effects

        css_lines = [
            "/* WebThief Hover Static CSS */",
            "/* Generated from dynamic hover effects */",
            "",
        ]

        # 按伪类分组
        grouped_effects = self._group_effects_by_pseudo_class(effects)

        # 生成各组样式
        css_lines.extend(self._generate_pseudo_class_styles(
            "Hover Effects", grouped_effects.get(PseudoClass.HOVER, [])
        ))
        css_lines.extend(self._generate_pseudo_class_styles(
            "Focus Effects", grouped_effects.get(PseudoClass.FOCUS, [])
        ))
        css_lines.extend(self._generate_pseudo_class_styles(
            "Active Effects", grouped_effects.get(PseudoClass.ACTIVE, [])
        ))

        # 生成静态替代类
        css_lines.extend(self._generate_static_utility_classes(effects))

        return "\n".join(css_lines)

    def _group_effects_by_pseudo_class(
        self, effects: list[HoverEffect]
    ) -> dict[PseudoClass, list[HoverEffect]]:
        """按伪类类型对效果进行分组"""
        grouped: dict[PseudoClass, list[HoverEffect]] = {
            PseudoClass.HOVER: [],
            PseudoClass.FOCUS: [],
            PseudoClass.ACTIVE: [],
        }
        for effect in effects:
            if effect.pseudo_class in grouped:
                grouped[effect.pseudo_class].append(effect)
        return grouped

    def _generate_pseudo_class_styles(
        self, section_name: str, effects: list[HoverEffect]
    ) -> list[str]:
        """生成特定伪类的 CSS 样式"""
        if not effects:
            return []

        css_lines = [f"/* {section_name} */"]
        for effect in effects:
            css_lines.append(f"{effect.selector} {{")
            css_lines.extend(f"    {prop}: {value};" for prop, value in effect.styles.items())
            css_lines.append("}")
            css_lines.append("")
        return css_lines

    def _generate_static_utility_classes(self, effects: list[HoverEffect]) -> list[str]:
        """生成静态工具类"""
        css_lines = [
            "/* Static Alternative Classes */",
            ".webthief-hover-static {",
            "    /* 通用 hover 静态替代样式 */",
            "    transition: none !important;",
            "}",
            "",
        ]

        for i, effect in enumerate(effects):
            class_name = f"webthief-hover-{effect.pseudo_class.value}-{i}"
            css_lines.append(f".{class_name} {{")
            css_lines.extend(f"    {prop}: {value};" for prop, value in effect.styles.items())
            css_lines.append("}")
            css_lines.append("")

        return css_lines

    def get_hover_report(self) -> HoverReport:
        """
        获取 hover 分析报告
        包含统计信息、建议和生成的 CSS
        """
        report = HoverReport()

        # 统计信息
        report.total_effects = len(self.detected_effects)
        report.hover_effects = self._count_effects_by_pseudo_class(PseudoClass.HOVER)
        report.focus_effects = self._count_effects_by_pseudo_class(PseudoClass.FOCUS)
        report.active_effects = self._count_effects_by_pseudo_class(PseudoClass.ACTIVE)
        report.animated_effects = sum(1 for e in self.detected_effects if e.is_animated)

        # 评估重要性并统计高重要性效果
        report.high_importance_effects = self._count_high_importance_effects()

        # 生成 CSS
        report.css_output = self.convert_to_static_css()

        # 生成建议
        report.recommendations = self._generate_hover_recommendations(report)

        self.report = report
        return report

    def _count_effects_by_pseudo_class(self, pseudo_class: PseudoClass) -> int:
        """统计特定伪类类型的效果数量"""
        return sum(1 for e in self.detected_effects if e.pseudo_class == pseudo_class)

    def _count_high_importance_effects(self) -> int:
        """统计高视觉重要性效果数量"""
        for effect in self.detected_effects:
            self.evaluate_visual_importance(effect)

        return sum(1 for e in self.detected_effects if e.visual_importance_score >= 0.6)

    def _generate_hover_recommendations(self, report: HoverReport) -> list[str]:
        """生成 hover 分析报告的建议"""
        recommendations = []

        if report.animated_effects > 0:
            recommendations.append(
                f"检测到 {report.animated_effects} 个动画效果，"
                "建议在静态克隆中保留或转换为 CSS 动画"
            )

        if report.high_importance_effects > 0:
            recommendations.append(
                f"发现 {report.high_importance_effects} 个高视觉重要性效果，"
                "建议优先处理这些效果"
            )

        if report.focus_effects > 0:
            recommendations.append(
                f"检测到 {report.focus_effects} 个 focus 效果，"
                "考虑在克隆页面中保留表单交互体验"
            )

        if report.total_effects == 0:
            recommendations.append("未检测到 hover 效果，页面可能使用 JavaScript 处理交互")

        return recommendations

    def print_report(self, report: HoverReport | None = None) -> None:
        """打印分析报告到控制台"""
        if report is None:
            report = self.report

        console.print("\n[bold cyan]━━━ Hover 效果分析报告 ━━━[/]")
        console.print(f"[white]总效果数: {report.total_effects}[/]")
        console.print(f"[white]  - Hover 效果: {report.hover_effects}[/]")
        console.print(f"[white]  - Focus 效果: {report.focus_effects}[/]")
        console.print(f"[white]  - Active 效果: {report.active_effects}[/]")
        console.print(f"[white]动画效果: {report.animated_effects}[/]")
        console.print(f"[white]高重要性效果: {report.high_importance_effects}[/]")

        if report.recommendations:
            console.print("\n[bold yellow]建议:[/]")
            for rec in report.recommendations:
                console.print(f"[dim]  • {rec}[/]")

        console.print("\n[green]✓ 分析完成[/]")

    async def extract_hover_from_element(self, page: Page, selector: str) -> HoverEffect | None:
        """
        从特定元素提取 hover 效果
        用于针对性分析单个元素
        """
        script = f"""
        () => {{
            const element = document.querySelector('{selector}');
            if (!element) return null;
            
            const result = {{
                selector: '{selector}',
                pseudoClass: 'hover',
                styles: {{}},
                originalStyles: {{}}
            }};
            
            // 获取原始样式
            const computed = window.getComputedStyle(element);
            
            // 模拟 hover 状态
            const originalPointerEvents = element.style.pointerEvents;
            element.style.pointerEvents = 'none';
            
            // 触发 mouseover 事件
            const mouseoverEvent = new MouseEvent('mouseover', {{
                bubbles: true,
                cancelable: true,
                view: window
            }});
            element.dispatchEvent(mouseoverEvent);
            
            // 获取 hover 后的样式
            const hoverComputed = window.getComputedStyle(element);
            
            const TRACKED_PROPERTIES = [
                'transform', 'filter', 'opacity', 'background-color', 'background',
                'color', 'border-color', 'box-shadow', 'text-shadow'
            ];
            
            TRACKED_PROPERTIES.forEach(prop => {{
                const original = computed.getPropertyValue(prop);
                const hover = hoverComputed.getPropertyValue(prop);
                if (original !== hover) {{
                    result.styles[prop] = hover;
                    result.originalStyles[prop] = original;
                }}
            }});
            
            // 恢复
            element.style.pointerEvents = originalPointerEvents;
            
            return result;
        }}
        """

        result = await page.evaluate(script)

        if result and result["styles"]:
            effect = HoverEffect(
                selector=result["selector"],
                pseudo_class=PseudoClass.HOVER,
                styles=result["styles"],
                original_styles=result["originalStyles"]
            )
            return effect

        return None
