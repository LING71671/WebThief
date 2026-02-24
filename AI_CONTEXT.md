# WebThief: AI 助手项目索引 (AI_CONTEXT.md)

> 文档维护更新（2026-02-24）：已清理仓库测试脚本与测试产物目录，本文档内容已同步调整。


WebThief 是一个高保真网页克隆引擎，旨在捕获现代复杂 Web 应用（如 Steam、Discord、SaaS 控制台）的 **运行时视觉状态** 与关键交互能力。

---

## 🏗️ 核心架构

### 1. `renderer.py` (核心引擎)
- **底层驱动**: Playwright (Chromium) + stealth-js。
- **劫持策略**:
    - `on_request`/`on_response`: 挂钩网络层，直接从浏览器内存中捕获二进制资源（图片、字体、CSS），并存入 `response_cache`，从而跳过冗余网络请求。
- **固化流水线 (Solidification Pipeline)**:
    - **CSS**: 扫描 `:root` 和各元素，提取计算样式（Computed Styles）和 CSS 变量，并注入固定 `<style>` 块，防止克隆页失去配色和布局。
    - **Canvas**: 使用 Playwright 元素截图将动态 `<canvas>` 转换为高分辨率 PNG (Base64)，保留图表或绘图。
    - **Shadow DOM**: 递归展开 Shadow Root 并合并到主 DOM 树，实现静态化捕获。

### 2. `config.py` (配置)
- 存储 Stealth JS 载荷和 User-Agent 随机化逻辑。
- 定义 `TRACKER_DOMAINS`，在克隆过程中过滤营销分析和广告脚本。

---

## 💎 当前状态: v3.0 (稳定版)
- **状态**: 已支持实时二维码克隆与交互菜单保留，动态还原能力进入稳定阶段。
- **核心逻辑**: 渲染引擎在触发悬停事件并确保页面充分渲染后，执行“冻结快照”。
- **语法规范**: `renderer.py` 遵循严格异步/等待流。严禁在未经过 `page.evaluate` 包裹的情况下直接向 Python 块注入原生 JS。

---

## 下一阶段目标 (v3.1 优化)
- **性能优化**: 降低高级拦截对渲染耗时和内存的增量。
- **兼容扩展**: 增强 Vue/Angular 站点的菜单与生命周期拦截。
- **稳定性提升**: 增加二维码刷新失败重试与更细粒度日志。

