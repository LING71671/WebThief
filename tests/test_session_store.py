from pathlib import Path

from webthief.session_store import SessionStore


def test_session_store_encrypt_roundtrip(tmp_path: Path):
    key_file = tmp_path / "session.key"
    sessions_dir = tmp_path / "sessions"
    store = SessionStore(key_file=key_file, sessions_dir=sessions_dir)

    payload = {"cookies": [{"name": "sid", "value": "abc"}], "origins": []}
    store.save("example.com", payload)
    loaded = store.load("example.com")
    assert loaded == payload


def test_session_store_bad_key_fallback(tmp_path: Path):
    key_file = tmp_path / "session.key"
    sessions_dir = tmp_path / "sessions"
    store = SessionStore(key_file=key_file, sessions_dir=sessions_dir)

    payload = {"cookies": [{"name": "sid", "value": "abc"}], "origins": []}
    store.save("example.com", payload)

    # 破坏密钥后加载应返回 None（不抛异常）
    key_file.write_bytes(b"not-a-valid-fernet-key")
    loaded = store.load("example.com")
    assert loaded is None

