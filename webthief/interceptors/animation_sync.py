"""
动画同步模块
目标：同步多个元素的动画时间，处理动画链和动画序列，支持 GSAP 时间轴同步
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from rich.console import Console

console = Console()


class AnimationType(Enum):
    """动画类型枚举"""
    CSS_KEYFRAMES = "css_keyframes"
    CSS_TRANSITION = "css_transition"
    GSAP_TIMELINE = "gsap_timeline"
    WEB_ANIMATION_API = "web_animation_api"


@dataclass
class AnimationNode:
    """动画节点，表示单个元素的动画配置"""
    element_selector: str
    animation_name: str
    duration: float = 1.0  # 秒
    delay: float = 0.0  # 秒
    easing: str = "ease"
    iteration_count: int | str = 1
    direction: str = "normal"
    fill_mode: str = "forwards"
    dependencies: list[str] = field(default_factory=list)  # 依赖的其他动画节点


@dataclass
class AnimationChain:
    """动画链，表示按顺序执行的动画序列"""
    chain_id: str
    nodes: list[AnimationNode] = field(default_factory=list)
    auto_adjust_delay: bool = True


@dataclass
class AnimationSequence:
    """动画序列，表示并行和顺序混合的复杂动画"""
    sequence_id: str
    chains: list[AnimationChain] = field(default_factory=list)
    parallel_groups: list[list[str]] = field(default_factory=list)  # 并行执行的链ID组


@dataclass
class SyncReport:
    """同步报告"""
    total_nodes: int = 0
    total_chains: int = 0
    total_duration: float = 0.0
    conflicts: list[dict[str, Any]] = field(default_factory=list)
    adjusted_delays: list[dict[str, Any]] = field(default_factory=list)
    timeline_summary: dict[str, Any] = field(default_factory=dict)
    gsap_config: dict[str, Any] = field(default_factory=dict)


class AnimationSync:
    """
    动画同步器
    负责：
    1. 分析多个元素的动画时间关系
    2. 计算 animation-delay 和 animation-duration
    3. 生成同步的 CSS 动画样式
    4. 处理动画链和动画序列
    5. 支持 GSAP 时间轴同步
    6. 提供同步报告
    """

    # CSS 缓动函数映射
    EASING_MAP: dict[str, str] = {
        "linear": "linear",
        "ease": "ease",
        "ease-in": "ease-in",
        "ease-out": "ease-out",
        "ease-in-out": "ease-in-out",
        "gsap.power1.out": "cubic-bezier(0.25, 0.46, 0.45, 0.94)",
        "gsap.power2.out": "cubic-bezier(0.215, 0.61, 0.355, 1)",
        "gsap.power3.out": "cubic-bezier(0.165, 0.84, 0.44, 1)",
        "gsap.power4.out": "cubic-bezier(0.23, 1, 0.32, 1)",
        "gsap.back.out": "cubic-bezier(0.175, 0.885, 0.32, 1.275)",
        "gsap.elastic.out": "cubic-bezier(0.68, -0.55, 0.265, 1.55)",
        "gsap.bounce.out": "cubic-bezier(0.34, 1.56, 0.64, 1)",
    }

    def __init__(self):
        self.animation_nodes: dict[str, AnimationNode] = {}
        self.animation_chains: dict[str, AnimationChain] = {}
        self.animation_sequences: dict[str, AnimationSequence] = {}
        self.keyframes_registry: dict[str, str] = {}
        self.sync_report: SyncReport = SyncReport()

    def register_node(self, node: AnimationNode) -> None:
        """
        注册动画节点
        """
        self.animation_nodes[node.element_selector] = node
        console.print(f"[dim]  📌 注册动画节点: {node.element_selector} -> {node.animation_name}[/]")

    def create_chain(self, chain_id: str, nodes: list[AnimationNode]) -> AnimationChain:
        """
        创建动画链
        """
        chain = AnimationChain(chain_id=chain_id, nodes=nodes)
        self.animation_chains[chain_id] = chain

        # 自动计算链中节点的延迟
        if chain.auto_adjust_delay:
            self._calculate_chain_delays(chain)

        console.print(f"[dim]  🔗 创建动画链: {chain_id} ({len(nodes)} 个节点)[/]")
        return chain

    def create_sequence(self, sequence_id: str, chains: list[AnimationChain],
                        parallel_groups: list[list[str]] | None = None) -> AnimationSequence:
        """
        创建动画序列
        """
        sequence = AnimationSequence(
            sequence_id=sequence_id,
            chains=chains,
            parallel_groups=parallel_groups or []
        )
        self.animation_sequences[sequence_id] = sequence
        console.print(f"[dim]  🎬 创建动画序列: {sequence_id} ({len(chains)} 条链)[/]")
        return sequence

    def _calculate_chain_delays(self, chain: AnimationChain) -> None:
        """
        计算动画链中各节点的延迟时间
        """
        cumulative_delay: float = 0.0

        for node in chain.nodes:
            node.delay = cumulative_delay
            cumulative_delay += node.duration

    def analyze_animation_timeline(self, nodes: list[AnimationNode] | None = None) -> dict[str, Any]:
        """
        分析多个元素的动画时间关系
        返回时间线分析结果
        """
        target_nodes = nodes or list(self.animation_nodes.values())

        if not target_nodes:
            console.print("[yellow]  ⚠️ 没有动画节点需要分析[/]")
            return {}

        console.print(f"[cyan]  📊 分析 {len(target_nodes)} 个动画节点的时间关系...[/]")

        timeline_data: dict[str, Any] = {
            "nodes": [],
            "time_range": {"start": float('inf'), "end": 0.0},
            "overlaps": [],
            "gaps": [],
            "critical_path": []
        }

        # 分析每个节点的时间范围
        for node in target_nodes:
            start_time = node.delay
            end_time = node.delay + node.duration

            node_data = {
                "selector": node.element_selector,
                "animation_name": node.animation_name,
                "start_time": start_time,
                "end_time": end_time,
                "duration": node.duration
            }
            timeline_data["nodes"].append(node_data)

            # 更新时间范围
            timeline_data["time_range"]["start"] = min(timeline_data["time_range"]["start"], start_time)
            timeline_data["time_range"]["end"] = max(timeline_data["time_range"]["end"], end_time)

        # 检测时间重叠
        timeline_data["overlaps"] = self._detect_overlaps(timeline_data["nodes"])

        # 检测时间间隙
        timeline_data["gaps"] = self._detect_gaps(timeline_data["nodes"])

        # 计算关键路径
        timeline_data["critical_path"] = self._calculate_critical_path(target_nodes)

        self.sync_report.timeline_summary = timeline_data
        console.print(f"[green]  ✓ 时间线分析完成: {len(timeline_data['overlaps'])} 个重叠, {len(timeline_data['gaps'])} 个间隙[/]")

        return timeline_data

    def _detect_overlaps(self, node_data: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        检测动画时间重叠
        """
        overlaps: list[dict[str, Any]] = []

        for i, node_a in enumerate(node_data):
            for node_b in node_data[i + 1:]:
                # 检查时间是否重叠
                if (node_a["start_time"] < node_b["end_time"] and
                        node_b["start_time"] < node_a["end_time"]):
                    overlap_start = max(node_a["start_time"], node_b["start_time"])
                    overlap_end = min(node_a["end_time"], node_b["end_time"])

                    overlaps.append({
                        "node_a": node_a["selector"],
                        "node_b": node_b["selector"],
                        "overlap_start": overlap_start,
                        "overlap_end": overlap_end,
                        "overlap_duration": overlap_end - overlap_start
                    })

        return overlaps

    def _detect_gaps(self, node_data: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        检测动画时间间隙
        """
        if not node_data:
            return []

        # 按开始时间排序
        sorted_nodes = sorted(node_data, key=lambda x: x["start_time"])
        gaps: list[dict[str, Any]] = []

        for i in range(len(sorted_nodes) - 1):
            current_end = sorted_nodes[i]["end_time"]
            next_start = sorted_nodes[i + 1]["start_time"]

            if next_start > current_end:
                gaps.append({
                    "before_node": sorted_nodes[i]["selector"],
                    "after_node": sorted_nodes[i + 1]["selector"],
                    "gap_start": current_end,
                    "gap_end": next_start,
                    "gap_duration": next_start - current_end
                })

        return gaps

    def _calculate_critical_path(self, nodes: list[AnimationNode]) -> list[str]:
        """
        计算关键路径（最长执行路径）
        """
        if not nodes:
            return []

        # 按延迟时间排序
        sorted_nodes = sorted(nodes, key=lambda x: x.delay)

        # 构建依赖图
        node_map: dict[str, AnimationNode] = {node.element_selector: node for node in nodes}
        critical_path: list[str] = []
        visited: set[str] = set()

        def visit_node(node_id: str, current_path: list[str]) -> None:
            if node_id in visited:
                return

            current_path.append(node_id)
            node = node_map.get(node_id)

            if node:
                for dep in node.dependencies:
                    if dep in node_map:
                        visit_node(dep, current_path.copy())

            if len(current_path) > len(critical_path):
                critical_path[:] = current_path

        for node in sorted_nodes:
            visit_node(node.element_selector, [])

        return critical_path if critical_path else [node.element_selector for node in sorted_nodes]

    def generate_synced_styles(self, nodes: list[AnimationNode] | None = None,
                               include_keyframes: bool = True) -> str:
        """
        生成同步的 CSS 动画样式
        """
        target_nodes = nodes or list(self.animation_nodes.values())

        if not target_nodes:
            return ""

        console.print(f"[cyan]  🎨 生成同步 CSS 样式 ({len(target_nodes)} 个节点)...[/]")

        css_styles: list[str] = []

        # 生成 @keyframes
        if include_keyframes:
            keyframes = self._generate_keyframes(target_nodes)
            css_styles.append(keyframes)

        # 生成元素动画样式
        for node in target_nodes:
            easing = self.EASING_MAP.get(node.easing, node.easing)
            iteration = node.iteration_count if isinstance(node.iteration_count, str) else str(node.iteration_count)

            style_block = f"""
{node.element_selector} {{
    animation-name: {node.animation_name};
    animation-duration: {node.duration}s;
    animation-delay: {node.delay}s;
    animation-timing-function: {easing};
    animation-iteration-count: {iteration};
    animation-direction: {node.direction};
    animation-fill-mode: {node.fill_mode};
}}"""
            css_styles.append(style_block)

        # 生成动画链样式
        for chain_id, chain in self.animation_chains.items():
            chain_styles = self._generate_chain_styles(chain)
            css_styles.append(chain_styles)

        css_output = "\n".join(css_styles)
        console.print(f"[green]  ✓ CSS 样式生成完成[/]")

        return css_output

    def _generate_keyframes(self, nodes: list[AnimationNode]) -> str:
        """
        生成 @keyframes 定义
        """
        keyframes: list[str] = []

        for node in nodes:
            if node.animation_name in self.keyframes_registry:
                continue

            # 生成默认的关键帧动画
            keyframe_def = f"""
@keyframes {node.animation_name} {{
    0% {{
        opacity: 0;
        transform: translateY(20px);
    }}
    100% {{
        opacity: 1;
        transform: translateY(0);
    }}
}}"""
            self.keyframes_registry[node.animation_name] = keyframe_def
            keyframes.append(keyframe_def)

        return "\n".join(keyframes)

    def _generate_chain_styles(self, chain: AnimationChain) -> str:
        """
        生成动画链的 CSS 样式
        """
        css_comments = [f"/* Animation Chain: {chain.chain_id} */"]

        for i, node in enumerate(chain.nodes):
            css_comments.append(f"/*   Step {i + 1}: {node.element_selector} (delay: {node.delay}s) */")

        return "\n".join(css_comments)

    def generate_gsap_timeline(self, sequence_id: str | None = None) -> dict[str, Any]:
        """
        生成 GSAP 时间轴配置
        """
        console.print(f"[cyan]  🎬 生成 GSAP 时间轴配置...[/]")

        gsap_config: dict[str, Any] = {
            "timeline": {
                "defaults": {
                    "ease": "power2.out",
                    "duration": 1.0
                }
            },
            "tweens": []
        }

        target_sequences = ([self.animation_sequences.get(sequence_id)]
                            if sequence_id else list(self.animation_sequences.values()))

        for sequence in target_sequences:
            if not sequence:
                continue

            for chain in sequence.chains:
                for node in chain.nodes:
                    easing = self._convert_to_gsap_easing(node.easing)

                    tween = {
                        "target": node.element_selector,
                        "vars": {
                            "duration": node.duration,
                            "delay": node.delay,
                            "ease": easing
                        },
                        "position": node.delay
                    }
                    gsap_config["tweens"].append(tween)

        self.sync_report.gsap_config = gsap_config
        console.print(f"[green]  ✓ GSAP 配置生成完成 ({len(gsap_config['tweens'])} 个动画)[/]")

        return gsap_config

    def _convert_to_gsap_easing(self, easing: str) -> str:
        """
        将 CSS 缓动函数转换为 GSAP 缓动函数
        """
        reverse_map: dict[str, str] = {
            "linear": "none",
            "ease": "power1.out",
            "ease-in": "power1.in",
            "ease-out": "power1.out",
            "ease-in-out": "power1.inOut",
        }

        # 如果已经是 GSAP 格式
        if easing.startswith("gsap."):
            return easing.replace("gsap.", "")

        return reverse_map.get(easing, "power2.out")

    def sync_with_gsap_timeline(self, timeline_config: dict[str, Any]) -> dict[str, Any]:
        """
        与现有 GSAP 时间轴同步
        调整本地动画节点以匹配 GSAP 时间轴
        """
        console.print(f"[cyan]  🔄 与 GSAP 时间轴同步...[/]")

        adjustments: list[dict[str, Any]] = []
        tweens = timeline_config.get("tweens", [])

        for tween in tweens:
            target = tween.get("target", "")
            vars_config = tween.get("vars", {})
            position = tween.get("position", 0)

            if target in self.animation_nodes:
                node = self.animation_nodes[target]
                old_delay = node.delay
                old_duration = node.duration

                # 同步 GSAP 配置
                node.delay = position
                node.duration = vars_config.get("duration", node.duration)
                node.easing = f"gsap.{vars_config.get('ease', 'power2.out')}"

                adjustments.append({
                    "selector": target,
                    "old_delay": old_delay,
                    "new_delay": node.delay,
                    "old_duration": old_duration,
                    "new_duration": node.duration
                })

        self.sync_report.adjusted_delays = adjustments
        console.print(f"[green]  ✓ GSAP 同步完成 ({len(adjustments)} 个节点已调整)[/]")

        return {"adjustments": adjustments, "synced_nodes": len(adjustments)}

    def detect_conflicts(self) -> list[dict[str, Any]]:
        """
        检测动画冲突
        """
        conflicts: list[dict[str, Any]] = []
        nodes = list(self.animation_nodes.values())

        for i, node_a in enumerate(nodes):
            for node_b in nodes[i + 1:]:
                # 检查选择器冲突
                if node_a.element_selector == node_b.element_selector:
                    if node_a.animation_name != node_b.animation_name:
                        conflicts.append({
                            "type": "selector_conflict",
                            "selector": node_a.element_selector,
                            "animations": [node_a.animation_name, node_b.animation_name],
                            "severity": "high"
                        })

                # 检查时间重叠导致的视觉冲突
                time_overlap = (
                        node_a.delay < node_b.delay + node_b.duration and
                        node_b.delay < node_a.delay + node_a.duration
                )

                if time_overlap and self._check_visual_conflict(node_a, node_b):
                    conflicts.append({
                        "type": "visual_overlap",
                        "node_a": node_a.element_selector,
                        "node_b": node_b.element_selector,
                        "overlap_period": {
                            "start": max(node_a.delay, node_b.delay),
                            "end": min(node_a.delay + node_a.duration, node_b.delay + node_b.duration)
                        },
                        "severity": "medium"
                    })

        self.sync_report.conflicts = conflicts
        return conflicts

    def _check_visual_conflict(self, node_a: AnimationNode, node_b: AnimationNode) -> bool:
        """
        检查两个动画节点是否会产生视觉冲突
        """
        # 简化判断：如果动画名称相似或选择器有包含关系，可能冲突
        selectors_close = (
                node_a.element_selector in node_b.element_selector or
                node_b.element_selector in node_a.element_selector
        )

        return selectors_close

    def resolve_conflicts(self, strategy: str = "auto") -> dict[str, Any]:
        """
        解决动画冲突
        """
        console.print(f"[cyan]  🔧 解决动画冲突 (策略: {strategy})...[/]")

        conflicts = self.detect_conflicts()
        resolved: list[dict[str, Any]] = []

        for conflict in conflicts:
            resolution = self._resolve_single_conflict(conflict, strategy)
            if resolution:
                resolved.append(resolution)

        console.print(f"[green]  ✓ 冲突解决完成 ({len(resolved)}/{len(conflicts)} 已解决)[/]")
        return {"resolved": resolved, "remaining": len(conflicts) - len(resolved)}

    def _resolve_single_conflict(
        self, conflict: dict[str, Any], strategy: str
    ) -> dict[str, Any] | None:
        """解决单个冲突"""
        if strategy != "auto":
            return None

        conflict_type = conflict.get("type")

        if conflict_type == "selector_conflict":
            return self._resolve_selector_conflict(conflict)
        elif conflict_type == "visual_overlap":
            return self._resolve_visual_overlap(conflict)

        return None

    def _resolve_selector_conflict(self, conflict: dict[str, Any]) -> dict[str, Any] | None:
        """解决选择器冲突：合并为序列动画"""
        selector = conflict.get("selector", "")
        animations = conflict.get("animations", [])

        if len(animations) < 2:
            return None

        for node in self.animation_nodes.values():
            if (node.element_selector == selector and
                node.animation_name == animations[1]):
                original_delay = node.delay
                node.delay += 1.0  # 延迟1秒

                return {
                    "conflict": conflict,
                    "resolution": "delayed_sequence",
                    "original_delay": original_delay,
                    "new_delay": node.delay
                }

        return None

    def _resolve_visual_overlap(self, conflict: dict[str, Any]) -> dict[str, Any] | None:
        """解决视觉重叠冲突：轻微错开时间"""
        node_b_selector = conflict.get("node_b", "")

        for node in self.animation_nodes.values():
            if node.element_selector == node_b_selector:
                node.delay += 0.1  # 错开 0.1 秒

                return {
                    "conflict": conflict,
                    "resolution": "staggered",
                    "stagger_amount": 0.1
                }

        return None

    def get_sync_report(self) -> SyncReport:
        """
        获取同步报告
        """
        self.sync_report.total_nodes = len(self.animation_nodes)
        self.sync_report.total_chains = len(self.animation_chains)

        # 计算总持续时间
        if self.animation_nodes:
            max_end_time = max(
                node.delay + node.duration
                for node in self.animation_nodes.values()
            )
            self.sync_report.total_duration = max_end_time

        return self.sync_report

    def export_sync_report(self, format_type: str = "json") -> str:
        """
        导出同步报告
        """
        report = self.get_sync_report()

        if format_type == "json":
            report_dict = {
                "total_nodes": report.total_nodes,
                "total_chains": report.total_chains,
                "total_duration": report.total_duration,
                "conflicts": report.conflicts,
                "adjusted_delays": report.adjusted_delays,
                "timeline_summary": report.timeline_summary,
                "gsap_config": report.gsap_config
            }
            return json.dumps(report_dict, indent=2, ensure_ascii=False)

        elif format_type == "markdown":
            lines = [
                "# 动画同步报告",
                "",
                f"## 概览",
                f"- **总节点数**: {report.total_nodes}",
                f"- **总链数**: {report.total_chains}",
                f"- **总持续时间**: {report.total_duration:.2f}s",
                "",
                "## 冲突检测",
                f"- 发现冲突: {len(report.conflicts)} 个",
            ]

            for conflict in report.conflicts:
                lines.append(f"  - [{conflict['severity'].upper()}] {conflict['type']}: {conflict.get('selector', '')}")

            lines.extend([
                "",
                "## 时间线摘要",
                f"- 动画节点: {len(report.timeline_summary.get('nodes', []))}",
                f"- 时间重叠: {len(report.timeline_summary.get('overlaps', []))} 处",
                f"- 时间间隙: {len(report.timeline_summary.get('gaps', []))} 处",
            ])

            return "\n".join(lines)

        return ""

    def parse_existing_css(self, css_text: str) -> list[AnimationNode]:
        """
        解析现有的 CSS 动画文本，提取动画节点
        """
        console.print(f"[cyan]  📄 解析现有 CSS 动画...[/]")

        nodes: list[AnimationNode] = []

        # 匹配 CSS 动画属性
        animation_pattern = re.compile(
            r'([^{]+)\{[^}]*animation-name:\s*([^;]+);[^}]*\}',
            re.IGNORECASE
        )

        duration_pattern = re.compile(r'animation-duration:\s*([\d.]+)s?', re.IGNORECASE)
        delay_pattern = re.compile(r'animation-delay:\s*([\d.]+)s?', re.IGNORECASE)
        easing_pattern = re.compile(r'animation-timing-function:\s*([^;]+);', re.IGNORECASE)

        for match in animation_pattern.finditer(css_text):
            selector = match.group(1).strip()
            animation_name = match.group(2).strip()
            block = match.group(0)

            duration_match = duration_pattern.search(block)
            delay_match = delay_pattern.search(block)
            easing_match = easing_pattern.search(block)

            node = AnimationNode(
                element_selector=selector,
                animation_name=animation_name,
                duration=float(duration_match.group(1)) if duration_match else 1.0,
                delay=float(delay_match.group(1)) if delay_match else 0.0,
                easing=easing_match.group(1).strip() if easing_match else "ease"
            )

            nodes.append(node)
            self.register_node(node)

        console.print(f"[green]  ✓ 解析完成，提取 {len(nodes)} 个动画节点[/]")
        return nodes

    def create_stagger_animation(self, base_selector: str, child_selector: str,
                                  count: int, stagger_delay: float = 0.1) -> AnimationChain:
        """
        创建交错动画（stagger animation）
        """
        nodes: list[AnimationNode] = []

        for i in range(count):
            selector = f"{base_selector} {child_selector}:nth-child({i + 1})"
            node = AnimationNode(
                element_selector=selector,
                animation_name=f"stagger-fade-in-{i}",
                duration=0.5,
                delay=i * stagger_delay,
                easing="gsap.power2.out"
            )
            nodes.append(node)
            self.register_node(node)

        chain = self.create_chain(f"stagger-{base_selector.replace(' ', '-')}", nodes)
        return chain
