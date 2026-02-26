"""
JavaScript 模块依赖解析器：
- 分析 JavaScript 模块依赖图
- 检测循环依赖
- 计算模块加载顺序（拓扑排序）
- 支持多种模块格式（ESM、CommonJS、AMD）
"""

from __future__ import annotations

import re
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from playwright.async_api import Page

from rich.console import Console
from rich.table import Table

console = Console()


class ModuleType(Enum):
    """模块类型"""
    ESM = "ES Module"
    COMMONJS = "CommonJS"
    AMD = "AMD"
    UMD = "UMD"
    SYSTEMJS = "SystemJS"
    UNKNOWN = "Unknown"


@dataclass
class ModuleInfo:
    """模块信息"""
    url: str
    module_type: ModuleType = ModuleType.UNKNOWN
    dependencies: set[str] = field(default_factory=set)
    dependents: set[str] = field(default_factory=set)
    is_entry: bool = False
    is_async: bool = False
    size: int = 0
    load_time: float = 0.0
    has_side_effects: bool = True
    exports: set[str] = field(default_factory=set)
    imports: dict[str, set[str]] = field(default_factory=lambda: defaultdict(set))


@dataclass
class DependencyGraph:
    """依赖图"""
    modules: dict[str, ModuleInfo] = field(default_factory=dict)
    entry_points: set[str] = field(default_factory=set)
    circular_dependencies: list[list[str]] = field(default_factory=list)

    def add_module(self, module: ModuleInfo) -> None:
        """添加模块到图中"""
        self.modules[module.url] = module
        if module.is_entry:
            self.entry_points.add(module.url)

    def add_dependency(self, from_url: str, to_url: str) -> None:
        """添加依赖关系"""
        if from_url not in self.modules:
            self.modules[from_url] = ModuleInfo(url=from_url)
        if to_url not in self.modules:
            self.modules[to_url] = ModuleInfo(url=to_url)

        self.modules[from_url].dependencies.add(to_url)
        self.modules[to_url].dependents.add(from_url)

    def get_load_order(self) -> list[str]:
        """
        使用 Kahn 算法进行拓扑排序
        返回模块加载顺序（依赖优先）
        """
        in_degree = self._calculate_in_degrees()
        queue = deque([url for url, degree in in_degree.items() if degree == 0])
        result: list[str] = []

        self._process_topological_sort(queue, in_degree, result)

        if len(result) != len(self.modules):
            console.print("[yellow]  ⚠ 检测到循环依赖，部分模块无法确定加载顺序[/]")

        return result

    def _calculate_in_degrees(self) -> dict[str, int]:
        """计算所有模块的入度"""
        in_degree: dict[str, int] = defaultdict(int)
        for url, module in self.modules.items():
            if url not in in_degree:
                in_degree[url] = 0
            for dep in module.dependencies:
                in_degree[dep] = in_degree.get(dep, 0)

        for module in self.modules.values():
            for dep in module.dependencies:
                in_degree[dep] += 1

        return in_degree

    def _process_topological_sort(
        self,
        queue: deque,
        in_degree: dict[str, int],
        result: list[str]
    ) -> None:
        """执行拓扑排序处理"""
        while queue:
            current = queue.popleft()
            result.append(current)

            if current in self.modules:
                for dep in self.modules[current].dependencies:
                    in_degree[dep] -= 1
                    if in_degree[dep] == 0:
                        queue.append(dep)

    def detect_cycles(self) -> list[list[str]]:
        """
        使用 DFS 检测所有循环依赖
        返回循环依赖链列表
        """
        self.circular_dependencies = []
        visited: set[str] = set()
        rec_stack: set[str] = set()
        path: list[str] = []

        def dfs(node: str) -> bool:
            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            if node in self.modules:
                for neighbor in self.modules[node].dependencies:
                    if neighbor not in visited:
                        if dfs(neighbor):
                            return True
                    elif neighbor in rec_stack:
                        cycle_start = path.index(neighbor)
                        cycle = path[cycle_start:] + [neighbor]
                        self.circular_dependencies.append(cycle)

            path.pop()
            rec_stack.remove(node)
            return False

        for url in self.modules:
            if url not in visited:
                dfs(url)

        return self.circular_dependencies

    def get_critical_path(self) -> list[str]:
        """
        计算关键路径（最长依赖链）
        用于确定最小加载时间
        """
        if not self.entry_points:
            return []

        memo: dict[str, int] = {}

        def get_depth(url: str) -> int:
            if url in memo:
                return memo[url]
            if url not in self.modules or not self.modules[url].dependencies:
                memo[url] = 0
                return 0

            max_depth = max(
                (get_depth(dep) for dep in self.modules[url].dependencies),
                default=0
            )
            memo[url] = max_depth + 1
            return memo[url]

        entry_depths = [(url, get_depth(url)) for url in self.entry_points]
        if not entry_depths:
            return []

        critical_entry = max(entry_depths, key=lambda x: x[1])[0]

        path: list[str] = [critical_entry]
        current = critical_entry

        while current in self.modules and self.modules[current].dependencies:
            next_module = max(
                self.modules[current].dependencies,
                key=lambda x: memo.get(x, 0)
            )
            path.append(next_module)
            current = next_module

        return path

    def get_modules_by_depth(self) -> dict[int, list[str]]:
        """
        按依赖深度分组模块
        同层模块可以并行加载
        """
        depths: dict[str, int] = {}

        def calculate_depth(url: str) -> int:
            if url in depths:
                return depths[url]
            if url not in self.modules or not self.modules[url].dependencies:
                depths[url] = 0
                return 0

            max_dep_depth = max(
                (calculate_depth(dep) for dep in self.modules[url].dependencies),
                default=0
            )
            depths[url] = max_dep_depth + 1
            return depths[url]

        for url in self.modules:
            calculate_depth(url)

        grouped: dict[int, list[str]] = defaultdict(list)
        for url, depth in depths.items():
            grouped[depth].append(url)

        return dict(sorted(grouped.items()))


class DependencyResolver:
    """
    JavaScript 模块依赖解析器
    支持多种模块格式，与 Playwright 集成
    """

    # ESM import 语句模式
    ESM_IMPORT_PATTERNS = [
        re.compile(r'import\s+.*?\s+from\s+["\']([^"\']+)["\']', re.DOTALL),
        re.compile(r'import\s+["\']([^"\']+)["\']'),
        re.compile(r'import\(["\']([^"\']+)["\']\)'),
        re.compile(r'export\s+.*?\s+from\s+["\']([^"\']+)["\']', re.DOTALL),
    ]

    # CommonJS require 模式
    CJS_REQUIRE_PATTERN = re.compile(
        r'require\(["\']([^"\']+)["\']\)'
    )

    # AMD define/require 模式
    AMD_PATTERN = re.compile(
        r'(?:define|require)\s*\(\s*\[[^\]]*\]|'
        r'(?:define|require)\s*\(\s*["\']([^"\']+)["\']'
    )

    # 动态导入模式
    DYNAMIC_IMPORT_PATTERN = re.compile(
        r'import\s*\(\s*["\']([^"\']+)["\']\s*\)'
    )

    def __init__(self, base_url: str):
        """
        初始化依赖解析器

        Args:
            base_url: 页面基础 URL，用于解析相对路径
        """
        self.base_url = base_url
        self.graph = DependencyGraph()
        self._analyzed_scripts: set[str] = set()

    def detect_module_type(self, script_content: str, script_url: str) -> ModuleType:
        """
        检测脚本的模块类型

        Args:
            script_content: 脚本内容
            script_url: 脚本 URL

        Returns:
            ModuleType: 检测到的模块类型
        """
        if not script_content:
            return ModuleType.UNKNOWN

        # 按优先级检测模块类型
        module_type = self._detect_esm(script_content)
        if module_type != ModuleType.UNKNOWN:
            return module_type

        module_type = self._detect_commonjs(script_content)
        if module_type != ModuleType.UNKNOWN:
            return module_type

        module_type = self._detect_amd(script_content)
        if module_type != ModuleType.UNKNOWN:
            return module_type

        module_type = self._detect_umd(script_content)
        if module_type != ModuleType.UNKNOWN:
            return module_type

        return self._detect_systemjs(script_content)

    def _detect_esm(self, content: str) -> ModuleType:
        """检测 ESM 模块"""
        for pattern in self.ESM_IMPORT_PATTERNS:
            if pattern.search(content):
                return ModuleType.ESM

        if re.search(r'\bexport\s+(?:default\s+)?(?:function|class|const|let|var)', content):
            return ModuleType.ESM

        return ModuleType.UNKNOWN

    def _detect_commonjs(self, content: str) -> ModuleType:
        """检测 CommonJS 模块"""
        if self.CJS_REQUIRE_PATTERN.search(content):
            if re.search(r'\bmodule\.exports\b', content) or \
               re.search(r'\bexports\.\w+\s*=', content):
                return ModuleType.COMMONJS
        return ModuleType.UNKNOWN

    def _detect_amd(self, content: str) -> ModuleType:
        """检测 AMD 模块"""
        if re.search(r'\bdefine\s*\(', content):
            return ModuleType.AMD
        return ModuleType.UNKNOWN

    def _detect_umd(self, content: str) -> ModuleType:
        """检测 UMD 模块"""
        if re.search(r'\(function\s*\([^)]*\)\s*\{[\s\S]*module\.exports[\s\S]*\}\)', content):
            return ModuleType.UMD
        return ModuleType.UNKNOWN

    def _detect_systemjs(self, content: str) -> ModuleType:
        """检测 SystemJS 模块"""
        if re.search(r'\bSystemJS?\b', content) or \
           re.search(r'\bSystem\.register\s*\(', content):
            return ModuleType.SYSTEMJS
        return ModuleType.UNKNOWN

    def extract_dependencies(
        self,
        script_content: str,
        script_url: str,
        module_type: ModuleType | None = None
    ) -> set[str]:
        """
        从脚本内容中提取依赖 URL

        Args:
            script_content: 脚本内容
            script_url: 脚本 URL
            module_type: 已知的模块类型（可选）

        Returns:
            依赖 URL 集合
        """
        if not script_content:
            return set()

        if module_type is None:
            module_type = self.detect_module_type(script_content, script_url)

        dependencies: set[str] = set()

        if module_type == ModuleType.ESM:
            dependencies.update(self._extract_esm_deps(script_content))
        elif module_type == ModuleType.COMMONJS:
            dependencies.update(self._extract_cjs_deps(script_content))
        elif module_type == ModuleType.AMD:
            dependencies.update(self._extract_amd_deps(script_content))
        else:
            # 尝试所有格式
            dependencies.update(self._extract_esm_deps(script_content))
            dependencies.update(self._extract_cjs_deps(script_content))
            dependencies.update(self._extract_amd_deps(script_content))

        # 解析相对路径为绝对路径
        resolved_deps: set[str] = set()
        for dep in dependencies:
            resolved = self._resolve_module_path(dep, script_url)
            if resolved:
                resolved_deps.add(resolved)

        return resolved_deps

    def _extract_esm_deps(self, content: str) -> set[str]:
        """提取 ESM 依赖"""
        deps: set[str] = set()

        for pattern in self.ESM_IMPORT_PATTERNS:
            for match in pattern.finditer(content):
                dep = match.group(1)
                if dep and not self._is_builtin_module(dep):
                    deps.add(dep)

        # 动态导入
        for match in self.DYNAMIC_IMPORT_PATTERN.finditer(content):
            dep = match.group(1)
            if dep and not self._is_builtin_module(dep):
                deps.add(dep)

        return deps

    def _extract_cjs_deps(self, content: str) -> set[str]:
        """提取 CommonJS 依赖"""
        deps: set[str] = set()

        for match in self.CJS_REQUIRE_PATTERN.finditer(content):
            dep = match.group(1)
            if dep and not self._is_builtin_module(dep):
                deps.add(dep)

        return deps

    def _extract_amd_deps(self, content: str) -> set[str]:
        """提取 AMD 依赖"""
        deps: set[str] = set()

        # 匹配 define(['dep1', 'dep2'], ...)
        define_array = re.search(r'define\s*\(\s*\[([^\]]+)\]', content)
        if define_array:
            array_content = define_array.group(1)
            for match in re.finditer(r'["\']([^"\']+)["\']', array_content):
                dep = match.group(1)
                if dep and not self._is_builtin_module(dep):
                    deps.add(dep)

        return deps

    def _is_builtin_module(self, module_name: str) -> bool:
        """判断是否为 Node.js 内置模块"""
        builtin_modules = {
            'fs', 'path', 'http', 'https', 'url', 'crypto', 'buffer',
            'stream', 'events', 'util', 'os', 'net', 'querystring',
            'child_process', 'cluster', 'dgram', 'dns', 'readline',
            'repl', 'tls', 'tty', 'v8', 'vm', 'zlib', 'worker_threads',
            'perf_hooks', 'async_hooks', 'console', 'process', 'timers',
        }
        return module_name in builtin_modules or module_name.startswith('node:')

    def _resolve_module_path(self, module_path: str, from_url: str) -> str | None:
        """
        解析模块路径为绝对 URL

        Args:
            module_path: 模块路径（可能是相对路径、绝对路径或裸模块名）
            from_url: 引用该模块的脚本 URL

        Returns:
            解析后的绝对 URL，或 None（如果是裸模块名）
        """
        from urllib.parse import urljoin, urlparse

        # 跳过裸模块名（如 'react', 'lodash'）
        if not module_path.startswith(('.', '/', 'http://', 'https://')):
            # 可能是 node_modules 中的模块
            if '/' not in module_path or module_path.split('/')[0].startswith('@'):
                return None

        # 协议相对 URL
        if module_path.startswith('//'):
            parsed = urlparse(self.base_url)
            return f"{parsed.scheme}:{module_path}"

        # 绝对路径
        if module_path.startswith('/'):
            parsed = urlparse(self.base_url)
            return f"{parsed.scheme}://{parsed.netloc}{module_path}"

        # 相对路径
        if module_path.startswith('.'):
            return urljoin(from_url, module_path)

        # 已经是绝对 URL
        if module_path.startswith(('http://', 'https://')):
            return module_path

        return None

    async def analyze_page(self, page: Page) -> DependencyGraph:
        """
        分析页面中的所有 JavaScript 模块依赖

        Args:
            page: Playwright Page 对象

        Returns:
            DependencyGraph: 完整的依赖图
        """
        console.print("[bold magenta]🔍 分析 JavaScript 模块依赖...[/]")

        # 获取所有脚本信息
        scripts_info = await self._collect_scripts_info(page)

        # 分析每个脚本
        for script_url, script_info in scripts_info.items():
            if script_url in self._analyzed_scripts:
                continue
            self._analyzed_scripts.add(script_url)

            content = script_info.get('content', '')
            is_entry = script_info.get('is_entry', False)

            module_type = self.detect_module_type(content, script_url)
            dependencies = self.extract_dependencies(content, script_url, module_type)

            module_info = ModuleInfo(
                url=script_url,
                module_type=module_type,
                dependencies=dependencies,
                is_entry=is_entry,
                size=len(content.encode('utf-8')),
            )

            self.graph.add_module(module_info)

            # 添加依赖边
            for dep in dependencies:
                self.graph.add_dependency(script_url, dep)

        # 检测循环依赖
        cycles = self.graph.detect_cycles()
        if cycles:
            console.print(f"[yellow]  ⚠ 检测到 {len(cycles)} 个循环依赖[/]")

        return self.graph

    async def _collect_scripts_info(self, page: Page) -> dict[str, dict]:
        """收集页面中所有脚本的信息"""
        try:
            scripts_data = await page.evaluate("""
                () => {
                    const scripts = [];

                    // 外部脚本
                    document.querySelectorAll('script[src]').forEach(script => {
                        scripts.push({
                            url: script.src,
                            type: script.type || 'text/javascript',
                            is_entry: !script.async && !script.defer,
                            async: script.async,
                            defer: script.defer,
                            module: script.type === 'module',
                        });
                    });

                    // 内联脚本
                    document.querySelectorAll('script:not([src])').forEach((script, index) => {
                        scripts.push({
                            url: `inline-script-${index}`,
                            content: script.textContent || '',
                            type: script.type || 'text/javascript',
                            is_entry: true,
                            inline: true,
                        });
                    });

                    return scripts;
                }
            """)

            result: dict[str, dict] = {}

            for script in scripts_data:
                url = script.get('url', '')
                if not url:
                    continue

                result[url] = {
                    'type': script.get('type', 'text/javascript'),
                    'is_entry': script.get('is_entry', False),
                    'async': script.get('async', False),
                    'defer': script.get('defer', False),
                    'module': script.get('module', False),
                    'inline': script.get('inline', False),
                    'content': script.get('content', ''),
                }

            return result

        except Exception as e:
            console.print(f"[red]  ✗ 收集脚本信息失败: {e}[/]")
            return {}

    def get_optimized_load_order(self) -> list[list[str]]:
        """
        获取优化后的加载顺序
        返回分层列表，同层可并行加载

        Returns:
            分层的模块 URL 列表
        """
        layers = self.graph.get_modules_by_depth()
        return [urls for _, urls in sorted(layers.items())]

    def print_summary(self) -> None:
        """打印依赖分析摘要"""
        if not self.graph.modules:
            console.print("[dim]  未检测到 JavaScript 模块[/]")
            return

        self._print_modules_table()
        self._print_circular_dependencies()
        self._print_load_analysis()

    def _print_modules_table(self) -> None:
        """打印模块表格"""
        table = Table(title="📦 模块依赖分析", show_header=True, header_style="bold cyan")
        table.add_column("模块", style="green", width=40)
        table.add_column("类型", style="yellow", width=12)
        table.add_column("依赖数", justify="right", width=8)
        table.add_column("被引用", justify="right", width=8)
        table.add_column("入口", style="magenta", width=6)

        for url, module in sorted(self.graph.modules.items(), key=lambda x: -len(x[1].dependencies)):
            short_url = url.split('/')[-1] if '/' in url else url
            if len(short_url) > 38:
                short_url = short_url[:35] + "..."

            table.add_row(
                short_url,
                module.module_type.value,
                str(len(module.dependencies)),
                str(len(module.dependents)),
                "✓" if module.is_entry else "",
            )

        console.print(table)

    def _print_circular_dependencies(self) -> None:
        """打印循环依赖信息"""
        if not self.graph.circular_dependencies:
            return

        console.print("\n[bold red]🔄 循环依赖检测:[/]")
        for i, cycle in enumerate(self.graph.circular_dependencies[:5], 1):
            cycle_str = " → ".join(
                url.split('/')[-1][:20] for url in cycle
            )
            console.print(f"  {i}. {cycle_str}")
        if len(self.graph.circular_dependencies) > 5:
            console.print(f"  ... 还有 {len(self.graph.circular_dependencies) - 5} 个")

    def _print_load_analysis(self) -> None:
        """打印加载层级分析"""
        layers = self.get_optimized_load_order()
        if not layers:
            return

        console.print(f"\n[bold cyan]📊 加载层级分析:[/]")
        console.print(f"  总模块数: {len(self.graph.modules)}")
        console.print(f"  加载层级: {len(layers)}")
        console.print(f"  关键路径长度: {len(self.graph.get_critical_path())}")

    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            "modules": {
                url: {
                    "type": module.module_type.value,
                    "dependencies": list(module.dependencies),
                    "dependents": list(module.dependents),
                    "is_entry": module.is_entry,
                    "size": module.size,
                }
                for url, module in self.graph.modules.items()
            },
            "entry_points": list(self.graph.entry_points),
            "circular_dependencies": [
                list(cycle) for cycle in self.graph.circular_dependencies
            ],
            "load_order": self.get_optimized_load_order(),
            "critical_path": self.graph.get_critical_path(),
        }
