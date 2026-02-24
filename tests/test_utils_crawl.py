from webthief.utils import make_relative_path, normalize_crawl_url, url_to_local_page_path


def test_normalize_crawl_url_strip_tracking_and_fragment():
    url = "https://example.com/path?a=1&utm_source=x&fbclid=y#section"
    assert normalize_crawl_url(url) == "https://example.com/path?a=1"


def test_url_to_local_page_path_root_and_nested():
    assert url_to_local_page_path("https://example.com/") == "index.html"
    assert url_to_local_page_path("https://example.com/a/b") == "a/b/index.html"


def test_url_to_local_page_path_with_query_hash():
    path = url_to_local_page_path("https://example.com/docs?p=1")
    assert path.startswith("docs/index_")
    assert path.endswith(".html")


def test_make_relative_path_page_links():
    src = "docs/index.html"
    dst = "docs/guide/index.html"
    assert make_relative_path(src, dst) == "guide/index.html"

