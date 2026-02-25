"""
网站技术栈分析器：
- 在渲染过程中同步分析网站技术栈
- 检测前端框架、后端技术、CDN、分析工具等
- 根据检测结果提供渲染策略建议
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from playwright.async_api import Page, Response

from rich.console import Console
from rich.table import Table

console = Console()


class TechCategory(Enum):
    FRAMEWORK = "前端框架"
    LIBRARY = "JS 库"
    CMS = "CMS"
    ECOMMERCE = "电商"
    ANALYTICS = "分析工具"
    CDN = "CDN"
    SERVER = "服务器"
    DATABASE = "数据库"
    BUILD_TOOL = "构建工具"
    UI_FRAMEWORK = "UI 框架"
    ANIMATION = "动画库"
    SEO = "SEO"
    SECURITY = "安全"
    OTHER = "其他"


@dataclass
class DetectedTech:
    name: str
    category: TechCategory
    confidence: int = 100
    version: str | None = None
    evidence: str | None = None


@dataclass
class TechStack:
    technologies: list[DetectedTech] = field(default_factory=list)

    def add(self, tech: DetectedTech) -> None:
        existing = next(
            (t for t in self.technologies if t.name == tech.name and t.category == tech.category),
            None
        )
        if existing:
            if tech.confidence > existing.confidence:
                self.technologies.remove(existing)
                self.technologies.append(tech)
        else:
            self.technologies.append(tech)

    def get_by_category(self, category: TechCategory) -> list[DetectedTech]:
        return [t for t in self.technologies if t.category == category]

    def has_tech(self, name: str) -> bool:
        return any(t.name.lower() == name.lower() for t in self.technologies)

    def get_tech(self, name: str) -> DetectedTech | None:
        return next((t for t in self.technologies if t.name.lower() == name.lower()), None)

    @property
    def is_spa(self) -> bool:
        spa_frameworks = {"React", "Vue.js", "Angular", "Svelte", "Next.js", "Nuxt.js", "Gatsby", "Astro"}
        return any(t.name in spa_frameworks for t in self.technologies)

    @property
    def is_ssr(self) -> bool:
        ssr_frameworks = {"Next.js", "Nuxt.js", "Gatsby", "Astro", "Remix"}
        return any(t.name in ssr_frameworks for t in self.technologies)

    @property
    def has_animation_lib(self) -> bool:
        anim_libs = {"GSAP", "Lottie", "Anime.js", "Motion One", "Framer Motion", "AOS"}
        return any(t.name in anim_libs for t in self.technologies)

    @property
    def is_traditional(self) -> bool:
        if self.is_spa:
            return False
        traditional_indicators = {"jQuery", "Bootstrap", "WordPress", "Drupal"}
        return any(t.name in traditional_indicators for t in self.technologies)


TECH_SIGNATURES: list[dict] = [
    {
        "name": "React",
        "category": TechCategory.FRAMEWORK,
        "patterns": [
            r"react\.production\.min\.js",
            r"react-dom",
            r"__REACT_DEVTOOLS_GLOBAL_HOOK__",
            r"data-reactroot",
            r"data-reactid",
            r"_reactRootContainer",
        ],
        "dom_check": """
            !!(window.React || window.__REACT_DEVTOOLS_GLOBAL_HOOK__ ||
               document.querySelector('[data-reactroot], [data-reactid]') ||
               Object.keys(document.documentElement).some(k => k.startsWith('__react')))
        """,
    },
    {
        "name": "Vue.js",
        "category": TechCategory.FRAMEWORK,
        "patterns": [
            r"vue\.runtime\.min\.js",
            r"vue\.min\.js",
            r"vue@[\d.]+",
            r"data-v-[a-f0-9]+",
            r"__VUE__",
            r"__vue_app__",
        ],
        "dom_check": """
            !!(window.Vue || window.__VUE__ || window.__vue_app__ ||
               document.querySelector('[data-v-]') ||
               document.querySelector('[data-v-app]'))
        """,
    },
    {
        "name": "Angular",
        "category": TechCategory.FRAMEWORK,
        "patterns": [
            r"ng-version",
            r"angular\.min\.js",
            r"angular\.io",
            r"ng-app",
            r"ng-controller",
            r"_ngcontent-",
            r"_nghost-",
        ],
        "dom_check": """
            !!(window.ng || window.angular ||
               document.querySelector('[ng-version], [ng-app], [_ngcontent-]') ||
               document.querySelector('app-root'))
        """,
    },
    {
        "name": "Svelte",
        "category": TechCategory.FRAMEWORK,
        "patterns": [
            r"svelte[\d-]*\.js",
            r"svelte@",
            r"class=\"svelte-[a-z0-9]+\"",
        ],
        "dom_check": """
            !!(document.querySelector('[class*="svelte-"]') ||
               Array.from(document.querySelectorAll('style')).some(s => s.textContent.includes('svelte-')))
        """,
    },
    {
        "name": "Next.js",
        "category": TechCategory.FRAMEWORK,
        "patterns": [
            r"__NEXT_DATA__",
            r"_next/static",
            r"/_next/",
            r"next/dist",
        ],
        "dom_check": """
            !!(window.__NEXT_DATA__ || document.getElementById('__next'))
        """,
    },
    {
        "name": "Nuxt.js",
        "category": TechCategory.FRAMEWORK,
        "patterns": [
            r"__NUXT__",
            r"_nuxt/",
            r"nuxt\.link",
            r"@nuxt",
        ],
        "dom_check": """
            !!(window.__NUXT__ || window.__NUXT_CONFIG__ || document.getElementById('__nuxt'))
        """,
    },
    {
        "name": "Gatsby",
        "category": TechCategory.FRAMEWORK,
        "patterns": [
            r"gatsby-link",
            r"gatsby-image",
            r"___gatsby",
            r"gatsby-script",
        ],
        "dom_check": """
            !!(window.___loader || document.getElementById('___gatsby'))
        """,
    },
    {
        "name": "Astro",
        "category": TechCategory.FRAMEWORK,
        "patterns": [
            r"astro\.runtime\.js",
            r"_astro/",
            r"astro-[a-z0-9]+",
        ],
        "dom_check": """
            !!(document.querySelector('[data-astro-root]') ||
               Array.from(document.querySelectorAll('style')).some(s => s.textContent.includes('astro-')))
        """,
    },
    {
        "name": "Remix",
        "category": TechCategory.FRAMEWORK,
        "patterns": [
            r"__remixContext",
            r"remix\.run",
            r"@remix-run",
        ],
        "dom_check": """
            !!(window.__remixContext || window.__remixManifest)
        """,
    },
    {
        "name": "jQuery",
        "category": TechCategory.LIBRARY,
        "patterns": [
            r"jquery[-.]?[\d.]*\.js",
            r"jquery\.min\.js",
            r"jquery-[0-9.]+",
        ],
        "dom_check": """
            !!(window.jQuery || window.$)
        """,
    },
    {
        "name": "Lodash",
        "category": TechCategory.LIBRARY,
        "patterns": [r"lodash\.min\.js", r"lodash@[0-9.]+"],
        "dom_check": "!!(window._ && window._.VERSION)",
    },
    {
        "name": "Axios",
        "category": TechCategory.LIBRARY,
        "patterns": [r"axios\.min\.js", r"axios@[0-9.]+", r"axios/dist"],
        "dom_check": "!!window.axios",
    },
    {
        "name": "GSAP",
        "category": TechCategory.ANIMATION,
        "patterns": [
            r"gsap\.min\.js",
            r"TweenMax",
            r"TimelineMax",
            r"ScrollTrigger",
        ],
        "dom_check": "!!(window.gsap || window.TweenMax || window.TweenLite)",
    },
    {
        "name": "Framer Motion",
        "category": TechCategory.ANIMATION,
        "patterns": [r"framer-motion", r"motion/dist"],
        "dom_check": None,
    },
    {
        "name": "AOS",
        "category": TechCategory.ANIMATION,
        "patterns": [r"aos\.js", r"aos\.min\.js", r"data-aos="],
        "dom_check": "!!window.AOS",
    },
    {
        "name": "Lottie",
        "category": TechCategory.ANIMATION,
        "patterns": [r"lottie\.min\.js", r"lottie-player", r"bodymovin"],
        "dom_check": "!!window.lottie",
    },
    {
        "name": "Three.js",
        "category": TechCategory.LIBRARY,
        "patterns": [r"three\.min\.js", r"three@[0-9.]+", r"three/build"],
        "dom_check": "!!window.THREE",
    },
    {
        "name": "Bootstrap",
        "category": TechCategory.UI_FRAMEWORK,
        "patterns": [
            r"bootstrap\.min\.js",
            r"bootstrap\.min\.css",
            r"bootstrap@[0-9.]+",
        ],
        "dom_check": """
            !!(window.bootstrap || document.querySelector('[class*="container-"]') ||
               document.querySelector('[class*="row"]'))
        """,
    },
    {
        "name": "Tailwind CSS",
        "category": TechCategory.UI_FRAMEWORK,
        "patterns": [r"tailwindcss", r"tailwind\.min\.css", r"cdn\.tailwindcss\.com"],
        "dom_check": """
            !!(Array.from(document.querySelectorAll('[class]')).some(el =>
                /\b(flex|grid|p-[0-9]|m-[0-9]|text-[a-z]+|bg-[a-z]+)/.test(el.className)))
        """,
    },
    {
        "name": "Material UI",
        "category": TechCategory.UI_FRAMEWORK,
        "patterns": [r"@mui/material", r"@material-ui", r"mui\.min\.js"],
        "dom_check": """
            !!(document.querySelector('[class*="MuiBox"]') ||
               document.querySelector('[class*="MuiButton"]'))
        """,
    },
    {
        "name": "Ant Design",
        "category": TechCategory.UI_FRAMEWORK,
        "patterns": [r"antd\.min\.js", r"antd\.min\.css", r"ant-design"],
        "dom_check": "!!document.querySelector('[class*=\"ant-\"]')",
    },
    {
        "name": "Element UI",
        "category": TechCategory.UI_FRAMEWORK,
        "patterns": [r"element-ui", r"element\.min\.js", r"element-plus"],
        "dom_check": "!!document.querySelector('[class*=\"el-\"]')",
    },
    {
        "name": "WordPress",
        "category": TechCategory.CMS,
        "patterns": [
            r"wp-content",
            r"wp-includes",
            r"wp-json",
            r"wordpress",
            r"/xmlrpc\.php",
        ],
        "dom_check": """
            !!(document.querySelector('link[href*="wp-content"]') ||
               document.querySelector('meta[name="generator"][content*="WordPress"]'))
        """,
    },
    {
        "name": "Drupal",
        "category": TechCategory.CMS,
        "patterns": [r"drupal\.js", r"/sites/default/files", r"Drupal\.settings"],
        "dom_check": """!!(window.Drupal || document.querySelector('meta[name="generator"][content*="Drupal"]'))""",
    },
    {
        "name": "Joomla",
        "category": TechCategory.CMS,
        "patterns": [r"/media/jui/", r"joomla", r"/administrator/"],
        "dom_check": None,
    },
    {
        "name": "Shopify",
        "category": TechCategory.ECOMMERCE,
        "patterns": [
            r"cdn\.shopify\.com",
            r"myshopify\.com",
            r"Shopify\.theme",
        ],
        "dom_check": "!!(window.Shopify || document.querySelector('link[href*=\"shopify\"]'))",
    },
    {
        "name": "WooCommerce",
        "category": TechCategory.ECOMMERCE,
        "patterns": [r"woocommerce", r"/wc-api/", r"wc-"],
        "dom_check": "!!document.querySelector('[class*=\"woocommerce\"]')",
    },
    {
        "name": "Magento",
        "category": TechCategory.ECOMMERCE,
        "patterns": [r"magento", r"/skin/frontend/", r"Mage\."],
        "dom_check": """!!(window.Mage || document.querySelector('meta[name="generator"][content*="Magento"]'))""",
    },
    {
        "name": "Google Analytics",
        "category": TechCategory.ANALYTICS,
        "patterns": [
            r"google-analytics\.com",
            r"gtag\.js",
            r"ga\.js",
            r"googletagmanager\.com/gtag",
        ],
        "dom_check": "!!(window.gtag || window.ga || window.dataLayer)",
    },
    {
        "name": "Google Tag Manager",
        "category": TechCategory.ANALYTICS,
        "patterns": [r"googletagmanager\.com/gtm\.js", r"gtm\.js"],
        "dom_check": "!!window.dataLayer",
    },
    {
        "name": "Hotjar",
        "category": TechCategory.ANALYTICS,
        "patterns": [r"hotjar\.com", r"hj\._"],
        "dom_check": "!!(window.hj && window.hj.q)",
    },
    {
        "name": "Mixpanel",
        "category": TechCategory.ANALYTICS,
        "patterns": [r"mixpanel\.com", r"mixpanel\.min\.js"],
        "dom_check": "!!window.mixpanel",
    },
    {
        "name": "Segment",
        "category": TechCategory.ANALYTICS,
        "patterns": [r"cdn\.segment\.com", r"analytics\.js"],
        "dom_check": "!!window.analytics",
    },
    {
        "name": "Cloudflare",
        "category": TechCategory.CDN,
        "patterns": [r"cloudflare", r"cf-ray", r"cdnjs\.cloudflare"],
        "headers": ["cf-ray", "cf-cache-status"],
        "dom_check": None,
    },
    {
        "name": "AWS CloudFront",
        "category": TechCategory.CDN,
        "patterns": [r"cloudfront\.net", r"\.cloudfront\."],
        "headers": ["x-amz-cf-id", "x-amz-cf-pop"],
        "dom_check": None,
    },
    {
        "name": "Fastly",
        "category": TechCategory.CDN,
        "patterns": [r"fastly\.net", r"fastly"],
        "headers": ["x-served-by", "x-cache"],
        "dom_check": None,
    },
    {
        "name": "jsDelivr",
        "category": TechCategory.CDN,
        "patterns": [r"cdn\.jsdelivr\.net"],
        "dom_check": None,
    },
    {
        "name": "unpkg",
        "category": TechCategory.CDN,
        "patterns": [r"unpkg\.com"],
        "dom_check": None,
    },
    {
        "name": "Nginx",
        "category": TechCategory.SERVER,
        "patterns": [],
        "headers": ["server: nginx"],
        "dom_check": None,
    },
    {
        "name": "Apache",
        "category": TechCategory.SERVER,
        "patterns": [],
        "headers": ["server: apache"],
        "dom_check": None,
    },
    {
        "name": "Vercel",
        "category": TechCategory.SERVER,
        "patterns": [r"vercel", r"_vercel/insights"],
        "headers": ["x-vercel-id", "x-vercel-cache"],
        "dom_check": None,
    },
    {
        "name": "Netlify",
        "category": TechCategory.SERVER,
        "patterns": [r"netlify", r"\.netlify\."],
        "headers": ["x-nf-request-id"],
        "dom_check": None,
    },
    {
        "name": "Webpack",
        "category": TechCategory.BUILD_TOOL,
        "patterns": [r"webpack", r"webpackChunk", r"__webpack_require__"],
        "dom_check": "!!(window.__webpack_require__ || window.webpackChunk)",
    },
    {
        "name": "Vite",
        "category": TechCategory.BUILD_TOOL,
        "patterns": [r"vite", r"/@vite/", r"vite/dist"],
        "dom_check": "!!window.__vite__",
    },
    {
        "name": "esbuild",
        "category": TechCategory.BUILD_TOOL,
        "patterns": [r"esbuild"],
        "dom_check": None,
    },
    {
        "name": "TypeScript",
        "category": TechCategory.LIBRARY,
        "patterns": [r"typescript", r"\.ts\.", r"ts\.lib"],
        "dom_check": None,
    },
    {
        "name": "Sass/SCSS",
        "category": TechCategory.BUILD_TOOL,
        "patterns": [r"\.scss", r"\.sass", r"sass\.min\.css"],
        "dom_check": None,
    },
    {
        "name": "Less",
        "category": TechCategory.BUILD_TOOL,
        "patterns": [r"\.less", r"less\.min\.js"],
        "dom_check": "!!window.less",
    },
    {
        "name": "Swiper",
        "category": TechCategory.LIBRARY,
        "patterns": [r"swiper\.min\.js", r"swiper\.min\.css", r"swiper@"],
        "dom_check": "!!(window.Swiper || document.querySelector('.swiper-container, .swiper'))",
    },
    {
        "name": "Slick",
        "category": TechCategory.LIBRARY,
        "patterns": [r"slick\.min\.js", r"slick\.min\.css", r"slick-carousel"],
        "dom_check": "!!document.querySelector('.slick-slider')",
    },
    {
        "name": "Alpine.js",
        "category": TechCategory.FRAMEWORK,
        "patterns": [r"alpine\.js", r"alpinejs", r"x-data"],
        "dom_check": "!!(window.Alpine || document.querySelector('[x-data]'))",
    },
    {
        "name": "htmx",
        "category": TechCategory.LIBRARY,
        "patterns": [r"htmx\.min\.js", r"htmx\.org"],
        "dom_check": "!!window.htmx",
    },
    {
        "name": "Stimulus",
        "category": TechCategory.FRAMEWORK,
        "patterns": [r"stimulus", r"data-controller"],
        "dom_check": "!!(window.Stimulus || document.querySelector('[data-controller]'))",
    },
    {
        "name": "hCaptcha",
        "category": TechCategory.SECURITY,
        "patterns": [r"hcaptcha\.com", r"h-captcha"],
        "dom_check": "!!document.querySelector('.h-captcha')",
    },
    {
        "name": "reCAPTCHA",
        "category": TechCategory.SECURITY,
        "patterns": [r"recaptcha", r"g-recaptcha", r"google\.com/recaptcha"],
        "dom_check": "!!(window.grecaptcha || document.querySelector('.g-recaptcha'))",
    },
    {
        "name": "Cloudflare Turnstile",
        "category": TechCategory.SECURITY,
        "patterns": [r"challenges\.cloudflare\.com", r"turnstile"],
        "dom_check": "!!window.turnstile",
    },
    {
        "name": "Yoast SEO",
        "category": TechCategory.SEO,
        "patterns": [r"yoast", r"yoast-seo"],
        "dom_check": "!!document.querySelector('meta[name*=\"yoast\"]')",
    },
    {
        "name": "Schema.org",
        "category": TechCategory.SEO,
        "patterns": [r"schema\.org", r"application/ld\+json"],
        "dom_check": "!!document.querySelector('script[type=\"application/ld+json\"]')",
    },
]


@dataclass
class RenderStrategy:
    wait_after_load: int = 3
    scroll_enabled: bool = True
    scroll_pause: float = 0.5
    aggressive_interactions: bool = False
    hydration_wait: int = 0
    lazy_load_activation: bool = True
    animation_freeze: bool = True
    extra_network_wait: int = 0
    recommendations: list[str] = field(default_factory=list)


class TechAnalyzer:
    """
    网站技术栈分析器
    在渲染过程中同步分析网站使用的技术栈
    """

    def __init__(self):
        self.tech_stack = TechStack()
        self._analyzed_urls: set[str] = set()
        self._response_headers: dict[str, str] = {}

    def analyze_headers(self, headers: dict[str, str]) -> None:
        for key, value in headers.items():
            self._response_headers[key.lower()] = value

        for sig in TECH_SIGNATURES:
            if not sig.get("headers"):
                continue
            for header_pattern in sig["headers"]:
                header_name = header_pattern.split(":")[0].strip().lower()
                if header_name in self._response_headers:
                    self.tech_stack.add(DetectedTech(
                        name=sig["name"],
                        category=sig["category"],
                        confidence=90,
                        evidence=f"Header: {header_name}",
                    ))

    def analyze_response(self, response: Response) -> None:
        try:
            url = response.url
            if url in self._analyzed_urls:
                return
            self._analyzed_urls.add(url)

            headers = dict(response.headers)
            self.analyze_headers(headers)

            content_type = headers.get("content-type", "").lower()

            if "javascript" in content_type or url.endswith(".js"):
                self._analyze_js_url(url)
            elif "css" in content_type or url.endswith(".css"):
                self._analyze_css_url(url)

        except Exception:
            pass

    def _analyze_js_url(self, url: str) -> None:
        url_lower = url.lower()
        for sig in TECH_SIGNATURES:
            patterns = sig.get("patterns", [])
            for pattern in patterns:
                if re.search(pattern, url_lower, re.IGNORECASE):
                    self.tech_stack.add(DetectedTech(
                        name=sig["name"],
                        category=sig["category"],
                        confidence=85,
                        evidence=f"URL: {url}",
                    ))
                    break

    def _analyze_css_url(self, url: str) -> None:
        url_lower = url.lower()
        for sig in TECH_SIGNATURES:
            patterns = sig.get("patterns", [])
            for pattern in patterns:
                if re.search(pattern, url_lower, re.IGNORECASE):
                    self.tech_stack.add(DetectedTech(
                        name=sig["name"],
                        category=sig["category"],
                        confidence=80,
                        evidence=f"CSS URL: {url}",
                    ))
                    break

    async def analyze_dom(self, page: Page) -> None:
        for sig in TECH_SIGNATURES:
            dom_check = sig.get("dom_check")
            if not dom_check:
                continue

            try:
                result = await page.evaluate(dom_check)
                if result:
                    self.tech_stack.add(DetectedTech(
                        name=sig["name"],
                        category=sig["category"],
                        confidence=95,
                        evidence="DOM detection",
                    ))
            except Exception:
                pass

        await self._analyze_meta_tags(page)
        await self._analyze_script_tags(page)
        await self._analyze_inline_styles(page)

    async def _analyze_meta_tags(self, page: Page) -> None:
        try:
            metas = await page.evaluate("""
                () => Array.from(document.querySelectorAll('meta')).map(m => ({
                    name: m.getAttribute('name') || m.getAttribute('property') || '',
                    content: m.getAttribute('content') || ''
                }))
            """)

            for meta in metas:
                name = (meta.get("name") or "").lower()
                content = (meta.get("content") or "").lower()

                if name == "generator":
                    if "wordpress" in content:
                        self.tech_stack.add(DetectedTech(
                            name="WordPress",
                            category=TechCategory.CMS,
                            confidence=100,
                            evidence=f"Meta generator: {content}",
                        ))
                    elif "drupal" in content:
                        self.tech_stack.add(DetectedTech(
                            name="Drupal",
                            category=TechCategory.CMS,
                            confidence=100,
                            evidence=f"Meta generator: {content}",
                        ))
                    elif "joomla" in content:
                        self.tech_stack.add(DetectedTech(
                            name="Joomla",
                            category=TechCategory.CMS,
                            confidence=100,
                            evidence=f"Meta generator: {content}",
                        ))
                    elif "magento" in content:
                        self.tech_stack.add(DetectedTech(
                            name="Magento",
                            category=TechCategory.ECOMMERCE,
                            confidence=100,
                            evidence=f"Meta generator: {content}",
                        ))

                if name == "viewport" and "width=device-width" in content:
                    pass

        except Exception:
            pass

    async def _analyze_script_tags(self, page: Page) -> None:
        try:
            scripts = await page.evaluate("""
                () => Array.from(document.querySelectorAll('script[src]')).map(s => s.src)
            """)

            for src in scripts:
                self._analyze_js_url(src)

            inline_scripts = await page.evaluate("""
                () => Array.from(document.querySelectorAll('script:not([src])'))
                    .map(s => s.textContent.substring(0, 500))
                    .join('\\n')
            """)

            self._analyze_inline_js(inline_scripts)

        except Exception:
            pass

    def _analyze_inline_js(self, content: str) -> None:
        content_lower = content.lower()

        inline_patterns = [
            (r"reactdom\.render", "React", TechCategory.FRAMEWORK),
            (r"createapp\(", "Vue.js", TechCategory.FRAMEWORK),
            (r"new vue\(", "Vue.js", TechCategory.FRAMEWORK),
            (r"platformbrowserdynamic", "Angular", TechCategory.FRAMEWORK),
            (r"gsap\.", "GSAP", TechCategory.ANIMATION),
            (r"scrolltrigger", "GSAP", TechCategory.ANIMATION),
            (r"anime\(", "Anime.js", TechCategory.ANIMATION),
            (r"lottie\.loadanimation", "Lottie", TechCategory.ANIMATION),
            (r"new swiper\(", "Swiper", TechCategory.LIBRARY),
            (r"\$\(document\)\.ready", "jQuery", TechCategory.LIBRARY),
            (r"gtag\(", "Google Analytics", TechCategory.ANALYTICS),
            (r"ga\(", "Google Analytics", TechCategory.ANALYTICS),
            (r"dataLayer\.push", "Google Tag Manager", TechCategory.ANALYTICS),
            (r"hj\(", "Hotjar", TechCategory.ANALYTICS),
            (r"mixpanel\.track", "Mixpanel", TechCategory.ANALYTICS),
            (r"alpine\.data", "Alpine.js", TechCategory.FRAMEWORK),
            (r"htmx\.on", "htmx", TechCategory.LIBRARY),
            (r"stimulus\.application", "Stimulus", TechCategory.FRAMEWORK),
        ]

        for pattern, name, category in inline_patterns:
            if re.search(pattern, content_lower, re.IGNORECASE):
                self.tech_stack.add(DetectedTech(
                    name=name,
                    category=category,
                    confidence=90,
                    evidence="Inline script",
                ))

    async def _analyze_inline_styles(self, page: Page) -> None:
        try:
            styles = await page.evaluate("""
                () => Array.from(document.querySelectorAll('style'))
                    .map(s => s.textContent.substring(0, 1000))
                    .join('\\n')
            """)

            style_lower = styles.lower()

            if "tailwind" in style_lower or re.search(r"\b(flex|grid|p-[0-9]|m-[0-9])", styles):
                pass

            if "svelte-" in style_lower:
                self.tech_stack.add(DetectedTech(
                    name="Svelte",
                    category=TechCategory.FRAMEWORK,
                    confidence=85,
                    evidence="Inline style with svelte-",
                ))

            if "astro-" in style_lower:
                self.tech_stack.add(DetectedTech(
                    name="Astro",
                    category=TechCategory.FRAMEWORK,
                    confidence=85,
                    evidence="Inline style with astro-",
                ))

        except Exception:
            pass

    def get_render_strategy(self) -> RenderStrategy:
        strategy = RenderStrategy()

        if self.tech_stack.is_ssr:
            strategy.hydration_wait = 2
            strategy.recommendations.append("SSR 框架检测到，增加 hydration 等待时间")

        if self.tech_stack.has_tech("Next.js"):
            strategy.hydration_wait = 3
            strategy.extra_network_wait = 2
            strategy.recommendations.append("Next.js: 等待 __NEXT_DATA__ 加载完成")

        if self.tech_stack.has_tech("Nuxt.js"):
            strategy.hydration_wait = 3
            strategy.recommendations.append("Nuxt.js: 等待 Vue hydration 完成")

        if self.tech_stack.has_tech("Gatsby"):
            strategy.hydration_wait = 2
            strategy.recommendations.append("Gatsby: 等待 React hydration")

        if self.tech_stack.has_animation_lib:
            strategy.scroll_enabled = True
            strategy.scroll_pause = 0.8
            strategy.animation_freeze = False
            strategy.recommendations.append("动画库检测到，启用滚动触发动画")

        if self.tech_stack.has_tech("GSAP"):
            strategy.scroll_enabled = True
            strategy.scroll_pause = 1.0
            strategy.recommendations.append("GSAP: 增加滚动间隔以触发 ScrollTrigger")

        if self.tech_stack.has_tech("AOS"):
            strategy.scroll_enabled = True
            strategy.recommendations.append("AOS: 滚动触发动画元素")

        if self.tech_stack.has_tech("Swiper") or self.tech_stack.has_tech("Slick"):
            strategy.aggressive_interactions = True
            strategy.recommendations.append("轮播组件检测到，启用交互预热")

        if self.tech_stack.is_traditional:
            strategy.scroll_enabled = True
            strategy.scroll_pause = 0.3
            strategy.aggressive_interactions = False
            strategy.recommendations.append("传统站点，使用保守渲染策略")

        if self.tech_stack.has_tech("WordPress"):
            strategy.lazy_load_activation = True
            strategy.recommendations.append("WordPress: 激活懒加载图片")

        if self.tech_stack.has_tech("Alpine.js"):
            strategy.hydration_wait = 1
            strategy.recommendations.append("Alpine.js: 等待初始化")

        if self.tech_stack.has_tech("htmx"):
            strategy.extra_network_wait = 2
            strategy.recommendations.append("htmx: 等待动态内容加载")

        if self.tech_stack.has_tech("Three.js"):
            strategy.wait_after_load = 5
            strategy.recommendations.append("Three.js: 增加 WebGL 渲染等待时间")

        return strategy

    def print_summary(self) -> None:
        if not self.tech_stack.technologies:
            console.print("[dim]  未检测到明显技术栈特征[/]")
            return

        table = Table(title="🔍 技术栈分析结果", show_header=True, header_style="bold cyan")
        table.add_column("类别", style="yellow", width=12)
        table.add_column("技术", style="green", width=20)
        table.add_column("置信度", justify="right", width=8)
        table.add_column("证据", style="dim", width=30)

        sorted_techs = sorted(
            self.tech_stack.technologies,
            key=lambda t: (t.category.value, t.name)
        )

        for tech in sorted_techs:
            table.add_row(
                tech.category.value,
                tech.name,
                f"{tech.confidence}%",
                tech.evidence or "-",
            )

        console.print(table)

        strategy = self.get_render_strategy()
        if strategy.recommendations:
            console.print("\n[bold cyan]📋 渲染策略建议:[/]")
            for rec in strategy.recommendations:
                console.print(f"  • {rec}")

    def to_dict(self) -> dict:
        return {
            "technologies": [
                {
                    "name": t.name,
                    "category": t.category.value,
                    "confidence": t.confidence,
                    "version": t.version,
                    "evidence": t.evidence,
                }
                for t in self.tech_stack.technologies
            ],
            "is_spa": self.tech_stack.is_spa,
            "is_ssr": self.tech_stack.is_ssr,
            "has_animation": self.tech_stack.has_animation_lib,
            "is_traditional": self.tech_stack.is_traditional,
            "render_strategy": {
                "wait_after_load": self.get_render_strategy().wait_after_load,
                "scroll_enabled": self.get_render_strategy().scroll_enabled,
                "aggressive_interactions": self.get_render_strategy().aggressive_interactions,
                "recommendations": self.get_render_strategy().recommendations,
            },
        }
