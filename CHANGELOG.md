# WebThief 版本日志 (CHANGELOG)

> 文档维护更新（2026-02-24）：已清理仓库测试脚本与测试产物目录，本文档内容已同步调整。

## v3.0.2 (2026-02-25) - 文档精简与忽略规则整理

### 📝 文档结构调整
- 保留核心文档：`README.md`、`ADVANCED_FEATURES.md`、`CHANGELOG.md`
- 将高级快速开始内容合并进 `ADVANCED_FEATURES.md`
- 删除过时或重复文档：
  - `AI_CONTEXT.md`
  - `IMPLEMENTATION_SUMMARY.md`
  - `QUICKSTART_ADVANCED.md`
  - `ROADMAP.md`
  - `TEST_RESULTS.md`
  - `VISUAL_INSPECTION_GUIDE.md`

### 🧹 仓库规则更新
- 扩展 `.gitignore`，补充常见 Python/IDE/日志/本地克隆输出忽略项

## v3.0.1 (2026-02-24) - 文档与仓库清理

### 🧹 仓库清理
- 移除测试脚本：`test_demo.py`、`test_steam.py`、`test_steam_login.py`、`test_unit.py`
- 移除测试目录：`tests/`、`qq_official_test/`
- 移除示例测试脚本：`examples/test_advanced_features.py`

### 📝 文档更新
- 全量 Markdown 文档增加维护更新标记
- 清理已删除测试脚本的文档引用
- 更新 AI 上下文与路线图到 v3.0 状态

---

## v3.0.0 (2026-02-24) - 动态交互还原版 (Dynamic Interaction Restoration)

这是 WebThief 的革命性版本，实现了 ROADMAP 中的两大核心目标：**实时二维码克隆**和**完全体交互菜单**。

### 🚀 核心新功能

#### 🔐 实时二维码克隆 (Live QR Code Cloning)
- **二维码 API 拦截器**：
    - 自动识别并拦截所有二维码相关的 API 请求（支持关键字匹配）
    - 捕获 fetch、XMLHttpRequest 和 Canvas toDataURL 调用
    - 记录二维码生成的完整生命周期数据
- **桥接脚本注入**：
    - 生成 CORS 代理层，使克隆页面能与原站服务器通信
    - 自动处理认证 Cookie 和 Token
    - 提供手动刷新接口 `window.__webthief_qr_refresh()`
- **脚本生命周期保留**：
    - 识别并保留二维码核心脚本（避免被净化）
    - 支持自定义二维码关键字扩展
- **最终效果**：克隆页面的二维码可以实时刷新，扫码交互与官方完全一致

#### ⚛️ 完全体交互菜单 (Full Interactive Menus)
- **React Unmount 拦截**：
    - 劫持 `ReactDOM.unmountComponentAtNode` 阻止组件卸载
    - 拦截 Fiber 节点的 `commitUnmount`（React 16+ 内部机制）
    - 阻止 `Element.removeChild` 删除 React 管理的节点
- **自动菜单触发**：
    - 遍历所有可能的菜单触发器（支持 Bootstrap、Material-UI、Ant Design 等）
    - 模拟完整的鼠标事件序列（mouseenter、mouseover、click 等）
    - 智能等待异步内容加载完成
- **状态冻结与固化**：
    - 强制所有展开的菜单保持可见（`display: block !important`）
    - 防止 JavaScript 再次隐藏菜单（拦截 style 属性修改）
    - 添加 `data-webthief-frozen` 标记
- **JS 到 CSS 转换**：
    - 将 JavaScript 驱动的显隐逻辑转换为纯 CSS `:hover` 规则
    - 注入菜单保留运行时脚本到克隆页面
    - 恢复原生的悬停交互体验
- **最终效果**：所有下拉菜单、Mega Menu 在克隆页面中完全可交互，逻辑一比一复刻

### 🔧 架构改进
- **新增模块**：
    - `qr_interceptor.py` - 二维码拦截与桥接
    - `react_interceptor.py` - React 组件拦截与菜单固化
- **渲染器增强**：
    - 支持可选的二维码拦截（`enable_qr_intercept`）
    - 支持可选的 React 拦截（`enable_react_intercept`）
    - 扩展 `RenderResult` 包含 QR 数据和菜单 CSS
- **净化器增强**：
    - 支持注入自定义脚本（二维码桥接、菜单保留）
    - 新增 `_inject_custom_script` 方法
- **CLI 增强**：
    - 新增 `--enable-qr-intercept` 选项（默认启用）
    - 新增 `--enable-react-intercept` 选项（默认启用）

### 📚 文档更新
- 新增 `ADVANCED_FEATURES.md` - 高级功能详细使用指南
- 更新 `README.md` - 添加新功能说明和示例
- 更新 `ROADMAP.md` - 标记已完成的目标

### 🎯 适用场景
- **二维码克隆**：Steam 登录、微信/QQ 扫码、支付二维码等
- **菜单克隆**：Steam 商店分类菜单、电商网站导航、SaaS 应用下拉菜单等

### ⚠️ 已知限制
- **二维码**：某些网站的 CORS 策略可能阻止跨域通信
- **菜单**：保留的组件会增加 DOM 大小（+10-30%）
- **性能**：高级功能会增加 2-5 秒的渲染时间

---

## v2.0.0 (2026-02-24) - 高保真固化版 (High-Fidelity Solidification)

这是 WebThief 的重大升级版本，旨在解决现代网页克隆中常见的“视觉破碎”和“动态内容丢失”问题。

### 🚀 核心改进
- **🎨 CSS 样式深度固化**：
    - 实现了 `:root` 样式固化：将所有动态 CSS 变量（`--var`）收集并注入为静态样式表，彻底解决克隆页失去配色和布局变量的问题。
    - 计算背景内联：自动将所有通过 CSS 计算产生的 `background-image` 写入元素的内联样式。
- **🖼️ Canvas 元素截图冻结**：
    - 废弃了不可靠的 `canvas.toDataURL` 方案。
    - 采用 Playwright 元素级截图技术，将所有 Canvas 实时内容转换为 Base64 图像并替换原始标签，完美保留图表、游戏预览和复杂绘图。
- **⚡ 响应体拦截器 (Response Header & Body Cache)**：
    - 新增 `response_cache` 机制，在浏览器渲染过程中直接截获二进制数据（图片、字体、CSS）。
    - 极大提升了资源采集的完整性，减少了对下载器的依赖，解决了需要身份验证或动态生成的资源抓取难题。
- **🖱️ 悬停预加载增强**：
    - 引入了 JS 事件模拟悬停逻辑，在快照提取前自动触发导航、下拉菜单等交互元素，并配合 `networkidle` 确保异步内容加载。
- **🔗 Blob 协议兼容处理**：
    - 实现了 `blob:` 协议解析与 Data URI 转换，初步解决了二维码等动态生成的 Blob 图像在克隆页中无法显示的问题。

### 🔧 性能与稳定性
- **Stealth 脚本集成**：内置最新的绕过检测脚本，提升了对 Steam 等具有反爬机制网站的访问成功率。
- **Shadow DOM 展开**：递归展开所有 Shadow Root，确保静态 HTML 包含所有组件内部的结构。
- **动画冻结**：在快照环节强制暂停所有 CSS 动画，避免截图时页面处于过渡态导致的布局错位。
- **智能资源归一化**：优化了 URL 提取算法，大幅减少冗余请求。

### ⚠️ 已知局限
- **React 状态依赖**：对于像 Steam 分类菜单这种在鼠标离开后会销毁 DOM 的 React 组件，目前的静态克隆仍需进一步优化（建议通过手动固定 Hover 状态处理）。

---

## v1.0.0 (2026-02-18) - 初始版本
- 基础 Playwright 渲染引擎。
- 支持完整资源嗅探与下载。
- 实现目录结构还原。
- 基础 CSS 图片路径分析。


