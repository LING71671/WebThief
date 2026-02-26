"""
LocalStorage / SessionStorage 管理模块

提供浏览器存储的持久化管理。
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


class LocalStorageManager:
    """LocalStorage / SessionStorage 加密存储管理器"""

    def __init__(self, key_file: str | Path | None = None, store_dir: str | Path | None = None):
        base_dir = Path.home() / ".webthief"
        self.key_file = Path(key_file) if key_file else (base_dir / "storage.key")
        self.store_dir = Path(store_dir) if store_dir else (base_dir / "storage")
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
        console.print(f"[dim]🔐 已生成新的存储加密密钥: {self.key_file}[/]")
        return key

    def _get_store_path(self, origin: str, storage_type: str = "local") -> Path:
        safe_origin = origin.replace("://", "_").replace("/", "_").replace(":", "_")
        return self.store_dir / f"{safe_origin}.{storage_type}.enc"

    def save(self, origin: str, storage_data: dict[str, str], storage_type: str = "local") -> bool:
        """保存存储数据到加密文件"""
        store_path = self._get_store_path(origin, storage_type)

        try:
            store_data = {
                "version": "1.0",
                "origin": origin,
                "storage_type": storage_type,
                "updated_at": datetime.now().isoformat(),
                "entries": list(storage_data.items()),
            }

            fernet = self._get_fernet()
            payload = json.dumps(store_data, ensure_ascii=False).encode("utf-8")
            ciphertext = fernet.encrypt(payload)
            store_path.write_bytes(ciphertext)

            console.print(f"[green]✓ 已保存 {len(storage_data)} 个 {storage_type}Storage 条目: {origin}[/]")
            return True

        except Exception as e:
            console.print(f"[red]✗ 存储数据保存失败: {e}[/]")
            return False

    def load(self, origin: str, storage_type: str = "local") -> dict[str, str]:
        """从加密文件加载存储数据"""
        store_path = self._get_store_path(origin, storage_type)

        if not store_path.exists():
            return {}

        try:
            fernet = self._get_fernet()
            ciphertext = store_path.read_bytes()
            plaintext = fernet.decrypt(ciphertext)
            data = json.loads(plaintext.decode("utf-8"))

            entries = data.get("entries", [])
            result = dict(entries)

            console.print(f"[green]✓ 已加载 {len(result)} 个 {storage_type}Storage 条目: {origin}[/]")
            return result

        except InvalidToken:
            console.print(f"[red]✗ 存储数据解密失败: {origin}[/]")
            return {}
        except Exception as e:
            console.print(f"[red]✗ 存储数据加载失败: {e}[/]")
            return {}

    def delete(self, origin: str, storage_type: str = "local") -> bool:
        """删除指定源的存储数据"""
        store_path = self._get_store_path(origin, storage_type)
        if not store_path.exists():
            return True
        try:
            store_path.unlink()
            console.print(f"[green]✓ 已删除 {storage_type}Storage 存储: {origin}[/]")
            return True
        except Exception as e:
            console.print(f"[red]✗ 存储数据删除失败: {e}[/]")
            return False

    def list_origins(self) -> list[str]:
        """列出所有已存储的源地址"""
        origins = set()
        for file_path in self.store_dir.glob("*.enc"):
            parts = file_path.stem.rsplit(".", 1)
            if parts:
                safe_origin = parts[0]
                origin = safe_origin.replace("_https_", "https://").replace("_http_", "http://")
                origins.add(origin)
        return sorted(origins)

    async def extract_from_page(self, page: Any, storage_type: str = "local") -> dict[str, str]:
        """从 Playwright 页面提取存储数据"""
        try:
            if storage_type == "local":
                script = """
                () => {
                    const data = {};
                    for (let i = 0; i < localStorage.length; i++) {
                        const key = localStorage.key(i);
                        data[key] = localStorage.getItem(key);
                    }
                    return data;
                }
                """
            else:
                script = """
                () => {
                    const data = {};
                    for (let i = 0; i < sessionStorage.length; i++) {
                        const key = sessionStorage.key(i);
                        data[key] = sessionStorage.getItem(key);
                    }
                    return data;
                }
                """

            data = await page.evaluate(script)
            return data if isinstance(data, dict) else {}

        except Exception as e:
            console.print(f"[yellow]⚠ 从页面提取存储数据失败: {e}[/]")
            return {}

    async def inject_to_page(self, page: Any, storage_data: dict[str, str], storage_type: str = "local") -> bool:
        """将存储数据注入到 Playwright 页面"""
        try:
            if storage_type == "local":
                script = """
                (entries) => {
                    entries.forEach(([key, value]) => {
                        localStorage.setItem(key, value);
                    });
                }
                """
            else:
                script = """
                (entries) => {
                    entries.forEach(([key, value]) => {
                        sessionStorage.setItem(key, value);
                    });
                }
                """

            await page.evaluate(script, list(storage_data.items()))
            console.print(f"[green]✓ 已注入 {len(storage_data)} 个 {storage_type}Storage 条目[/]")
            return True

        except Exception as e:
            console.print(f"[red]✗ 存储数据注入失败: {e}[/]")
            return False

    def merge_storage(self, origin: str, new_data: dict[str, str], storage_type: str = "local") -> bool:
        """合并新数据到现有存储"""
        existing = self.load(origin, storage_type)
        existing.update(new_data)
        return self.save(origin, existing, storage_type)
