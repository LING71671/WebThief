"""
嵌套 Hover 状态处理模块
目标：处理嵌套的 hover 状态，分析层级依赖关系，确保状态一致性
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from playwright.async_api import Page
from rich.console import Console

console = Console()


class HoverSelectorType(Enum):
    """Hover 选择器类型"""
    HOVER = ":hover"
    FOCUS_WITHIN = ":focus-within"
    HAS_HOVER = ":has(:hover)"
    HAS_FOCUS = ":has(:focus)"
    NESTED_HOVER = "nested_hover"  # 父元素 hover 影响子元素
    SIBLING_HOVER = "sibling_hover"  # 兄弟元素 hover 影响


@dataclass
class HoverDependencyNode:
    """Hover 依赖图节点"""
    selector: str
    selector_type: HoverSelectorType
    styles: dict[str, str] = field(default_factory=dict)
    children: list[str] = field(default_factory=list)
    parents: list[str] = field(default_factory=list)
    depth: int = 0
    visibility_properties: dict[str, str] = field(default_factory=dict)


@dataclass
class VisibilityChange:
    """可见性变化记录"""
    selector: str
    property_name: str
    original_value: str
    hover_value: str
    change_type: str  # display, visibility, opacity


@dataclass
class NestedHoverReport:
    """嵌套 Hover 分析报告"""
    total_nodes: int = 0
    max_depth: int = 0
    hover_nodes: int = 0
    focus_within_nodes: int = 0
    has_hover_nodes: int = 0
    nested_hover_nodes: int = 0
    sibling_hover_nodes: int = 0
    visibility_changes: list[VisibilityChange] = field(default_factory=list)
    inconsistency_issues: list[str] = field(default_factory=list)
    dependency_graph: dict[str, HoverDependencyNode] = field(default_factory=dict)
    recommendations: list[str] = field(default_factory=list)


class NestedHoverHandler:
    """
    嵌套 Hover 状态处理器
    
    负责：
    1. 分析 hover 状态的层级依赖关系
    2. 构建 hover 状态依赖图（有向图表示父子关系）
    3. 确保 hover 状态一致性
    4. 处理 hover 触发的可见性变化（display、visibility、opacity）
    5. 检测嵌套的 :hover、:focus-within、:has(:hover) 选择器
    6. 生成嵌套 hover 分析报告
    """

    # 可见性相关 CSS 属性
    VISIBILITY_PROPERTIES = [
        "display",
        "visibility",
        "opacity",
    ]

    # 嵌套选择器正则模式
    NESTED_PATTERNS = {
        HoverSelectorType.HOVER: r':hover',
        HoverSelectorType.FOCUS_WITHIN: r':focus-within',
        HoverSelectorType.HAS_HOVER: r':has\s*\(\s*:hover\s*\)',
        HoverSelectorType.HAS_FOCUS: r':has\s*\(\s*:focus\s*\)',
    }

    # 父子关系选择器模式
    PARENT_CHILD_PATTERNS = [
        r'([^\s:]+):hover\s+([^\s{}]+)',  # parent:hover child
        r'([^\s:]+):hover\s*>\s*([^\s{}]+)',  # parent:hover > child
        r'([^\s:]+):hover\s*~\s*([^\s{}]+)',  # parent:hover ~ sibling
        r'([^\s:]+):hover\s*\+\s*([^\s{}]+)',  # parent:hover + adjacent
    ]

    def __init__(self):
        self.dependency_graph: dict[str, HoverDependencyNode] = {}
        self.visibility_changes: list[VisibilityChange] = []
        self.inconsistency_issues: list[str] = []
        self.report: NestedHoverReport = NestedHoverReport()

    def analyze_hover_dependencies(
        self,
        css_rules: list[dict[str, Any]]
    ) -> dict[str, HoverDependencyNode]:
        """
        分析 hover 状态的层级依赖关系
        
        Args:
            css_rules: CSS 规则列表，每个规则包含 selector 和 styles
            
        Returns:
            依赖图字典，key 为选择器，value 为 HoverDependencyNode
        """
        console.print("[cyan]  🔍 分析 Hover 层级依赖关系...[/]")

        self.dependency_graph = {}

        for rule in css_rules:
            selector = rule.get("selector", "")
            styles = rule.get("styles", {})

            # 检测选择器类型
            selector_type = self._detect_selector_type(selector)

            if selector_type:
                node = HoverDependencyNode(
                    selector=selector,
                    selector_type=selector_type,
                    styles=styles,
                    visibility_properties=self._extract_visibility_properties(styles)
                )
                self.dependency_graph[selector] = node

        # 构建父子关系
        self._build_parent_child_relationships()

        # 计算层级深度
        self._calculate_depths()

        console.print(f"[green]  ✓ 分析了 {len(self.dependency_graph)} 个 hover 依赖节点[/]")

        return self.dependency_graph

    def _detect_selector_type(self, selector: str) -> HoverSelectorType | None:
        """检测选择器类型"""
        selector_lower = selector.lower()

        # 检测 :has(:hover)
        if re.search(self.NESTED_PATTERNS[HoverSelectorType.HAS_HOVER], selector_lower):
            return HoverSelectorType.HAS_HOVER

        # 检测 :has(:focus)
        if re.search(self.NESTED_PATTERNS[HoverSelectorType.HAS_FOCUS], selector_lower):
            return HoverSelectorType.HAS_FOCUS

        # 检测 :focus-within
        if re.search(self.NESTED_PATTERNS[HoverSelectorType.FOCUS_WITHIN], selector_lower):
            return HoverSelectorType.FOCUS_WITHIN

        # 检测嵌套 hover（父元素 hover 影响子元素）
        for pattern in self.PARENT_CHILD_PATTERNS:
            if re.search(pattern, selector_lower) and ":hover" in selector_lower:
                if "~" in selector or "+" in selector:
                    return HoverSelectorType.SIBLING_HOVER
                return HoverSelectorType.NESTED_HOVER

        # 检测普通 :hover
        if re.search(self.NESTED_PATTERNS[HoverSelectorType.HOVER], selector_lower):
            return HoverSelectorType.HOVER

        return None

    def _extract_visibility_properties(
        self,
        styles: dict[str, str]
    ) -> dict[str, str]:
        """提取可见性相关属性"""
        visibility_props = {}
        for prop in self.VISIBILITY_PROPERTIES:
            if prop in styles:
                visibility_props[prop] = styles[prop]
        return visibility_props

    def _build_parent_child_relationships(self) -> None:
        """构建父子关系"""
        for selector, node in self.dependency_graph.items():
            # 解析父子关系
            for pattern in self.PARENT_CHILD_PATTERNS:
                match = re.search(pattern, selector)
                if match:
                    parent_selector = match.group(1).strip()
                    child_selector = match.group(2).strip()

                    # 查找父节点
                    for other_selector, other_node in self.dependency_graph.items():
                        if other_selector.strip() == parent_selector:
                            node.parents.append(other_selector)
                            other_node.children.append(selector)
                            break

    def _calculate_depths(self) -> None:
        """计算每个节点的层级深度"""
        visited: set[str] = set()

        def calculate_node_depth(selector: str, current_depth: int) -> None:
            if selector in visited:
                return
            visited.add(selector)

            node = self.dependency_graph.get(selector)
            if node:
                node.depth = max(node.depth, current_depth)
                for child_selector in node.children:
                    calculate_node_depth(child_selector, current_depth + 1)

        # 从根节点开始计算
        for selector, node in self.dependency_graph.items():
            if not node.parents:
                calculate_node_depth(selector, 0)

    def build_hover_dependency_graph(
        self,
        page: Page
    ) -> dict[str, HoverDependencyNode]:
        """
        构建 hover 状态依赖图（使用有向图表示父子关系）
        
        Args:
            page: Playwright Page 对象
            
        Returns:
            依赖图字典
        """
        console.print("[cyan]  🔗 构建 Hover 依赖图...[/]")

        # 从页面提取 CSS 规则
        css_rules = self._extract_css_rules_from_page(page)

        # 分析依赖关系
        self.analyze_hover_dependencies(css_rules)

        console.print(f"[green]  ✓ 依赖图构建完成，共 {len(self.dependency_graph)} 个节点[/]")

        return self.dependency_graph

    def _extract_css_rules_from_page(self, page: Page) -> list[dict[str, Any]]:
        """从页面提取 CSS 规则"""
        script = """
        () => {
            const rules = [];
            const sheets = document.styleSheets;
            
            for (const sheet of sheets) {
                try {
                    const cssRules = sheet.cssRules || sheet.rules;
                    for (const rule of cssRules) {
                        if (rule.selectorText) {
                            const selector = rule.selectorText;
                            const styles = {};
                            const style = rule.style;
                            
                            for (let i = 0; i < style.length; i++) {
                                const prop = style[i];
                                styles[prop] = style.getPropertyValue(prop);
                            }
                            
                            if (Object.keys(styles).length > 0) {
                                rules.push({
                                    selector: selector,
                                    styles: styles
                                });
                            }
                        }
                    }
                } catch (e) {
                    // 跨域样式表可能无法访问
                }
            }
            
            return rules;
        }
        """

        try:
            return page.evaluate(script)
        except Exception as e:
            console.print(f"[yellow]  ⚠ 提取 CSS 规则失败: {e}[/]")
            return []

    def ensure_hover_consistency(self) -> list[str]:
        """
        确保 hover 状态一致性
        
        检查并修复以下问题：
        1. 循环依赖
        2. 冲突的可见性设置
        3. 不一致的层级关系
        
        Returns:
            检测到的问题列表
        """
        console.print("[cyan]  🔍 检查 Hover 状态一致性...[/]")

        self.inconsistency_issues = []

        # 检查循环依赖
        self._detect_circular_dependencies()

        # 检查冲突的可见性设置
        self._detect_visibility_conflicts()

        # 检查不一致的层级关系
        self._detect_depth_inconsistencies()

        if self.inconsistency_issues:
            console.print(f"[yellow]  ⚠ 发现 {len(self.inconsistency_issues)} 个一致性问题[/]")
        else:
            console.print("[green]  ✓ 未发现一致性问题[/]")

        return self.inconsistency_issues

    def _detect_circular_dependencies(self) -> None:
        """检测循环依赖"""
        visited: set[str] = set()
        recursion_stack: set[str] = set()

        def has_cycle(selector: str, path: list[str]) -> bool:
            visited.add(selector)
            recursion_stack.add(selector)

            node = self.dependency_graph.get(selector)
            if node:
                for child in node.children:
                    if child not in visited:
                        if has_cycle(child, path + [child]):
                            return True
                    elif child in recursion_stack:
                        cycle_path = " -> ".join(path + [child])
                        issue = f"检测到循环依赖: {cycle_path}"
                        if issue not in self.inconsistency_issues:
                            self.inconsistency_issues.append(issue)
                        return True

            recursion_stack.remove(selector)
            return False

        for selector in self.dependency_graph:
            if selector not in visited:
                has_cycle(selector, [selector])

    def _detect_visibility_conflicts(self) -> None:
        """检测冲突的可见性设置"""
        for selector, node in self.dependency_graph.items():
            self._check_conflicts_with_parents(selector, node)

    def _check_conflicts_with_parents(self, selector: str, node: HoverDependencyNode) -> None:
        """检查节点与其父节点之间的可见性冲突。"""
        for parent_selector in node.parents:
            parent_node = self.dependency_graph.get(parent_selector)
            if not parent_node:
                continue
            self._detect_property_conflicts(selector, node, parent_selector, parent_node)

    def _detect_property_conflicts(
        self,
        selector: str,
        node: HoverDependencyNode,
        parent_selector: str,
        parent_node: HoverDependencyNode
    ) -> None:
        """检测两个节点之间的属性冲突。"""
        for prop in self.VISIBILITY_PROPERTIES:
            if not self._has_property_in_both_nodes(prop, node, parent_node):
                continue
            node_value = node.visibility_properties[prop]
            parent_value = parent_node.visibility_properties[prop]
            self._report_if_conflict(selector, parent_selector, prop, node_value, parent_value)

    def _has_property_in_both_nodes(
        self,
        prop: str,
        node: HoverDependencyNode,
        parent_node: HoverDependencyNode
    ) -> bool:
        """检查属性是否同时存在于两个节点中。"""
        return prop in node.visibility_properties and prop in parent_node.visibility_properties

    def _report_if_conflict(
        self,
        selector: str,
        parent_selector: str,
        prop: str,
        node_value: str,
        parent_value: str
    ) -> None:
        """如果检测到冲突，则记录问题。"""
        if prop == "display" and node_value == "none" and parent_value != "none":
            issue = (
                f"可见性冲突: {selector} 在 hover 时隐藏，"
                f"但其父元素 {parent_selector} 保持显示"
            )
            self._add_unique_issue(issue)

    def _add_unique_issue(self, issue: str) -> None:
        """添加唯一的问题记录，避免重复。"""
        if issue not in self.inconsistency_issues:
            self.inconsistency_issues.append(issue)

    def _detect_depth_inconsistencies(self) -> None:
        """检测层级深度不一致"""
        max_depth = max(
            (node.depth for node in self.dependency_graph.values()),
            default=0
        )

        # 检查深度跳跃（子节点深度不应比父节点大太多）
        for selector, node in self.dependency_graph.items():
            for parent_selector in node.parents:
                parent_node = self.dependency_graph.get(parent_selector)
                if parent_node:
                    depth_diff = node.depth - parent_node.depth
                    if depth_diff > 2:
                        issue = (f"层级深度异常: {selector} (深度 {node.depth}) 与 "
                                f"父元素 {parent_selector} (深度 {parent_node.depth}) 差距过大")
                        if issue not in self.inconsistency_issues:
                            self.inconsistency_issues.append(issue)

    async def handle_hover_visibility_changes(
        self,
        page: Page,
        target_selector: str | None = None
    ) -> list[VisibilityChange]:
        """
        处理 hover 触发的可见性变化
        
        检测并记录以下属性的变化：
        - display (none, block, flex, etc.)
        - visibility (hidden, visible)
        - opacity (0-1)
        
        Args:
            page: Playwright Page 对象
            target_selector: 目标选择器，如果为 None 则处理所有元素
            
        Returns:
            可见性变化列表
        """
        console.print("[cyan]  👁 处理 Hover 可见性变化...[/]")

        self.visibility_changes = []

        if target_selector:
            changes = await self._analyze_element_visibility(page, target_selector)
            self.visibility_changes.extend(changes)
        else:
            # 分析所有在依赖图中的元素
            for selector in self.dependency_graph:
                changes = await self._analyze_element_visibility(page, selector)
                self.visibility_changes.extend(changes)

        console.print(f"[green]  ✓ 检测到 {len(self.visibility_changes)} 个可见性变化[/]")

        return self.visibility_changes

    async def _analyze_element_visibility(
        self,
        page: Page,
        selector: str
    ) -> list[VisibilityChange]:
        """分析单个元素的可见性变化"""
        changes = []

        # 清理选择器（移除伪类）
        clean_selector = re.sub(r':hover|:focus|:focus-within|:active', '', selector)
        clean_selector = re.sub(r':has\([^)]+\)', '', clean_selector)

        script = f"""
        (selector) => {{
            const results = [];
            const elements = document.querySelectorAll(selector);
            
            elements.forEach((element, index) => {{
                const computed = window.getComputedStyle(element);
                const originalStyles = {{
                    display: computed.display,
                    visibility: computed.visibility,
                    opacity: computed.opacity
                }};
                
                // 模拟 hover
                const mouseoverEvent = new MouseEvent('mouseover', {{
                    bubbles: true,
                    cancelable: true,
                    view: window
                }});
                element.dispatchEvent(mouseoverEvent);
                
                // 获取 hover 后的样式
                const hoverComputed = window.getComputedStyle(element);
                const hoverStyles = {{
                    display: hoverComputed.display,
                    visibility: hoverComputed.visibility,
                    opacity: hoverComputed.opacity
                }};
                
                // 检测变化
                const VISIBILITY_PROPERTIES = ['display', 'visibility', 'opacity'];
                VISIBILITY_PROPERTIES.forEach(prop => {{
                    if (originalStyles[prop] !== hoverStyles[prop]) {{
                        results.push({{
                            selector: selector + ':nth-of-type(' + (index + 1) + ')',
                            propertyName: prop,
                            originalValue: originalStyles[prop],
                            hoverValue: hoverStyles[prop],
                            changeType: prop
                        }});
                    }}
                }});
                
                // 触发 mouseout 恢复状态
                const mouseoutEvent = new MouseEvent('mouseout', {{
                    bubbles: true,
                    cancelable: true,
                    view: window
                }});
                element.dispatchEvent(mouseoutEvent);
            }});
            
            return results;
        }}
        """

        try:
            result = await page.evaluate(script, clean_selector)
            for change_data in result:
                change = VisibilityChange(
                    selector=change_data["selector"],
                    property_name=change_data["propertyName"],
                    original_value=change_data["originalValue"],
                    hover_value=change_data["hoverValue"],
                    change_type=change_data["changeType"]
                )
                changes.append(change)
        except Exception as e:
            console.print(f"[yellow]  ⚠ 分析元素 {selector} 失败: {e}[/]")

        return changes

    def get_nested_hover_report(self) -> NestedHoverReport:
        """
        获取嵌套 hover 报告

        包含：
        - 节点统计信息
        - 最大嵌套深度
        - 各类型选择器数量
        - 可见性变化列表
        - 一致性问题列表
        - 建议

        Returns:
            嵌套 hover 分析报告
        """
        report = self._create_base_report()
        self._populate_selector_counts(report)
        self._populate_issues_and_changes(report)
        report.recommendations = self._generate_nested_recommendations(report)
        self.report = report
        return report

    def _create_base_report(self) -> NestedHoverReport:
        """创建基础报告对象，填充基本统计信息。"""
        return NestedHoverReport(
            total_nodes=len(self.dependency_graph),
            dependency_graph=self.dependency_graph,
            max_depth=self._calculate_max_depth()
        )

    def _populate_selector_counts(self, report: NestedHoverReport) -> None:
        """统计并填充各类型选择器数量到报告。"""
        type_counters = self._get_selector_type_counters()
        for node in self.dependency_graph.values():
            if node.selector_type in type_counters:
                type_counters[node.selector_type](report)

    def _get_selector_type_counters(self) -> dict[HoverSelectorType, callable]:
        """获取选择器类型计数器映射。"""
        return {
            HoverSelectorType.HOVER: self._increment_hover_nodes,
            HoverSelectorType.FOCUS_WITHIN: self._increment_focus_within_nodes,
            HoverSelectorType.HAS_HOVER: self._increment_has_hover_nodes,
            HoverSelectorType.NESTED_HOVER: self._increment_nested_hover_nodes,
            HoverSelectorType.SIBLING_HOVER: self._increment_sibling_hover_nodes,
        }

    def _increment_hover_nodes(self, report: NestedHoverReport) -> None:
        """增加 hover 节点计数。"""
        report.hover_nodes += 1

    def _increment_focus_within_nodes(self, report: NestedHoverReport) -> None:
        """增加 focus-within 节点计数。"""
        report.focus_within_nodes += 1

    def _increment_has_hover_nodes(self, report: NestedHoverReport) -> None:
        """增加 has(:hover) 节点计数。"""
        report.has_hover_nodes += 1

    def _increment_nested_hover_nodes(self, report: NestedHoverReport) -> None:
        """增加嵌套 hover 节点计数。"""
        report.nested_hover_nodes += 1

    def _increment_sibling_hover_nodes(self, report: NestedHoverReport) -> None:
        """增加兄弟 hover 节点计数。"""
        report.sibling_hover_nodes += 1

    def _populate_issues_and_changes(self, report: NestedHoverReport) -> None:
        """填充可见性变化和一致性问题到报告。"""
        report.visibility_changes = self.visibility_changes
        report.inconsistency_issues = self.inconsistency_issues

    def _calculate_max_depth(self) -> int:
        """计算最大嵌套深度"""
        if not self.dependency_graph:
            return 0
        return max(node.depth for node in self.dependency_graph.values())

    def _generate_nested_recommendations(self, report: NestedHoverReport) -> list[str]:
        """生成嵌套 hover 报告的建议"""
        recommendations = []

        if report.max_depth > 3:
            recommendations.append(
                f"检测到较深的嵌套层级（最大深度 {report.max_depth}），"
                "建议简化 hover 状态结构以提高性能"
            )

        if report.has_hover_nodes > 0:
            recommendations.append(
                f"检测到 {report.has_hover_nodes} 个 :has(:hover) 选择器，"
                "注意浏览器兼容性问题"
            )

        if report.nested_hover_nodes > 0:
            recommendations.append(
                f"检测到 {report.nested_hover_nodes} 个嵌套 hover 效果，"
                "建议确保父子状态同步"
            )

        if report.sibling_hover_nodes > 0:
            recommendations.append(
                f"检测到 {report.sibling_hover_nodes} 个兄弟元素 hover 影响，"
                "注意状态传播的一致性"
            )

        display_changes = sum(
            1 for v in self.visibility_changes if v.change_type == "display"
        )
        if display_changes > 0:
            recommendations.append(
                f"检测到 {display_changes} 个 display 属性变化，"
                "注意布局重排对性能的影响"
            )

        if self.inconsistency_issues:
            recommendations.append(
                f"发现 {len(self.inconsistency_issues)} 个一致性问题，建议修复"
            )

        if report.total_nodes == 0:
            recommendations.append("未检测到嵌套 hover 效果")

        return recommendations

    def print_report(self, report: NestedHoverReport | None = None) -> None:
        """打印分析报告到控制台"""
        if report is None:
            report = self.report

        console.print("\n[bold cyan]━━━ 嵌套 Hover 效果分析报告 ━━━[/]")
        console.print(f"[white]总节点数: {report.total_nodes}[/]")
        console.print(f"[white]最大嵌套深度: {report.max_depth}[/]")
        console.print(f"[white]  - Hover 节点: {report.hover_nodes}[/]")
        console.print(f"[white]  - Focus-within 节点: {report.focus_within_nodes}[/]")
        console.print(f"[white]  - :has(:hover) 节点: {report.has_hover_nodes}[/]")
        console.print(f"[white]  - 嵌套 Hover 节点: {report.nested_hover_nodes}[/]")
        console.print(f"[white]  - 兄弟 Hover 节点: {report.sibling_hover_nodes}[/]")
        console.print(f"[white]可见性变化: {len(report.visibility_changes)}[/]")
        console.print(f"[white]一致性问题: {len(report.inconsistency_issues)}[/]")

        if report.visibility_changes:
            console.print("\n[bold yellow]可见性变化详情:[/]")
            for change in report.visibility_changes[:5]:  # 只显示前5个
                console.print(
                    f"[dim]  • {change.selector}: {change.property_name} "
                    f"({change.original_value} → {change.hover_value})[/]"
                )
            if len(report.visibility_changes) > 5:
                console.print(f"[dim]  ... 还有 {len(report.visibility_changes) - 5} 个变化[/]")

        if report.inconsistency_issues:
            console.print("\n[bold red]一致性问题:[/]")
            for issue in report.inconsistency_issues:
                console.print(f"[dim]  • {issue}[/]")

        if report.recommendations:
            console.print("\n[bold yellow]建议:[/]")
            for rec in report.recommendations:
                console.print(f"[dim]  • {rec}[/]")

        console.print("\n[green]✓ 分析完成[/]")

    def get_static_css_for_nested_hover(self) -> str:
        """
        生成嵌套 hover 的静态 CSS
        
        将复杂的嵌套 hover 效果转换为静态类
        
        Returns:
            生成的 CSS 代码
        """
        css_lines = []
        css_lines.append("/* WebThief Nested Hover Static CSS */")
        css_lines.append("/* Generated from nested hover dependencies */")
        css_lines.append("")

        # 按深度分组
        depth_groups: dict[int, list[HoverDependencyNode]] = {}
        for node in self.dependency_graph.values():
            if node.depth not in depth_groups:
                depth_groups[node.depth] = []
            depth_groups[node.depth].append(node)

        # 按深度顺序生成 CSS
        for depth in sorted(depth_groups.keys()):
            css_lines.append(f"/* Depth {depth} */")

            for node in depth_groups[depth]:
                # 生成静态类名
                safe_selector = re.sub(r'[^a-zA-Z0-9]', '-', node.selector)[:50]
                class_name = f"webthief-nested-hover-{safe_selector}"

                css_lines.append(f".{class_name} {{")
                for prop, value in node.styles.items():
                    css_lines.append(f"    {prop}: {value};")
                css_lines.append("}")
                css_lines.append("")

        # 添加通用嵌套 hover 处理类
        css_lines.append("/* Nested Hover Utility Classes */")
        css_lines.append(".webthief-hover-visible {")
        css_lines.append("    visibility: visible !important;")
        css_lines.append("    opacity: 1 !important;")
        css_lines.append("}")
        css_lines.append("")

        css_lines.append(".webthief-hover-hidden {")
        css_lines.append("    display: none !important;")
        css_lines.append("}")
        css_lines.append("")

        css_lines.append(".webthief-nested-hover-container {")
        css_lines.append("    /* 标记嵌套 hover 容器 */")
        css_lines.append("    position: relative;")
        css_lines.append("}")
        css_lines.append("")

        return "\n".join(css_lines)

    async def apply_nested_hover_states(
        self,
        page: Page,
        target_depth: int | None = None
    ) -> None:
        """
        应用嵌套 hover 状态到页面
        
        Args:
            page: Playwright Page 对象
            target_depth: 目标深度，如果为 None 则应用所有层级
        """
        console.print("[cyan]  🎨 应用嵌套 Hover 状态...[/]")

        nodes_to_apply = []
        for selector, node in self.dependency_graph.items():
            if target_depth is None or node.depth == target_depth:
                nodes_to_apply.append({
                    "selector": selector,
                    "styles": node.styles,
                    "depth": node.depth
                })

        script = """
        (nodes) => {
            nodes.forEach(node => {
                try {
                    // 清理选择器
                    let cleanSelector = node.selector
                        .replace(/:hover|:focus|:focus-within|:active/g, '')
                        .replace(/:has\([^)]+\)/g, '');
                    
                    const elements = document.querySelectorAll(cleanSelector);
                    elements.forEach(el => {
                        // 应用样式
                        Object.entries(node.styles).forEach(([prop, value]) => {
                            el.style.setProperty(prop, value, 'important');
                        });
                        
                        // 添加标记
                        el.setAttribute('data-webthief-nested-hover', 'true');
                        el.setAttribute('data-webthief-hover-depth', node.depth);
                    });
                } catch (e) {
                    console.error('应用嵌套 hover 样式失败:', node.selector, e);
                }
            });
        }
        """

        await page.evaluate(script, nodes_to_apply)

        console.print(f"[green]  ✓ 已应用 {len(nodes_to_apply)} 个嵌套 hover 状态[/]")
