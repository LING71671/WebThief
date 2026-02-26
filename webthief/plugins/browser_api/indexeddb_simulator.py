"""
IndexedDB 模拟器

将 IndexedDB 操作重定向到文件系统存储，支持离线环境。
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from rich.console import Console
from rich.table import Table

console = Console()


@dataclass
class IDBDatabaseInfo:
    """IndexedDB 数据库信息"""

    name: str
    version: int = 1
    object_stores: list[str] = field(default_factory=list)


@dataclass
class IDBObjectStoreInfo:
    """IndexedDB 对象存储信息"""

    name: str
    key_path: Optional[str] = None
    auto_increment: bool = False
    indexes: list[str] = field(default_factory=list)
    record_count: int = 0


@dataclass
class IDBOperation:
    """IndexedDB 操作记录"""

    operation: str
    database: str
    store: str
    key: Optional[Any] = None
    value: Optional[Any] = None
    timestamp: float = 0.0
    success: bool = True


class IndexedDBSimulator:
    """
    IndexedDB 模拟器

    功能：
    - 模拟完整的 IndexedDB API
    - 数据持久化到文件系统
    - 操作记录和审计
    - 支持导入导出
    """

    def __init__(
        self,
        storage_dir: str | Path = "./browser_api_storage/idb_storage",
        max_storage_size: int = 50 * 1024 * 1024,  # 50MB
        record_operations: bool = True,
    ):
        """
        初始化 IndexedDB 模拟器

        Args:
            storage_dir: 存储目录
            max_storage_size: 最大存储大小（字节）
            record_operations: 是否记录操作
        """
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        self.max_storage_size = max_storage_size
        self.record_operations = record_operations

        # 操作记录
        self._operations: list[IDBOperation] = []

        # 数据库信息缓存
        self._databases: dict[str, IDBDatabaseInfo] = {}

        # 加载已有数据库
        self._load_databases()

    def _load_databases(self) -> None:
        """加载已有的数据库信息"""
        for db_dir in self.storage_dir.iterdir():
            if db_dir.is_dir():
                info_file = db_dir / "_db_info.json"
                if info_file.exists():
                    try:
                        with open(info_file, "r", encoding="utf-8") as f:
                            info = json.load(f)
                            self._databases[info["name"]] = IDBDatabaseInfo(
                                name=info["name"],
                                version=info.get("version", 1),
                                object_stores=info.get("objectStores", []),
                            )
                    except Exception:
                        pass

    def _get_db_dir(self, db_name: str) -> Path:
        """获取数据库目录"""
        return self.storage_dir / self._sanitize_name(db_name)

    def _get_store_file(self, db_name: str, store_name: str) -> Path:
        """获取对象存储文件"""
        return self._get_db_dir(db_name) / f"{self._sanitize_name(store_name)}.json"

    @staticmethod
    def _sanitize_name(name: str) -> str:
        """清理名称，移除不安全字符"""
        return "".join(c if c.isalnum() or c in "_-" else "_" for c in name)

    def get_injection_script(self) -> str:
        """
        获取 IndexedDB 模拟注入脚本

        Returns:
            JavaScript 注入脚本
        """
        return """
(function() {
    'use strict';
    // ━━━ WebThief IndexedDB Simulator ━━━

    // 存储结构
    var __webthief_idb_databases__ = {};
    var __webthief_idb_operations__ = [];
    var __webthief_idb_storage__ = {};

    // 从 localStorage 恢复数据
    try {
        var savedData = localStorage.getItem('__webthief_idb_data__');
        if (savedData) {
            __webthief_idb_storage__ = JSON.parse(savedData);
        }
    } catch (e) {}

    function saveIDBData() {
        try {
            localStorage.setItem('__webthief_idb_data__', JSON.stringify(__webthief_idb_storage__));
        } catch (e) {
            console.warn('[WebThief IDB] 数据保存失败:', e);
        }
    }

    function recordOperation(op, db, store, key, value, success) {
        __webthief_idb_operations__.push({
            operation: op,
            database: db,
            store: store,
            key: key,
            value: value,
            timestamp: Date.now(),
            success: success !== false
        });
    }

    // ── Mock IDBRequest ──
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
                var event = { target: self, type: 'success' };
                self._onsuccess(event);
            }
        }, 0);
    };

    MockIDBRequest.prototype._fireError = function(error) {
        var self = this;
        this.error = error;
        this.readyState = 'done';
        setTimeout(function() {
            if (self._onerror) {
                var event = { target: self, type: 'error' };
                self._onerror(event);
            }
        }, 0);
    };

    MockIDBRequest.prototype._fireUpgradeNeeded = function(oldVersion, newVersion) {
        var self = this;
        setTimeout(function() {
            if (self._onupgradeneeded) {
                var event = {
                    target: self,
                    type: 'upgradeneeded',
                    oldVersion: oldVersion,
                    newVersion: newVersion
                };
                self._onupgradeneeded(event);
            }
        }, 0);
    };

    // ── Mock IDBDatabase ──
    var MockIDBDatabase = function(name, version) {
        this.name = name;
        this.version = version || 1;
        this._stores = {};
        this._data = __webthief_idb_storage__[name] || {};
        this.onabort = null;
        this.onclose = null;
        this.onerror = null;
        this.onversionchange = null;

        // 初始化 objectStoreNames
        var storeNames = Object.keys(this._data);
        this._objectStoreNamesList = storeNames;
    };

    Object.defineProperty(MockIDBDatabase.prototype, 'objectStoreNames', {
        get: function() {
            var self = this;
            return {
                contains: function(name) {
                    return self._objectStoreNamesList.indexOf(name) !== -1;
                },
                length: self._objectStoreNamesList.length,
                item: function(i) {
                    return self._objectStoreNamesList[i] || null;
                }
            };
        }
    });

    MockIDBDatabase.prototype = {
        createObjectStore: function(name, options) {
            console.log('[WebThief IDB] 创建对象存储:', name);
            var storeInfo = {
                name: name,
                keyPath: options && options.keyPath ? options.keyPath : null,
                autoIncrement: options && options.autoIncrement ? options.autoIncrement : false,
                indexes: {},
                _data: {}
            };
            this._stores[name] = storeInfo;
            this._data[name] = this._data[name] || {};
            this._objectStoreNamesList = Object.keys(this._data);
            saveIDBData();
            return new MockIDBObjectStore(storeInfo, this._data[name]);
        },

        deleteObjectStore: function(name) {
            console.log('[WebThief IDB] 删除对象存储:', name);
            delete this._stores[name];
            delete this._data[name];
            this._objectStoreNamesList = Object.keys(this._data);
            saveIDBData();
        },

        transaction: function(storeNames, mode) {
            return new MockIDBTransaction(this, storeNames, mode);
        },

        close: function() {
            console.log('[WebThief IDB] 关闭数据库:', this.name);
        },

        addEventListener: function(type, listener) {},
        removeEventListener: function(type, listener) {}
    };

    // ── Mock IDBTransaction ──
    var MockIDBTransaction = function(db, storeNames, mode) {
        this.db = db;
        this.mode = mode || 'readonly';
        this.error = null;
        this.onabort = null;
        this.oncomplete = null;
        this.onerror = null;
        this._storeNames = Array.isArray(storeNames) ? storeNames : [storeNames];
    };

    MockIDBTransaction.prototype = {
        objectStore: function(name) {
            if (!this.db._data[name]) {
                this.db._data[name] = {};
            }
            var storeInfo = this.db._stores[name] || {
                name: name,
                keyPath: null,
                autoIncrement: false,
                indexes: {}
            };
            return new MockIDBObjectStore(storeInfo, this.db._data[name]);
        },

        abort: function() {
            console.log('[WebThief IDB] 事务中止');
        },

        addEventListener: function(type, listener) {},
        removeEventListener: function(type, listener) {}
    };

    // ── Mock IDBObjectStore ──
    var MockIDBObjectStore = function(store, data) {
        this.name = store.name;
        this.keyPath = store.keyPath;
        this.autoIncrement = store.autoIncrement;
        this._data = data || {};
        this._indexes = store.indexes || {};
        this.indexNames = {
            contains: function(name) { return false; },
            length: 0,
            item: function() { return null; }
        };
    };

    MockIDBObjectStore.prototype = {
        add: function(value, key) {
            var k = key || (this.keyPath ? value[this.keyPath] : Date.now().toString());
            if (this._data[k] !== undefined) {
                var req = new MockIDBRequest();
                req._fireError('Key already exists: ' + k);
                recordOperation('add', '', this.name, k, value, false);
                return req;
            }
            this._data[k] = value;
            saveIDBData();
            recordOperation('add', '', this.name, k, value, true);
            var req = new MockIDBRequest();
            req._fireSuccess(k);
            return req;
        },

        put: function(value, key) {
            var k = key || (this.keyPath ? value[this.keyPath] : Date.now().toString());
            this._data[k] = value;
            saveIDBData();
            recordOperation('put', '', this.name, k, value, true);
            var req = new MockIDBRequest();
            req._fireSuccess(k);
            return req;
        },

        get: function(key) {
            recordOperation('get', '', this.name, key, null, true);
            var req = new MockIDBRequest();
            req._fireSuccess(this._data[key]);
            return req;
        },

        getAll: function(query, count) {
            var results = [];
            for (var k in this._data) {
                results.push(this._data[k]);
            }
            if (count && count > 0) {
                results = results.slice(0, count);
            }
            recordOperation('getAll', '', this.name, null, null, true);
            var req = new MockIDBRequest();
            req._fireSuccess(results);
            return req;
        },

        delete: function(key) {
            delete this._data[key];
            saveIDBData();
            recordOperation('delete', '', this.name, key, null, true);
            var req = new MockIDBRequest();
            req._fireSuccess(undefined);
            return req;
        },

        clear: function() {
            this._data = {};
            saveIDBData();
            recordOperation('clear', '', this.name, null, null, true);
            var req = new MockIDBRequest();
            req._fireSuccess(undefined);
            return req;
        },

        count: function(query) {
            var count = Object.keys(this._data).length;
            var req = new MockIDBRequest();
            req._fireSuccess(count);
            return req;
        },

        openCursor: function(query, direction) {
            var req = new MockIDBRequest();
            var keys = Object.keys(this._data);
            var index = 0;
            var self = this;

            var cursor = {
                key: null,
                value: null,
                primaryKey: null,
                direction: direction || 'next',
                source: self,

                continue: function(key) {
                    index++;
                    if (index < keys.length) {
                        this.key = keys[index];
                        this.value = self._data[keys[index]];
                        this.primaryKey = keys[index];
                        req._fireSuccess(this);
                    } else {
                        req._fireSuccess(null);
                    }
                },

                advance: function(count) {
                    index += count;
                    if (index < keys.length) {
                        this.key = keys[index];
                        this.value = self._data[keys[index]];
                        this.primaryKey = keys[index];
                        req._fireSuccess(this);
                    } else {
                        req._fireSuccess(null);
                    }
                },

                update: function(value) {
                    self._data[this.key] = value;
                    saveIDBData();
                    var updateReq = new MockIDBRequest();
                    updateReq._fireSuccess(this.key);
                    return updateReq;
                },

                delete: function() {
                    delete self._data[this.key];
                    saveIDBData();
                    var deleteReq = new MockIDBRequest();
                    deleteReq._fireSuccess(undefined);
                    return deleteReq;
                }
            };

            if (keys.length > 0) {
                cursor.key = keys[0];
                cursor.value = this._data[keys[0]];
                cursor.primaryKey = keys[0];
                req._fireSuccess(cursor);
            } else {
                req._fireSuccess(null);
            }
            return req;
        },

        openKeyCursor: function(query, direction) {
            return this.openCursor(query, direction);
        },

        createIndex: function(name, keyPath, options) {
            console.log('[WebThief IDB] 创建索引:', name);
            var index = {
                name: name,
                keyPath: keyPath,
                unique: options && options.unique ? options.unique : false,
                multiEntry: options && options.multiEntry ? options.multiEntry : false
            };
            this._indexes[name] = index;
            return new MockIDBIndex(index, this._data);
        },

        index: function(name) {
            return new MockIDBIndex(this._indexes[name] || {}, this._data);
        },

        deleteIndex: function(name) {
            delete this._indexes[name];
        }
    };

    // ── Mock IDBIndex ──
    var MockIDBIndex = function(index, data) {
        this.name = index.name || '';
        this.keyPath = index.keyPath || '';
        this.unique = index.unique || false;
        this.multiEntry = index.multiEntry || false;
        this._data = data;
    };

    MockIDBIndex.prototype = {
        get: function(key) {
            var req = new MockIDBRequest();
            for (var k in this._data) {
                var val = this._data[k];
                if (val && val[this.keyPath] === key) {
                    req._fireSuccess(val);
                    return req;
                }
            }
            req._fireSuccess(undefined);
            return req;
        },

        getAll: function(query, count) {
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
        },

        openCursor: function(query, direction) {
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
        },

        count: function(query) {
            var req = new MockIDBRequest();
            req._fireSuccess(Object.keys(this._data).length);
            return req;
        }
    };

    // ── Mock IDBKeyRange ──
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

    // ── Mock IDBFactory ──
    var MockIDBFactory = function() {};

    MockIDBFactory.prototype = {
        open: function(name, version) {
            console.log('[WebThief IDB] 打开数据库:', name, '版本:', version);
            var req = new MockIDBRequest();

            var existingData = __webthief_idb_storage__[name] || {};
            var oldVersion = existingData.__version__ || 0;
            var newVersion = version || 1;

            var db = new MockIDBDatabase(name, newVersion);
            __webthief_idb_databases__[name] = db;

            // 触发 upgradeneeded 事件
            if (oldVersion < newVersion) {
                req._fireUpgradeNeeded(oldVersion, newVersion);
            }

            // 延迟触发 success
            setTimeout(function() {
                req._fireSuccess(db);
            }, 10);

            return req;
        },

        deleteDatabase: function(name) {
            console.log('[WebThief IDB] 删除数据库:', name);
            delete __webthief_idb_databases__[name];
            delete __webthief_idb_storage__[name];
            saveIDBData();

            var req = new MockIDBRequest();
            req._fireSuccess(undefined);
            return req;
        },

        databases: function() {
            var dbs = Object.keys(__webthief_idb_databases__).map(function(name) {
                return {
                    name: name,
                    version: __webthief_idb_databases__[name].version
                };
            });
            return Promise.resolve(dbs);
        },

        cmp: function(a, b) {
            if (a < b) return -1;
            if (a > b) return 1;
            return 0;
        }
    };

    // ── 替换原生 IndexedDB API ──
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

        console.log('[WebThief IDB] IndexedDB API 已模拟');
    } catch (e) {
        console.warn('[WebThief IDB] IndexedDB 模拟失败:', e);
    }

    // ── 导出函数 ──
    window.__webthief_get_idb_operations__ = function() {
        return __webthief_idb_operations__;
    };

    window.__webthief_get_idb_databases__ = function() {
        return Object.keys(__webthief_idb_databases__);
    };

    window.__webthief_get_idb_data__ = function(dbName, storeName) {
        if (dbName && storeName) {
            return __webthief_idb_storage__[dbName] && __webthief_idb_storage__[dbName][storeName] || {};
        }
        if (dbName) {
            return __webthief_idb_storage__[dbName] || {};
        }
        return __webthief_idb_storage__;
    };

    window.__webthief_clear_idb_operations__ = function() {
        __webthief_idb_operations__ = [];
    };

    window.__webthief_export_idb_data__ = function() {
        return JSON.stringify(__webthief_idb_storage__);
    };

    window.__webthief_import_idb_data__ = function(jsonData) {
        try {
            __webthief_idb_storage__ = JSON.parse(jsonData);
            saveIDBData();
            return true;
        } catch (e) {
            return false;
        }
    };

    console.log('[WebThief IDB] IndexedDB 模拟器已激活');
})();
"""

    async def inject_to_page(self, page: Any) -> None:
        """
        将 IndexedDB 模拟器注入到页面

        Args:
            page: Playwright Page 对象
        """
        script = self.get_injection_script()
        await page.evaluate(script)
        console.print("[green]  ✓ IndexedDB 模拟器已注入[/]")

    async def get_operations(self, page: Any) -> list[dict[str, Any]]:
        """
        获取操作记录

        Args:
            page: Playwright Page 对象

        Returns:
            操作记录列表
        """
        try:
            operations = await page.evaluate("() => window.__webthief_get_idb_operations__?.() || []")
            return operations
        except Exception:
            return []

    async def get_databases(self, page: Any) -> list[str]:
        """
        获取数据库名称列表

        Args:
            page: Playwright Page 对象

        Returns:
            数据库名称列表
        """
        try:
            databases = await page.evaluate("() => window.__webthief_get_idb_databases__?.() || []")
            return databases
        except Exception:
            return []

    async def get_store_data(self, page: Any, db_name: str, store_name: str) -> dict[str, Any]:
        """
        获取对象存储数据

        Args:
            page: Playwright Page 对象
            db_name: 数据库名称
            store_name: 对象存储名称

        Returns:
            存储数据字典
        """
        try:
            data = await page.evaluate(
                "([dbName, storeName]) => window.__webthief_get_idb_data__?.(dbName, storeName) || {}",
                [db_name, store_name]
            )
            return data
        except Exception:
            return {}

    async def export_data(self, page: Any) -> str:
        """
        导出所有 IndexedDB 数据

        Args:
            page: Playwright Page 对象

        Returns:
            JSON 字符串
        """
        try:
            data = await page.evaluate("() => window.__webthief_export_idb_data__?.() || '{}'")
            return data
        except Exception:
            return "{}"

    async def import_data(self, page: Any, json_data: str) -> bool:
        """
        导入 IndexedDB 数据

        Args:
            page: Playwright Page 对象
            json_data: JSON 字符串

        Returns:
            是否成功
        """
        try:
            result = await page.evaluate(
                "([jsonData]) => window.__webthief_import_idb_data__?.(jsonData) || false",
                [json_data]
            )
            return bool(result)
        except Exception:
            return False

    async def clear_operations(self, page: Any) -> None:
        """
        清除操作记录

        Args:
            page: Playwright Page 对象
        """
        try:
            await page.evaluate("() => window.__webthief_clear_idb_operations__?.()")
        except Exception:
            pass

    def save_data_to_file(self, data: str, filename: str = "idb_export.json") -> Path:
        """
        保存数据到文件

        Args:
            data: JSON 数据
            filename: 文件名

        Returns:
            文件路径
        """
        filepath = self.storage_dir / filename
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(data)
        return filepath

    def load_data_from_file(self, filename: str = "idb_export.json") -> str:
        """
        从文件加载数据

        Args:
            filename: 文件名

        Returns:
            JSON 数据
        """
        filepath = self.storage_dir / filename
        if not filepath.exists():
            return "{}"
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()

    def print_operations_summary(self, operations: list[dict[str, Any]]) -> None:
        """
        打印操作摘要

        Args:
            operations: 操作记录
        """
        if not operations:
            console.print("[yellow]  无 IndexedDB 操作记录[/]")
            return

        table = Table(title=f"IndexedDB 操作摘要 (共 {len(operations)} 条)")
        table.add_column("操作", style="cyan")
        table.add_column("数据库", style="green")
        table.add_column("存储", style="blue")
        table.add_column("键", style="yellow")
        table.add_column("状态", style="dim")

        for op in operations[:50]:  # 限制显示数量
            key = str(op.get("key", ""))[:20]
            status = "✓" if op.get("success") else "✗"
            table.add_row(
                op.get("operation", "unknown"),
                op.get("database", ""),
                op.get("store", ""),
                key,
                status
            )

        console.print(table)

    def get_storage_stats(self) -> dict[str, Any]:
        """
        获取存储统计信息

        Returns:
            统计信息字典
        """
        total_size = 0
        db_count = 0
        store_count = 0

        for db_dir in self.storage_dir.iterdir():
            if db_dir.is_dir():
                db_count += 1
                for store_file in db_dir.glob("*.json"):
                    if store_file.name != "_db_info.json":
                        store_count += 1
                        try:
                            total_size += store_file.stat().st_size
                        except Exception:
                            pass

        return {
            "database_count": db_count,
            "store_count": store_count,
            "total_size_bytes": total_size,
            "max_size_bytes": self.max_storage_size,
            "usage_percent": (total_size / self.max_storage_size * 100) if self.max_storage_size > 0 else 0,
        }
