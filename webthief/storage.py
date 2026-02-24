"""
镜像存储层：
- 根据 URL 结构自动创建嵌套目录
- 保存 HTML 和所有资源文件
- 处理文件名特殊字符
- 生成最终的离线镜像站点
"""

from __future__ import annotations

from pathlib import Path

from rich.console import Console

console = Console()


class Storage:
    """
    镜像文件系统管理器
    负责：创建目录 → 写入文件 → 组织结构
    """

    def __init__(self, output_dir: str | Path):
        self.output_dir = Path(output_dir)

    def initialize(self) -> None:
        """创建输出根目录"""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        console.print(f"[bold cyan]📁 输出目录: {self.output_dir.resolve()}[/]")

    def save_html(self, html: str, filename: str = "index.html") -> Path:
        """
        保存主 HTML 文件

        Args:
            html: 净化并重写过路径的 HTML 内容
            filename: 文件名（默认 index.html）

        Returns:
            保存的文件路径
        """
        file_path = self.output_dir / filename
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(html, encoding="utf-8")
        console.print(f"[green]  ✓ 已保存: {filename} ({len(html):,} 字符)[/]")
        return file_path

    def save_file(self, content: bytes, local_path: str) -> Path:
        """
        保存资源文件，自动创建嵌套目录

        Args:
            content: 文件二进制内容
            local_path: 相对于输出目录的本地路径

        Returns:
            保存的文件路径
        """
        file_path = self.output_dir / local_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_bytes(content)
        return file_path

    def save_text(self, text: str, local_path: str, encoding: str = "utf-8") -> Path:
        """
        保存文本文件（如重写后的 CSS）

        Args:
            text: 文本内容
            local_path: 相对于输出目录的本地路径
            encoding: 编码

        Returns:
            保存的文件路径
        """
        file_path = self.output_dir / local_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(text, encoding=encoding)
        return file_path

    def get_output_path(self) -> Path:
        """获取输出目录的绝对路径"""
        return self.output_dir.resolve()

    def print_tree(self, max_depth: int = 3) -> None:
        """打印输出目录的文件树"""
        console.print(f"\n[bold cyan]📂 镜像站点结构:[/]")
        self._print_dir(self.output_dir, "", 0, max_depth)

    def _print_dir(self, path: Path, prefix: str, depth: int, max_depth: int) -> None:
        """递归打印目录树"""
        if depth >= max_depth:
            return

        items = sorted(path.iterdir(), key=lambda p: (p.is_file(), p.name))
        for i, item in enumerate(items):
            is_last = i == len(items) - 1
            connector = "└── " if is_last else "├── "
            extension = "    " if is_last else "│   "

            if item.is_dir():
                # 统计子项数
                child_count = sum(1 for _ in item.rglob("*") if _.is_file())
                console.print(f"{prefix}{connector}[bold blue]{item.name}/[/] [dim]({child_count} 文件)[/]")
                self._print_dir(item, prefix + extension, depth + 1, max_depth)
            else:
                size = item.stat().st_size
                size_str = self._format_size(size)
                console.print(f"{prefix}{connector}{item.name} [dim]({size_str})[/]")

    @staticmethod
    def _format_size(size_bytes: int) -> str:
        """格式化文件大小"""
        for unit in ("B", "KB", "MB", "GB"):
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} TB"
