## 问题分析

发现根本原因：`__WEBTHIEF_RESPONSE_MAP__` 中错误地缓存了主页面的 HTML 内容（`"https://www.nanfu.global/"`）。

当浏览器打开克隆的页面时，JavaScript 代码通过 `fetch` 或 `XHR` 请求主页内容，返回了这个缓存的 HTML 字符串，导致页面显示 JSON 格式的 HTML 内容。

## 修复方案

### 1. 修改 renderer.py
在 `_attach_network_hooks` 方法中，**不应该缓存 HTML 页面内容**（Content-Type 为 text/html 且 URL 是页面主 URL）。

### 2. 修改 sanitizer.py
在 `_inject_resource_map_script` 方法中，**不应该将 HTML 页面内容注入到 response_map** 中。

### 3. 重新测试
重新克隆南孚官网，验证修复效果。

请确认此修复方案后，我将开始实施具体的代码修改。