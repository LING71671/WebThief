# WebThief: AI 助手项目索引 (AI_CONTEXT.md)

WebThief 是一个高保真网页克隆引擎，旨在捕获现代复杂 Web 应用（如 Steam、Discord、SaaS 控制台）的 **运行时视觉状态**。

---

## 🏗️ 核心架构

### 1. `renderer.py` (核心引擎)
- **底层驱动**: Playwright (Chromium) + stealth-js。
- **劫持策略**: 
    - `on_request`/`on_response`: 挂钩网络层，直接从浏览器内存中捕获二进制资源（图片、字体、CSS），并存入 `response_cache`，从而跳过冗余的网络请求。
- **固化流水线 (Solidification Pipeline)**:
    - **CSS**: 扫描 `:root` 和各元素，提取计算样式（Computed Styles）和 CSS 变量，并注入为固定 `<style>` 块，防止克隆页失去配色和布局。
    - **Canvas**: 使用 Playwright 元素截图技术将动态 `<canvas>` 转换为高分辨率 PNG (Base64)，以保留复杂的图表或绘图。
    - **Shadow DOM**: 递归展开 Shadow Root 并合并到主 DOM 树中，实现静态化捕获。

### 2. `config.py` (配置)
- 存储 Stealth JS 载荷和 User-Agent 随机化逻辑。
- 定义 `TRACKER_DOMAINS`，在克隆过程中过滤掉营销分析和广告脚本。

---

## 💎 当前状态: v2.0 (稳定版)
- **状态**: 视觉保真度极高；动态交互目前处于静态化处理阶段。
- **核心逻辑**: 渲染引擎在触发一系列悬停事件并确保页面充分渲染后，执行“冻结快照”。
- **语法规范**: `renderer.py` 遵循严格的异步/等待流。严禁在未经过 `page.evaluate` 包裹的情况下直接向 Python 块注入原生 JS。

---

##  下一阶段目标 (交互保真)
项目正致力于实现 **“1:1 动态还原”**:
- **目标**: 实现带 **实时刷新二维码** 和 **全功能交互菜单** 的克隆。
