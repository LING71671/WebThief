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

    // ── 5. fetch / XHR 本地镜像资源代理 ──
    // 优先将请求映射到本地已下载资源，减少离线 CORS 与空白数据块
    function toAbsoluteRequestUrl(input) {
        try {
            if (typeof input === 'string') {
                return new URL(input, ORIGINAL_ORIGIN).href;
            }
            if (typeof Request !== 'undefined' && input instanceof Request) {
                return new URL(input.url, ORIGINAL_ORIGIN).href;
            }
            if (input && input.url) {
                return new URL(input.url, ORIGINAL_ORIGIN).href;
            }
        } catch (e) {}
        return '';
    }

    function pushUnique(arr, value) {
        if (!value || typeof value !== 'string') return;
        if (arr.indexOf(value) === -1) {
            arr.push(value);
        }
    }

    function addLookupCandidates(target, rawValue) {
        if (!rawValue || typeof rawValue !== 'string') return;
        var value = rawValue.trim();
        if (!value) return;

        pushUnique(target, value);

        var noHash = value.split('#')[0];
        pushUnique(target, noHash);

        var noQuery = noHash.split('?')[0];
        pushUnique(target, noQuery);

        try {
            var parsed = new URL(noHash, ORIGINAL_ORIGIN);
            var absolute = parsed.href;
            pushUnique(target, absolute);

            var absoluteNoHash = absolute.split('#')[0];
            pushUnique(target, absoluteNoHash);

            var absoluteNoQuery = absoluteNoHash.split('?')[0];
            pushUnique(target, absoluteNoQuery);

            var path = parsed.pathname || '/';
            var pathWithQuery = parsed.search ? (path + parsed.search) : path;

            pushUnique(target, pathWithQuery);
            pushUnique(target, path);

            if (pathWithQuery.startsWith('/')) {
                var relWithQuery = pathWithQuery.slice(1);
                pushUnique(target, relWithQuery);
                pushUnique(target, './' + relWithQuery);
            }

            if (path.startsWith('/')) {
                var relPath = path.slice(1);
                pushUnique(target, relPath);
                pushUnique(target, './' + relPath);
            }
        } catch (e) {}
    }

    function resolveMappedResource(input) {
        try {
            var resourceMap = window.__WEBTHIEF_RESOURCE_MAP__ || {};
            var direct = '';
            if (typeof input === 'string') {
                direct = input.trim();
            } else if (input && typeof input.url === 'string') {
                direct = input.url.trim();
            }

            var candidates = [];
            if (direct) {
                addLookupCandidates(candidates, direct);
            }

            var absolute = toAbsoluteRequestUrl(input);
            if (absolute) {
                addLookupCandidates(candidates, absolute);
            }

            for (var i = 0; i < candidates.length; i++) {
                var candidate = candidates[i];
                if (candidate && resourceMap[candidate]) {
                    return resourceMap[candidate];
                }
            }

            return '';
        } catch (e) {
            return '';
        }
    }

    function resolveCachedResponse(input) {
        try {
            var responseMap = window.__WEBTHIEF_RESPONSE_MAP__ || {};
            var direct = '';
            if (typeof input === 'string') {
                direct = input.trim();
            } else if (input && typeof input.url === 'string') {
                direct = input.url.trim();
            }

            var candidates = [];
            if (direct) {
                addLookupCandidates(candidates, direct);
            }

            var absolute = toAbsoluteRequestUrl(input);
            if (absolute) {
                addLookupCandidates(candidates, absolute);
            }

            for (var i = 0; i < candidates.length; i++) {
                var candidate = candidates[i];
                if (candidate && responseMap[candidate]) {
                    return responseMap[candidate];
                }
            }
            return null;
        } catch (e) {
            return null;
        }
    }

    function remapSrcsetValue(srcset) {
        if (!srcset || typeof srcset !== 'string') return srcset;
        var parts = srcset.split(',');
        for (var i = 0; i < parts.length; i++) {
            var entry = parts[i].trim();
            if (!entry) continue;
            var tokens = entry.split(/\\s+/);
            if (!tokens.length) continue;
            var mapped = resolveMappedResource(tokens[0]);
            if (mapped) {
                tokens[0] = mapped;
                parts[i] = tokens.join(' ');
            }
        }
        return parts.join(', ');
    }

    function remapUrlForDom(url) {
        if (!url || typeof url !== 'string') return url;
        var mapped = resolveMappedResource(url);
        return mapped || url;
    }

    function patchUrlSetter(prototypeObj, propName, isSrcset) {
        try {
            if (!prototypeObj) return;
            var desc = Object.getOwnPropertyDescriptor(prototypeObj, propName);
            if (!desc || typeof desc.set !== 'function') return;
            Object.defineProperty(prototypeObj, propName, {
                configurable: true,
                enumerable: desc.enumerable,
                get: function() {
                    if (typeof desc.get === 'function') {
                        return desc.get.call(this);
                    }
                    return undefined;
                },
                set: function(value) {
                    var nextValue = isSrcset ? remapSrcsetValue(value) : remapUrlForDom(value);
                    return desc.set.call(this, nextValue);
                }
            });
        } catch (e) {}
    }

    patchUrlSetter(window.HTMLImageElement && window.HTMLImageElement.prototype, 'src', false);
    patchUrlSetter(window.HTMLScriptElement && window.HTMLScriptElement.prototype, 'src', false);
    patchUrlSetter(window.HTMLLinkElement && window.HTMLLinkElement.prototype, 'href', false);
    patchUrlSetter(window.HTMLSourceElement && window.HTMLSourceElement.prototype, 'src', false);
    patchUrlSetter(window.HTMLSourceElement && window.HTMLSourceElement.prototype, 'srcset', true);
    patchUrlSetter(window.HTMLVideoElement && window.HTMLVideoElement.prototype, 'src', false);
    patchUrlSetter(window.HTMLVideoElement && window.HTMLVideoElement.prototype, 'poster', false);
    patchUrlSetter(window.HTMLAudioElement && window.HTMLAudioElement.prototype, 'src', false);

    var _origSetAttribute = Element.prototype.setAttribute;
    Element.prototype.setAttribute = function(name, value) {
        try {
            var attr = String(name || '').toLowerCase();
            if (typeof value === 'string') {
                if (attr === 'src' || attr === 'poster' || attr === 'data-src' || attr === 'data-original' || attr === 'data-bg' || attr === 'data-background') {
                    value = remapUrlForDom(value);
                } else if (attr === 'srcset') {
                    value = remapSrcsetValue(value);
                } else if (attr === 'href') {
                    var tagName = (this.tagName || '').toLowerCase();
                    if (tagName === 'link') {
                        value = remapUrlForDom(value);
                    }
                }
            }
        } catch (e) {}
        return _origSetAttribute.call(this, name, value);
    };

    function remapExistingDomUrls() {
        try {
            var selectors = [
                'img[src]', 'img[data-src]', 'img[data-original]',
                'script[src]', 'link[href]',
                'source[src]', 'source[srcset]',
                'video[src]', 'video[poster]', 'audio[src]',
                '[data-bg]', '[data-background]'
            ];
            document.querySelectorAll(selectors.join(',')).forEach(function(el) {
                var tagName = (el.tagName || '').toLowerCase();
                if (el.hasAttribute('src')) {
                    var srcVal = el.getAttribute('src');
                    var mappedSrc = remapUrlForDom(srcVal);
                    if (mappedSrc && mappedSrc !== srcVal) {
                        el.setAttribute('src', mappedSrc);
                    }
                }
                if (el.hasAttribute('poster')) {
                    var posterVal = el.getAttribute('poster');
                    var mappedPoster = remapUrlForDom(posterVal);
                    if (mappedPoster && mappedPoster !== posterVal) {
                        el.setAttribute('poster', mappedPoster);
                    }
                }
                if (el.hasAttribute('srcset')) {
                    var srcsetVal = el.getAttribute('srcset');
                    var mappedSrcset = remapSrcsetValue(srcsetVal);
                    if (mappedSrcset && mappedSrcset !== srcsetVal) {
                        el.setAttribute('srcset', mappedSrcset);
                    }
                }
                if (tagName === 'link' && el.hasAttribute('href')) {
                    var hrefVal = el.getAttribute('href');
                    var mappedHref = remapUrlForDom(hrefVal);
                    if (mappedHref && mappedHref !== hrefVal) {
                        el.setAttribute('href', mappedHref);
                    }
                }
                if (el.hasAttribute('data-src')) {
                    var dsrc = el.getAttribute('data-src');
                    var mappedDsrc = remapUrlForDom(dsrc);
                    if (mappedDsrc && mappedDsrc !== dsrc) {
                        el.setAttribute('data-src', mappedDsrc);
                    }
                }
                if (el.hasAttribute('data-original')) {
                    var dorig = el.getAttribute('data-original');
                    var mappedDorig = remapUrlForDom(dorig);
                    if (mappedDorig && mappedDorig !== dorig) {
                        el.setAttribute('data-original', mappedDorig);
                    }
                }
                if (el.hasAttribute('data-bg')) {
                    var dbg = el.getAttribute('data-bg');
                    var mappedDbg = remapUrlForDom(dbg);
                    if (mappedDbg && mappedDbg !== dbg) {
                        el.setAttribute('data-bg', mappedDbg);
                        if (!el.style.backgroundImage || el.style.backgroundImage === 'none') {
                            el.style.backgroundImage = 'url(\"' + mappedDbg + '\")';
                        }
                    }
                }
                if (el.hasAttribute('data-background')) {
                    var db = el.getAttribute('data-background');
                    var mappedDb = remapUrlForDom(db);
                    if (mappedDb && mappedDb !== db) {
                        el.setAttribute('data-background', mappedDb);
                        if (!el.style.backgroundImage || el.style.backgroundImage === 'none') {
                            el.style.backgroundImage = 'url(\"' + mappedDb + '\")';
                        }
                    }
                }
            });
        } catch (e) {}
    }

    try { remapExistingDomUrls(); } catch (e) {}
    document.addEventListener('DOMContentLoaded', remapExistingDomUrls);
    window.addEventListener('load', remapExistingDomUrls);

    var _origFetch = window.fetch;
    if (typeof _origFetch === 'function') {
        window.fetch = function(input, init) {
            var cached = resolveCachedResponse(input);
            if (cached && typeof cached.body === 'string' && typeof Response !== 'undefined') {
                try {
                    return Promise.resolve(
                        new Response(cached.body, {
                            status: 200,
                            headers: {
                                'Content-Type': cached.contentType || 'application/json'
                            }
                        })
                    );
                } catch (e) {}
            }

            var mapped = resolveMappedResource(input);
            if (mapped) {
                // 本地镜像资源统一按 GET 读取，避免原请求 method/body 导致离线失败
                var nextInit = {};
                if (init && typeof init === 'object') {
                    for (var k in init) {
                        nextInit[k] = init[k];
                    }
                }
                nextInit.method = 'GET';
                if ('body' in nextInit) {
                    try { delete nextInit.body; } catch (e) { nextInit.body = undefined; }
                }
                if (!nextInit.credentials) {
                    nextInit.credentials = 'same-origin';
                }
                return _origFetch.call(this, mapped, nextInit);
            }
            return _origFetch.apply(this, arguments);
        };
    }

    if (window.XMLHttpRequest && window.XMLHttpRequest.prototype) {
        var _origXHROpen = window.XMLHttpRequest.prototype.open;
        var _origXHRSend = window.XMLHttpRequest.prototype.send;
        function defineReadonlyProp(obj, key, value) {
            try {
                Object.defineProperty(obj, key, { value: value, configurable: true });
            } catch (e) {
                try { obj[key] = value; } catch (e2) {}
            }
        }
        function triggerXHRCallbacks(xhr) {
            try {
                if (typeof xhr.onreadystatechange === 'function') {
                    xhr.onreadystatechange();
                }
            } catch (e) {}
            try {
                if (typeof xhr.onload === 'function') {
                    xhr.onload();
                }
            } catch (e) {}
            try {
                if (typeof xhr.dispatchEvent === 'function') {
                    xhr.dispatchEvent(new Event('readystatechange'));
                    xhr.dispatchEvent(new Event('load'));
                    xhr.dispatchEvent(new Event('loadend'));
                }
            } catch (e) {}
        }
        window.XMLHttpRequest.prototype.open = function(method, url) {
            var cachedPayload = resolveCachedResponse(url);
            this.__webthief_cached_payload__ = cachedPayload;
            this.__webthief_cached_content_type__ = (
                cachedPayload && cachedPayload.contentType
            ) ? cachedPayload.contentType : 'application/json';
            this.__webthief_original_url__ = url;
            var mapped = resolveMappedResource(url);
            if (mapped) {
                arguments[0] = 'GET';
                arguments[1] = mapped;
                this.__webthief_mapped_local__ = true;
            } else {
                this.__webthief_mapped_local__ = false;
            }
            return _origXHROpen.apply(this, arguments);
        };
        window.XMLHttpRequest.prototype.send = function(body) {
            if (this.__webthief_cached_payload__ && typeof this.__webthief_cached_payload__.body === 'string') {
                var payload = this.__webthief_cached_payload__;
                var contentType = this.__webthief_cached_content_type__ || 'application/json';
                var xhr = this;
                setTimeout(function() {
                    var bodyText = String(payload.body || '');
                    defineReadonlyProp(xhr, 'readyState', 4);
                    defineReadonlyProp(xhr, 'status', 200);
                    defineReadonlyProp(xhr, 'statusText', 'OK');
                    defineReadonlyProp(xhr, 'responseText', bodyText);
                    defineReadonlyProp(xhr, 'responseURL', String(xhr.__webthief_original_url__ || ''));

                    var responseValue = bodyText;
                    try {
                        if (xhr.responseType === 'json') {
                            responseValue = JSON.parse(bodyText);
                        }
                    } catch (e) {
                        responseValue = null;
                    }
                    defineReadonlyProp(xhr, 'response', responseValue);

                    xhr.getResponseHeader = function(name) {
                        if (!name) return null;
                        if (String(name).toLowerCase() === 'content-type') {
                            return contentType;
                        }
                        return null;
                    };
                    xhr.getAllResponseHeaders = function() {
                        return 'content-type: ' + contentType + '\\r\\n';
                    };
                    triggerXHRCallbacks(xhr);
                }, 0);
                return;
            }

            if (this.__webthief_mapped_local__) {
                return _origXHRSend.call(this, null);
            }
            return _origXHRSend.apply(this, arguments);
        };
    }

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

    // ── 10. ES Module 动态导入补丁 ──
    // 修复 file:// 协议下 import() CORS 错误
    // 注意：JS 文件中的 import() 已被替换为 __webthief_import__()
    (function() {
        if (typeof window === 'undefined') return;
        
        // 模块缓存，避免重复加载
        window.__webthief_module_cache__ = window.__webthief_module_cache__ || {};
        
        // 自定义导入函数
        window.__webthief_import__ = function(specifier) {
            return new Promise(function(resolve, reject) {
                // 如果已经在缓存中，直接返回
                if (window.__webthief_module_cache__[specifier]) {
                    return resolve(window.__webthief_module_cache__[specifier]);
                }
                
                // 处理相对路径，转换为本地路径
                var url = specifier;
                if (url.startsWith('./') || url.startsWith('../')) {
                    // 尝试通过本地资源映射解析
                    var mapped = resolveMappedResource(url);
                    if (mapped) {
                        url = mapped;
                    }
                }
                
                // 使用 fetch + eval 方式加载模块
                fetch(url)
                    .then(function(response) {
                        if (!response.ok) {
                            throw new Error('HTTP ' + response.status);
                        }
                        return response.text();
                    })
                    .then(function(code) {
                        // 包装为模块格式
                        var moduleExports = {};
                        var moduleContext = {
                            exports: moduleExports,
                            __esModule: true,
                            default: {}
                        };
                        
                        try {
                            // 使用 Function 构造器执行代码
                            var wrappedCode = '(function(module, exports, __webpack_require__) {\\n' + code + '\\n})(moduleContext, moduleExports, window.__webpack_require__);';
                            var fn = new Function('moduleContext', 'moduleExports', wrappedCode);
                            fn(moduleContext, moduleExports);
                            
                            // 缓存并返回
                            var result = moduleExports.default || moduleExports;
                            window.__webthief_module_cache__[specifier] = result;
                            resolve(result);
                        } catch (e) {
                            console.warn('[WebThief Shim] 模块执行错误:', specifier, e);
                            // 返回空对象，避免应用崩溃
                            var emptyModule = { default: {} };
                            window.__webthief_module_cache__[specifier] = emptyModule;
                            resolve(emptyModule);
                        }
                    })
                    .catch(function(err) {
                        console.warn('[WebThief Shim] 模块加载失败:', specifier, err);
                        // 返回空对象，避免应用崩溃
                        var emptyModule = { default: {} };
                        window.__webthief_module_cache__[specifier] = emptyModule;
                        resolve(emptyModule);
                    });
            });
        };
    })();

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
