"""
浏览器指纹生成器

生成真实的浏览器指纹信息。
"""

from __future__ import annotations

import hashlib
import json
import random
import time
from dataclasses import dataclass, field
from typing import Any

from rich.console import Console

console = Console()


@dataclass
class BrowserFingerprint:
    """浏览器指纹数据类"""
    user_agent: str = ""
    platform: str = ""
    vendor: str = ""
    language: str = ""
    languages: list[str] = field(default_factory=list)
    screen_width: int = 1920
    screen_height: int = 1080
    device_pixel_ratio: float = 1.0
    color_depth: int = 24
    timezone: str = "Asia/Shanghai"
    timezone_offset: int = -480
    hardware_concurrency: int = 8
    device_memory: int = 8
    max_touch_points: int = 0
    webgl_vendor: str = ""
    webgl_renderer: str = ""
    canvas_fingerprint: str = ""
    audio_fingerprint: str = ""
    fonts: list[str] = field(default_factory=list)
    plugins: list[dict[str, str]] = field(default_factory=list)
    do_not_track: str | None = None
    cookie_enabled: bool = True
    local_storage: bool = True
    session_storage: bool = True

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "user_agent": self.user_agent,
            "platform": self.platform,
            "vendor": self.vendor,
            "language": self.language,
            "languages": self.languages,
            "screen": {
                "width": self.screen_width, "height": self.screen_height,
                "device_pixel_ratio": self.device_pixel_ratio, "color_depth": self.color_depth,
            },
            "timezone": self.timezone,
            "timezone_offset": self.timezone_offset,
            "hardware": {
                "concurrency": self.hardware_concurrency,
                "memory": self.device_memory,
                "max_touch_points": self.max_touch_points,
            },
            "webgl": {"vendor": self.webgl_vendor, "renderer": self.webgl_renderer},
            "canvas_fingerprint": self.canvas_fingerprint,
            "audio_fingerprint": self.audio_fingerprint,
            "fonts": self.fonts,
            "plugins": self.plugins,
            "privacy": {
                "do_not_track": self.do_not_track,
                "cookie_enabled": self.cookie_enabled,
                "local_storage": self.local_storage,
                "session_storage": self.session_storage,
            },
        }

    def to_playwright_context_options(self) -> dict[str, Any]:
        """转换为 Playwright 浏览器上下文选项"""
        return {
            "user_agent": self.user_agent,
            "viewport": {"width": self.screen_width, "height": self.screen_height},
            "device_scale_factor": self.device_pixel_ratio,
            "locale": self.language,
            "timezone_id": self.timezone,
        }

    def generate_hash(self) -> str:
        """生成指纹哈希值"""
        fingerprint_str = json.dumps(self.to_dict(), sort_keys=True)
        return hashlib.sha256(fingerprint_str.encode()).hexdigest()[:16]


class FingerprintGenerator:
    """浏览器指纹生成器"""

    SCREEN_RESOLUTIONS = [
        (1920, 1080), (2560, 1440), (3840, 2160),
        (1366, 768), (1536, 864), (1440, 900),
        (1680, 1050), (2560, 1600), (1280, 720), (1600, 900),
    ]

    TIMEZONES = [
        ("Asia/Shanghai", -480), ("Asia/Hong_Kong", -480),
        ("Asia/Tokyo", -540), ("Asia/Seoul", -540),
        ("Asia/Singapore", -480), ("America/New_York", 300),
        ("America/Los_Angeles", 480), ("Europe/London", 0),
        ("Europe/Paris", -60), ("Australia/Sydney", -600),
    ]

    WEBGL_CONFIGS = [
        ("Google Inc. (NVIDIA)", "ANGLE (NVIDIA, NVIDIA GeForce RTX 3080 Direct3D11 vs_5_0 ps_5_0)"),
        ("Google Inc. (NVIDIA)", "ANGLE (NVIDIA, NVIDIA GeForce RTX 3070 Direct3D11 vs_5_0 ps_5_0)"),
        ("Google Inc. (AMD)", "ANGLE (AMD, AMD Radeon RX 6800 XT Direct3D11 vs_5_0 ps_5_0)"),
        ("Google Inc. (Intel)", "ANGLE (Intel, Intel(R) UHD Graphics 630 Direct3D11 vs_5_0 ps_5_0)"),
        ("Google Inc. (Intel)", "ANGLE (Intel, Intel(R) Iris(R) Xe Graphics Direct3D11 vs_5_0 ps_5_0)"),
        ("Apple Inc.", "Apple GPU"),
        ("Intel Inc.", "Intel Iris OpenGL Engine"),
        ("NVIDIA Corporation", "GeForce GTX 1080/PCIe/SSE2"),
    ]

    COMMON_FONTS = [
        "Arial", "Helvetica", "Times New Roman", "Times",
        "Courier New", "Courier", "Verdana", "Georgia",
        "Palatino", "Garamond", "Bookman", "Comic Sans MS",
        "Trebuchet MS", "Impact", "Arial Black", "Tahoma",
        "Microsoft YaHei", "SimSun", "SimHei", "PingFang SC",
        "Hiragino Sans GB", "Microsoft JhengHei", "Noto Sans CJK SC",
    ]

    USER_AGENT_CONFIGS = [
        {
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "platform": "Win32", "vendor": "Google Inc.",
            "language": "zh-CN", "languages": ["zh-CN", "zh", "en-US", "en"],
        },
        {
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
            "platform": "Win32", "vendor": "Google Inc.",
            "language": "zh-CN", "languages": ["zh-CN", "zh", "en-US", "en"],
        },
        {
            "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "platform": "MacIntel", "vendor": "Google Inc.",
            "language": "zh-CN", "languages": ["zh-CN", "zh", "en-US", "en"],
        },
        {
            "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1 Safari/605.1.15",
            "platform": "MacIntel", "vendor": "Apple Computer, Inc.",
            "language": "zh-CN", "languages": ["zh-CN", "zh-Hans", "en-US", "en"],
        },
        {
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) Gecko/20100101 Firefox/133.0",
            "platform": "Win32", "vendor": "",
            "language": "zh-CN", "languages": ["zh-CN", "zh", "en-US", "en"],
        },
        {
            "user_agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "platform": "Linux x86_64", "vendor": "Google Inc.",
            "language": "zh-CN", "languages": ["zh-CN", "zh", "en-US", "en"],
        },
    ]

    def __init__(self, seed: int | None = None):
        self.seed = seed
        if seed is not None:
            random.seed(seed)

    def generate(self, browser_type: str = "chrome", device_type: str = "desktop") -> BrowserFingerprint:
        """生成浏览器指纹"""
        fingerprint = BrowserFingerprint()

        ua_config = self._select_user_agent_config(browser_type)
        fingerprint.user_agent = ua_config["user_agent"]
        fingerprint.platform = ua_config["platform"]
        fingerprint.vendor = ua_config["vendor"]
        fingerprint.language = ua_config["language"]
        fingerprint.languages = ua_config["languages"]

        screen = self._select_screen_resolution(device_type)
        fingerprint.screen_width = screen[0]
        fingerprint.screen_height = screen[1]
        fingerprint.device_pixel_ratio = self._select_device_pixel_ratio(device_type)
        fingerprint.color_depth = random.choice([24, 32])

        timezone = random.choice(self.TIMEZONES)
        fingerprint.timezone = timezone[0]
        fingerprint.timezone_offset = timezone[1]

        fingerprint.hardware_concurrency = random.choice([4, 6, 8, 12, 16])
        fingerprint.device_memory = random.choice([4, 8, 16, 32])
        fingerprint.max_touch_points = 0 if device_type == "desktop" else random.choice([5, 10])

        webgl = random.choice(self.WEBGL_CONFIGS)
        fingerprint.webgl_vendor = webgl[0]
        fingerprint.webgl_renderer = webgl[1]

        fingerprint.canvas_fingerprint = self._generate_canvas_fingerprint()
        fingerprint.audio_fingerprint = self._generate_audio_fingerprint()
        fingerprint.fonts = self._select_fonts()
        fingerprint.plugins = self._generate_plugins(browser_type)

        fingerprint.do_not_track = random.choice([None, "1", "unspecified"])
        fingerprint.cookie_enabled = True
        fingerprint.local_storage = True
        fingerprint.session_storage = True

        return fingerprint

    def _select_user_agent_config(self, browser_type: str) -> dict[str, Any]:
        filtered = [ua for ua in self.USER_AGENT_CONFIGS if browser_type.lower() in ua["user_agent"].lower()]
        if filtered:
            return random.choice(filtered)
        return random.choice(self.USER_AGENT_CONFIGS)

    def _select_screen_resolution(self, device_type: str) -> tuple[int, int]:
        if device_type == "mobile":
            return random.choice([(375, 812), (414, 896), (360, 800), (412, 915)])
        elif device_type == "tablet":
            return random.choice([(768, 1024), (834, 1194), (1024, 1366)])
        return random.choice(self.SCREEN_RESOLUTIONS)

    def _select_device_pixel_ratio(self, device_type: str) -> float:
        if device_type == "mobile":
            return random.choice([2.0, 3.0])
        elif device_type == "tablet":
            return random.choice([1.5, 2.0])
        return random.choice([1.0, 1.25, 1.5, 2.0])

    def _generate_canvas_fingerprint(self) -> str:
        base_data = f"canvas_{time.time()}_{random.random()}"
        return hashlib.md5(base_data.encode()).hexdigest()

    def _generate_audio_fingerprint(self) -> str:
        base_data = f"audio_{time.time()}_{random.random()}"
        return hashlib.sha256(base_data.encode()).hexdigest()[:32]

    def _select_fonts(self) -> list[str]:
        count = random.randint(10, 15)
        return random.sample(self.COMMON_FONTS, min(count, len(self.COMMON_FONTS)))

    def _generate_plugins(self, browser_type: str) -> list[dict[str, str]]:
        if browser_type.lower() == "chrome":
            return [
                {"name": "PDF Viewer", "description": "Portable Document Format", "filename": "internal-pdf-viewer"},
                {"name": "Chrome PDF Viewer", "description": "Portable Document Format", "filename": "internal-pdf-viewer"},
                {"name": "Chromium PDF Viewer", "description": "Portable Document Format", "filename": "internal-pdf-viewer"},
            ]
        elif browser_type.lower() == "firefox":
            return [{"name": "PDF Viewer", "description": "Portable Document Format", "filename": "pdfjs"}]
        return []

    def generate_playwright_init_script(self, fingerprint: BrowserFingerprint) -> str:
        """生成 Playwright 初始化脚本"""
        return f"""
(function() {{
    'use strict';

    const navigatorProps = {{
        platform: '{fingerprint.platform}',
        vendor: '{fingerprint.vendor}',
        language: '{fingerprint.language}',
        languages: {json.dumps(fingerprint.languages)},
        hardwareConcurrency: {fingerprint.hardware_concurrency},
        deviceMemory: {fingerprint.device_memory},
        maxTouchPoints: {fingerprint.max_touch_points},
        cookieEnabled: {str(fingerprint.cookie_enabled).lower()},
        doNotTrack: {f"'{fingerprint.do_not_track}'" if fingerprint.do_not_track else 'null'}
    }};

    for (const [key, value] of Object.entries(navigatorProps)) {{
        try {{
            Object.defineProperty(navigator, key, {{ get: () => value, configurable: true }});
        }} catch (e) {{}}
    }}

    const screenProps = {{
        width: {fingerprint.screen_width},
        height: {fingerprint.screen_height},
        availWidth: {fingerprint.screen_width},
        availHeight: {fingerprint.screen_height - 40},
        colorDepth: {fingerprint.color_depth},
        pixelDepth: {fingerprint.color_depth}
    }};

    for (const [key, value] of Object.entries(screenProps)) {{
        try {{
            Object.defineProperty(screen, key, {{ get: () => value, configurable: true }});
        }} catch (e) {{}}
    }}

    try {{
        Object.defineProperty(window, 'devicePixelRatio', {{ get: () => {fingerprint.device_pixel_ratio}, configurable: true }});
    }} catch (e) {{}}

    const getParameterProxyHandler = {{
        apply: function(target, thisArg, args) {{
            const param = args[0];
            if (param === 37445) return '{fingerprint.webgl_vendor}';
            if (param === 37446) return '{fingerprint.webgl_renderer}';
            return target.apply(thisArg, args);
        }}
    }};

    const originalGetParameter = WebGLRenderingContext.prototype.getParameter;
    WebGLRenderingContext.prototype.getParameter = new Proxy(originalGetParameter, getParameterProxyHandler);

    if (typeof WebGL2RenderingContext !== 'undefined') {{
        const originalGetParameter2 = WebGL2RenderingContext.prototype.getParameter;
        WebGL2RenderingContext.prototype.getParameter = new Proxy(originalGetParameter2, getParameterProxyHandler);
    }}

    const originalGetTimezoneOffset = Date.prototype.getTimezoneOffset;
    Date.prototype.getTimezoneOffset = function() {{ return {fingerprint.timezone_offset}; }};

    console.log('[WebThief] 浏览器指纹已注入');
}})();
"""

    def rotate(self, current_fingerprint: BrowserFingerprint | None = None) -> BrowserFingerprint:
        """轮换生成新的浏览器指纹"""
        if self.seed is not None:
            random.seed(int(time.time() * 1000) % 2**32)

        new_fingerprint = self.generate()

        if current_fingerprint and new_fingerprint.generate_hash() == current_fingerprint.generate_hash():
            return self.rotate(current_fingerprint)

        return new_fingerprint
