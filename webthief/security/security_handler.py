"""
安全处理器

整合 CSP 分析、浏览器指纹生成功能。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from playwright.async_api import BrowserContext, Page, Response
from rich.console import Console

from ..config import get_random_ua
from .csp_analyzer import CSPAnalysisResult, CSPAnalyzer
from .fingerprint_generator import BrowserFingerprint, FingerprintGenerator

console = Console()


@dataclass
class SecurityAnalysisResult:
    """安全分析结果"""
    csp_result: CSPAnalysisResult = field(default_factory=CSPAnalysisResult)
    fingerprint: BrowserFingerprint = field(default_factory=BrowserFingerprint)
    security_score: float = 0.0
    recommendations: list[str] = field(default_factory=list)
    headers: dict[str, str] = field(default_factory=dict)


class SecurityHandler:
    """安全处理器"""

    def __init__(self, fingerprint_seed: int | None = None):
        self.csp_analyzer = CSPAnalyzer()
        self.fingerprint_generator = FingerprintGenerator(seed=fingerprint_seed)
        self.current_fingerprint: BrowserFingerprint | None = None

    def generate_fingerprint(self, browser_type: str = "chrome", device_type: str = "desktop") -> BrowserFingerprint:
        """生成浏览器指纹"""
        fingerprint = self.fingerprint_generator.generate(browser_type, device_type)
        self.current_fingerprint = fingerprint
        return fingerprint

    def rotate_fingerprint(self) -> BrowserFingerprint:
        """轮换浏览器指纹"""
        new_fingerprint = self.fingerprint_generator.rotate(self.current_fingerprint)
        self.current_fingerprint = new_fingerprint
        console.print("[cyan]🔄 浏览器指纹已轮换[/]")
        return new_fingerprint

    def get_random_user_agent(self) -> str:
        """获取随机 User-Agent"""
        return get_random_ua()

    def get_request_headers(self, base_url: str = "", custom_headers: dict[str, str] | None = None) -> dict[str, str]:
        """生成请求头"""
        headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept-Encoding": "gzip, deflate, br",
            "Cache-Control": "max-age=0",
            "Sec-Ch-Ua": '"Chromium";v="131", "Google Chrome";v="131", "Not_A Brand";v="24"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1",
            "User-Agent": self.current_fingerprint.user_agent if self.current_fingerprint else get_random_ua(),
        }

        if base_url:
            headers["Referer"] = base_url
            headers["Origin"] = base_url

        if custom_headers:
            headers.update(custom_headers)

        return headers

    def analyze_csp(self, csp_string: str) -> CSPAnalysisResult:
        """分析 CSP 策略"""
        return self.csp_analyzer.parse(csp_string)

    def analyze_csp_from_headers(self, headers: dict[str, str]) -> CSPAnalysisResult:
        """从 HTTP 响应头分析 CSP 策略"""
        return self.csp_analyzer.parse_from_headers(headers)

    def analyze_csp_from_html(self, html: str) -> CSPAnalysisResult:
        """从 HTML 内容分析 CSP 策略"""
        return self.csp_analyzer.parse_from_html(html)

    async def setup_browser_context(self, context: BrowserContext, fingerprint: BrowserFingerprint | None = None) -> None:
        """设置浏览器上下文的安全配置"""
        if fingerprint is None:
            fingerprint = self.current_fingerprint or self.generate_fingerprint()

        init_script = self.fingerprint_generator.generate_playwright_init_script(fingerprint)
        await context.add_init_script(init_script)
        console.print("[green]✓ 浏览器安全配置已应用[/]")

    def get_local_compatible_csp(self, original_csp: str) -> str:
        """获取本地兼容的 CSP 策略"""
        result = self.csp_analyzer.parse(original_csp)
        return result.local_compatible_policy

    async def analyze_page_security(
        self,
        page: Page,
        response: Response | None = None,
        html: str = "",
    ) -> SecurityAnalysisResult:
        """综合分析页面安全状况"""
        result = SecurityAnalysisResult()

        if response:
            headers = dict(response.headers)
            result.headers = headers
            result.csp_result = self.analyze_csp_from_headers(headers)
        elif html:
            result.csp_result = self.analyze_csp_from_html(html)

        result.fingerprint = self.current_fingerprint or BrowserFingerprint()
        result.security_score = self._calculate_security_score(result)
        result.recommendations = self._generate_recommendations(result)

        return result

    def _calculate_security_score(self, result: SecurityAnalysisResult) -> float:
        """计算安全分数"""
        score = 100.0

        if result.csp_result.has_strict_csp:
            score -= 10
        if not result.csp_result.allows_inline_scripts:
            score -= 5

        return max(0, min(100, score))

    def _generate_recommendations(self, result: SecurityAnalysisResult) -> list[str]:
        """生成安全建议"""
        recommendations = []

        if result.csp_result.recommendations:
            recommendations.extend([f"CSP: {rec}" for rec in result.csp_result.recommendations])

        if not self.current_fingerprint:
            recommendations.append("建议生成浏览器指纹以提高隐蔽性")

        return recommendations

    def to_dict(self, result: SecurityAnalysisResult) -> dict[str, Any]:
        """转换为字典"""
        return {
            "security_score": result.security_score,
            "csp": self.csp_analyzer.to_dict(),
            "fingerprint": result.fingerprint.to_dict() if result.fingerprint else None,
            "recommendations": result.recommendations,
            "headers": result.headers,
        }
