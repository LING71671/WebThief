"""
浏览器 API 模拟器核心模块

提供浏览器原生 API 的模拟和垫片功能，用于在离线环境下
模拟真实浏览器 API 行为，确保克隆页面正常运行。
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional, Union

from rich.console import Console
from rich.table import Table

console = Console()


@dataclass
class APICallRecord:
    """API 调用记录"""

    api_name: str
    method: str
    args: list[Any]
    kwargs: dict[str, Any]
    result: Any
    timestamp: float
    duration_ms: float
    success: bool
    error: Optional[str] = None


@dataclass
class GeolocationConfig:
    """地理位置配置"""

    latitude: float = 39.9042  # 北京
    longitude: float = 116.4074
    accuracy: float = 100.0
    altitude: Optional[float] = None
    altitude_accuracy: Optional[float] = None
    heading: Optional[float] = None
    speed: Optional[float] = None


@dataclass
class NotificationConfig:
    """通知配置"""

    permission: str = "granted"  # granted, denied, default
    max_notifications: int = 10


@dataclass
class CryptoConfig:
    """加密 API 配置"""

    enabled: bool = True
    mock_subtle: bool = True


class BrowserAPISimulator:
    """
    浏览器 API 模拟器

    注入 API 垫片到页面，模拟浏览器原生 API 行为：
    - Service Worker 拦截和模拟
    - IndexedDB 文件存储模拟
    - Web Crypto API 模拟
    - Notification API 模拟
    - Geolocation API 模拟
    - API 调用记录和回放
    """

    def __init__(
        self,
        storage_dir: str | Path = "./browser_api_storage",
        geolocation: Optional[GeolocationConfig] = None,
        notification: Optional[NotificationConfig] = None,
        crypto: Optional[CryptoConfig] = None,
        record_calls: bool = True,
        max_records: int = 1000,
    ):
        """
        初始化浏览器 API 模拟器

        Args:
            storage_dir: 存储目录
            geolocation: 地理位置配置
            notification: 通知配置
            crypto: 加密 API 配置
            record_calls: 是否记录 API 调用
            max_records: 最大记录数
        """
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        self.geolocation = geolocation or GeolocationConfig()
        self.notification = notification or NotificationConfig()
        self.crypto = crypto or CryptoConfig()

        self.record_calls = record_calls
        self.max_records = max_records

        # API 调用记录
        self._call_records: list[APICallRecord] = []

        # 状态存储
        self._state: dict[str, Any] = {}

        # 加载已保存的状态
        self._load_state()

    def _load_state(self) -> None:
        """加载已保存的状态"""
        state_file = self.storage_dir / "api_state.json"
        if state_file.exists():
            try:
                with open(state_file, "r", encoding="utf-8") as f:
                    self._state = json.load(f)
            except Exception:
                self._state = {}

    def _save_state(self) -> None:
        """保存状态"""
        state_file = self.storage_dir / "api_state.json"
        try:
            with open(state_file, "w", encoding="utf-8") as f:
                json.dump(self._state, f, ensure_ascii=False, indent=2)
        except Exception as e:
            console.print(f"[yellow]  ⚠ 保存状态失败: {e}[/]")

    def get_injection_script(self) -> str:
        """
        获取完整的 API 垫片注入脚本

        Returns:
            JavaScript 注入脚本
        """
        return self._generate_shim_script()

    def _generate_shim_script(self) -> str:
        """生成垫片脚本"""
        return f"""
(function() {{
    'use strict';
    // ━━━ WebThief Browser API Simulator v1.0 ━━━

    var __webthief_api_records__ = [];
    var __webthief_max_records__ = {self.max_records};

    function recordAPICall(apiName, method, args, result, duration, success, error) {{
        if (__webthief_api_records__.length >= __webthief_max_records__) {{
            __webthief_api_records__.shift();
        }}
        __webthief_api_records__.push({{
            api: apiName,
            method: method,
            args: args ? Array.from(args).map(function(a) {{
                try {{ return JSON.stringify(a); }} catch(e) {{ return String(a); }}
            }}) : [],
            result: result,
            duration: duration,
            timestamp: Date.now(),
            success: success,
            error: error
        }});
    }}

    function wrapAsyncAPICall(apiName, method, fn) {{
        return function() {{
            var args = arguments;
            var startTime = performance.now();
            try {{
                var result = fn.apply(this, args);
                if (result && typeof result.then === 'function') {{
                    return result.then(function(r) {{
                        recordAPICall(apiName, method, args, r, performance.now() - startTime, true);
                        return r;
                    }}).catch(function(e) {{
                        recordAPICall(apiName, method, args, null, performance.now() - startTime, false, String(e));
                        throw e;
                    }});
                }}
                recordAPICall(apiName, method, args, result, performance.now() - startTime, true);
                return result;
            }} catch (e) {{
                recordAPICall(apiName, method, args, null, performance.now() - startTime, false, String(e));
                throw e;
            }}
        }};
    }}

    // ── 1. Service Worker 模拟 ──
    (function() {{
        if (!('serviceWorker' in navigator)) return;

        var MockServiceWorkerContainer = function() {{
            this._registrations = new Map();
            this._controller = null;
            this._ready = Promise.resolve(null);
        }};

        MockServiceWorkerContainer.prototype = {{
            get controller() {{ return this._controller; }},
            get ready() {{ return this._ready; }},
            get oncontrollerchange() {{ return null; }},
            set oncontrollerchange(v) {{}},

            register: wrapAsyncAPICall('ServiceWorker', 'register', function(scriptURL, options) {{
                console.log('[WebThief API] Service Worker 注册已拦截:', scriptURL);
                var registration = new MockServiceWorkerRegistration(scriptURL, options);
                this._registrations.set(scriptURL, registration);
                return Promise.resolve(registration);
            }}),

            getRegistration: wrapAsyncAPICall('ServiceWorker', 'getRegistration', function(scope) {{
                return Promise.resolve(this._registrations.get(scope) || null);
            }}),

            getRegistrations: wrapAsyncAPICall('ServiceWorker', 'getRegistrations', function() {{
                return Promise.resolve(Array.from(this._registrations.values()));
            }}),

            startMessages: function() {{}},

            addEventListener: function() {{}},
            removeEventListener: function() {{}}
        }};

        var MockServiceWorkerRegistration = function(scriptURL, options) {{
            this._scriptURL = scriptURL;
            this._scope = options && options.scope || '/';
            this.active = new MockServiceWorker(scriptURL);
            this.installing = null;
            this.waiting = null;
            this.onupdatefound = null;
        }};

        MockServiceWorkerRegistration.prototype = {{
            get scope() {{ return this._scope; }},
            get navigationPreload() {{ return {{ enable: function() {{}}, disable: function() {{}}, setHeaderValue: function() {{}} }}; }},

            unregister: wrapAsyncAPICall('ServiceWorkerRegistration', 'unregister', function() {{
                return Promise.resolve(true);
            }}),

            update: wrapAsyncAPICall('ServiceWorkerRegistration', 'update', function() {{
                return Promise.resolve();
            }}),

            showNotification: wrapAsyncAPICall('ServiceWorkerRegistration', 'showNotification', function(title, options) {{
                console.log('[WebThief API] 通知已模拟:', title);
                return Promise.resolve();
            }}),

            getNotifications: wrapAsyncAPICall('ServiceWorkerRegistration', 'getNotifications', function() {{
                return Promise.resolve([]);
            }}),

            addEventListener: function() {{}},
            removeEventListener: function() {{}}
        }};

        var MockServiceWorker = function(scriptURL) {{
            this.scriptURL = scriptURL;
            this.state = 'activated';
            this.onstatechange = null;
            this.onerror = null;
        }};

        MockServiceWorker.prototype = {{
            postMessage: function(message) {{
                console.log('[WebThief API] Service Worker 消息已拦截:', message);
            }},
            addEventListener: function() {{}},
            removeEventListener: function() {{}}
        }};

        try {{
            Object.defineProperty(navigator, 'serviceWorker', {{
                value: new MockServiceWorkerContainer(),
                configurable: true,
                writable: true
            }});
            console.log('[WebThief API] Service Worker API 已模拟');
        }} catch (e) {{
            console.warn('[WebThief API] Service Worker 模拟失败:', e);
        }}
    }})();

    // ── 2. IndexedDB 模拟 ──
    (function() {{
        var __webthief_idb_databases__ = {{}};
        var __webthief_idb_storage__ = {{}};

        try {{
            var savedData = localStorage.getItem('__webthief_idb_data__');
            if (savedData) {{
                __webthief_idb_storage__ = JSON.parse(savedData);
            }}
        }} catch (e) {{}}

        function saveIDBData() {{
            try {{
                localStorage.setItem('__webthief_idb_data__', JSON.stringify(__webthief_idb_storage__));
            }} catch (e) {{}}
        }}

        var MockIDBRequest = function() {{
            this.result = null;
            this.error = null;
            this.source = null;
            this.transaction = null;
            this.readyState = 'pending';
            this._onsuccess = null;
            this._onerror = null;
        }};

        Object.defineProperty(MockIDBRequest.prototype, 'onsuccess', {{
            get: function() {{ return this._onsuccess; }},
            set: function(fn) {{ this._onsuccess = fn; }}
        }});

        Object.defineProperty(MockIDBRequest.prototype, 'onerror', {{
            get: function() {{ return this._onerror; }},
            set: function(fn) {{ this._onerror = fn; }}
        }});

        MockIDBRequest.prototype._fireSuccess = function(result) {{
            var self = this;
            this.result = result;
            this.readyState = 'done';
            setTimeout(function() {{
                if (self._onsuccess) {{
                    self._onsuccess({{ target: self, type: 'success' }});
                }}
            }}, 0);
        }};

        MockIDBRequest.prototype._fireError = function(error) {{
            var self = this;
            this.error = error;
            this.readyState = 'done';
            setTimeout(function() {{
                if (self._onerror) {{
                    self._onerror({{ target: self, type: 'error' }});
                }}
            }}, 0);
        }};

        var MockIDBDatabase = function(name, version) {{
            this.name = name;
            this.version = version || 1;
            this.objectStoreNames = {{ contains: function() {{ return false; }}, length: 0, item: function() {{ return null; }} }};
            this._stores = {{}};
            this._data = __webthief_idb_storage__[name] || {{}};
            this.onabort = null;
            this.onclose = null;
            this.onerror = null;
            this.onversionchange = null;
        }};

        MockIDBDatabase.prototype = {{
            createObjectStore: function(name, options) {{
                this._stores[name] = {{ name: name, keyPath: options && options.keyPath, autoIncrement: options && options.autoIncrement, _data: {{}} }};
                this._data[name] = this._data[name] || {{}};
                return new MockIDBObjectStore(this._stores[name], this._data[name]);
            }},

            deleteObjectStore: function(name) {{
                delete this._stores[name];
                delete this._data[name];
                saveIDBData();
            }},

            transaction: function(storeNames, mode) {{
                return new MockIDBTransaction(this, storeNames, mode);
            }},

            close: function() {{}},

            addEventListener: function() {{}},
            removeEventListener: function() {{}}
        }};

        var MockIDBTransaction = function(db, storeNames, mode) {{
            this.db = db;
            this.mode = mode || 'readonly';
            this.error = null;
            this.onabort = null;
            this.oncomplete = null;
            this.onerror = null;
            this._storeNames = Array.isArray(storeNames) ? storeNames : [storeNames];
        }};

        MockIDBTransaction.prototype = {{
            objectStore: function(name) {{
                return new MockIDBObjectStore(this.db._stores[name], this.db._data[name]);
            }},

            abort: function() {{}},

            addEventListener: function() {{}},
            removeEventListener: function() {{}}
        }};

        var MockIDBObjectStore = function(store, data) {{
            this.name = store.name;
            this.keyPath = store.keyPath;
            this.autoIncrement = store.autoIncrement;
            this._data = data || {{}};
            this.indexNames = {{ contains: function() {{ return false; }}, length: 0 }};
        }};

        MockIDBObjectStore.prototype = {{
            add: wrapAsyncAPICall('IndexedDB', 'add', function(value, key) {{
                var k = key || (this.keyPath ? value[this.keyPath] : Date.now());
                this._data[k] = value;
                saveIDBData();
                var req = new MockIDBRequest();
                req._fireSuccess(k);
                return req;
            }}),

            put: wrapAsyncAPICall('IndexedDB', 'put', function(value, key) {{
                var k = key || (this.keyPath ? value[this.keyPath] : Date.now());
                this._data[k] = value;
                saveIDBData();
                var req = new MockIDBRequest();
                req._fireSuccess(k);
                return req;
            }}),

            get: wrapAsyncAPICall('IndexedDB', 'get', function(key) {{
                var req = new MockIDBRequest();
                req._fireSuccess(this._data[key]);
                return req;
            }}),

            delete: wrapAsyncAPICall('IndexedDB', 'delete', function(key) {{
                delete this._data[key];
                saveIDBData();
                var req = new MockIDBRequest();
                req._fireSuccess(undefined);
                return req;
            }}),

            clear: wrapAsyncAPICall('IndexedDB', 'clear', function() {{
                this._data = {{}};
                saveIDBData();
                var req = new MockIDBRequest();
                req._fireSuccess(undefined);
                return req;
            }}),

            count: wrapAsyncAPICall('IndexedDB', 'count', function() {{
                var req = new MockIDBRequest();
                req._fireSuccess(Object.keys(this._data).length);
                return req;
            }}),

            openCursor: function() {{
                var req = new MockIDBRequest();
                var keys = Object.keys(this._data);
                var index = 0;
                var self = this;

                var cursor = {{
                    key: null,
                    value: null,
                    continue: function() {{
                        index++;
                        if (index < keys.length) {{
                            this.key = keys[index];
                            this.value = self._data[keys[index]];
                            req._fireSuccess(this);
                        }} else {{
                            req._fireSuccess(null);
                        }}
                    }}
                }};

                if (keys.length > 0) {{
                    cursor.key = keys[0];
                    cursor.value = this._data[keys[0]];
                    req._fireSuccess(cursor);
                }} else {{
                    req._fireSuccess(null);
                }}
                return req;
            }},

            createIndex: function(name, keyPath, options) {{
                return {{ name: name, keyPath: keyPath }};
            }},

            index: function(name) {{
                return {{
                    get: function(key) {{
                        var req = new MockIDBRequest();
                        for (var k in this._data) {{
                            if (this._data[k][name] === key) {{
                                req._fireSuccess(this._data[k]);
                                return req;
                            }}
                        }}
                        req._fireSuccess(undefined);
                        return req;
                    }}.bind(this)
                }};
            }}
        }};

        var MockIDBFactory = function() {{}};

        MockIDBFactory.prototype = {{
            open: wrapAsyncAPICall('IndexedDB', 'open', function(name, version) {{
                var req = new MockIDBRequest();
                var db = new MockIDBDatabase(name, version);
                __webthief_idb_databases__[name] = db;
                req._fireSuccess(db);
                return req;
            }}),

            deleteDatabase: wrapAsyncAPICall('IndexedDB', 'deleteDatabase', function(name) {{
                delete __webthief_idb_databases__[name];
                delete __webthief_idb_storage__[name];
                saveIDBData();
                var req = new MockIDBRequest();
                req._fireSuccess(undefined);
                return req;
            }}),

            databases: wrapAsyncAPICall('IndexedDB', 'databases', function() {{
                return Promise.resolve(Object.keys(__webthief_idb_databases__).map(function(name) {{
                    return {{ name: name, version: __webthief_idb_databases__[name].version }};
                }}));
            }}),

            cmp: function(a, b) {{
                return a < b ? -1 : (a > b ? 1 : 0);
            }}
        }};

        try {{
            Object.defineProperty(window, 'indexedDB', {{
                value: new MockIDBFactory(),
                configurable: true,
                writable: true
            }});
            console.log('[WebThief API] IndexedDB API 已模拟');
        }} catch (e) {{
            console.warn('[WebThief API] IndexedDB 模拟失败:', e);
        }}
    }})();

    // ── 3. Web Crypto API 模拟 ──
    (function() {{
        if (!window.crypto) {{
            window.crypto = {{}};
        }}

        var MockSubtleCrypto = function() {{}};

        MockSubtleCrypto.prototype = {{
            encrypt: wrapAsyncAPICall('Crypto', 'encrypt', function(algorithm, key, data) {{
                console.log('[WebThief API] Crypto.encrypt 已模拟');
                return Promise.resolve(new Uint8Array(data).buffer);
            }}),

            decrypt: wrapAsyncAPICall('Crypto', 'decrypt', function(algorithm, key, data) {{
                console.log('[WebThief API] Crypto.decrypt 已模拟');
                return Promise.resolve(new Uint8Array(data).buffer);
            }}),

            sign: wrapAsyncAPICall('Crypto', 'sign', function(algorithm, key, data) {{
                console.log('[WebThief API] Crypto.sign 已模拟');
                return Promise.resolve(new ArrayBuffer(32));
            }}),

            verify: wrapAsyncAPICall('Crypto', 'verify', function(algorithm, key, signature, data) {{
                console.log('[WebThief API] Crypto.verify 已模拟');
                return Promise.resolve(true);
            }}),

            digest: wrapAsyncAPICall('Crypto', 'digest', function(algorithm, data) {{
                var arr = new Uint8Array(data);
                var hash = new Uint8Array(32);
                for (var i = 0; i < arr.length; i++) {{
                    hash[i % 32] ^= arr[i];
                }}
                return Promise.resolve(hash.buffer);
            }}),

            generateKey: wrapAsyncAPICall('Crypto', 'generateKey', function(algorithm, extractable, keyUsages) {{
                console.log('[WebThief API] Crypto.generateKey 已模拟');
                return Promise.resolve({{
                    type: 'secret',
                    extractable: extractable,
                    algorithm: algorithm,
                    usages: keyUsages
                }});
            }}),

            deriveKey: wrapAsyncAPICall('Crypto', 'deriveKey', function(algorithm, baseKey, derivedKeyType, extractable, keyUsages) {{
                console.log('[WebThief API] Crypto.deriveKey 已模拟');
                return Promise.resolve({{
                    type: 'secret',
                    extractable: extractable,
                    algorithm: derivedKeyType,
                    usages: keyUsages
                }});
            }}),

            deriveBits: wrapAsyncAPICall('Crypto', 'deriveBits', function(algorithm, baseKey, length) {{
                console.log('[WebThief API] Crypto.deriveBits 已模拟');
                return Promise.resolve(new ArrayBuffer(length / 8));
            }}),

            importKey: wrapAsyncAPICall('Crypto', 'importKey', function(format, keyData, algorithm, extractable, keyUsages) {{
                console.log('[WebThief API] Crypto.importKey 已模拟');
                return Promise.resolve({{
                    type: format === 'raw' ? 'secret' : 'public',
                    extractable: extractable,
                    algorithm: algorithm,
                    usages: keyUsages,
                    _data: keyData
                }});
            }}),

            exportKey: wrapAsyncAPICall('Crypto', 'exportKey', function(format, key) {{
                console.log('[WebThief API] Crypto.exportKey 已模拟');
                if (key._data) {{
                    return Promise.resolve(key._data);
                }}
                return Promise.resolve(new ArrayBuffer(32));
            }}),

            wrapKey: wrapAsyncAPICall('Crypto', 'wrapKey', function(format, key, wrappingKey, wrapAlgorithm) {{
                console.log('[WebThief API] Crypto.wrapKey 已模拟');
                return Promise.resolve(new ArrayBuffer(64));
            }}),

            unwrapKey: wrapAsyncAPICall('Crypto', 'unwrapKey', function(format, wrappedKey, unwrappingKey, unwrapAlgorithm, unwrappedKeyAlgorithm, extractable, keyUsages) {{
                console.log('[WebThief API] Crypto.unwrapKey 已模拟');
                return Promise.resolve({{
                    type: 'secret',
                    extractable: extractable,
                    algorithm: unwrappedKeyAlgorithm,
                    usages: keyUsages
                }});
            }})
        }};

        try {{
            if (!window.crypto.subtle) {{
                Object.defineProperty(window.crypto, 'subtle', {{
                    value: new MockSubtleCrypto(),
                    configurable: true,
                    writable: true
                }});
            }}

            if (!window.crypto.getRandomValues) {{
                window.crypto.getRandomValues = function(array) {{
                    for (var i = 0; i < array.length; i++) {{
                        array[i] = Math.floor(Math.random() * 256);
                    }}
                    return array;
                }};
            }}

            if (!window.crypto.randomUUID) {{
                window.crypto.randomUUID = function() {{
                    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {{
                        var r = Math.random() * 16 | 0;
                        var v = c === 'x' ? r : (r & 0x3 | 0x8);
                        return v.toString(16);
                    }});
                }};
            }}

            console.log('[WebThief API] Web Crypto API 已模拟');
        }} catch (e) {{
            console.warn('[WebThief API] Web Crypto 模拟失败:', e);
        }}
    }})();

    // ── 4. Notification API 模拟 ──
    (function() {{
        var MockNotification = function(title, options) {{
            this.title = title;
            this.body = options && options.body || '';
            this.icon = options && options.icon || '';
            this.tag = options && options.tag || '';
            this.data = options && options.data || null;
            this.timestamp = Date.now();
            this.onclick = null;
            this.onclose = null;
            this.onerror = null;
            this.onshow = null;

            console.log('[WebThief API] 通知已创建:', title);
            recordAPICall('Notification', 'constructor', [title, options], {{ title: title }}, 0, true);
        }};

        MockNotification.permission = '{self.notification.permission}';
        MockNotification.maxActions = 2;

        MockNotification.requestPermission = wrapAsyncAPICall('Notification', 'requestPermission', function() {{
            return Promise.resolve('{self.notification.permission}');
        }});

        MockNotification.close = function() {{}};

        try {{
            Object.defineProperty(window, 'Notification', {{
                value: MockNotification,
                configurable: true,
                writable: true
            }});

            if (navigator.permissions) {{
                var originalQuery = navigator.permissions.query;
                navigator.permissions.query = function(parameters) {{
                    if (parameters.name === 'notifications') {{
                        return Promise.resolve({{ state: '{self.notification.permission}' }});
                    }}
                    if (parameters.name === 'geolocation') {{
                        return Promise.resolve({{ state: 'granted' }});
                    }}
                    return originalQuery ? originalQuery.call(navigator.permissions, parameters) : Promise.resolve({{ state: 'granted' }});
                }};
            }}

            console.log('[WebThief API] Notification API 已模拟');
        }} catch (e) {{
            console.warn('[WebThief API] Notification 模拟失败:', e);
        }}
    }})();

    // ── 5. Geolocation API 模拟 ──
    (function() {{
        var geoConfig = {{
            latitude: {self.geolocation.latitude},
            longitude: {self.geolocation.longitude},
            accuracy: {self.geolocation.accuracy},
            altitude: {self.geolocation.altitude},
            altitudeAccuracy: {self.geolocation.altitude_accuracy},
            heading: {self.geolocation.heading},
            speed: {self.geolocation.speed}
        }};

        var MockGeolocation = function() {{}};

        MockGeolocation.prototype = {{
            getCurrentPosition: wrapAsyncAPICall('Geolocation', 'getCurrentPosition', function(success, error, options) {{
                var position = {{
                    coords: {{
                        latitude: geoConfig.latitude,
                        longitude: geoConfig.longitude,
                        accuracy: geoConfig.accuracy,
                        altitude: geoConfig.altitude,
                        altitudeAccuracy: geoConfig.altitudeAccuracy,
                        heading: geoConfig.heading,
                        speed: geoConfig.speed
                    }},
                    timestamp: Date.now()
                }};
                if (success) {{
                    setTimeout(function() {{ success(position); }}, 0);
                }}
            }}),

            watchPosition: wrapAsyncAPICall('Geolocation', 'watchPosition', function(success, error, options) {{
                var position = {{
                    coords: {{
                        latitude: geoConfig.latitude,
                        longitude: geoConfig.longitude,
                        accuracy: geoConfig.accuracy,
                        altitude: geoConfig.altitude,
                        altitudeAccuracy: geoConfig.altitudeAccuracy,
                        heading: geoConfig.heading,
                        speed: geoConfig.speed
                    }},
                    timestamp: Date.now()
                }};
                if (success) {{
                    setTimeout(function() {{ success(position); }}, 0);
                }}
                return 1;
            }}),

            clearWatch: function(watchId) {{}}
        }};

        try {{
            if (!navigator.geolocation) {{
                Object.defineProperty(navigator, 'geolocation', {{
                    value: new MockGeolocation(),
                    configurable: true,
                    writable: true
                }});
            }} else {{
                navigator.geolocation.getCurrentPosition = MockGeolocation.prototype.getCurrentPosition;
                navigator.geolocation.watchPosition = MockGeolocation.prototype.watchPosition;
                navigator.geolocation.clearWatch = MockGeolocation.prototype.clearWatch;
            }}
            console.log('[WebThief API] Geolocation API 已模拟');
        }} catch (e) {{
            console.warn('[WebThief API] Geolocation 模拟失败:', e);
        }}
    }})();

    // ── 6. 其他 API 模拟 ──
    try {{
        if ('getBattery' in navigator) {{
            navigator.getBattery = wrapAsyncAPICall('Battery', 'getBattery', function() {{
                return Promise.resolve({{
                    charging: true,
                    chargingTime: 0,
                    dischargingTime: Infinity,
                    level: 1,
                    onchargingchange: null,
                    onchargingtimechange: null,
                    ondischargingtimechange: null,
                    onlevelchange: null
                }});
            }});
        }}
    }} catch (e) {{}}

    try {{
        if (!navigator.vibrate) {{
            navigator.vibrate = function(pattern) {{
                console.log('[WebThief API] 振动已模拟:', pattern);
                return true;
            }};
        }}
    }} catch (e) {{}}

    try {{
        if (!navigator.clipboard) {{
            navigator.clipboard = {{
                writeText: wrapAsyncAPICall('Clipboard', 'writeText', function(text) {{
                    console.log('[WebThief API] 剪贴板写入已模拟');
                    return Promise.resolve();
                }}),
                readText: wrapAsyncAPICall('Clipboard', 'readText', function() {{
                    return Promise.resolve('');
                }})
            }};
        }}
    }} catch (e) {{}}

    // ── 7. API 调用记录导出 ──
    window.__webthief_get_api_records__ = function() {{
        return __webthief_api_records__;
    }};

    window.__webthief_clear_api_records__ = function() {{
        __webthief_api_records__ = [];
    }};

    console.log('[WebThief API] 浏览器 API 模拟器已激活');
}})();
"""

    async def inject_to_page(self, page: Any) -> None:
        """
        将 API 垫片注入到页面

        Args:
            page: Playwright Page 对象
        """
        script = self.get_injection_script()
        await page.evaluate(script)
        console.print("[green]  ✓ 浏览器 API 垫片已注入[/]")

    async def get_api_records(self, page: Any) -> list[dict[str, Any]]:
        """
        获取页面中的 API 调用记录

        Args:
            page: Playwright Page 对象

        Returns:
            API 调用记录列表
        """
        try:
            records = await page.evaluate("() => window.__webthief_get_api_records__?.() || []")
            return records
        except Exception:
            return []

    async def clear_api_records(self, page: Any) -> None:
        """
        清除页面中的 API 调用记录

        Args:
            page: Playwright Page 对象
        """
        try:
            await page.evaluate("() => window.__webthief_clear_api_records__?.()")
        except Exception:
            pass

    def save_records_to_file(self, records: list[dict[str, Any]], filename: str = "api_records.json") -> Path:
        """
        将 API 调用记录保存到文件

        Args:
            records: API 调用记录
            filename: 文件名

        Returns:
            保存的文件路径
        """
        filepath = self.storage_dir / filename
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(records, f, ensure_ascii=False, indent=2)
        return filepath

    def load_records_from_file(self, filename: str = "api_records.json") -> list[dict[str, Any]]:
        """
        从文件加载 API 调用记录

        Args:
            filename: 文件名

        Returns:
            API 调用记录列表
        """
        filepath = self.storage_dir / filename
        if not filepath.exists():
            return []
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)

    def print_api_summary(self, records: list[dict[str, Any]]) -> None:
        """
        打印 API 调用摘要

        Args:
            records: API 调用记录
        """
        if not records:
            console.print("[yellow]  无 API 调用记录[/]")
            return

        # 统计各 API 调用次数
        api_stats: dict[str, dict[str, int]] = {}
        for record in records:
            api_name = record.get("api", "unknown")
            method = record.get("method", "unknown")
            key = f"{api_name}.{method}"
            if key not in api_stats:
                api_stats[key] = {"count": 0, "success": 0, "failed": 0}
            api_stats[key]["count"] += 1
            if record.get("success"):
                api_stats[key]["success"] += 1
            else:
                api_stats[key]["failed"] += 1

        table = Table(title=f"API 调用摘要 (共 {len(records)} 条)")
        table.add_column("API", style="cyan")
        table.add_column("调用次数", style="green")
        table.add_column("成功", style="green")
        table.add_column("失败", style="red")

        for api_key, stats in sorted(api_stats.items(), key=lambda x: x[1]["count"], reverse=True):
            table.add_row(api_key, str(stats["count"]), str(stats["success"]), str(stats["failed"]))

        console.print(table)

    def set_geolocation(self, latitude: float, longitude: float, **kwargs: Any) -> None:
        """
        设置地理位置配置

        Args:
            latitude: 纬度
            longitude: 经度
            **kwargs: 其他地理位置参数
        """
        self.geolocation = GeolocationConfig(
            latitude=latitude,
            longitude=longitude,
            accuracy=kwargs.get("accuracy", 100.0),
            altitude=kwargs.get("altitude"),
            altitude_accuracy=kwargs.get("altitude_accuracy"),
            heading=kwargs.get("heading"),
            speed=kwargs.get("speed"),
        )
        self._save_state()

    def set_notification_permission(self, permission: str) -> None:
        """
        设置通知权限

        Args:
            permission: 权限状态 (granted, denied, default)
        """
        if permission not in ("granted", "denied", "default"):
            raise ValueError("permission must be 'granted', 'denied', or 'default'")
        self.notification.permission = permission
        self._save_state()

    def get_config(self) -> dict[str, Any]:
        """
        获取当前配置

        Returns:
            配置字典
        """
        return {
            "geolocation": {
                "latitude": self.geolocation.latitude,
                "longitude": self.geolocation.longitude,
                "accuracy": self.geolocation.accuracy,
                "altitude": self.geolocation.altitude,
                "altitude_accuracy": self.geolocation.altitude_accuracy,
                "heading": self.geolocation.heading,
                "speed": self.geolocation.speed,
            },
            "notification": {
                "permission": self.notification.permission,
                "max_notifications": self.notification.max_notifications,
            },
            "crypto": {
                "enabled": self.crypto.enabled,
                "mock_subtle": self.crypto.mock_subtle,
            },
            "record_calls": self.record_calls,
            "max_records": self.max_records,
        }