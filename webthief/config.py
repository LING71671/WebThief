"""
全局配置：User-Agent 池、反检测参数、已知追踪器列表
"""

import random

# ─── 并发与网络参数 ───────────────────────────────────────
DEFAULT_CONCURRENCY = 20          # 默认并发下载数
DEFAULT_TIMEOUT = 30              # 单文件下载超时 (秒)
DEFAULT_DELAY = 0.1               # 请求间隔 (秒)
DEFAULT_RETRIES = 3               # 最大重试次数
DEFAULT_WAIT_AFTER_LOAD = 3       # 页面加载后额外等待 (秒)
DEFAULT_SCROLL_PAUSE = 0.5        # 滚动间隔 (秒)

# ─── User-Agent 池 ────────────────────────────────────────
USER_AGENTS = [
    # Chrome (Windows)
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
    # Chrome (macOS)
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    # Firefox (Windows)
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) Gecko/20100101 Firefox/133.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:132.0) Gecko/20100101 Firefox/132.0",
    # Firefox (macOS)
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:133.0) Gecko/20100101 Firefox/133.0",
    # Edge
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36 Edg/130.0.0.0",
    # Safari (macOS)
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.6 Safari/605.1.15",
    # Chrome (Linux)
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    # Firefox (Linux)
    "Mozilla/5.0 (X11; Linux x86_64; rv:133.0) Gecko/20100101 Firefox/133.0",
    # 移动端 Chrome (Android)
    "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36",
    # 移动端 Safari (iOS)
    "Mozilla/5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1 Mobile/15E148 Safari/604.1",
]


def get_random_ua() -> str:
    """随机获取一个 User-Agent 字符串"""
    return random.choice(USER_AGENTS)


# ─── 已知追踪器 / 分析脚本域名 ──────────────────────────
TRACKER_DOMAINS = frozenset({
    "www.google-analytics.com",
    "google-analytics.com",
    "www.googletagmanager.com",
    "googletagmanager.com",
    "connect.facebook.net",
    "www.facebook.com",
    "static.hotjar.com",
    "script.hotjar.com",
    "snap.licdn.com",
    "bat.bing.com",
    "analytics.tiktok.com",
    "cdn.segment.com",
    "cdn.mxpnl.com",        # Mixpanel
    "js.intercomcdn.com",
    "widget.intercom.io",
    "js.hs-scripts.com",     # HubSpot
    "js.hs-analytics.net",
    "js.hsforms.net",
    "cdn.heapanalytics.com",
    "t.co",
    "platform.twitter.com",
    "sentry.io",
    "browser.sentry-cdn.com",
    "js.sentry-cdn.com",
    "rum.browser-intake-datadoghq.com",
    "plausible.io",
    "cdn.amplitude.com",
    "clarity.ms",
    "www.clarity.ms",
})

# ─── 追踪器脚本关键字（用于内联 script 检测）────────────
TRACKER_KEYWORDS = [
    "google-analytics.com",
    "googletagmanager.com",
    "gtag(",
    "ga('create'",
    "ga('send'",
    "fbq(",
    "hotjar.com",
    "hj(",
    "_hmt.push",             # 百度统计
    "hm.baidu.com",
    "51.la",
    "cnzz.com",
    "umami.is",
]

# ─── Service Worker 关键字 ────────────────────────────────
SW_KEYWORDS = [
    "serviceWorker.register",
    "navigator.serviceWorker",
]

# ─── 需要跳过的 URL 协议 ──────────────────────────────────
SKIP_PROTOCOLS = frozenset({
    "data:",
    "blob:",
    "javascript:",
    "mailto:",
    "tel:",
    "about:",
    "chrome-extension:",
    "moz-extension:",
})

# ─── Stealth JS 脚本 —— 绕过 WebDriver 检测 ─────────────
STEALTH_JS = """
// 覆盖 navigator.webdriver
Object.defineProperty(navigator, 'webdriver', {
    get: () => undefined,
});

// 覆盖 Chrome 运行时
window.chrome = {
    runtime: {},
    loadTimes: function() {},
    csi: function() {},
    app: {},
};

// 覆盖 Permissions API
const originalQuery = window.navigator.permissions.query;
window.navigator.permissions.query = (parameters) => (
    parameters.name === 'notifications' ?
        Promise.resolve({ state: Notification.permission }) :
        originalQuery(parameters)
);

// 覆盖 plugins
Object.defineProperty(navigator, 'plugins', {
    get: () => [1, 2, 3, 4, 5],
});

// 覆盖 languages
Object.defineProperty(navigator, 'languages', {
    get: () => ['zh-CN', 'zh', 'en-US', 'en'],
});

// 防止 iframe 检测
Object.defineProperty(HTMLIFrameElement.prototype, 'contentWindow', {
    get: function() {
        return window;
    }
});
"""

# ─── 深度滚动脚本 —— 触发懒加载 ──────────────────────────
SCROLL_SCRIPT = """
async function autoScroll() {
    return new Promise((resolve) => {
        let totalHeight = 0;
        const distance = 300;
        const delay = %d;  // 滚动间隔毫秒
        const maxScrolls = 200;  // 防止无限滚动
        let scrollCount = 0;
        
        const timer = setInterval(() => {
            const scrollHeight = document.body.scrollHeight;
            window.scrollBy(0, distance);
            totalHeight += distance;
            scrollCount++;
            
            if (totalHeight >= scrollHeight || scrollCount >= maxScrolls) {
                clearInterval(timer);
                // 滚回顶部
                window.scrollTo(0, 0);
                resolve();
            }
        }, delay);
    });
}
await autoScroll();
"""

# ─── 运行时兼容层 Shim —— 注入到克隆页面的 <head> 顶部 ──
# 使用 %s 占位符传入原站 origin（如 https://www.typescriptlang.org）
RUNTIME_SHIM_JS = """
(function() {
    'use strict';
    // ━━━ WebThief Runtime Shim v1.0 ━━━
    // 在所有页面脚本之前执行，修补 file:// 协议下的兼容性问题

    var ORIGINAL_ORIGIN = '%s';
    var ORIGINAL_HOSTNAME = '%s';
    var ORIGINAL_PROTOCOL = '%s';

    // ── 1. 伪造 location 属性（绕过域名校验）──
    try {
        // 拦截 location.href setter 防止跳转
        var _realLocation = window.location;
        var _blockedProps = {
            hostname: ORIGINAL_HOSTNAME,
            host: ORIGINAL_HOSTNAME,
            origin: ORIGINAL_ORIGIN,
            protocol: ORIGINAL_PROTOCOL,
            port: ''
        };

        // 为 document.location 和 window.location 的只读属性创建覆盖
        // 无法直接 defineProperty 在 location 上，用 Proxy 代理 document.location 的读取
        if (typeof Proxy !== 'undefined') {
            var locationProxy = new Proxy(_realLocation, {
                get: function(target, prop) {
                    if (prop in _blockedProps) {
                        return _blockedProps[prop];
                    }
                    var val = target[prop];
                    if (typeof val === 'function') {
                        // 拦截 assign/replace 防止跳转到原站
                        if (prop === 'assign' || prop === 'replace') {
                            return function(url) {
                                if (url && (url.indexOf(ORIGINAL_HOSTNAME) !== -1 || url.indexOf('http') === 0)) {
                                    console.warn('[WebThief Shim] 已拦截跳转:', url);
                                    return;
                                }
                                return target[prop].call(target, url);
                            };
                        }
                        return val.bind(target);
                    }
                    return val;
                },
                set: function(target, prop, value) {
                    // 拦截 location.href = '...' 赋值跳转
                    if (prop === 'href') {
                        if (value && (value.indexOf(ORIGINAL_HOSTNAME) !== -1 || value.indexOf('http') === 0)) {
                            console.warn('[WebThief Shim] 已拦截跳转:', value);
                            return true;
                        }
                    }
                    try { target[prop] = value; } catch(e) {}
                    return true;
                }
            });

            try {
                Object.defineProperty(document, 'location', {
                    get: function() { return locationProxy; },
                    configurable: true
                });
            } catch(e) {}
        }
    } catch(e) {}

    // ── 2. 安全代理 localStorage / sessionStorage ──
    // file:// 下直接调用会抛 SecurityError，用内存 Map 降级
    function createSafeStorage() {
        var store = {};
        return {
            getItem: function(key) { return store.hasOwnProperty(key) ? store[key] : null; },
            setItem: function(key, val) { store[key] = String(val); },
            removeItem: function(key) { delete store[key]; },
            clear: function() { store = {}; },
            get length() { return Object.keys(store).length; },
            key: function(i) { var keys = Object.keys(store); return keys[i] || null; }
        };
    }

    try {
        // 测试 localStorage 是否可用
        window.localStorage.setItem('__webthief_test__', '1');
        window.localStorage.removeItem('__webthief_test__');
    } catch(e) {
        // 不可用，用安全代理替换
        try {
            Object.defineProperty(window, 'localStorage', {
                value: createSafeStorage(), configurable: true, writable: true
            });
        } catch(e2) {}
    }

    try {
        window.sessionStorage.setItem('__webthief_test__', '1');
        window.sessionStorage.removeItem('__webthief_test__');
    } catch(e) {
        try {
            Object.defineProperty(window, 'sessionStorage', {
                value: createSafeStorage(), configurable: true, writable: true
            });
        } catch(e2) {}
    }

    // ── 3. 消除 Service Worker ──
    try {
        if ('serviceWorker' in navigator) {
            Object.defineProperty(navigator, 'serviceWorker', {
                value: undefined, configurable: true, writable: true
            });
        }
    } catch(e) {}

    // ── 4. 全局错误熔断器 ──
    // 捕获所有未处理异常，防止单个 JS 错误导致整页崩溃
    window.addEventListener('error', function(e) {
        console.warn('[WebThief Shim] 已捕获错误:', e.message);
        e.preventDefault();
        return true;
    }, true);

    window.addEventListener('unhandledrejection', function(e) {
        console.warn('[WebThief Shim] 已捕获 Promise 拒绝:', e.reason);
        e.preventDefault();
        return true;
    }, true);

    // ── 5. 拦截 fetch / XMLHttpRequest 对原站的请求 ──
    // 在离线环境下，对外部的网络请求必然失败，静默处理
    var _origFetch = window.fetch;
    window.fetch = function() {
        var url = arguments[0];
        if (typeof url === 'string' && (url.indexOf('http://') === 0 || url.indexOf('https://') === 0)) {
            console.warn('[WebThief Shim] 已拦截外部 fetch:', url);
            return Promise.resolve(new Response('{}', {status: 200, headers: {'Content-Type': 'application/json'}}));
        }
        return _origFetch.apply(this, arguments);
    };

    // ── 6. 阻止 History API 导致的路由错误 ──
    try {
        var _origPushState = history.pushState;
        var _origReplaceState = history.replaceState;
        history.pushState = function() {
            try { return _origPushState.apply(this, arguments); } catch(e) {}
        };
        history.replaceState = function() {
            try { return _origReplaceState.apply(this, arguments); } catch(e) {}
        };
    } catch(e) {}

    console.log('[WebThief Shim] 运行时兼容层已激活');
})();
"""

# ─── SPA 框架特征关键字 ──────────────────────────────────
# 用于检测内联 script 中的 SPA Hydration 启动代码
SPA_HYDRATION_KEYWORDS = [
    # Gatsby
    "window.___loader",
    "window.___webpackCompilationHash",
    "window.___push",
    # Next.js
    "__NEXT_DATA__",
    "_next/static",
    "self.__next_f",
    # Nuxt
    "__NUXT__",
    "window.__NUXT__",
    # React
    "ReactDOM.hydrate",
    "hydrateRoot",
    # Vue
    "__vue_ssr_context__",
    # Angular Universal
    "ng-server-context",
]
