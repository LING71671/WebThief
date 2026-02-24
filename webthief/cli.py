"""
CLI 入口：click 参数解析 + 主流程调度
"""

import asyncio
import sys

import click
from rich.console import Console

from . import __version__
from .orchestrator import Orchestrator

console = Console()


@click.command(
    name="webthief",
    help="🕷️ WebThief — 高保真网站克隆工具\n\n"
         "完美还原依赖 JavaScript 动态渲染的现代 SPA 网页，"
         "克隆结果可在 file:// 协议或独立服务器上离线运行。",
)
@click.argument("url")
@click.option(
    "-o", "--output",
    default="./webthief_output",
    help="输出目录 (默认: ./webthief_output)",
    show_default=True,
)
@click.option(
    "-c", "--concurrency",
    default=20,
    type=int,
    help="并发下载数",
    show_default=True,
)
@click.option(
    "-t", "--timeout",
    default=30,
    type=int,
    help="单文件下载超时 (秒)",
    show_default=True,
)
@click.option(
    "--delay",
    default=0.1,
    type=float,
    help="请求间隔 (秒)",
    show_default=True,
)
@click.option(
    "--no-js",
    is_flag=True,
    default=False,
    help="禁用 JavaScript 渲染 (仅抓静态 HTML)",
)
@click.option(
    "--keep-js",
    is_flag=True,
    default=False,
    help="保留 JS 执行能力 (默认中和所有 JS 防闪退)",
)
@click.option(
    "--user-agent",
    default=None,
    help="自定义 User-Agent 字符串",
)
@click.option(
    "--wait",
    default=3,
    type=int,
    help="页面加载后额外等待 (秒)",
    show_default=True,
)
@click.option(
    "--verbose", "-v",
    is_flag=True,
    default=False,
    help="详细日志输出",
)
@click.option(
    "--enable-qr-intercept",
    is_flag=True,
    default=True,
    help="启用二维码拦截（实时二维码克隆）",
)
@click.option(
    "--enable-react-intercept",
    is_flag=True,
    default=True,
    help="启用 React 组件拦截（完全体交互菜单）",
)
@click.option(
    "--crawl-site/--single-page",
    default=True,
    help="递归抓取整个站点（同 host）/仅抓取单页",
)
@click.option(
    "--max-pages",
    default=5000,
    type=int,
    help="站点抓取模式下的最大页面数上限",
    show_default=True,
)
@click.option(
    "--auth-mode",
    type=click.Choice(["manual-pause", "import-session", "skip"], case_sensitive=False),
    default="manual-pause",
    help="遇到登录页时的处理策略",
    show_default=True,
)
@click.option(
    "--session-cache/--no-session-cache",
    default=True,
    help="启用加密会话缓存（~/.webthief/sessions）",
)
@click.option(
    "--session-file",
    default=None,
    help="会话文件路径（import-session 模式读取；或作为缓存文件路径）",
)
@click.option(
    "--headful-auth/--no-headful-auth",
    default=True,
    help="manual-pause 模式下是否启用可视浏览器人工认证",
)
@click.version_option(version=__version__, prog_name="WebThief")
def main(
    url: str,
    output: str,
    concurrency: int,
    timeout: int,
    delay: float,
    no_js: bool,
    keep_js: bool,
    user_agent: str | None,
    wait: int,
    verbose: bool,
    enable_qr_intercept: bool,
    enable_react_intercept: bool,
    crawl_site: bool,
    max_pages: int,
    auth_mode: str,
    session_cache: bool,
    session_file: str | None,
    headful_auth: bool,
) -> None:
    """克隆指定 URL 的网页到本地"""

    # 基本 URL 校验
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
        console.print(f"[dim]自动补全协议: {url}[/]")

    orchestrator = Orchestrator(
        url=url,
        output_dir=output,
        concurrency=concurrency,
        timeout=timeout,
        delay=delay,
        user_agent=user_agent,
        extra_wait=wait,
        disable_js=no_js,
        keep_js=keep_js,
        verbose=verbose,
        enable_qr_intercept=enable_qr_intercept,
        enable_react_intercept=enable_react_intercept,
        crawl_site=crawl_site,
        max_pages=max_pages,
        auth_mode=auth_mode,
        session_cache=session_cache,
        session_file=session_file,
        headful_auth=headful_auth,
    )

    try:
        # Windows 需要特殊的事件循环策略
        if sys.platform == "win32":
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

        asyncio.run(orchestrator.run())

    except KeyboardInterrupt:
        console.print("\n[yellow]⚠ 用户中断操作[/]")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[bold red]✗ 克隆失败: {e}[/]")
        if verbose:
            console.print_exception()
        sys.exit(1)


if __name__ == "__main__":
    main()
