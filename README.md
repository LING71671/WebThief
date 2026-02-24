# 🕷️ WebThief

> 高保真 1:1 网站克隆工具 — 完美还原依赖 JavaScript 动态渲染的现代 SPA 网页

## ✨ 核心特性

- **无头浏览器渲染** — Playwright Chromium 引擎，完美处理 SPA / CSR 页面
- **深度懒加载触发** — 自动滚动页面触发所有 `IntersectionObserver` 和异步请求
- **反检测** — Stealth 脚本绕过 WebDriver 检测，UA 随机伪装
- **AST 级解析** — tinycss2 CSS 语法树解析，BeautifulSoup DOM 遍历，**零正则**
- **智能净化** — 自动移除 CSP / Service Worker / 追踪器 / SRI 校验
- **高并发下载** — asyncio + aiohttp，SHA256 哈希去重，指数退避重试
- **离线可用** — 克隆后的站点可在 `file://` 协议或本地服务器上完美运行
- **全站递归抓取** — 同 host BFS 队列抓取所有层级页面（可设置页面上限）
- **人工登录暂停** — 遇登录墙自动暂停，完成扫码/登录后继续抓取
- **会话加密缓存** — 认证状态加密保存，二次运行自动复用
- **🔐 实时二维码克隆** — 拦截二维码 API，保留刷新逻辑，实现"活的"二维码（NEW v3.0）
- **⚛️ 完全体交互菜单** — React 组件拦截，保留所有下拉菜单和交互元素（NEW v3.0）

## 📦 安装

```bash
# 克隆仓库
git clone https://github.com/LING71671/WebThief.git
cd WebThief

# 安装依赖
pip install -e .

# 安装 Playwright 浏览器
playwright install chromium
```

## 🚀 使用

```bash
# 基本用法
webthief https://example.com

# 全站递归（默认开启）
webthief https://example.com --crawl-site --max-pages 800

# 仅抓单页（兼容旧行为）
webthief https://example.com --single-page

# 指定输出目录
webthief https://example.com -o ./my_clone

# 高并发 + 详细日志
webthief https://example.com -c 30 -v

# 禁用 JS（纯静态抓取）
webthief https://example.com --no-js

# 自定义等待时间（适合慢速 SPA）
webthief https://example.com --wait 10

# 遇登录墙时暂停人工认证，并缓存会话
webthief https://example.com --auth-mode manual-pause --session-cache

# 导入已有 Playwright storageState
webthief https://example.com --auth-mode import-session --session-file ./state.json
```

### 完整参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `URL` | 目标网页地址 | (必填) |
| `-o, --output` | 输出目录 | `./webthief_output` |
| `-c, --concurrency` | 并发下载数 | `20` |
| `-t, --timeout` | 单文件超时 (秒) | `30` |
| `--delay` | 请求间隔 (秒) | `0.1` |
| `--no-js` | 禁用 JS 渲染 | `false` |
| `--keep-js` | 保留 JS 执行能力 | `false` |
| `--user-agent` | 自定义 UA | 随机 |
| `--wait` | 额外等待 (秒) | `3` |
| `--enable-qr-intercept` | 启用二维码拦截 | `true` |
| `--enable-react-intercept` | 启用 React 拦截 | `true` |
| `--crawl-site / --single-page` | 全站递归 / 单页抓取 | `--crawl-site` |
| `--max-pages` | 递归抓取最大页面数 | `5000` |
| `--auth-mode` | 登录页处理策略 (`manual-pause/import-session/skip`) | `manual-pause` |
| `--session-cache / --no-session-cache` | 启用加密会话缓存 | `--session-cache` |
| `--session-file` | 会话文件路径（导入或缓存路径） | `None` |
| `--headful-auth / --no-headful-auth` | 手动认证时是否打开可视浏览器 | `--headful-auth` |
| `-v, --verbose` | 详细日志 | `false` |

### 高级功能示例

```bash
# 克隆带实时二维码的登录页
webthief https://example.com/login --enable-qr-intercept

# 克隆带复杂菜单的 SPA 网站
webthief https://example.com --enable-react-intercept

# 同时启用所有高级功能
webthief https://example.com --enable-qr-intercept --enable-react-intercept --wait 5
```

详细的高级功能使用指南请参考 [ADVANCED_FEATURES.md](./ADVANCED_FEATURES.md)

## 🔒 合规说明

- 仅应对你拥有或获得明确授权的站点执行全站抓取。
- 默认递归范围限制为入口 URL 的同一 host，不跨域抓取。

## 🏗️ 架构

```
渲染层 (Playwright) → 净化层 (CSP/SW清洗) → 解析重写层 (AST) → 下载引擎 (async) → 存储层
```

## ⚠️ 免责声明

本工具仅供学习研究使用。请遵守目标网站的 `robots.txt` 和服务条款。
