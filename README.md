# WebThief

高保真网站克隆工具，专为现代 JavaScript 应用程序设计。

## 功能特性

### 核心能力
- **高保真克隆**：完美复现 JavaScript 动态渲染的 SPA 页面
- **运行时兼容层**：完整的 XHR/fetch 响应镜像和代理级位置欺骗
- **视口激活**：分段式滚动触发 IntersectionObserver 驱动的动画
- **SPA 预渲染**：自动提取并预渲染 Angular/React/Vue 路由
- **技术栈检测**：自动检测 50+ 种技术并调整渲染策略

### 动画优化功能 (v4.2.0 新增)
WebThief 现在提供专业的动画处理功能，确保克隆的网站保留最佳视觉效果：

#### CSS 动画分析与保留
- **智能动画检测**：自动识别入场动画、悬停动画、循环动画等类型
- **重要性评分**：根据视觉重要性为每个动画打分（0-100）
- **选择性保留**：智能保留关键动画，移除装饰性动画
- **冻结点计算**：计算最优动画冻结点，确保静态页面呈现最佳效果

#### 视差滚动效果捕获
- **多属性支持**：支持 `data-speed`、`data-parallax`、`data-parallax-speed` 等属性
- **库检测**：自动检测 rellax、skrollr、simpleParallax 等视差库
- **位置计算**：精确计算不同滚动位置的视差层偏移
- **静态转换**：将视差效果转换为 CSS 动画或 IntersectionObserver 实现

#### GSAP ScrollTrigger 支持
- **库检测**：自动检测 GSAP ScrollTrigger、ScrollMagic、AOS 等滚动动画库
- **配置解析**：提取 scrub、pin、trigger、start、end 等配置
- **状态捕获**：在多个滚动位置采样动画状态
- **桥接脚本**：生成兼容性脚本，在克隆页面恢复滚动动画

#### Canvas 应用克隆
- **元素检测**：自动检测页面中的 Canvas 元素
- **内容捕获**：截图保存 Canvas 实时绘制内容
- **动态录制**：支持录制 Canvas 动画序列
- **静态替换**：将动态 Canvas 转换为静态图像

#### Hover 效果检测
- **伪类分析**：检测 `:hover`、`:focus`、`:active` 伪类触发的样式变化
- **视觉评估**：评估 hover 效果的视觉重要性
- **静态转换**：将动态 hover 效果转换为静态 CSS
- **交互保留**：选择性保留关键交互效果

#### 鼠标轨迹模拟
- **智能遍历**：模拟鼠标在页面上的自然移动轨迹
- **悬停触发**：自动触发悬停效果，捕获动态内容
- **交互激活**：激活鼠标跟随动画和交互元素

### 服务器与预览
- **独立服务器**：`webthief serve` 命令启动本地 HTTP 服务器
- **CORS 支持**：内置 CORS 配置，方便开发调试
- **自动打开浏览器**：可选自动打开浏览器预览

### 插件系统（可选）
- WebSocket 代理：记录和回放 WebSocket 消息
- 浏览器 API 模拟：Service Worker、IndexedDB 模拟
- 前端适配器：微前端和 SSR 检测
- 安全处理器：指纹轮换、反爬虫绕过
- 性能优化器：动态并发调整、内存管理

## 安装

```bash
pip install webthief
```

## 快速开始

### 克隆网站

```bash
# 基础用法
webthief clone https://example.com -o ./output

# 单页面模式，延长等待时间
webthief clone https://example.com --single-page --wait 5 -o ./output -v

# 全站爬取
webthief clone https://example.com --crawl-site --max-pages 100 -o ./output
```

### 启用动画优化功能

```bash
# 启用所有动画优化功能
webthief clone https://example.com \
  --mouse-simulation \
  --scroll-precision \
  --canvas-recording \
  --physics-capture \
  --animation-analyze \
  -o ./output

# 仅启用 CSS 动画分析
webthief clone https://example.com --animation-analyze -o ./output

# 克隆 GSAP 滚动动画网站
webthief clone https://example.com \
  --scroll-precision \
  --mouse-simulation \
  --wait 5 \
  -o ./output

# 克隆 Canvas 应用
webthief clone https://example.com \
  --canvas-recording \
  --wait 3 \
  -o ./output
```

### 预览克隆结果

```bash
# 启动本地服务器
webthief serve ./output --port 8080

# 自定义主机地址
webthief serve ./output --host 0.0.0.0 --port 3000

# 禁用自动打开浏览器
webthief serve ./output --no-browser
```

## CLI 命令

### `webthief clone` - 克隆网站

| 选项 | 默认值 | 描述 |
|------|--------|------|
| `-o, --output` | `./webthief_output` | 输出目录 |
| `-c, --concurrency` | `20` | 并发下载数 |
| `-t, --timeout` | `30` | 下载超时（秒） |
| `--delay` | `0.1` | 请求间隔（秒） |
| `--no-js` | `False` | 禁用 JavaScript 渲染 |
| `--keep-js/--neutralize-js` | `True` | 保留 JS 执行 / 中和所有 JS |
| `--user-agent` | 随机 | 自定义 User-Agent |
| `--wait` | `3` | 页面加载后额外等待（秒） |
| `-v, --verbose` | `False` | 详细日志输出 |
| `--enable-qr-intercept` | `True` | 二维码拦截（实时二维码克隆） |
| `--enable-react-intercept` | `True` | React 组件拦截（完全体交互菜单） |
| `--crawl-site/--single-page` | `True` | 递归抓取整个站点 / 仅抓取单页 |
| `--max-pages` | `5000` | 站点抓取模式下的最大页面数上限 |
| `--auth-mode` | `manual-pause` | 认证处理策略 |
| `--session-cache` | `True` | 启用加密会话缓存 |
| `--local-server` | `False` | 克隆完成后启动本地服务器 |
| `--port` | `8080` | 服务器端口 |
| `--https` | `False` | 启用 HTTPS 模拟 |

#### 动画优化选项

| 选项 | 默认值 | 描述 |
|------|--------|------|
| `--mouse-simulation` | `False` | 启用鼠标轨迹模拟（触发交互式动画） |
| `--scroll-precision` | `False` | 启用高精度滚动（捕获滚动触发动画） |
| `--canvas-recording` | `False` | 启用 Canvas 录制（捕获动态绘制内容） |
| `--physics-capture` | `False` | 启用物理引擎捕获（保存物理模拟状态） |
| `--animation-analyze` | `False` | 启用 CSS 动画分析（选择性保留关键动画） |

### `webthief serve` - 本地服务器

| 选项 | 默认值 | 描述 |
|------|--------|------|
| `-p, --port` | `8080` | 服务器端口 |
| `--host` | `127.0.0.1` | 服务器主机地址 |
| `--no-browser` | `False` | 禁用自动打开浏览器 |
| `--no-cors` | `False` | 禁用 CORS 支持 |

## 插件选项

高级插件默认禁用，可通过 CLI 选项启用：

```bash
# 启用 API 模拟（缓存 API 响应）
webthief clone https://example.com --api-simulation

# 启用安全处理器（指纹轮换、反爬虫绕过）
webthief clone https://example.com --security-handler

# 启用性能优化器（动态并发调整、内存管理）
webthief clone https://example.com --performance-optimizer

# 启用所有插件和动画功能
webthief clone https://example.com \
  --api-simulation \
  --security-handler \
  --performance-optimizer \
  --mouse-simulation \
  --scroll-precision \
  --canvas-recording \
  --animation-analyze
```

## Python API

```python
import asyncio
from webthief.core.orchestrator import Orchestrator

async def main():
    orchestrator = Orchestrator(
        url="https://example.com",
        output_dir="./output",
        concurrency=20,
        timeout=30,
        verbose=True,
        # 动画优化选项
        enable_mouse_simulation=True,
        enable_scroll_precision=True,
        enable_canvas_recording=True,
        enable_physics_capture=True,
        enable_animation_analyze=True,
    )
    await orchestrator.run()

asyncio.run(main())
```

## 使用示例

### 示例 1：克隆带有视差滚动的网站

```bash
webthief clone https://parallax-example.com \
  --scroll-precision \
  --mouse-simulation \
  --wait 5 \
  -o ./parallax-site \
  -v
```

### 示例 2：克隆带有 GSAP 动画的网站

```bash
webthief clone https://gsap-example.com \
  --scroll-precision \
  --animation-analyze \
  --wait 5 \
  -o ./gsap-site \
  -v
```

### 示例 3：克隆 Canvas 游戏/应用

```bash
webthief clone https://canvas-game.com \
  --canvas-recording \
  --mouse-simulation \
  --wait 3 \
  -o ./canvas-game \
  -v
```

### 示例 4：克隆带有复杂 Hover 效果的网站

```bash
webthief clone https://hover-effects.com \
  --mouse-simulation \
  --animation-analyze \
  --wait 3 \
  -o ./hover-site \
  -v
```

### 示例 5：完整动画捕获（推荐用于展示型网站）

```bash
webthief clone https://showcase-site.com \
  --mouse-simulation \
  --scroll-precision \
  --canvas-recording \
  --physics-capture \
  --animation-analyze \
  --wait 5 \
  -o ./showcase \
  -v
```

## 适用场景

- **离线演示**：创建完全离线运行的网站克隆
- **SPA 克隆**：Angular、React、Vue 单页应用
- **技术栈分析**：快速识别网站使用的技术栈
- **文档站点**：将 SPA 文档转换为静态多页站点
- **动画展示**：保留复杂的 CSS/JS 动画效果
- **设计参考**：克隆优秀网站用于设计参考

## 已知限制

- **WebGL/Canvas**：在 `file://` 协议下部分功能受限，建议使用 HTTP 服务器预览
- **动态路由**：某些动态生成的路由可能无法预渲染
- **HTTPS 证书**：自签名证书会触发浏览器安全警告
- **复杂物理引擎**：某些复杂物理模拟可能无法完全捕获
- **WebSocket 实时数据**：实时数据流需要预先录制

## 最佳实践

1. **动画网站克隆**：对于带有复杂动画的网站，建议启用 `--mouse-simulation` 和 `--scroll-precision`
2. **Canvas 应用**：使用 `--canvas-recording` 捕获动态绘制内容
3. **等待时间**：对于动画丰富的网站，适当增加 `--wait` 时间（5-10 秒）
4. **本地预览**：克隆完成后使用 `webthief serve` 启动服务器预览，避免 `file://` 协议限制

## 文档

- [高级功能指南](ADVANCED_FEATURES.md) - 运行时保留、二维码拦截、菜单克隆
- [动画处理最佳实践](docs/animation_best_practices.md) - 不同动画类型的处理建议
- [Changelog](CHANGELOG.md) - 版本历史和变更记录

## 许可证

MIT License
