"""
实时二维码拦截与克隆模块
目标：捕获动态生成的二维码，保留其刷新逻辑和官方通信能力
"""

from __future__ import annotations

import re
import base64
from typing import Any
from urllib.parse import urlparse

from playwright.async_api import Page, Route, Request
from rich.console import Console

console = Console()


class QRInterceptor:
    """
    二维码拦截器
    负责：
    1. 识别二维码生成脚本
    2. 拦截二维码 API 请求
    3. 保留刷新逻辑
    4. 注入代理层使克隆页面能与官方服务器通信
    """

    def __init__(self):
        self.qr_scripts: list[str] = []
        self.qr_api_endpoints: set[str] = set()
        self.qr_images: dict[str, bytes] = {}
        self.auth_tokens: dict[str, str] = {}

    async def inject_qr_proxy(self, page: Page) -> None:
        """
        注入二维码代理层脚本
        在页面加载前注入，拦截所有二维码相关的 API 调用
        """
        console.print("[cyan]  🔐 注入二维码代理层...[/]")

        proxy_script = """
        (function() {
            'use strict';
            // ━━━ WebThief QR Code Proxy Layer ━━━
            
            // 存储原始 fetch 和 XMLHttpRequest
            const _origFetch = window.fetch;
            const _origXHR = window.XMLHttpRequest;
            
            // 二维码 API 特征关键字
            const QR_KEYWORDS = [
                'qrcode', 'qr_code', 'login/qr', 'auth/qr',
                'getqr', 'qrlogin', 'qrscan', 'qrcheck',
                'steamqr', 'wechatqr', 'qqlogin'
            ];
            
            // 检测 URL 是否为二维码相关
            function isQRUrl(url) {
                const urlLower = url.toLowerCase();
                return QR_KEYWORDS.some(kw => urlLower.includes(kw));
            }
            
            // 拦截 fetch
            window.fetch = function(url, options) {
                const urlStr = typeof url === 'string' ? url : url.url;
                
                if (isQRUrl(urlStr)) {
                    console.log('[WebThief QR Proxy] 拦截二维码 API:', urlStr);
                    
                    // 标记为二维码请求
                    window.__webthief_qr_requests = window.__webthief_qr_requests || [];
                    window.__webthief_qr_requests.push({
                        url: urlStr,
                        method: options?.method || 'GET',
                        timestamp: Date.now()
                    });
                }
                
                // 继续原始请求
                return _origFetch.apply(this, arguments);
            };
            
            // 拦截 XMLHttpRequest
            const XHRProto = _origXHR.prototype;
            const _origOpen = XHRProto.open;
            const _origSend = XHRProto.send;
            
            XHRProto.open = function(method, url) {
                this._webthief_url = url;
                this._webthief_method = method;
                
                if (isQRUrl(url)) {
                    console.log('[WebThief QR Proxy] 拦截 XHR 二维码请求:', url);
                    
                    window.__webthief_qr_requests = window.__webthief_qr_requests || [];
                    window.__webthief_qr_requests.push({
                        url: url,
                        method: method,
                        timestamp: Date.now()
                    });
                }
                
                return _origOpen.apply(this, arguments);
            };
            
            // 拦截二维码图片生成
            const _origCreateElement = document.createElement;
            document.createElement = function(tagName) {
                const el = _origCreateElement.call(document, tagName);
                
                if (tagName.toLowerCase() === 'img') {
                    // 监听 src 变化
                    const _origSrcSetter = Object.getOwnPropertyDescriptor(HTMLImageElement.prototype, 'src').set;
                    Object.defineProperty(el, 'src', {
                        set: function(value) {
                            if (value && (value.startsWith('data:image') || value.startsWith('blob:'))) {
                                // 可能是二维码
                                console.log('[WebThief QR Proxy] 检测到动态图片:', value.substring(0, 50));
                                
                                window.__webthief_qr_images = window.__webthief_qr_images || [];
                                window.__webthief_qr_images.push({
                                    src: value,
                                    timestamp: Date.now()
                                });
                            }
                            return _origSrcSetter.call(this, value);
                        },
                        get: function() {
                            return this.getAttribute('src');
                        }
                    });
                }
                
                return el;
            };
            
            // 拦截 Canvas toDataURL（二维码生成库常用）
            const _origToDataURL = HTMLCanvasElement.prototype.toDataURL;
            HTMLCanvasElement.prototype.toDataURL = function() {
                const result = _origToDataURL.apply(this, arguments);
                
                // 检测是否为二维码（简单启发式：正方形 canvas）
                if (this.width === this.height && this.width >= 100 && this.width <= 500) {
                    console.log('[WebThief QR Proxy] 检测到 Canvas 二维码生成');
                    
                    window.__webthief_qr_canvas = window.__webthief_qr_canvas || [];
                    window.__webthief_qr_canvas.push({
                        dataUrl: result,
                        width: this.width,
                        height: this.height,
                        timestamp: Date.now()
                    });
                }
                
                return result;
            };
            
            console.log('[WebThief QR Proxy] 二维码代理层已激活');
        })();
        """

        await page.add_init_script(proxy_script)

    async def capture_qr_lifecycle(self, page: Page) -> dict[str, Any]:
        """
        捕获二维码的完整生命周期
        返回：二维码请求、图片、刷新逻辑等信息
        """
        console.print("[cyan]  📸 捕获二维码生命周期...[/]")

        # 等待页面稳定
        try:
            await page.wait_for_load_state("networkidle", timeout=10000)
        except Exception:
            pass

        # 提取拦截到的数据
        qr_data = await page.evaluate("""
            () => ({
                requests: window.__webthief_qr_requests || [],
                images: window.__webthief_qr_images || [],
                canvas: window.__webthief_qr_canvas || []
            })
        """)

        console.print(f"[green]  ✓ 捕获 {len(qr_data['requests'])} 个二维码 API 请求[/]")
        console.print(f"[green]  ✓ 捕获 {len(qr_data['images'])} 个二维码图片[/]")
        console.print(f"[green]  ✓ 捕获 {len(qr_data['canvas'])} 个 Canvas 二维码[/]")

        return qr_data

    async def preserve_qr_scripts(self, page: Page) -> list[str]:
        """
        识别并保留二维码核心脚本
        返回需要保留的脚本 URL 列表
        """
        console.print("[cyan]  🔍 识别二维码核心脚本...[/]")

        # 提取所有脚本
        scripts = await page.evaluate("""
            () => {
                const scripts = [];
                document.querySelectorAll('script[src]').forEach(script => {
                    scripts.push({
                        src: script.src,
                        async: script.async,
                        defer: script.defer
                    });
                });
                return scripts;
            }
        """)

        # 识别二维码相关脚本
        qr_keywords = ['qr', 'login', 'auth', 'scan', 'code']
        preserved_scripts = []

        for script in scripts:
            src = script['src'].lower()
            if any(kw in src for kw in qr_keywords):
                preserved_scripts.append(script['src'])
                console.print(f"[dim]  📦 保留脚本: {script['src']}[/]")

        return preserved_scripts

    def generate_qr_bridge_script(self, original_domain: str) -> str:
        """
        生成二维码桥接脚本
        使克隆页面能够与原站服务器通信
        """
        bridge_script = f"""
        (function() {{
            'use strict';
            // ━━━ WebThief QR Bridge Script ━━━
            
            const ORIGINAL_DOMAIN = '{original_domain}';
            
            // 创建 CORS 代理
            function createCORSProxy(url) {{
                // 如果是相对路径，补全为原站域名
                if (url.startsWith('/')) {{
                    return ORIGINAL_DOMAIN + url;
                }}
                return url;
            }}
            
            // 重写 fetch 以支持跨域二维码请求
            const _origFetch = window.fetch;
            window.fetch = function(url, options) {{
                const urlStr = typeof url === 'string' ? url : url.url;
                
                // 检测二维码 API
                const qrKeywords = ['qrcode', 'qr_code', 'login/qr', 'auth/qr'];
                const isQRRequest = qrKeywords.some(kw => urlStr.toLowerCase().includes(kw));
                
                if (isQRRequest) {{
                    const proxiedUrl = createCORSProxy(urlStr);
                    console.log('[WebThief QR Bridge] 代理二维码请求:', proxiedUrl);
                    
                    // 添加 CORS 头
                    const newOptions = {{
                        ...options,
                        mode: 'cors',
                        credentials: 'include'
                    }};
                    
                    return _origFetch(proxiedUrl, newOptions);
                }}
                
                return _origFetch.apply(this, arguments);
            }};
            
            // 定时刷新二维码（如果页面有刷新逻辑）
            window.__webthief_qr_refresh = function() {{
                console.log('[WebThief QR Bridge] 触发二维码刷新');
                
                // 查找二维码刷新函数（常见命名）
                const refreshFunctions = [
                    'refreshQRCode', 'updateQRCode', 'getNewQRCode',
                    'qrRefresh', 'reloadQR', 'fetchQRCode'
                ];
                
                for (const fnName of refreshFunctions) {{
                    if (typeof window[fnName] === 'function') {{
                        console.log('[WebThief QR Bridge] 调用刷新函数:', fnName);
                        window[fnName]();
                        return true;
                    }}
                }}
                
                return false;
            }};
            
            console.log('[WebThief QR Bridge] 二维码桥接脚本已激活');
        }})();
        """
        return bridge_script
