"""
本地服务器管理器

功能：
- 管理 HTTP 服务器生命周期
- 端口自动检测与冲突处理
- 浏览器自动打开
- 静态文件服务
"""

from __future__ import annotations

import asyncio
import json
import socket
import threading
import webbrowser
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

console = Console()


class ServerStatus(Enum):
    """服务器状态枚举"""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    ERROR = "error"


@dataclass
class ServerConfig:
    """服务器配置"""
    host: str = "127.0.0.1"
    port: int = 8080
    root_dir: str = "."
    open_browser: bool = True
    browser_url: str = "/"
    cors_enabled: bool = True
    cors_origins: list[str] = field(default_factory=lambda: ["*"])
    custom_headers: dict[str, str] = field(default_factory=dict)
    log_requests: bool = True
    max_port_attempts: int = 100


class ServerManager:
    """
    本地服务器管理器
    
    使用 Python 内置 asyncio 实现异步 HTTP 服务器。
    """

    def __init__(self, config: ServerConfig | None = None):
        self.config = config or ServerConfig()
        self._status = ServerStatus.STOPPED
        self._server: asyncio.Server | None = None
        self._actual_port: int = self.config.port
        self._stop_event = asyncio.Event()
        self._request_handlers: dict[str, Callable] = {}
        self._error_message: str | None = None

    @property
    def status(self) -> ServerStatus:
        return self._status

    @property
    def actual_port(self) -> int:
        return self._actual_port

    @property
    def actual_url(self) -> str:
        return f"http://{self.config.host}:{self._actual_port}"

    @property
    def error_message(self) -> str | None:
        return self._error_message

    @staticmethod
    def is_port_available(port: int, host: str = "127.0.0.1") -> bool:
        """检查端口是否可用"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(1)
                return sock.connect_ex((host, port)) != 0
        except Exception:
            return True

    def find_available_port(self, start_port: int | None = None) -> int:
        """查找可用端口"""
        port = start_port or self.config.port
        for attempt in range(self.config.max_port_attempts):
            current_port = port + attempt
            if self.is_port_available(current_port, self.config.host):
                return current_port
        raise RuntimeError(f"无法在 {port}-{port + self.config.max_port_attempts - 1} 范围内找到可用端口")

    async def _handle_request(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        """处理 HTTP 请求"""
        try:
            request_line = await reader.readline()
            if not request_line:
                return

            try:
                request_str = request_line.decode('utf-8', errors='replace').strip()
                parts = request_str.split(' ')
                if len(parts) < 2:
                    return
                method, path = parts[0], parts[1]
            except Exception:
                return

            # 读取请求头
            headers = {}
            while True:
                line = await reader.readline()
                if not line or line == b'\r\n':
                    break
                try:
                    header_line = line.decode('utf-8', errors='replace').strip()
                    if ':' in header_line:
                        key, value = header_line.split(':', 1)
                        headers[key.strip().lower()] = value.strip()
                except Exception:
                    continue

            if self.config.log_requests:
                console.print(f"[dim]{method} {path}[/]")

            # 检查自定义路由
            handler_key = f"{method}:{path}"
            if handler_key in self._request_handlers:
                response = await self._call_handler(self._request_handlers[handler_key], method, path, headers)
                await self._send_response(writer, response)
                return

            await self._serve_static_file(writer, path)

        except asyncio.CancelledError:
            pass
        except Exception as e:
            if self.config.log_requests:
                console.print(f"[red]✗ 请求处理错误: {e}[/]")
        finally:
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass

    async def _call_handler(self, handler: Callable, method: str, path: str, headers: dict) -> tuple[int, dict, bytes]:
        """调用自定义请求处理器"""
        try:
            import inspect
            sig = inspect.signature(handler)
            params = {'method': method, 'path': path, 'headers': headers}
            kwargs = {k: v for k, v in params.items() if k in sig.parameters}
            result = handler(**kwargs)

            if asyncio.iscoroutine(result):
                result = await result

            if isinstance(result, tuple):
                return result
            elif isinstance(result, dict):
                return 200, {}, json.dumps(result).encode('utf-8')
            elif isinstance(result, (str, bytes)):
                body = result if isinstance(result, bytes) else result.encode('utf-8')
                return 200, {}, body
            return 200, {}, b''
        except Exception as e:
            return 500, {}, f"Handler Error: {e}".encode('utf-8')

    async def _serve_static_file(self, writer: asyncio.StreamWriter, path: str) -> None:
        """提供静态文件服务"""
        parsed = urlparse(path)
        file_path = parsed.path

        if '..' in file_path:
            await self._send_error_response(writer, 403, "Forbidden")
            return

        if file_path.startswith('/'):
            file_path = file_path[1:]

        if not file_path or file_path.endswith('/'):
            file_path += 'index.html'

        root_path = Path(self.config.root_dir).resolve()
        full_path = (root_path / file_path).resolve()

        try:
            full_path.relative_to(root_path)
        except ValueError:
            await self._send_error_response(writer, 403, "Forbidden")
            return

        if not full_path.exists() or not full_path.is_file():
            await self._send_error_response(writer, 404, "Not Found")
            return

        content_type = self._get_mime_type(full_path)

        try:
            content = full_path.read_bytes()
        except Exception as e:
            await self._send_error_response(writer, 500, f"Internal Server Error: {e}")
            return

        headers = {
            'Content-Type': content_type,
            'Content-Length': str(len(content)),
            'Connection': 'close'
        }

        if self.config.cors_enabled:
            headers['Access-Control-Allow-Origin'] = ', '.join(self.config.cors_origins)

        headers.update(self.config.custom_headers)
        await self._send_response(writer, (200, headers, content))

    async def _send_response(self, writer: asyncio.StreamWriter, response: tuple[int, dict, bytes]) -> None:
        """发送 HTTP 响应"""
        status_code, headers, body = response

        status_text = {
            200: 'OK', 201: 'Created', 204: 'No Content',
            301: 'Moved Permanently', 302: 'Found', 304: 'Not Modified',
            400: 'Bad Request', 401: 'Unauthorized', 403: 'Forbidden',
            404: 'Not Found', 405: 'Method Not Allowed',
            500: 'Internal Server Error', 502: 'Bad Gateway', 503: 'Service Unavailable'
        }.get(status_code, 'Unknown')

        response_lines = [f"HTTP/1.1 {status_code} {status_text}"]
        for key, value in headers.items():
            response_lines.append(f"{key}: {value}")
        response_lines.extend(["", ""])

        writer.write('\r\n'.join(response_lines).encode('utf-8'))
        writer.write(body)
        await writer.drain()

    async def _send_error_response(self, writer: asyncio.StreamWriter, status_code: int, message: str) -> None:
        """发送错误响应"""
        body = f"<html><body><h1>{status_code} - {message}</h1></body></html>".encode('utf-8')
        headers = {'Content-Type': 'text/html; charset=utf-8', 'Content-Length': str(len(body))}
        await self._send_response(writer, (status_code, headers, body))

    @staticmethod
    def _get_mime_type(file_path: Path) -> str:
        """根据文件扩展名获取 MIME 类型"""
        mime_types = {
            '.html': 'text/html; charset=utf-8', '.htm': 'text/html; charset=utf-8',
            '.css': 'text/css; charset=utf-8', '.js': 'application/javascript; charset=utf-8',
            '.mjs': 'application/javascript; charset=utf-8', '.json': 'application/json; charset=utf-8',
            '.xml': 'application/xml; charset=utf-8', '.txt': 'text/plain; charset=utf-8',
            '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
            '.gif': 'image/gif', '.svg': 'image/svg+xml', '.ico': 'image/x-icon',
            '.webp': 'image/webp', '.woff': 'font/woff', '.woff2': 'font/woff2',
            '.ttf': 'font/ttf', '.otf': 'font/otf', '.eot': 'application/vnd.ms-fontobject',
            '.mp3': 'audio/mpeg', '.mp4': 'video/mp4', '.webm': 'video/webm',
            '.ogg': 'audio/ogg', '.pdf': 'application/pdf', '.zip': 'application/zip',
            '.wasm': 'application/wasm',
        }
        return mime_types.get(file_path.suffix.lower(), 'application/octet-stream')

    def register_handler(self, method: str, path: str, handler: Callable) -> None:
        """注册自定义请求处理器"""
        self._request_handlers[f"{method.upper()}:{path}"] = handler

    def unregister_handler(self, method: str, path: str) -> bool:
        """注销自定义请求处理器"""
        key = f"{method.upper()}:{path}"
        if key in self._request_handlers:
            del self._request_handlers[key]
            return True
        return False

    async def start(self) -> bool:
        """异步启动服务器"""
        if self._status == ServerStatus.RUNNING:
            console.print("[yellow]⚠ 服务器已在运行中[/]")
            return True

        self._status = ServerStatus.STARTING
        self._error_message = None

        try:
            self._actual_port = self.find_available_port()

            self._server = await asyncio.start_server(
                self._handle_request,
                host=self.config.host,
                port=self._actual_port
            )

            self._status = ServerStatus.RUNNING
            self._stop_event.clear()
            self._print_startup_info()

            if self.config.open_browser:
                self._open_browser()

            return True

        except Exception as e:
            self._status = ServerStatus.ERROR
            self._error_message = str(e)
            console.print(f"[red]✗ 服务器启动失败: {e}[/]")
            return False

    def _print_startup_info(self) -> None:
        """打印服务器启动信息"""
        info = Text()
        info.append(f"\n🚀 HTTP 服务器已启动\n\n", style="bold green")
        info.append(f"  🌐 本地地址: ", style="white")
        info.append(f"{self.actual_url}\n", style="cyan")
        info.append(f"  📂 根目录: ", style="white")
        info.append(f"{Path(self.config.root_dir).resolve()}\n", style="cyan")
        info.append(f"\n  💡 按 Ctrl+C 停止服务器", style="dim")

        panel = Panel(info, title="[bold green]✅ 服务器运行中[/]", border_style="green", padding=(0, 2))
        console.print(panel)

    def _open_browser(self) -> None:
        """打开浏览器"""
        url = f"{self.actual_url}{self.config.browser_url}"

        def open_url():
            try:
                webbrowser.open(url)
            except Exception:
                pass

        threading.Thread(target=open_url, daemon=True).start()

    async def stop(self) -> None:
        """异步停止服务器"""
        if self._status != ServerStatus.RUNNING:
            return

        self._status = ServerStatus.STOPPING
        self._stop_event.set()

        if self._server:
            self._server.close()
            await self._server.wait_closed()
            self._server = None

        self._status = ServerStatus.STOPPED
        console.print("\n[bold yellow]🛑 服务器已停止[/]")

    def run(self) -> None:
        """同步运行服务器（阻塞）"""
        async def run_server():
            if not await self.start():
                return
            try:
                while self._status == ServerStatus.RUNNING:
                    await asyncio.sleep(0.5)
            except asyncio.CancelledError:
                pass
            finally:
                await self.stop()

        try:
            asyncio.run(run_server())
        except KeyboardInterrupt:
            console.print("\n[dim]收到中断信号...[/]")

    async def serve_forever(self) -> None:
        """异步运行服务器（阻塞）"""
        if not await self.start():
            return
        try:
            while self._status == ServerStatus.RUNNING:
                await asyncio.sleep(0.5)
        except asyncio.CancelledError:
            pass
        finally:
            await self.stop()


def create_simple_server(root_dir: str, port: int = 8080, open_browser: bool = True) -> ServerManager:
    """快速创建简单 HTTP 服务器的便捷函数"""
    config = ServerConfig(root_dir=root_dir, port=port, open_browser=open_browser)
    return ServerManager(config)
