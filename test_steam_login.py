"""
Steam 登录页克隆测试
测试实时二维码拦截功能
"""

import asyncio
import sys
from pathlib import Path

from webthief.orchestrator import Orchestrator
from rich.console import Console

console = Console()


async def clone_steam_login():
    """克隆 Steam 登录页（带二维码）"""
    console.print("\n[bold cyan]" + "="*70 + "[/]")
    console.print("[bold cyan]Steam 登录页克隆测试 - 实时二维码拦截[/]")
    console.print("[bold cyan]" + "="*70 + "[/]\n")
    
    console.print("[yellow]目标 URL: https://store.steampowered.com/login/[/]")
    console.print("[yellow]功能: 二维码拦截 + React 菜单拦截[/]\n")
    
    orchestrator = Orchestrator(
        url="https://store.steampowered.com/login/",
        output_dir="./steam_login_clone",
        enable_qr_intercept=True,      # 启用二维码拦截
        enable_react_intercept=True,   # 启用 React 拦截
        extra_wait=5,                  # 等待二维码加载
        concurrency=30,                # 提高并发
        verbose=True
    )
    
    try:
        console.print("[cyan]开始克隆 Steam 登录页...[/]\n")
        result_path = await orchestrator.run()
        
        console.print("\n[bold green]" + "="*70 + "[/]")
        console.print("[bold green]✓ 克隆完成！[/]")
        console.print("[bold green]" + "="*70 + "[/]\n")
        
        console.print(f"[cyan]输出目录: {result_path}[/]\n")
        
        # 检查生成的文件
        index_file = Path(result_path) / "index.html"
        if index_file.exists():
            content = index_file.read_text(encoding='utf-8', errors='ignore')
            
            console.print("[bold yellow]功能检测:[/]\n")
            
            # 检查二维码功能
            if 'data-webthief="qr-bridge"' in content:
                console.print("[green]  ✓ 二维码桥接脚本已注入[/]")
            else:
                console.print("[yellow]  ⚠ 未检测到二维码桥接脚本[/]")
            
            if '__webthief_qr_requests' in content:
                console.print("[green]  ✓ 二维码拦截代码已注入[/]")
            else:
                console.print("[yellow]  ⚠ 未检测到二维码拦截代码[/]")
            
            if 'QR_KEYWORDS' in content or 'qrcode' in content.lower():
                console.print("[green]  ✓ 检测到二维码相关代码[/]")
            
            # 检查 React 功能
            if 'data-webthief="menu-preservation"' in content:
                console.print("[green]  ✓ 菜单保留脚本已注入[/]")
            else:
                console.print("[yellow]  ⚠ 未检测到菜单保留脚本[/]")
            
            if 'WebThief React' in content or 'data-webthief-frozen' in content:
                console.print("[green]  ✓ React 拦截代码已注入[/]")
            else:
                console.print("[yellow]  ⚠ 未检测到 React 拦截代码[/]")
            
            # 检查运行时 Shim
            if 'data-webthief="shim"' in content:
                console.print("[green]  ✓ 运行时兼容层已注入[/]")
            
            console.print(f"\n[cyan]HTML 文件大小: {len(content):,} 字符[/]")
        
        # 统计资源
        assets_dir = Path(result_path) / "assets"
        if assets_dir.exists():
            file_count = sum(1 for _ in assets_dir.rglob("*") if _.is_file())
            console.print(f"[cyan]下载资源数量: {file_count} 个文件[/]")
        
        console.print("\n[bold yellow]使用说明:[/]\n")
        console.print("1. 打开输出目录: ./steam_login_clone/")
        console.print("2. 使用浏览器打开 index.html")
        console.print("3. 查看二维码是否显示")
        console.print("4. 打开浏览器控制台，输入: window.__webthief_qr_refresh()")
        console.print("5. 检查菜单是否可以悬停展开\n")
        
        console.print("[dim]注意: 由于 CORS 限制，二维码刷新功能需要在本地服务器上运行[/]")
        console.print("[dim]建议: cd steam_login_clone && python -m http.server 8000[/]\n")
        
        return True
        
    except Exception as e:
        console.print(f"\n[bold red]✗ 克隆失败: {e}[/]\n")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """主函数"""
    success = await clone_steam_login()
    
    if success:
        console.print("[bold green]🎉 测试成功完成！[/]\n")
        return 0
    else:
        console.print("[bold red]❌ 测试失败[/]\n")
        return 1


if __name__ == "__main__":
    # Windows 需要特殊的事件循环策略
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        console.print("\n[yellow]⚠ 用户中断操作[/]")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[bold red]✗ 发生错误: {e}[/]\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)
