"""
WebThief 高级功能测试示例
演示如何使用二维码拦截和 React 组件拦截功能
"""

import asyncio
import sys
from pathlib import Path

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from webthief.orchestrator import Orchestrator
from rich.console import Console

console = Console()


async def test_qr_intercept():
    """
    测试二维码拦截功能
    适用于：Steam 登录、微信扫码等场景
    """
    console.print("\n[bold cyan]━━━ 测试 1: 二维码拦截 ━━━[/]\n")
    
    orchestrator = Orchestrator(
        url="https://store.steampowered.com/login/",  # Steam 登录页
        output_dir="./test_output/qr_test",
        enable_qr_intercept=True,      # 启用二维码拦截
        enable_react_intercept=False,  # 禁用 React 拦截（专注测试二维码）
        extra_wait=5,                  # 等待二维码加载
        verbose=True
    )
    
    try:
        result_path = await orchestrator.run()
        console.print(f"\n[green]✓ 二维码拦截测试完成[/]")
        console.print(f"[cyan]输出目录: {result_path}[/]")
        console.print(f"[yellow]提示: 打开 index.html 查看克隆的二维码是否可以刷新[/]")
    except Exception as e:
        console.print(f"\n[red]✗ 测试失败: {e}[/]")


async def test_react_intercept():
    """
    测试 React 组件拦截功能
    适用于：复杂菜单、下拉导航等场景
    """
    console.print("\n[bold cyan]━━━ 测试 2: React 组件拦截 ━━━[/]\n")
    
    orchestrator = Orchestrator(
        url="https://store.steampowered.com/",  # Steam 商店首页
        output_dir="./test_output/react_test",
        enable_qr_intercept=False,     # 禁用二维码拦截
        enable_react_intercept=True,   # 启用 React 拦截
        extra_wait=5,                  # 等待菜单加载
        verbose=True
    )
    
    try:
        result_path = await orchestrator.run()
        console.print(f"\n[green]✓ React 拦截测试完成[/]")
        console.print(f"[cyan]输出目录: {result_path}[/]")
        console.print(f"[yellow]提示: 打开 index.html 查看菜单是否可以悬停展开[/]")
    except Exception as e:
        console.print(f"\n[red]✗ 测试失败: {e}[/]")


async def test_both_features():
    """
    测试两个功能同时启用
    适用于：同时需要二维码和复杂菜单的页面
    """
    console.print("\n[bold cyan]━━━ 测试 3: 二维码 + React 拦截 ━━━[/]\n")
    
    orchestrator = Orchestrator(
        url="https://store.steampowered.com/login/",
        output_dir="./test_output/combined_test",
        enable_qr_intercept=True,      # 启用二维码拦截
        enable_react_intercept=True,   # 启用 React 拦截
        extra_wait=5,
        verbose=True
    )
    
    try:
        result_path = await orchestrator.run()
        console.print(f"\n[green]✓ 组合功能测试完成[/]")
        console.print(f"[cyan]输出目录: {result_path}[/]")
        console.print(f"[yellow]提示: 打开 index.html 查看二维码和菜单是否都正常工作[/]")
    except Exception as e:
        console.print(f"\n[red]✗ 测试失败: {e}[/]")


async def main():
    """运行所有测试"""
    console.print("[bold green]WebThief 高级功能测试套件[/]\n")
    
    # 选择要运行的测试
    console.print("请选择测试:")
    console.print("1. 二维码拦截测试")
    console.print("2. React 组件拦截测试")
    console.print("3. 组合功能测试")
    console.print("4. 运行所有测试")
    
    choice = input("\n输入选项 (1-4): ").strip()
    
    if choice == "1":
        await test_qr_intercept()
    elif choice == "2":
        await test_react_intercept()
    elif choice == "3":
        await test_both_features()
    elif choice == "4":
        await test_qr_intercept()
        await test_react_intercept()
        await test_both_features()
    else:
        console.print("[red]无效选项[/]")
        return
    
    console.print("\n[bold green]所有测试完成！[/]")


if __name__ == "__main__":
    # Windows 需要特殊的事件循环策略
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    asyncio.run(main())
