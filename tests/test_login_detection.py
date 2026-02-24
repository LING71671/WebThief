from webthief.renderer import Renderer


def test_login_like_by_status():
    assert Renderer.is_login_like("https://example.com/private", 401, False)
    assert Renderer.is_login_like("https://example.com/private", 403, False)


def test_login_like_by_url_keyword():
    assert Renderer.is_login_like("https://example.com/login", 200, False)
    assert Renderer.is_login_like("https://example.com/auth/callback", 200, False)


def test_login_like_by_dom_hint():
    assert Renderer.is_login_like("https://example.com/home", 200, True)
    assert not Renderer.is_login_like("https://example.com/home", 200, False)


def test_has_auth_cookie():
    cookies = [{"name": "sessionid", "value": "x"}]
    assert Renderer.has_auth_cookie(cookies)
    assert not Renderer.has_auth_cookie([{"name": "lang", "value": "zh-CN"}])

