# WebThief

High-fidelity website cloning tool for modern JS-heavy pages (SPA/CSR), with offline-friendly output.

高保真网站克隆工具，面向现代 JavaScript 动态页面（SPA/CSR），支持离线运行产物。

## Overview | 项目简介

- EN: WebThief renders pages in Chromium (Playwright), captures runtime resources, rewrites paths, and outputs a runnable local mirror.
- 中文：WebThief 通过 Playwright Chromium 渲染页面，捕获运行时资源并重写路径，输出可运行的本地镜像站点。

## Features | 核心特性

- EN: Playwright-based rendering for SPA/CSR pages
- 中文：基于 Playwright 的页面渲染，适配 SPA/CSR
- EN: Deep lazy-load triggering (scroll + interaction preloading)
- 中文：深度懒加载触发（滚动 + 交互预加载）
- EN: AST-level parsing/rewrite for HTML/CSS (BeautifulSoup + tinycss2)
- 中文：HTML/CSS AST 级解析与重写（BeautifulSoup + tinycss2）
- EN: Resource downloader with concurrency, retry, and SHA256 dedup
- 中文：高并发下载、重试与 SHA256 去重
- EN: Optional login pause with encrypted session cache
- 中文：可选登录暂停与加密会话缓存
- EN: Optional QR/menu intercept capabilities for advanced dynamic pages
- 中文：可选二维码/菜单拦截能力，适配复杂动态页面

## Install | 安装

```bash
git clone https://github.com/LING71671/WebThief.git
cd WebThief
pip install -e .
playwright install chromium
```

## Quick Start | 快速开始

```bash
# Single page | 单页抓取
webthief https://example.com --single-page

# Site crawl (same host) | 同站点递归抓取
webthief https://example.com --crawl-site --max-pages 800

# Force static-safe output (disable runtime JS) | 强制静态安全输出
webthief https://example.com --neutralize-js

# Verbose mode | 详细日志
webthief https://example.com -v

# Manual auth pause + session cache | 人工登录暂停 + 会话缓存
webthief https://example.com --auth-mode manual-pause --session-cache
```

## CLI Options | 参数说明

| Option | Default | Description (EN / 中文) |
|---|---:|---|
| `URL` | required | Target URL / 目标地址 |
| `-o, --output` | `./webthief_output` | Output directory / 输出目录 |
| `-c, --concurrency` | `20` | Download concurrency / 下载并发数 |
| `-t, --timeout` | `30` | File timeout (sec) / 单文件超时（秒） |
| `--delay` | `0.1` | Request delay / 请求间隔 |
| `--no-js` | `false` | Disable JS rendering / 禁用 JS 渲染 |
| `--keep-js / --neutralize-js` | `--keep-js` | Keep JS runtime in output / 保留输出页 JS 执行能力（默认） |
| `--wait` | `3` | Extra wait after load / 页面加载后额外等待 |
| `--enable-qr-intercept` | `true` | Enable QR interception / 启用二维码拦截 |
| `--enable-react-intercept` | `true` | Enable React/menu interception / 启用 React 菜单拦截 |
| `--crawl-site / --single-page` | `--crawl-site` | Site crawl or single page / 递归或单页 |
| `--max-pages` | `5000` | Crawl page limit / 最大抓取页数 |
| `--auth-mode` | `manual-pause` | `manual-pause/import-session/skip` |
| `--session-cache` | `true` | Encrypted session cache / 加密会话缓存 |
| `--session-file` | `None` | Session file path / 会话文件路径 |
| `--headful-auth` | `true` | Visual browser for auth / 人工认证可视浏览器 |
| `-v, --verbose` | `false` | Verbose logs / 详细日志 |

## Architecture | 架构

```text
Renderer (Playwright)
  -> Sanitizer (CSP/SW/tracker cleanup)
  -> Parser/Rewriter (AST)
  -> Downloader (async + dedup)
  -> Storage
```

## Docs | 文档

- [ADVANCED_FEATURES.md](./ADVANCED_FEATURES.md)
- [CHANGELOG.md](./CHANGELOG.md)

## Compliance | 合规说明

- EN: Use only on websites you own or are explicitly authorized to test.
- 中文：仅用于你拥有或明确授权的站点。
- EN: Respect target website terms, robots rules, and applicable laws.
- 中文：请遵守目标网站条款、robots 规则及适用法律。

## License | 许可

[GNU General Public License v3 (GPLv3)](./LICENSE)
