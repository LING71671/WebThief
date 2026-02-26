"""
会话缓存模块：
- 使用 Fernet 加密存储 Playwright storageState
- 默认路径: ~/.webthief/sessions/{host}.state.enc
"""

from __future__ import annotations

import json
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken
from rich.console import Console

console = Console()


class SessionStore:
    """加密会话存储"""

    def __init__(
        self,
        key_file: str | Path | None = None,
        sessions_dir: str | Path | None = None,
    ):
        base_dir = Path.home() / ".webthief"
        self.key_file = Path(key_file) if key_file else (base_dir / "session.key")
        self.sessions_dir = Path(sessions_dir) if sessions_dir else (base_dir / "sessions")
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        self.key_file.parent.mkdir(parents=True, exist_ok=True)

    def _get_or_create_key(self) -> bytes:
        if self.key_file.exists():
            return self.key_file.read_bytes()
        key = Fernet.generate_key()
        self.key_file.write_bytes(key)
        return key

    def get_session_path(self, host: str, custom_path: str | Path | None = None) -> Path:
        if custom_path:
            return Path(custom_path)
        safe_host = host.replace(":", "_")
        return self.sessions_dir / f"{safe_host}.state.enc"

    def load(self, host: str, custom_path: str | Path | None = None) -> dict | None:
        session_path = self.get_session_path(host, custom_path)
        if not session_path.exists():
            return None

        try:
            fernet = Fernet(self._get_or_create_key())
            ciphertext = session_path.read_bytes()
            plaintext = fernet.decrypt(ciphertext)
            data = json.loads(plaintext.decode("utf-8"))
            if isinstance(data, dict):
                return data
        except InvalidToken:
            console.print("[yellow]⚠ 会话缓存解密失败，将回退到人工认证[/]")
        except Exception as e:
            console.print(f"[yellow]⚠ 会话缓存读取失败: {e}[/]")
        return None

    def save(self, host: str, storage_state: dict, custom_path: str | Path | None = None) -> None:
        session_path = self.get_session_path(host, custom_path)
        try:
            fernet = Fernet(self._get_or_create_key())
            payload = json.dumps(storage_state, ensure_ascii=False).encode("utf-8")
            ciphertext = fernet.encrypt(payload)
            session_path.parent.mkdir(parents=True, exist_ok=True)
            session_path.write_bytes(ciphertext)
            console.print(f"[dim]💾 已保存会话缓存: {session_path}[/]")
        except Exception as e:
            console.print(f"[yellow]⚠ 会话缓存保存失败: {e}[/]")
