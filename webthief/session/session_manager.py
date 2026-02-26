"""
会话管理器主模块

提供会话管理功能：
- Cookie 和 Storage 统一管理
- 会话持久化与恢复
- 与 Playwright 浏览器上下文集成
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from rich.console import Console

from webthief.session.cookie_store import CookieStore
from webthief.session.local_storage_manager import LocalStorageManager

console = Console()


@dataclass
class SessionMetadata:
    """会话元数据"""
    session_id: str
    name: str
    origin: str
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id, "name": self.name,
            "origin": self.origin, "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SessionMetadata":
        return cls(
            session_id=data.get("session_id", ""), name=data.get("name", ""),
            origin=data.get("origin", ""), created_at=data.get("created_at", datetime.now().isoformat()),
            updated_at=data.get("updated_at", datetime.now().isoformat()),
        )


@dataclass
class SessionData:
    """完整会话数据"""
    metadata: SessionMetadata
    cookies: list[dict[str, Any]] = field(default_factory=list)
    local_storage: dict[str, str] = field(default_factory=dict)
    session_storage: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "metadata": self.metadata.to_dict(),
            "cookies": self.cookies,
            "local_storage": self.local_storage,
            "session_storage": self.session_storage,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SessionData":
        metadata = SessionMetadata.from_dict(data.get("metadata", {}))
        return cls(
            metadata=metadata,
            cookies=data.get("cookies", []),
            local_storage=data.get("local_storage", {}),
            session_storage=data.get("session_storage", {}),
        )


class SessionManager:
    """会话管理器"""

    def __init__(self, base_dir: str | Path | None = None):
        self.base_dir = Path(base_dir) if base_dir else (Path.home() / ".webthief")
        self.cookie_store = CookieStore(store_dir=self.base_dir / "cookies")
        self.storage_manager = LocalStorageManager(store_dir=self.base_dir / "storage")
        self.index_file = self.base_dir / "sessions" / "index.json"
        self.sessions_dir = self.base_dir / "sessions"
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        self._session_index: dict[str, SessionMetadata] = {}
        self._load_index()

    def _load_index(self) -> None:
        if not self.index_file.exists():
            return
        try:
            content = self.index_file.read_text(encoding="utf-8")
            data = json.loads(content)
            for session_id, meta_dict in data.items():
                self._session_index[session_id] = SessionMetadata.from_dict(meta_dict)
        except Exception as e:
            console.print(f"[yellow]⚠ 会话索引加载失败: {e}[/]")

    def _save_index(self) -> None:
        try:
            data = {sid: meta.to_dict() for sid, meta in self._session_index.items()}
            self.index_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception as e:
            console.print(f"[red]✗ 会话索引保存失败: {e}[/]")

    def _get_session_file(self, session_id: str) -> Path:
        return self.sessions_dir / f"{session_id}.json"

    def _generate_session_id(self, origin: str) -> str:
        import hashlib
        import time
        timestamp = str(time.time())
        return hashlib.md5(f"{origin}_{timestamp}".encode("utf-8")).hexdigest()[:12]

    def _extract_origin(self, url: str) -> str:
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}"

    def _extract_domain(self, url: str) -> str:
        parsed = urlparse(url)
        return parsed.netloc

    def create_session(self, name: str, origin: str, description: str = "") -> SessionMetadata:
        """创建新会话"""
        session_id = self._generate_session_id(origin)
        metadata = SessionMetadata(
            session_id=session_id,
            name=name,
            origin=self._extract_origin(origin),
        )
        self._session_index[session_id] = metadata
        self._save_index()
        console.print(f"[green]✓ 已创建会话: {name} ({session_id})[/]")
        return metadata

    def get_session(self, session_id: str) -> SessionData | None:
        """获取完整会话数据"""
        if session_id not in self._session_index:
            return None

        session_file = self._get_session_file(session_id)
        if not session_file.exists():
            return SessionData(metadata=self._session_index[session_id])

        try:
            content = session_file.read_text(encoding="utf-8")
            data = json.loads(content)
            return SessionData.from_dict(data)
        except Exception as e:
            console.print(f"[red]✗ 会话数据加载失败: {e}[/]")
            return None

    def list_sessions(self) -> list[SessionMetadata]:
        """列出所有会话"""
        sessions = list(self._session_index.values())
        sessions.sort(key=lambda x: x.updated_at, reverse=True)
        return sessions

    def delete_session(self, session_id: str) -> bool:
        """删除会话"""
        if session_id not in self._session_index:
            return False

        try:
            session_file = self._get_session_file(session_id)
            if session_file.exists():
                session_file.unlink()
            meta = self._session_index.pop(session_id)
            self._save_index()
            console.print(f"[green]✓ 已删除会话: {meta.name} ({session_id})[/]")
            return True
        except Exception as e:
            console.print(f"[red]✗ 会话删除失败: {e}[/]")
            return False

    async def save_session(
        self,
        context: Any,
        name: str,
        origin: str,
        session_id: str | None = None,
    ) -> SessionMetadata | None:
        """从 Playwright 上下文保存会话"""
        try:
            if session_id and session_id in self._session_index:
                metadata = self._session_index[session_id]
                metadata.updated_at = datetime.now().isoformat()
            else:
                metadata = self.create_session(name=name, origin=origin)

            storage_state = await context.storage_state()
            cookies = storage_state.get("cookies", [])

            local_storage = {}
            session_storage = {}

            pages = context.pages
            if pages:
                page = pages[0]
                try:
                    local_storage = await self.storage_manager.extract_from_page(page, "local")
                    session_storage = await self.storage_manager.extract_from_page(page, "session")
                except Exception as e:
                    console.print(f"[yellow]⚠ Storage 提取失败: {e}[/]")

            session_data = SessionData(
                metadata=metadata,
                cookies=cookies,
                local_storage=local_storage,
                session_storage=session_storage,
            )

            session_file = self._get_session_file(metadata.session_id)
            session_file.write_text(json.dumps(session_data.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")

            domain = self._extract_domain(origin)
            self.cookie_store.save(domain, cookies)

            if local_storage:
                self.storage_manager.save(origin, local_storage, "local")
            if session_storage:
                self.storage_manager.save(origin, session_storage, "session")

            metadata.updated_at = datetime.now().isoformat()
            self._save_index()

            console.print(f"[green]✓ 已保存会话: {name} ({len(cookies)} Cookie, {len(local_storage)} LocalStorage)[/]")
            return metadata

        except Exception as e:
            console.print(f"[red]✗ 会话保存失败: {e}[/]")
            return None

    async def load_session(self, context: Any, session_id: str) -> bool:
        """加载会话到 Playwright 上下文"""
        session_data = self.get_session(session_id)
        if session_data is None:
            console.print(f"[red]✗ 会话不存在: {session_id}[/]")
            return False

        try:
            if session_data.cookies:
                await context.add_cookies(session_data.cookies)

            pages = context.pages
            if pages:
                page = pages[0]
                if session_data.local_storage:
                    await self.storage_manager.inject_to_page(page, session_data.local_storage, "local")
                if session_data.session_storage:
                    await self.storage_manager.inject_to_page(page, session_data.session_storage, "session")

            session_data.metadata.updated_at = datetime.now().isoformat()
            self._session_index[session_id] = session_data.metadata
            self._save_index()

            console.print(f"[green]✓ 已加载会话: {session_data.metadata.name} ({len(session_data.cookies)} Cookie)[/]")
            return True

        except Exception as e:
            console.print(f"[red]✗ 会话加载失败: {e}[/]")
            return False

    async def apply_to_context(self, context: Any, origin: str) -> bool:
        """根据 origin 自动查找并应用会话"""
        extracted_origin = self._extract_origin(origin)

        for meta in self._session_index.values():
            if meta.origin == extracted_origin:
                return await self.load_session(context, meta.session_id)

        domain = self._extract_domain(origin)
        cookies = self.cookie_store.load(domain)

        if cookies:
            await context.add_cookies(cookies)
            console.print(f"[green]✓ 已从 Cookie 存储加载: {domain}[/]")
            return True

        console.print(f"[yellow]⚠ 未找到匹配的会话: {origin}[/]")
        return False

    def export_session(self, session_id: str, output_path: str | Path) -> bool:
        """导出会话到 JSON 文件"""
        session_data = self.get_session(session_id)
        if session_data is None:
            return False

        try:
            output_file = Path(output_path)
            output_file.write_text(json.dumps(session_data.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
            console.print(f"[green]✓ 已导出会话到: {output_file}[/]")
            return True
        except Exception as e:
            console.print(f"[red]✗ 会话导出失败: {e}[/]")
            return False

    def import_session(self, input_path: str | Path, new_name: str | None = None) -> SessionMetadata | None:
        """从 JSON 文件导入会话"""
        try:
            input_file = Path(input_path)
            content = input_file.read_text(encoding="utf-8")
            data = json.loads(content)

            session_data = SessionData.from_dict(data)
            new_session_id = self._generate_session_id(session_data.metadata.origin)

            session_data.metadata.session_id = new_session_id
            if new_name:
                session_data.metadata.name = new_name
            session_data.metadata.created_at = datetime.now().isoformat()
            session_data.metadata.updated_at = datetime.now().isoformat()

            session_file = self._get_session_file(new_session_id)
            session_file.write_text(json.dumps(session_data.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")

            self._session_index[new_session_id] = session_data.metadata
            self._save_index()

            console.print(f"[green]✓ 已导入会话: {session_data.metadata.name} ({new_session_id})[/]")
            return session_data.metadata

        except Exception as e:
            console.print(f"[red]✗ 会话导入失败: {e}[/]")
            return None
