"""
CSP (Content Security Policy) 分析器

解析和分析网站的 CSP 规则。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse

from rich.console import Console

console = Console()


@dataclass
class CSPAnalysisResult:
    """CSP 分析结果"""
    original_policy: str = ""
    has_strict_csp: bool = False
    allows_inline_scripts: bool = False
    allows_inline_styles: bool = False
    allows_eval: bool = False
    allowed_sources: dict[str, list[str]] = field(default_factory=dict)
    recommendations: list[str] = field(default_factory=list)
    local_compatible_policy: str = ""


class CSPAnalyzer:
    """CSP 分析器"""

    def __init__(self):
        self.result: CSPAnalysisResult = CSPAnalysisResult()

    def parse(self, csp_string: str) -> CSPAnalysisResult:
        """解析 CSP 策略字符串"""
        self.result = CSPAnalysisResult(original_policy=csp_string)

        if not csp_string or not csp_string.strip():
            return self.result

        directive_parts = csp_string.strip().split(";")

        for part in directive_parts:
            part = part.strip()
            if not part:
                continue

            tokens = part.split()
            if not tokens:
                continue

            directive_name = tokens[0].lower()
            directive_values = tokens[1:] if len(tokens) > 1 else []
            self.result.allowed_sources[directive_name] = directive_values

        self._analyze_policy_features()
        self._generate_local_compatible_policy()
        self._generate_recommendations()

        return self.result

    def parse_from_headers(self, headers: dict[str, str]) -> CSPAnalysisResult:
        """从 HTTP 响应头解析 CSP 策略"""
        csp_header = headers.get("content-security-policy", "")
        csp_report_only = headers.get("content-security-policy-report-only", "")
        csp_string = csp_header or csp_report_only
        return self.parse(csp_string)

    def parse_from_html(self, html: str) -> CSPAnalysisResult:
        """从 HTML 内容中提取并解析 CSP 策略"""
        pattern = r'<meta\s+http-equiv=["\']?Content-Security-Policy["\']?\s+content=["\']([^"\']+)["\']'
        match = re.search(pattern, html, re.IGNORECASE)

        if match:
            return self.parse(match.group(1))

        return CSPAnalysisResult()

    def _analyze_policy_features(self) -> None:
        """分析 CSP 策略的特性"""
        script_src = self.result.allowed_sources.get("script-src", [])
        style_src = self.result.allowed_sources.get("style-src", [])
        default_src = self.result.allowed_sources.get("default-src", [])

        self.result.allows_inline_scripts = "'unsafe-inline'" in script_src or "'unsafe-inline'" in default_src
        self.result.allows_inline_styles = "'unsafe-inline'" in style_src or "'unsafe-inline'" in default_src
        self.result.allows_eval = "'unsafe-eval'" in script_src or "'unsafe-eval'" in default_src

        has_strict_default = "'none'" in default_src or "'self'" in default_src
        has_strict_script = "'self'" in script_src and "'unsafe-inline'" not in script_src
        self.result.has_strict_csp = has_strict_default or has_strict_script

    def _generate_local_compatible_policy(self) -> None:
        """生成兼容本地服务器的 CSP 策略"""
        local_sources = [
            "'self'", "'unsafe-inline'", "'unsafe-eval'",
            "data:", "blob:", "http://localhost:*", "http://127.0.0.1:*", "file:",
        ]

        new_directives = []

        for directive_name, values in self.result.allowed_sources.items():
            if directive_name in ("report-uri", "report-to"):
                continue
            new_values = list(set(values + local_sources))
            new_values = [
                v for v in new_values
                if not v.startswith("https://") and not v.startswith("http://")
                or "localhost" in v or "127.0.0.1" in v
            ]
            new_directives.append(f"{directive_name} {' '.join(new_values)}")

        if "default-src" not in self.result.allowed_sources:
            new_directives.append(f"default-src {' '.join(local_sources)}")

        self.result.local_compatible_policy = "; ".join(new_directives)

    def _generate_recommendations(self) -> None:
        """生成安全建议"""
        if not self.result.allowed_sources:
            self.result.recommendations.append("未检测到 CSP 策略")
            return

        if self.result.allows_inline_scripts:
            self.result.recommendations.append("允许内联脚本，存在 XSS 风险")

        if self.result.allows_eval:
            self.result.recommendations.append("允许 eval，存在代码注入风险")

        if not self.result.has_strict_csp:
            self.result.recommendations.append("CSP 策略较宽松")

    def get_blocked_resources(self, resource_url: str, resource_type: str) -> bool:
        """检查资源是否被 CSP 阻止"""
        if not self.result.allowed_sources:
            return False

        directive_name = self._get_directive_for_type(resource_type)
        allowed = self._get_allowed_sources(directive_name)

        if "'none'" in allowed:
            return True

        if "'self'" in allowed or "'*'" in allowed:
            return False

        return self._check_url_against_sources(resource_url, allowed)

    def _get_directive_for_type(self, resource_type: str) -> str:
        """获取资源类型对应的指令名"""
        type_to_directive = {
            "script": "script-src", "style": "style-src", "img": "img-src",
            "connect": "connect-src", "font": "font-src", "media": "media-src",
            "frame": "frame-src",
        }
        return type_to_directive.get(resource_type, "default-src")

    def _get_allowed_sources(self, directive_name: str) -> list[str]:
        """获取允许的源列表"""
        return self.result.allowed_sources.get(
            directive_name,
            self.result.allowed_sources.get("default-src", [])
        )

    def _check_url_against_sources(self, resource_url: str, allowed: list[str]) -> bool:
        """检查 URL 是否匹配允许的源"""
        try:
            parsed = urlparse(resource_url)
            origin = f"{parsed.scheme}://{parsed.netloc}"

            for source in allowed:
                if source in ("'self'", "'unsafe-inline'", "'unsafe-eval'", "'none'"):
                    continue
                if source == "*" or source == origin:
                    return False
                if source.endswith("*") and origin.startswith(source[:-1]):
                    return False
        except Exception:
            pass

        return True

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式"""
        return {
            "original_policy": self.result.original_policy,
            "has_strict_csp": self.result.has_strict_csp,
            "allows_inline_scripts": self.result.allows_inline_scripts,
            "allows_inline_styles": self.result.allows_inline_styles,
            "allows_eval": self.result.allows_eval,
            "allowed_sources": self.result.allowed_sources,
            "recommendations": self.result.recommendations,
            "local_compatible_policy": self.result.local_compatible_policy,
        }
