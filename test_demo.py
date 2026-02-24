"""
WebThief v3.0 功能演示脚本
快速验证二维码拦截和 React 组件拦截功能
"""

import asyncio
import sys
from pathlib import Path

from webthief.orchestrator import Orchestrator
from rich.console import Console

console = Console()


async def demo_basic_clone():
    """演示 1: 基础克隆（不启用高级功能）"""
    console.print("\n[bold cyan]━━━ 演示 1: 基础克隆 ━━━[/]\n")
    console.print("[yellow]目标: 克隆一个简单页面，不启用高级功能[/]\n")
    
    orchestrator = Orchestrator(
        url="https://example.com",
        output_dir="./demo_output/basic",
        enable_qr_intercept=False,
        enable_react_intercept=False,
        verbose=True
    )
    
    try:
        console.print("[cyan]开始克隆...[/]")
        result_path = await orchestrator.run()
        console.print(f"\n[green]✓ 基础克隆完成[/]")
        console.print(f"[cyan]输出: {result_path}[/]")
        return True
    except Exception as e:
        console.print(f"\n[red]✗ 失败: {e}[/]")
        import traceback
        traceback.print_exc()
        return False


async def demo_qr_intercept():
    """演示 2: 二维码拦截功能"""
    console.print("\n[bold cyan]━━━ 演示 2: 二维码拦截 ━━━[/]\n")
    console.print("[yellow]目标: 测试二维码拦截器的注入和数据捕获[/]\n")
    
    orchestrator = Orchestrator(
        url="https://example.com",  # 使用简单页面测试
        output_dir="./demo_output/qr_test",
        enable_qr_intercept=True,   # 启用二维码拦截
        enable_react_intercept=False,
        extra_wait=2,
        verbose=True
    )
    
    try:
        console.print("[cyan]开始克隆（启用二维码拦截）...[/]")
        result_path = await orchestrator.run()
        console.print(f"\n[green]✓ 二维码拦截测试完成[/]")
        console.print(f"[cyan]输出: {result_path}[/]")
        
        # 检查生成的文件
        index_file = Path(result_path) / "index.html"
        if index_file.exists():
            content = index_file.read_text(encoding='utf-8')
            if 'data-webthief="qr-bridge"' in content:
                console.print("[green]  ✓ 检测到二维码桥接脚本[/]")
            if '__webthief_qr_requests' in content:
                console.print("[green]  ✓ 检测到二维码拦截代码[/]")
        
        return True
    except Exception as e:
        console.print(f"\n[red]✗ 失败: {e}[/]")
        import traceback
        traceback.print_exc()
        return False


async def demo_react_intercept():
    """演示 3: React 组件拦截功能"""
    console.print("\n[bold cyan]━━━ 演示 3: React 组件拦截 ━━━[/]\n")
    console.print("[yellow]目标: 测试 React 拦截器的注入和菜单保留[/]\n")
    
    orchestrator = Orchestrator(
        url="https://example.com",
        output_dir="./demo_output/react_test",
        enable_qr_intercept=False,
        enable_react_intercept=True,  # 启用 React 拦截
        extra_wait=2,
        verbose=True
    )
    
    try:
        console.print("[cyan]开始克隆（启用 React 拦截）...[/]")
        result_path = await orchestrator.run()
        console.print(f"\n[green]✓ React 拦截测试完成[/]")
        console.print(f"[cyan]输出: {result_path}[/]")
        
        # 检查生成的文件
        index_file = Path(result_path) / "index.html"
        if index_file.exists():
            content = index_file.read_text(encoding='utf-8')
            if 'data-webthief="menu-preservation"' in content:
                console.print("[green]  ✓ 检测到菜单保留脚本[/]")
            if 'data-webthief-frozen' in content or 'WebThief React' in content:
                console.print("[green]  ✓ 检测到 React 拦截代码[/]")
        
        return True
    except Exception as e:
        console.print(f"\n[red]✗ 失败: {e}[/]")
        import traceback
        traceback.print_exc()
        return False


async def demo_combined():
    """演示 4: 组合功能"""
    console.print("\n[bold cyan]━━━ 演示 4: 组合功能 ━━━[/]\n")
    console.print("[yellow]目标: 同时启用二维码拦截和 React 拦截[/]\n")
    
    orchestrator = Orchestrator(
        url="https://example.com",
        output_dir="./demo_output/combined",
        enable_qr_intercept=True,   # 启用二维码拦截
        enable_react_intercept=True,  # 启用 React 拦截
        extra_wait=2,
        verbose=True
    )
    
    try:
        console.print("[cyan]开始克隆（启用所有高级功能）...[/]")
        result_path = await orchestrator.run()
        console.print(f"\n[green]✓ 组合功能测试完成[/]")
        console.print(f"[cyan]输出: {result_path}[/]")
        
        # 检查生成的文件
        index_file = Path(result_path) / "index.html"
        if index_file.exists():
            content = index_file.read_text(encoding='utf-8')
            has_qr = 'data-webthief="qr-bridge"' in content
            has_react = 'data-webthief="menu-preservation"' in content
            
            if has_qr and has_react:
                console.print("[green]  ✓ 检测到所有高级功能脚本[/]")
            elif has_qr:
                console.print("[yellow]  ⚠ 仅检测到二维码脚本[/]")
            elif has_react:
                console.print("[yellow]  ⚠ 仅检测到 React 脚本[/]")
        
        return True
    except Exception as e:
        console.print(f"\n[red]✗ 失败: {e}[/]")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """运行所有演示"""
    console.print("[bold green]" + "="*60 + "[/]")
    console.print("[bold green]WebThief v3.0 功能演示[/]")
    console.print("[bold green]" + "="*60 + "[/]\n")
    
    console.print("[cyan]本演示将测试以下功能：[/]")
    console.print("  1. 基础克隆（对照组）")
    console.print("  2. 二维码拦截功能")
    console.print("  3. React 组件拦截功能")
    console.print("  4. 组合功能\n")
    
    results = []
    
    # 运行所有演示
    console.print("[yellow]开始测试...[/]\n")
    
    results.append(("基础克隆", await demo_basic_clone()))
    results.append(("二维码拦截", await demo_qr_intercept()))
    results.append(("React 拦截", await demo_react_intercept()))
    results.append(("组合功能", await demo_combined()))
    
    # 打印总结
    console.print("\n[bold green]" + "="*60 + "[/]")
    console.print("[bold green]测试总结[/]")
    console.print("[bold green]" + "="*60 + "[/]\n")
    
    for name, success in results:
        status = "[green]✓ 通过[/]" if success else "[red]✗ 失败[/]"
        console.print(f"  {name:20s} {status}")
    
    total = len(results)
    passed = sum(1 for _, s in results if s)
    
    console.print(f"\n[bold]总计: {passed}/{total} 通过[/]")
    
    if passed == total:
        console.print("\n[bold green]🎉 所有测试通过！[/]")
    else:
        console.print(f"\n[bold yellow]⚠ {total - passed} 个测试失败[/]")
    
    console.print("\n[cyan]输出目录: ./demo_output/[/]")
    console.print("[dim]提示: 打开各个目录下的 index.html 查看克隆结果[/]\n")


if __name__ == "__main__":
    # Windows 需要特殊的事件循环策略
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("\n[yellow]⚠ 用户中断[/]")
    except Exception as e:
        console.print(f"\n[red]✗ 发生错误: {e}[/]")
        import traceback
        traceback.print_exc()
