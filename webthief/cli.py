"""
CLI 入口：click 参数解析 + 主流程调度

简化版 CLI，移除了以下选项（已集成到智能检测模块）：
- --websocket-proxy: WebSocket 代理功能已整合
- --browser-api: 浏览器 API 模拟已整合
- --frontend-adapter: 前端适配器已整合
"""

import asyncio
import sys
from pathlib import Path

import click
from rich.console import Console

from . import __version__
from .core.orchestrator import Orchestrator
from .server.server_manager import ServerManager, ServerConfig

console = Console()


@click.group(
    name="webthief",
    help="🕷️ WebThief — 高保真网站克隆工具\n\n"
         "完美还原依赖 JavaScript 动态渲染的现代 SPA 网页，"
         "克隆结果可在 file:// 协议或独立服务器上离线运行。\n\n"
         "命令:\n"
         "  clone  克隆指定 URL 的网页到本地\n"
         "  serve  启动本地 HTTP 服务器",
    invoke_without_command=True,
)
@click.option("--version", "-V", is_flag=True, help="显示版本信息")
@click.pass_context
def main(ctx: click.Context, version: bool) -> None:
    """WebThief 主命令入口"""
    if version:
        console.print(f"WebThief 版本: {__version__}")
        ctx.exit(0)

    # 如果没有指定子命令，显示帮助信息
    if ctx.invoked_subcommand is None:
        console.print(ctx.get_help())
        ctx.exit(0)


@main.command(name="clone", help="克隆指定 URL 的网页到本地")
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
    "--keep-js/--neutralize-js",
    default=True,
    help="保留 JS 执行能力（默认）/ 中和所有 JS 防止运行时异常",
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
    "--enable-qr-intercept/--disable-qr-intercept",
    default=True,
    help="启用/禁用二维码拦截（实时二维码克隆）",
)
@click.option(
    "--enable-react-intercept/--disable-react-intercept",
    default=True,
    help="启用/禁用 React 组件拦截（完全体交互菜单）",
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
@click.option(
    "--local-server",
    is_flag=True,
    default=False,
    help="克隆完成后启动本地服务器",
)
@click.option(
    "--port",
    default=8080,
    type=int,
    help="本地服务器端口（默认: 8080）",
    show_default=True,
)
@click.option(
    "--https",
    is_flag=True,
    default=False,
    help="启用 HTTPS 模拟（本地服务器）",
)
@click.option(
    "--api-simulation",
    is_flag=True,
    default=False,
    help="启用 API 模拟（缓存 API 响应）",
)
@click.option(
    "--security-handler",
    is_flag=True,
    default=False,
    help="启用安全处理器（指纹轮换、反爬虫绕过）",
)
@click.option(
    "--performance-optimizer",
    is_flag=True,
    default=False,
    help="启用性能优化器（动态并发调整、内存管理）",
)
@click.option(
    "--mouse-simulation",
    is_flag=True,
    default=False,
    help="启用鼠标轨迹模拟（触发交互式动画）",
)
@click.option(
    "--scroll-precision",
    is_flag=True,
    default=False,
    help="启用高精度滚动（捕获滚动触发动画）",
)
@click.option(
    "--canvas-recording",
    is_flag=True,
    default=False,
    help="启用 Canvas 录制（捕获动态绘制内容）",
)
@click.option(
    "--physics-capture",
    is_flag=True,
    default=False,
    help="启用物理引擎捕获（保存物理模拟状态）",
)
@click.option(
    "--animation-analyze",
    is_flag=True,
    default=False,
    help="启用 CSS 动画分析（选择性保留关键动画）",
)
def clone(
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
    local_server: bool,
    port: int,
    https: bool,
    api_simulation: bool,
    security_handler: bool,
    performance_optimizer: bool,
    mouse_simulation: bool,
    scroll_precision: bool,
    canvas_recording: bool,
    physics_capture: bool,
    animation_analyze: bool,
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
        local_server=local_server,
        server_port=port,
        enable_https=https,
        api_simulation=api_simulation,
        enable_security_handler=security_handler,
        enable_performance_optimizer=performance_optimizer,
        # 动画相关参数
        enable_mouse_simulation=mouse_simulation,
        enable_scroll_precision=scroll_precision,
        enable_canvas_recording=canvas_recording,
        enable_physics_capture=physics_capture,
        enable_animation_analyze=animation_analyze,
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


@main.command(name="serve", help="启动本地 HTTP 服务器")
@click.argument("output_dir", default="./webthief_output")
@click.option(
    "-p", "--port",
    default=8080,
    type=int,
    help="服务器端口 (默认: 8080)",
    show_default=True,
)
@click.option(
    "--host",
    default="127.0.0.1",
    help="服务器主机地址 (默认: 127.0.0.1)",
    show_default=True,
)
@click.option(
    "--no-browser",
    is_flag=True,
    default=False,
    help="不自动打开浏览器",
)
@click.option(
    "--no-cors",
    is_flag=True,
    default=False,
    help="禁用 CORS 支持",
)
def serve(
    output_dir: str,
    port: int,
    host: str,
    no_browser: bool,
    no_cors: bool,
) -> None:
    """
    启动本地 HTTP 服务器，用于预览克隆的网站。

    OUTPUT_DIR: 要服务的目录路径 (默认: ./webthief_output)
    """
    # 验证目录是否存在
    root_path = Path(output_dir).resolve()
    if not root_path.exists():
        console.print(f"[red]✗ 目录不存在: {root_path}[/]")
        console.print("[dim]提示: 请先使用 'webthief clone' 命令克隆网站[/]")
        sys.exit(1)

    if not root_path.is_dir():
        console.print(f"[red]✗ 路径不是目录: {root_path}[/]")
        sys.exit(1)

    # 创建服务器配置
    config = ServerConfig(
        host=host,
        port=port,
        root_dir=str(root_path),
        open_browser=not no_browser,
        cors_enabled=not no_cors,
        log_requests=True,
    )

    # 创建并启动服务器
    server = ServerManager(config)

    try:
        # Windows 需要特殊的事件循环策略
        if sys.platform == "win32":
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

        server.run()

    except KeyboardInterrupt:
        console.print("\n[dim]收到中断信号...[/]")
    except Exception as e:
        console.print(f"\n[bold red]✗ 服务器错误: {e}[/]")
        sys.exit(1)


if __name__ == "__main__":
    main()
