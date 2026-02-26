"""
WebThief Parser 模块

包含解析器相关模块：
- base: Parser 主类（对外接口）
- core: 解析器核心类和配置
- html: HTML 解析入口
- extractor: HTML 资源提取
- rewriter: HTML 重写
- injector: 浏览器 API 垫片注入
- css: CSS 解析
- js: JS 解析
"""

# 从 base.py 导入 Parser 主类（解决命名冲突）
from .base import (
    Parser,
    ParseResult,
    parse_html,
    HTMLResourceExtractor,
    HTMLRewriter,
    BrowserAPIShimInjector,
    CSSUrlParser,
    CSSResourceCollector,
    CSSRewriter,
    parse_external_css,
    parse_external_js_assets,
)

# 从 core 导入配置类
from .core import ParserConfig

__all__ = [
    # 主类
    "Parser",
    # 核心类
    "ParseResult",
    "ParserConfig",
    # HTML 解析
    "parse_html",
    "HTMLResourceExtractor",
    "HTMLRewriter",
    "BrowserAPIShimInjector",
    # CSS 解析
    "CSSUrlParser",
    "CSSResourceCollector",
    "CSSRewriter",
    "parse_external_css",
    # JS 解析
    "parse_external_js_assets",
]
