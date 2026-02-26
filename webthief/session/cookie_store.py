"""
Cookie 加密存储模块

提供 Cookie 的安全存储和加载功能。
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from cryptography.fernet import Fernet, InvalidToken
from rich.console import Console

console = Console()


@dataclass
class CookieData:
    """Cookie 数据结构（与 Playwright 兼容）"""
    name: str
    value: str
    domain: str
    path: str = "/"
    expires: float = -1
    http_only: bool = False
    secure: bool = False
    same_site: str = "Lax"

    def is_expired(self) -> bool:
        if self.expires == -1:
            return False
        return datetime.now().timestamp() > self.expires

    def to_playwright_format(self) -> dict[str, Any]:
        result = {
            "name": self.name, "value": self.value,
            "domain": self.domain, "path": self.path,
            "httpOnly": self.http_only, "secure": self.secure,
            "sameSite": self.same_site,
        }
        if self.expires != -1:
            result["expires"] = self.expires
        return result

    @classmethod
    def from_playwright_format(cls, data: dict[str, Any]) -> "CookieData":
        return cls(
            name=data.get("name", ""), value=data.get("value", ""),
            domain=data.get("domain", ""), path=data.get("path", "/"),
            expires=data.get("expires", -1), http_only=data.get("httpOnly", False),
            secure=data.get("secure", False), same_site=data.get("sameSite", "Lax"),
        )


class CookieStore:
    """Cookie 加密存储管理器"""

    def __init__(self, key_file: str | Path | None = None, store_dir: str | Path | None = None):
        base_dir = Path.home() / ".webthief"
        self.key_file = Path(key_file) if key_file else (base_dir / "cookie.key")
        self.store_dir = Path(store_dir) if store_dir else (base_dir / "cookies")
        self._fernet: Fernet | None = None

        self.store_dir.mkdir(parents=True, exist_ok=True)
        self.key_file.parent.mkdir(parents=True, exist_ok=True)

    def _get_fernet(self) -> Fernet:
        if self._fernet is None:
            key = self._get_or_create_key()
            self._fernet = Fernet(key)
        return self._fernet

    def _get_or_create_key(self) -> bytes:
        if self.key_file.exists():
            return self.key_file.read_bytes()
        key = Fernet.generate_key()
        self.key_file.write_bytes(key)
        console.print(f"[dim]🔐 已生成新的加密密钥: {self.key_file}[/]")
        return key

    def _get_store_path(self, domain: str) -> Path:
        safe_domain = domain.replace(":", "_").replace("/", "_")
        return self.store_dir / f"{safe_domain}.cookies.enc"

    def save(self, domain: str, cookies: list[dict[str, Any]]) -> bool:
        """保存 Cookie 到加密文件"""
        store_path = self._get_store_path(domain)

        try:
            valid_cookies = [
                c for c in cookies
                if not CookieData.from_playwright_format(c).is_expired()
            ]

            store_data = {
                "version": "1.0",
                "updated_at": datetime.now().isoformat(),
                "cookies": valid_cookies,
            }

            fernet = self._get_fernet()
            payload = json.dumps(store_data, ensure_ascii=False).encode("utf-8")
            ciphertext = fernet.encrypt(payload)
            store_path.write_bytes(ciphertext)

            console.print(f"[green]✓ 已保存 {len(valid_cookies)} 个 Cookie: {domain}[/]")
            return True

        except Exception as e:
            console.print(f"[red]✗ Cookie 保存失败: {e}[/]")
            return False

    def load(self, domain: str) -> list[dict[str, Any]]:
        """从加密文件加载 Cookie"""
        store_path = self._get_store_path(domain)

        if not store_path.exists():
            return []

        try:
            fernet = self._get_fernet()
            ciphertext = store_path.read_bytes()
            plaintext = fernet.decrypt(ciphertext)
            data = json.loads(plaintext.decode("utf-8"))

            cookies = data.get("cookies", [])
            valid_cookies = [
                c for c in cookies
                if not CookieData.from_playwright_format(c).is_expired()
            ]

            console.print(f"[green]✓ 已加载 {len(valid_cookies)} 个 Cookie: {domain}[/]")
            return valid_cookies

        except InvalidToken:
            console.print(f"[red]✗ Cookie 解密失败: {domain}[/]")
            return []
        except Exception as e:
            console.print(f"[red]✗ Cookie 加载失败: {e}[/]")
            return []

    def delete(self, domain: str) -> bool:
        """删除指定域名的 Cookie 存储"""
        store_path = self._get_store_path(domain)
        if not store_path.exists():
            return True
        try:
            store_path.unlink()
            console.print(f"[green]✓ 已删除 Cookie 存储: {domain}[/]")
            return True
        except Exception as e:
            console.print(f"[red]✗ Cookie 存储删除失败: {e}[/]")
            return False

    def list_domains(self) -> list[str]:
        """列出所有已存储 Cookie 的域名"""
        domains = []
        for file_path in self.store_dir.glob("*.cookies.enc"):
            domain = file_path.stem.replace("_cookies", "").replace("_", ":")
            domains.append(domain)
        return sorted(domains)

    def export_to_json(self, domain: str, output_path: str | Path) -> bool:
        """导出 Cookie 为 JSON 文件"""
        cookies = self.load(domain)
        if not cookies:
            return False
        try:
            output_file = Path(output_path)
            output_file.write_text(json.dumps(cookies, indent=2, ensure_ascii=False), encoding="utf-8")
            console.print(f"[green]✓ 已导出 Cookie 到: {output_file}[/]")
            return True
        except Exception as e:
            console.print(f"[red]✗ Cookie 导出失败: {e}[/]")
            return False

    def import_from_json(self, domain: str, input_path: str | Path) -> bool:
        """从 JSON 文件导入 Cookie"""
        try:
            input_file = Path(input_path)
            content = input_file.read_text(encoding="utf-8")
            cookies = json.loads(content)
            if not isinstance(cookies, list):
                console.print("[red]✗ 无效的 Cookie 格式[/]")
                return False
            return self.save(domain, cookies)
        except Exception as e:
            console.print(f"[red]✗ Cookie 导入失败: {e}[/]")
            return False
