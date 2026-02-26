/**
 * WebThief Browser API Shim
 * 
 * 浏览器 API 垫片，用于在离线环境下模拟浏览器原生 API。
 * 
 * 功能：
 * - Service Worker 注册拦截
 * - IndexedDB 文件存储模拟
 * - Web Crypto API 模拟
 * - Notification API 模拟
 * - Geolocation API 模拟
 * - 其他浏览器 API 模拟
 * 
 * 使用方法：
 * 1. 在页面加载前注入此脚本
 * 2. 或在 HTML <head> 顶部添加 <script src="api_shim.js"></script>
 * 
 * @version 1.0.0
 * @license MIT
 */

(function() {
    'use strict';

    // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    // 配置
    // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    var CONFIG = {
        // 地理位置（默认北京）
        geolocation: {
            latitude: 39.9042,
            longitude: 116.4074,
            accuracy: 100,
            altitude: null,
            altitudeAccuracy: null,
            heading: null,
            speed: null
        },
        // 通知权限
        notificationPermission: 'granted',
        // 最大 API 记录数
        maxApiRecords: 1000,
        // 是否启用调试日志
        debug: true
    };

    // 从全局配置覆盖
    if (typeof window.__WEBTHIEF_API_CONFIG__ === 'object') {
        for (var key in window.__WEBTHIEF_API_CONFIG__) {
            if (CONFIG.hasOwnProperty(key)) {
                CONFIG[key] = window.__WEBTHIEF_API_CONFIG__[key];
            }
        }
    }

    // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    // 工具函数
    // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    function log(message) {
        if (CONFIG.debug) {
            console.log('[WebThief API] ' + message);
        }
    }

    function warn(message) {
        console.warn('[WebThief API] ' + message);
    }

    // API 调用记录
    var apiRecords = [];

    function recordAPICall(apiName, method, args, result, duration, success, error) {
        if (apiRecords.length >= CONFIG.maxApiRecords) {
            apiRecords.shift();
        }
        apiRecords.push({
            api: apiName,
            method: method,
            args: args ? Array.from(args).map(function(a) {
                try { return JSON.stringify(a); } catch(e) { return String(a); }
            }) : [],
            result: result,
            duration: duration,
            timestamp: Date.now(),
            success: success,
            error: error
        });
    }

    function wrapAsyncAPICall(apiName, method, fn) {
        return function() {
            var args = arguments;
            var startTime = performance.now();
            try {
                var result = fn.apply(this, args);
                if (result && typeof result.then === 'function') {
                    return result.then(function(r) {
                        recordAPICall(apiName, method, args, r, performance.now() - startTime, true);
                        return r;
                    }).catch(function(e) {
                        recordAPICall(apiName, method, args, null, performance.now() - startTime, false, String(e));
                        throw e;
                    });
                }
                recordAPICall(apiName, method, args, result, performance.now() - startTime, true);
                return result;
            } catch (e) {
                recordAPICall(apiName, method, args, null, performance.now() - startTime, false, String(e));
                throw e;
            }
        };
    }

    // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    // 1. Service Worker 模拟
    // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    (function() {
        if (!('serviceWorker' in navigator)) return;

        var swRegistrations = {};

        // Mock ServiceWorker
        var MockServiceWorker = function(scriptURL) {
            this.scriptURL = scriptURL;
            this.state = 'activated';
            this.onstatechange = null;
            this.onerror = null;
        };

        MockServiceWorker.prototype = {
            postMessage: function(message) {
                log('Service Worker 消息已拦截: ' + message);
            },
            addEventListener: function() {},
            removeEventListener: function() {}
        };

        // Mock PushSubscription
        var MockPushSubscription = function() {
            this.endpoint = 'https://webthief.mock.push/subscription';
            this.expirationTime = null;
        };

        MockPushSubscription.prototype = {
            getKey: function(name) {
                var mockKey = new Uint8Array(16);
                for (var i = 0; i < 16; i++) {
                    mockKey[i] = Math.floor(Math.random() * 256);
                }
                return mockKey.buffer;
            },
            toJSON: function() {
                return {
                    endpoint: this.endpoint,
                    keys: { p256dh: 'mock_key', auth: 'mock_auth' }
                };
            },
            unsubscribe: function() {
                return Promise.resolve(true);
            }
        };

        // Mock PushManager
        var MockPushManager = function() {};

        MockPushManager.prototype = {
            subscribe: function(options) {
                log('Push 订阅已模拟');
                return Promise.resolve(new MockPushSubscription());
            },
            getSubscription: function() {
                return Promise.resolve(null);
            },
            permissionState: function() {
                return Promise.resolve('granted');
            }
        };

        // Mock SyncManager
        var MockSyncManager = function() {};

        MockSyncManager.prototype = {
            register: function(tag) {
                log('后台同步已模拟: ' + tag);
                return Promise.resolve();
            },
            getTags: function() {
                return Promise.resolve([]);
            }
        };

        // Mock ServiceWorkerRegistration
        var MockServiceWorkerRegistration = function(scriptURL, options) {
            this._scriptURL = scriptURL;
            this._scope = options && options.scope ? options.scope : '/';
            this.active = new MockServiceWorker(scriptURL);
            this.installing = null;
            this.waiting = null;
            this.navigationPreload = {
                enable: function() {},
                disable: function() {},
                setHeaderValue: function() {}
            };
            this.pushManager = new MockPushManager();
            this.sync = new MockSyncManager();
            this.onupdatefound = null;

            swRegistrations[scriptURL] = {
                scriptURL: scriptURL,
                scope: this._scope,
                state: 'activated'
            };
        };

        Object.defineProperty(MockServiceWorkerRegistration.prototype, 'scope', {
            get: function() { return this._scope; }
        });

        MockServiceWorkerRegistration.prototype.unregister = wrapAsyncAPICall('SWRegistration', 'unregister', function() {
            log('注销已模拟: ' + this._scriptURL);
            delete swRegistrations[this._scriptURL];
            return Promise.resolve(true);
        });

        MockServiceWorkerRegistration.prototype.update = wrapAsyncAPICall('SWRegistration', 'update', function() {
            log('更新已模拟: ' + this._scriptURL);
            return Promise.resolve();
        });

        MockServiceWorkerRegistration.prototype.showNotification = wrapAsyncAPICall('SWRegistration', 'showNotification', function(title, options) {
            log('通知已模拟: ' + title);
            return Promise.resolve();
        });

        MockServiceWorkerRegistration.prototype.getNotifications = function() {
            return Promise.resolve([]);
        };

        MockServiceWorkerRegistration.prototype.addEventListener = function() {};
        MockServiceWorkerRegistration.prototype.removeEventListener = function() {};

        // Mock ServiceWorkerContainer
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

        MockServiceWorkerContainer.prototype.register = wrapAsyncAPICall('ServiceWorker', 'register', function(scriptURL, options) {
            log('注册已拦截: ' + scriptURL);
            var registration = new MockServiceWorkerRegistration(scriptURL, options || {});
            this._registrations.set(scriptURL, registration);
            this._ready = Promise.resolve(registration);
            return Promise.resolve(registration);
        });

        MockServiceWorkerContainer.prototype.getRegistration = function(scope) {
            for (var url in swRegistrations) {
                if (swRegistrations[url].scope === scope) {
                    return Promise.resolve(new MockServiceWorkerRegistration(url, { scope: scope }));
                }
            }
            return Promise.resolve(undefined);
        };

        MockServiceWorkerContainer.prototype.getRegistrations = function() {
            var regs = [];
            for (var url in swRegistrations) {
                regs.push(new MockServiceWorkerRegistration(url, { scope: swRegistrations[url].scope }));
            }
            return Promise.resolve(regs);
        };

        MockServiceWorkerContainer.prototype.startMessages = function() {};
        MockServiceWorkerContainer.prototype.addEventListener = function() {};
        MockServiceWorkerContainer.prototype.removeEventListener = function() {};

        // 替换原生 API
        try {
            Object.defineProperty(navigator, 'serviceWorker', {
                value: new MockServiceWorkerContainer(),
                configurable: true,
                writable: true
            });
            log('Service Worker API 已模拟');
        } catch (e) {
            warn('Service Worker 模拟失败: ' + e);
        }
    })();

    // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    // 2. IndexedDB 模拟
    // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    (function() {
        var idbDatabases = {};
        var idbStorage = {};

        // 从 localStorage 恢复数据
        try {
            var savedData = localStorage.getItem('__webthief_idb_data__');
            if (savedData) {
                idbStorage = JSON.parse(savedData);
            }
        } catch (e) {}

        function saveIDBData() {
            try {
                localStorage.setItem('__webthief_idb_data__', JSON.stringify(idbStorage));
            } catch (e) {}
        }

        // Mock IDBRequest
        var MockIDBRequest = function() {
            this.result = null;
            this.error = null;
            this.source = null;
            this.transaction = null;
            this.readyState = 'pending';
            this._onsuccess = null;
            this._onerror = null;
            this._onupgradeneeded = null;
        };

        Object.defineProperty(MockIDBRequest.prototype, 'onsuccess', {
            get: function() { return this._onsuccess; },
            set: function(fn) { this._onsuccess = fn; }
        });

        Object.defineProperty(MockIDBRequest.prototype, 'onerror', {
            get: function() { return this._onerror; },
            set: function(fn) { this._onerror = fn; }
        });

        Object.defineProperty(MockIDBRequest.prototype, 'onupgradeneeded', {
            get: function() { return this._onupgradeneeded; },
            set: function(fn) { this._onupgradeneeded = fn; }
        });

        MockIDBRequest.prototype._fireSuccess = function(result) {
            var self = this;
            this.result = result;
            this.readyState = 'done';
            setTimeout(function() {
                if (self._onsuccess) {
                    self._onsuccess({ target: self, type: 'success' });
                }
            }, 0);
        };

        MockIDBRequest.prototype._fireError = function(error) {
            var self = this;
            this.error = error;
            this.readyState = 'done';
            setTimeout(function() {
                if (self._onerror) {
                    self._onerror({ target: self, type: 'error' });
                }
            }, 0);
        };

        MockIDBRequest.prototype._fireUpgradeNeeded = function(oldVersion, newVersion) {
            var self = this;
            setTimeout(function() {
                if (self._onupgradeneeded) {
                    self._onupgradeneeded({
                        target: self,
                        type: 'upgradeneeded',
                        oldVersion: oldVersion,
                        newVersion: newVersion
                    });
                }
            }, 0);
        };

        // Mock IDBDatabase
        var MockIDBDatabase = function(name, version) {
            this.name = name;
            this.version = version || 1;
            this._stores = {};
            this._data = idbStorage[name] || {};
            this._objectStoreNamesList = Object.keys(this._data);
            this.onabort = null;
            this.onclose = null;
            this.onerror = null;
            this.onversionchange = null;
        };

        Object.defineProperty(MockIDBDatabase.prototype, 'objectStoreNames', {
            get: function() {
                var self = this;
                return {
                    contains: function(name) { return self._objectStoreNamesList.indexOf(name) !== -1; },
                    length: self._objectStoreNamesList.length,
                    item: function(i) { return self._objectStoreNamesList[i] || null; }
                };
            }
        });

        MockIDBDatabase.prototype.createObjectStore = function(name, options) {
            log('创建对象存储: ' + name);
            this._stores[name] = {
                name: name,
                keyPath: options && options.keyPath,
                autoIncrement: options && options.autoIncrement
            };
            this._data[name] = this._data[name] || {};
            this._objectStoreNamesList = Object.keys(this._data);
            saveIDBData();
            return new MockIDBObjectStore(this._stores[name], this._data[name]);
        };

        MockIDBDatabase.prototype.deleteObjectStore = function(name) {
            log('删除对象存储: ' + name);
            delete this._stores[name];
            delete this._data[name];
            this._objectStoreNamesList = Object.keys(this._data);
            saveIDBData();
        };

        MockIDBDatabase.prototype.transaction = function(storeNames, mode) {
            return new MockIDBTransaction(this, storeNames, mode);
        };

        MockIDBDatabase.prototype.close = function() {};

        MockIDBDatabase.prototype.addEventListener = function() {};
        MockIDBDatabase.prototype.removeEventListener = function() {};

        // Mock IDBTransaction
        var MockIDBTransaction = function(db, storeNames, mode) {
            this.db = db;
            this.mode = mode || 'readonly';
            this.error = null;
            this.onabort = null;
            this.oncomplete = null;
            this.onerror = null;
        };

        MockIDBTransaction.prototype.objectStore = function(name) {
            if (!this.db._data[name]) {
                this.db._data[name] = {};
            }
            var storeInfo = this.db._stores[name] || { name: name, keyPath: null, autoIncrement: false };
            return new MockIDBObjectStore(storeInfo, this.db._data[name]);
        };

        MockIDBTransaction.prototype.abort = function() {};
        MockIDBTransaction.prototype.addEventListener = function() {};
        MockIDBTransaction.prototype.removeEventListener = function() {};

        // Mock IDBObjectStore
        var MockIDBObjectStore = function(store, data) {
            this.name = store.name;
            this.keyPath = store.keyPath;
            this.autoIncrement = store.autoIncrement;
            this._data = data || {};
            this.indexNames = { contains: function() { return false; }, length: 0 };
        };

        MockIDBObjectStore.prototype.add = wrapAsyncAPICall('IndexedDB', 'add', function(value, key) {
            var k = key || (this.keyPath ? value[this.keyPath] : Date.now().toString());
            if (this._data[k] !== undefined) {
                var req = new MockIDBRequest();
                req._fireError('Key already exists: ' + k);
                return req;
            }
            this._data[k] = value;
            saveIDBData();
            var req = new MockIDBRequest();
            req._fireSuccess(k);
            return req;
        });

        MockIDBObjectStore.prototype.put = wrapAsyncAPICall('IndexedDB', 'put', function(value, key) {
            var k = key || (this.keyPath ? value[this.keyPath] : Date.now().toString());
            this._data[k] = value;
            saveIDBData();
            var req = new MockIDBRequest();
            req._fireSuccess(k);
            return req;
        });

        MockIDBObjectStore.prototype.get = wrapAsyncAPICall('IndexedDB', 'get', function(key) {
            var req = new MockIDBRequest();
            req._fireSuccess(this._data[key]);
            return req;
        });

        MockIDBObjectStore.prototype.getAll = function(query, count) {
            var results = [];
            for (var k in this._data) {
                results.push(this._data[k]);
            }
            if (count && count > 0) {
                results = results.slice(0, count);
            }
            var req = new MockIDBRequest();
            req._fireSuccess(results);
            return req;
        };

        MockIDBObjectStore.prototype.delete = wrapAsyncAPICall('IndexedDB', 'delete', function(key) {
            delete this._data[key];
            saveIDBData();
            var req = new MockIDBRequest();
            req._fireSuccess(undefined);
            return req;
        });

        MockIDBObjectStore.prototype.clear = wrapAsyncAPICall('IndexedDB', 'clear', function() {
            this._data = {};
            saveIDBData();
            var req = new MockIDBRequest();
            req._fireSuccess(undefined);
            return req;
        });

        MockIDBObjectStore.prototype.count = function() {
            var req = new MockIDBRequest();
            req._fireSuccess(Object.keys(this._data).length);
            return req;
        };

        MockIDBObjectStore.prototype.openCursor = function() {
            var req = new MockIDBRequest();
            var keys = Object.keys(this._data);
            var index = 0;
            var self = this;

            var cursor = {
                key: null,
                value: null,
                continue: function() {
                    index++;
                    if (index < keys.length) {
                        this.key = keys[index];
                        this.value = self._data[keys[index]];
                        req._fireSuccess(this);
                    } else {
                        req._fireSuccess(null);
                    }
                }
            };

            if (keys.length > 0) {
                cursor.key = keys[0];
                cursor.value = this._data[keys[0]];
                req._fireSuccess(cursor);
            } else {
                req._fireSuccess(null);
            }
            return req;
        };

        MockIDBObjectStore.prototype.createIndex = function(name, keyPath, options) {
            return { name: name, keyPath: keyPath };
        };

        MockIDBObjectStore.prototype.index = function(name) {
            return { get: function() { var req = new MockIDBRequest(); req._fireSuccess(undefined); return req; } };
        };

        // Mock IDBKeyRange
        var MockIDBKeyRange = function(lower, upper, lowerOpen, upperOpen) {
            this.lower = lower;
            this.upper = upper;
            this.lowerOpen = lowerOpen || false;
            this.upperOpen = upperOpen || false;
        };

        MockIDBKeyRange.only = function(value) {
            return new MockIDBKeyRange(value, value, false, false);
        };
        MockIDBKeyRange.lowerBound = function(lower, open) {
            return new MockIDBKeyRange(lower, undefined, open || false, true);
        };
        MockIDBKeyRange.upperBound = function(upper, open) {
            return new MockIDBKeyRange(undefined, upper, true, open || false);
        };
        MockIDBKeyRange.bound = function(lower, upper, lowerOpen, upperOpen) {
            return new MockIDBKeyRange(lower, upper, lowerOpen || false, upperOpen || false);
        };

        // Mock IDBFactory
        var MockIDBFactory = function() {};

        MockIDBFactory.prototype.open = wrapAsyncAPICall('IndexedDB', 'open', function(name, version) {
            log('打开数据库: ' + name);
            var req = new MockIDBRequest();
            var db = new MockIDBDatabase(name, version);
            idbDatabases[name] = db;

            var oldVersion = idbStorage[name] && idbStorage[name].__version__ ? idbStorage[name].__version__ : 0;
            var newVersion = version || 1;

            if (oldVersion < newVersion) {
                req._fireUpgradeNeeded(oldVersion, newVersion);
            }

            setTimeout(function() {
                req._fireSuccess(db);
            }, 10);

            return req;
        });

        MockIDBFactory.prototype.deleteDatabase = wrapAsyncAPICall('IndexedDB', 'deleteDatabase', function(name) {
            log('删除数据库: ' + name);
            delete idbDatabases[name];
            delete idbStorage[name];
            saveIDBData();
            var req = new MockIDBRequest();
            req._fireSuccess(undefined);
            return req;
        });

        MockIDBFactory.prototype.databases = function() {
            return Promise.resolve(Object.keys(idbDatabases).map(function(name) {
                return { name: name, version: idbDatabases[name].version };
            }));
        };

        MockIDBFactory.prototype.cmp = function(a, b) {
            return a < b ? -1 : (a > b ? 1 : 0);
        };

        // 替换原生 API
        try {
            Object.defineProperty(window, 'indexedDB', {
                value: new MockIDBFactory(),
                configurable: true,
                writable: true
            });
            Object.defineProperty(window, 'IDBKeyRange', {
                value: MockIDBKeyRange,
                configurable: true,
                writable: true
            });
            log('IndexedDB API 已模拟');
        } catch (e) {
            warn('IndexedDB 模拟失败: ' + e);
        }
    })();

    // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    // 3. Web Crypto API 模拟
    // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    (function() {
        if (!window.crypto) {
            window.crypto = {};
        }

        var MockSubtleCrypto = function() {};

        MockSubtleCrypto.prototype.encrypt = wrapAsyncAPICall('Crypto', 'encrypt', function(algorithm, key, data) {
            return Promise.resolve(new Uint8Array(data).buffer);
        });

        MockSubtleCrypto.prototype.decrypt = wrapAsyncAPICall('Crypto', 'decrypt', function(algorithm, key, data) {
            return Promise.resolve(new Uint8Array(data).buffer);
        });

        MockSubtleCrypto.prototype.sign = wrapAsyncAPICall('Crypto', 'sign', function(algorithm, key, data) {
            return Promise.resolve(new ArrayBuffer(32));
        });

        MockSubtleCrypto.prototype.verify = wrapAsyncAPICall('Crypto', 'verify', function(algorithm, key, signature, data) {
            return Promise.resolve(true);
        });

        MockSubtleCrypto.prototype.digest = wrapAsyncAPICall('Crypto', 'digest', function(algorithm, data) {
            var arr = new Uint8Array(data);
            var hash = new Uint8Array(32);
            for (var i = 0; i < arr.length; i++) {
                hash[i % 32] ^= arr[i];
            }
            return Promise.resolve(hash.buffer);
        });

        MockSubtleCrypto.prototype.generateKey = wrapAsyncAPICall('Crypto', 'generateKey', function(algorithm, extractable, keyUsages) {
            return Promise.resolve({
                type: 'secret',
                extractable: extractable,
                algorithm: algorithm,
                usages: keyUsages
            });
        });

        MockSubtleCrypto.prototype.importKey = wrapAsyncAPICall('Crypto', 'importKey', function(format, keyData, algorithm, extractable, keyUsages) {
            return Promise.resolve({
                type: format === 'raw' ? 'secret' : 'public',
                extractable: extractable,
                algorithm: algorithm,
                usages: keyUsages,
                _data: keyData
            });
        });

        MockSubtleCrypto.prototype.exportKey = wrapAsyncAPICall('Crypto', 'exportKey', function(format, key) {
            if (key._data) {
                return Promise.resolve(key._data);
            }
            return Promise.resolve(new ArrayBuffer(32));
        });

        try {
            if (!window.crypto.subtle) {
                Object.defineProperty(window.crypto, 'subtle', {
                    value: new MockSubtleCrypto(),
                    configurable: true,
                    writable: true
                });
            }

            if (!window.crypto.getRandomValues) {
                window.crypto.getRandomValues = function(array) {
                    for (var i = 0; i < array.length; i++) {
                        array[i] = Math.floor(Math.random() * 256);
                    }
                    return array;
                };
            }

            if (!window.crypto.randomUUID) {
                window.crypto.randomUUID = function() {
                    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
                        var r = Math.random() * 16 | 0;
                        var v = c === 'x' ? r : (r & 0x3 | 0x8);
                        return v.toString(16);
                    });
                };
            }

            log('Web Crypto API 已模拟');
        } catch (e) {
            warn('Web Crypto 模拟失败: ' + e);
        }
    })();

    // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    // 4. Notification API 模拟
    // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    (function() {
        var MockNotification = function(title, options) {
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

            log('通知已创建: ' + title);
            recordAPICall('Notification', 'constructor', [title, options], { title: title }, 0, true);
        };

        MockNotification.permission = CONFIG.notificationPermission;
        MockNotification.maxActions = 2;

        MockNotification.requestPermission = wrapAsyncAPICall('Notification', 'requestPermission', function() {
            return Promise.resolve(CONFIG.notificationPermission);
        });

        MockNotification.close = function() {};

        try {
            Object.defineProperty(window, 'Notification', {
                value: MockNotification,
                configurable: true,
                writable: true
            });

            if (navigator.permissions) {
                var originalQuery = navigator.permissions.query;
                navigator.permissions.query = function(parameters) {
                    if (parameters.name === 'notifications') {
                        return Promise.resolve({ state: CONFIG.notificationPermission });
                    }
                    if (parameters.name === 'geolocation') {
                        return Promise.resolve({ state: 'granted' });
                    }
                    return originalQuery ? originalQuery.call(navigator.permissions, parameters) : Promise.resolve({ state: 'granted' });
                };
            }

            log('Notification API 已模拟');
        } catch (e) {
            warn('Notification 模拟失败: ' + e);
        }
    })();

    // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    // 5. Geolocation API 模拟
    // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    (function() {
        var geoConfig = CONFIG.geolocation;

        var MockGeolocation = function() {};

        MockGeolocation.prototype.getCurrentPosition = wrapAsyncAPICall('Geolocation', 'getCurrentPosition', function(success, error, options) {
            var position = {
                coords: {
                    latitude: geoConfig.latitude,
                    longitude: geoConfig.longitude,
                    accuracy: geoConfig.accuracy,
                    altitude: geoConfig.altitude,
                    altitudeAccuracy: geoConfig.altitudeAccuracy,
                    heading: geoConfig.heading,
                    speed: geoConfig.speed
                },
                timestamp: Date.now()
            };
            if (success) {
                setTimeout(function() { success(position); }, 0);
            }
        });

        MockGeolocation.prototype.watchPosition = wrapAsyncAPICall('Geolocation', 'watchPosition', function(success, error, options) {
            var position = {
                coords: {
                    latitude: geoConfig.latitude,
                    longitude: geoConfig.longitude,
                    accuracy: geoConfig.accuracy,
                    altitude: geoConfig.altitude,
                    altitudeAccuracy: geoConfig.altitudeAccuracy,
                    heading: geoConfig.heading,
                    speed: geoConfig.speed
                },
                timestamp: Date.now()
            };
            if (success) {
                setTimeout(function() { success(position); }, 0);
            }
            return 1;
        });

        MockGeolocation.prototype.clearWatch = function(watchId) {};

        try {
            if (!navigator.geolocation) {
                Object.defineProperty(navigator, 'geolocation', {
                    value: new MockGeolocation(),
                    configurable: true,
                    writable: true
                });
            } else {
                navigator.geolocation.getCurrentPosition = MockGeolocation.prototype.getCurrentPosition;
                navigator.geolocation.watchPosition = MockGeolocation.prototype.watchPosition;
                navigator.geolocation.clearWatch = MockGeolocation.prototype.clearWatch;
            }
            log('Geolocation API 已模拟');
        } catch (e) {
            warn('Geolocation 模拟失败: ' + e);
        }
    })();

    // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    // 6. 其他 API 模拟
    // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    // Battery API
    try {
        if ('getBattery' in navigator) {
            navigator.getBattery = wrapAsyncAPICall('Battery', 'getBattery', function() {
                return Promise.resolve({
                    charging: true,
                    chargingTime: 0,
                    dischargingTime: Infinity,
                    level: 1
                });
            });
        }
    } catch (e) {}

    // Vibration API
    try {
        if (!navigator.vibrate) {
            navigator.vibrate = function(pattern) {
                log('振动已模拟: ' + pattern);
                return true;
            };
        }
    } catch (e) {}

    // Clipboard API
    try {
        if (!navigator.clipboard) {
            navigator.clipboard = {
                writeText: wrapAsyncAPICall('Clipboard', 'writeText', function(text) {
                    log('剪贴板写入已模拟');
                    return Promise.resolve();
                }),
                readText: wrapAsyncAPICall('Clipboard', 'readText', function() {
                    return Promise.resolve('');
                })
            };
        }
    } catch (e) {}

    // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    // 导出全局函数
    // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    window.__webthief_get_api_records__ = function() {
        return apiRecords;
    };

    window.__webthief_clear_api_records__ = function() {
        apiRecords = [];
    };

    window.__webthief_get_api_config__ = function() {
        return CONFIG;
    };

    window.__webthief_set_api_config__ = function(key, value) {
        if (CONFIG.hasOwnProperty(key)) {
            CONFIG[key] = value;
        }
    };

    log('浏览器 API 模拟器已激活');
})();
