"""
Service Worker 模拟器

拦截 Service Worker 注册，返回模拟对象，防止离线缓存干扰。
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from rich.console import Console

console = Console()


@dataclass
class MockServiceWorkerInfo:
    """模拟的 Service Worker 信息"""

    script_url: str
    scope: str = "/"
    state: str = "activated"


@dataclass
class ServiceWorkerEvent:
    """Service Worker 事件记录"""

    event_type: str
    script_url: str
    timestamp: float
    data: dict[str, Any] = field(default_factory=dict)


class ServiceWorkerSimulator:
    """
    Service Worker 模拟器

    功能：
    - 拦截 Service Worker 注册请求
    - 返回模拟的 Registration 对象
    - 记录 Service Worker 相关事件
    - 支持自定义 Service Worker 行为
    """

    def __init__(
        self,
        storage_dir: str | Path = "./browser_api_storage",
        block_registration: bool = True,
        mock_push_subscription: bool = True,
    ):
        """
        初始化 Service Worker 模拟器

        Args:
            storage_dir: 存储目录
            block_registration: 是否阻止真实的 Service Worker 注册
            mock_push_subscription: 是否模拟 Push 订阅
        """
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        self.block_registration = block_registration
        self.mock_push_subscription = mock_push_subscription

        # 事件记录
        self._events: list[ServiceWorkerEvent] = []

        # 模拟的 Service Worker 注册
        self._registrations: dict[str, MockServiceWorkerInfo] = {}

    def get_injection_script(self) -> str:
        """
        获取 Service Worker 模拟注入脚本

        Returns:
            JavaScript 注入脚本
        """
        return """
(function() {
    'use strict';
    // ━━━ WebThief Service Worker Simulator ━━━

    if (!('serviceWorker' in navigator)) {
        console.log('[WebThief SW] Service Worker 不受支持，跳过模拟');
        return;
    }

    // 存储注册信息
    var __webthief_sw_registrations__ = {};
    var __webthief_sw_events__ = [];

    function recordSWEvent(eventType, scriptUrl, data) {
        __webthief_sw_events__.push({
            type: eventType,
            scriptUrl: scriptUrl,
            timestamp: Date.now(),
            data: data || {}
        });
    }

    // ── Mock ServiceWorker ──
    var MockServiceWorker = function(scriptURL) {
        this.scriptURL = scriptURL;
        this.state = 'activated';
        this.onstatechange = null;
        this.onerror = null;
    };

    MockServiceWorker.prototype = {
        postMessage: function(message) {
            console.log('[WebThief SW] 消息已拦截:', message);
            recordSWEvent('message', this.scriptURL, { message: message });
        },
        addEventListener: function(type, listener) {
            console.log('[WebThief SW] 事件监听已注册:', type);
        },
        removeEventListener: function(type, listener) {}
    };

    // ── Mock PushSubscription ──
    var MockPushSubscription = function() {
        this.endpoint = 'https://webthief.mock.push/subscription';
        this.expirationTime = null;
        this.options = {
            userVisibleOnly: true,
            applicationServerKey: null
        };
    };

    MockPushSubscription.prototype = {
        getKey: function(name) {
            // 返回模拟的密钥
            var mockKey = new Uint8Array(16);
            for (var i = 0; i < 16; i++) {
                mockKey[i] = Math.floor(Math.random() * 256);
            }
            return mockKey.buffer;
        },
        toJSON: function() {
            return {
                endpoint: this.endpoint,
                expirationTime: this.expirationTime,
                keys: {
                    p256dh: 'mock_p256dh_key',
                    auth: 'mock_auth_key'
                }
            };
        },
        unsubscribe: function() {
            return Promise.resolve(true);
        }
    };

    // ── Mock PushManager ──
    var MockPushManager = function() {};

    MockPushManager.prototype = {
        subscribe: function(options) {
            console.log('[WebThief SW] Push 订阅已模拟');
            recordSWEvent('push_subscribe', '', { options: options });
            return Promise.resolve(new MockPushSubscription());
        },
        getSubscription: function() {
            return Promise.resolve(null);
        },
        permissionState: function(options) {
            return Promise.resolve('granted');
        }
    };

    // ── Mock SyncManager ──
    var MockSyncManager = function() {};

    MockSyncManager.prototype = {
        register: function(tag) {
            console.log('[WebThief SW] 后台同步已模拟:', tag);
            recordSWEvent('sync_register', '', { tag: tag });
            return Promise.resolve();
        },
        getTags: function() {
            return Promise.resolve([]);
        }
    };

    // ── Mock ServiceWorkerRegistration ──
    var MockServiceWorkerRegistration = function(scriptURL, options) {
        this._scriptURL = scriptURL;
        this._scope = options && options.scope ? options.scope : '/';
        this.active = new MockServiceWorker(scriptURL);
        this.installing = null;
        this.waiting = null;
        this.navigationPreload = {
            enable: function() {},
            disable: function() {},
            setHeaderValue: function() {},
            getState: function() { return Promise.resolve({ enabled: false }); }
        };
        this.pushManager = new MockPushManager();
        this.sync = new MockSyncManager();
        this.onupdatefound = null;

        __webthief_sw_registrations__[scriptURL] = {
            scriptURL: scriptURL,
            scope: this._scope,
            state: 'activated'
        };
    };

    Object.defineProperty(MockServiceWorkerRegistration.prototype, 'scope', {
        get: function() { return this._scope; }
    });

    MockServiceWorkerRegistration.prototype = Object.create(
        MockServiceWorkerRegistration.prototype,
        {
            unregister: {
                value: function() {
                    console.log('[WebThief SW] 注销已模拟:', this._scriptURL);
                    recordSWEvent('unregister', this._scriptURL, {});
                    delete __webthief_sw_registrations__[this._scriptURL];
                    return Promise.resolve(true);
                }
            },
            update: {
                value: function() {
                    console.log('[WebThief SW] 更新已模拟:', this._scriptURL);
                    recordSWEvent('update', this._scriptURL, {});
                    return Promise.resolve();
                }
            },
            showNotification: {
                value: function(title, options) {
                    console.log('[WebThief SW] 通知已模拟:', title);
                    recordSWEvent('notification', this._scriptURL, { title: title, options: options });
                    return Promise.resolve();
                }
            },
            getNotifications: {
                value: function(options) {
                    return Promise.resolve([]);
                }
            },
            addEventListener: {
                value: function(type, listener) {}
            },
            removeEventListener: {
                value: function(type, listener) {}
            }
        }
    );

    // ── Mock ServiceWorkerContainer ──
    var MockServiceWorkerContainer = function() {
        this._registrations = new Map();
        this._controller = null;
        this._ready = Promise.resolve(null);
    };

    Object.defineProperty(MockServiceWorkerContainer.prototype, 'controller', {
        get: function() { return this._controller; }
    });

    Object.defineProperty(MockServiceWorkerContainer.prototype, 'ready', {
        get: function() { return this._ready; }
    });

    MockServiceWorkerContainer.prototype = Object.create(
        MockServiceWorkerContainer.prototype,
        {
            register: {
                value: function(scriptURL, options) {
                    console.log('[WebThief SW] 注册已拦截:', scriptURL);
                    recordSWEvent('register', scriptURL, { options: options || {} });

                    var registration = new MockServiceWorkerRegistration(scriptURL, options || {});
                    this._registrations.set(scriptURL, registration);

                    // 触发 ready Promise
                    this._ready = Promise.resolve(registration);

                    return Promise.resolve(registration);
                }
            },
            getRegistration: {
                value: function(scope) {
                    for (var url in __webthief_sw_registrations__) {
                        var reg = __webthief_sw_registrations__[url];
                        if (reg.scope === scope) {
                            return Promise.resolve(new MockServiceWorkerRegistration(url, { scope: scope }));
                        }
                    }
                    return Promise.resolve(undefined);
                }
            },
            getRegistrations: {
                value: function() {
                    var regs = [];
                    for (var url in __webthief_sw_registrations__) {
                        var reg = __webthief_sw_registrations__[url];
                        regs.push(new MockServiceWorkerRegistration(url, { scope: reg.scope }));
                    }
                    return Promise.resolve(regs);
                }
            },
            startMessages: {
                value: function() {}
            },
            addEventListener: {
                value: function(type, listener) {}
            },
            removeEventListener: {
                value: function(type, listener) {}
            }
        }
    );

    // ── 替换原生 Service Worker API ──
    try {
        Object.defineProperty(navigator, 'serviceWorker', {
            value: new MockServiceWorkerContainer(),
            configurable: true,
            writable: true
        });
        console.log('[WebThief SW] Service Worker API 已模拟');
    } catch (e) {
        console.warn('[WebThief SW] Service Worker 模拟失败:', e);
    }

    // ── 导出事件记录函数 ──
    window.__webthief_get_sw_events__ = function() {
        return __webthief_sw_events__;
    };

    window.__webthief_get_sw_registrations__ = function() {
        return __webthief_sw_registrations__;
    };

    window.__webthief_clear_sw_events__ = function() {
        __webthief_sw_events__ = [];
    };

    console.log('[WebThief SW] Service Worker 模拟器已激活');
})();
"""

    async def inject_to_page(self, page: Any) -> None:
        """
        将 Service Worker 模拟器注入到页面

        Args:
            page: Playwright Page 对象
        """
        script = self.get_injection_script()
        await page.evaluate(script)
        console.print("[green]  ✓ Service Worker 模拟器已注入[/]")

    async def get_events(self, page: Any) -> list[dict[str, Any]]:
        """
        获取 Service Worker 事件记录

        Args:
            page: Playwright Page 对象

        Returns:
            事件记录列表
        """
        try:
            events = await page.evaluate("() => window.__webthief_get_sw_events__?.() || []")
            return events
        except Exception:
            return []

    async def get_registrations(self, page: Any) -> dict[str, Any]:
        """
        获取模拟的 Service Worker 注册信息

        Args:
            page: Playwright Page 对象

        Returns:
            注册信息字典
        """
        try:
            registrations = await page.evaluate("() => window.__webthief_get_sw_registrations__?.() || {}")
            return registrations
        except Exception:
            return {}

    async def clear_events(self, page: Any) -> None:
        """
        清除事件记录

        Args:
            page: Playwright Page 对象
        """
        try:
            await page.evaluate("() => window.__webthief_clear_sw_events__?.()")
        except Exception:
            pass

    def save_events_to_file(self, events: list[dict[str, Any]], filename: str = "sw_events.json") -> Path:
        """
        保存事件记录到文件

        Args:
            events: 事件记录
            filename: 文件名

        Returns:
            文件路径
        """
        filepath = self.storage_dir / filename
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(events, f, ensure_ascii=False, indent=2)
        return filepath

    def print_summary(self, events: list[dict[str, Any]]) -> None:
        """
        打印事件摘要

        Args:
            events: 事件记录
        """
        if not events:
            console.print("[yellow]  无 Service Worker 事件记录[/]")
            return

        from rich.table import Table

        table = Table(title=f"Service Worker 事件摘要 (共 {len(events)} 条)")
        table.add_column("事件类型", style="cyan")
        table.add_column("脚本 URL", style="green")
        table.add_column("时间戳", style="dim")

        for event in events:
            script_url = event.get("scriptUrl", "")
            if len(script_url) > 50:
                script_url = script_url[:47] + "..."
            table.add_row(
                event.get("type", "unknown"),
                script_url,
                str(event.get("timestamp", 0))
            )

        console.print(table)
