# WebThief 动画处理最佳实践

> 本文档提供针对不同动画类型的处理建议和常见问题解答，帮助您获得最佳的网站克隆效果。

## 目录

- [快速选择指南](#快速选择指南)
- [CSS 动画处理](#css-动画处理)
- [视差滚动效果](#视差滚动效果)
- [GSAP ScrollTrigger](#gsap-scrolltrigger)
- [Canvas 应用](#canvas-应用)
- [Hover 效果](#hover-效果)
- [鼠标跟随动画](#鼠标跟随动画)
- [常见问题解答](#常见问题解答)

---

## 快速选择指南

根据网站类型选择合适的命令行选项：

| 网站类型 | 推荐选项 | 说明 |
|---------|---------|------|
| 普通企业官网 | `--animation-analyze` | 保留入场动画，移除装饰性动画 |
| 视差滚动网站 | `--scroll-precision --mouse-simulation` | 捕获视差效果和滚动动画 |
| GSAP 动画网站 | `--scroll-precision --animation-analyze --wait 5` | 保留 ScrollTrigger 动画 |
| Canvas 游戏/应用 | `--canvas-recording --mouse-simulation` | 捕获 Canvas 内容 |
| 交互式展示网站 | 所有动画选项 + `--wait 5` | 完整保留所有动画效果 |
| 电商/门户 | `--mouse-simulation --animation-analyze` | 保留悬停效果和关键动画 |

---

## CSS 动画处理

### 支持的动画类型

WebThief 可以识别和处理以下 CSS 动画类型：

#### 1. 入场动画 (Entrance)
```css
/* 会被识别的关键字 */
fadein, slidein, zoomin, bouncein, fade-in, slide-in,
zoom-in, bounce-in, enter, appear, show, intro,
reveal, dropin, grow, expand, popin, flyin
```

**处理建议**：
- 入场动画通常很重要，会被自动保留
- 冻结点默认设置为 100%（动画结束状态）
- 建议保持 `--animation-analyze` 启用

#### 2. 悬停动画 (Hover)
```css
/* 通过选择器识别 */
.btn:hover { animation: pulse 0.3s; }
.card:hover { transform: scale(1.05); }
```

**处理建议**：
- 结合 `--mouse-simulation` 触发悬停效果
- 重要悬停动画会被保留
- 冻结点默认设置为 0%（默认状态）

#### 3. 循环动画 (Loop)
```css
/* 会被识别的关键字 */
infinite, loop, rotate, spin, pulse, shake,
bounce, flash, swing, tada, wobble, loading, spinner
```

**处理建议**：
- 加载动画（loading、spinner）建议保留
- 装饰性动画（如背景浮动元素）会被移除
- 冻结点默认设置为 50%（视觉平衡点）

#### 4. 滚动动画 (Scroll)
```css
/* 会被识别的关键字 */
scroll, parallax, scrolltrigger, scroll-trigger,
aos, scrollreveal, waypoint, sticky
```

**处理建议**：
- 使用 `--scroll-precision` 捕获滚动状态
- 结合 `--mouse-simulation` 获得更好效果
- 需要增加 `--wait` 时间等待动画稳定

### 重要性评分机制

WebThief 根据以下因素计算动画重要性分数（0-100）：

| 因素 | 权重 | 说明 |
|-----|------|------|
| 动画类型 | 10-30 | 入场动画 > 悬停动画 > 循环动画 |
| 关键属性 | 15 | transform、opacity 等关键属性 |
| 持续时间 | 10 | 短动画（<300ms）可能是微交互 |
| 无限循环 | -10 | 装饰性动画降低权重 |

**保留阈值**：分数 >= 40 的动画会被保留

### 使用示例

```bash
# 基础 CSS 动画分析
webthief clone https://example.com --animation-analyze -o ./output

# 分析并查看详细报告
webthief clone https://example.com --animation-analyze -v -o ./output
```

---

## 视差滚动效果

### 支持的视差属性

WebThief 支持检测以下视差相关属性：

```html
<!-- data-speed 属性 -->
<div data-speed="0.5">视差元素</div>

<!-- data-parallax 属性 -->
<div data-parallax="0.3">视差元素</div>

<!-- data-parallax-speed 属性 -->
<div data-parallax-speed="-0.2">反向视差</div>

<!-- data-parallax-direction 属性 -->
<div data-speed="0.5" data-parallax-direction="horizontal">水平视差</div>

<!-- 视差类名 -->
<div class="parallax">视差元素</div>
<div class="parallax-bg">背景视差</div>
<div class="parallax-layer">视差层</div>
```

### 视差库支持

自动检测以下视差库：

| 库名 | 检测方式 | 支持程度 |
|-----|---------|---------|
| Rellax | `window.Rellax` | 完整支持 |
| Skrollr | `window.skrollr` | 完整支持 |
| simpleParallax | `window.simpleParallax` | 完整支持 |
| parallax.js | `window.parallax` | 完整支持 |

### 速度值说明

- `speed > 0`：元素随滚动同向移动（speed=1 表示与滚动速度相同）
- `speed < 0`：元素随滚动反向移动
- `speed = 0.5`：元素移动速度是滚动速度的一半（典型视差效果）
- `speed > 1`：元素移动比滚动快

### 使用示例

```bash
# 基础视差捕获
webthief clone https://parallax-site.com --scroll-precision -o ./output

# 完整视差捕获（推荐）
webthief clone https://parallax-site.com \
  --scroll-precision \
  --mouse-simulation \
  --wait 5 \
  -o ./output \
  -v
```

### 常见问题

**Q: 视差效果在克隆后不明显？**
A: 尝试增加 `--wait` 时间，确保页面完全加载。某些视差库需要滚动触发初始化。

**Q: 多层视差只捕获了部分？**
A: 启用 `--mouse-simulation`，让鼠标遍历整个页面触发所有视差层。

---

## GSAP ScrollTrigger

### 支持的滚动动画库

WebThief 可以检测和处理以下滚动动画库：

| 库名 | 检测标识 | 版本识别 |
|-----|---------|---------|
| GSAP ScrollTrigger | `window.gsap.plugins.scrollTrigger` | 是 |
| ScrollMagic | `window.ScrollMagic` | 是 |
| AOS | `window.AOS` | 否 |
| ScrollReveal | `window.ScrollReveal` | 否 |
| Locomotive Scroll | `window.LocomotiveScroll` | 否 |
| Lenis | `window.Lenis` | 否 |
| Skrollr | `window.skrollr` | 否 |

### ScrollTrigger 配置解析

WebThief 可以提取以下 ScrollTrigger 配置：

```javascript
// 可解析的配置项
gsap.to(".element", {
  scrollTrigger: {
    trigger: ".trigger",      // 触发元素
    start: "top center",      // 开始位置
    end: "bottom center",     // 结束位置
    scrub: true,              // 平滑 scrub
    pin: true,                // 固定元素
    markers: true,            // 调试标记
    toggleActions: "play none none none"  // 切换动作
  },
  x: 100,                     // 动画属性
  opacity: 0.5
});
```

### 状态捕获策略

WebThief 在以下滚动位置采样动画状态：

- 0% - 页面顶部
- 25% - 1/4 位置
- 50% - 中间位置
- 75% - 3/4 位置
- 100% - 页面底部

### 桥接脚本

生成的桥接脚本提供以下 API：

```javascript
// ScrollTrigger 兼容层
window.ScrollTrigger.create({
  trigger: ".element",
  start: "top center"
});

// WebThief 扩展 API
window.WebThiefScrollBridge.observe(".element");
window.WebThiefScrollBridge.refresh();
window.WebThiefScrollBridge.getScrollProgress();
```

### 使用示例

```bash
# 基础 ScrollTrigger 捕获
webthief clone https://gsap-site.com --scroll-precision -o ./output

# 完整 ScrollTrigger 捕获（推荐）
webthief clone https://gsap-site.com \
  --scroll-precision \
  --animation-analyze \
  --mouse-simulation \
  --wait 5 \
  -o ./output \
  -v
```

### 最佳实践

1. **增加等待时间**：GSAP 网站通常需要更长的加载时间，建议 `--wait 5` 或更长
2. **启用鼠标模拟**：某些 ScrollTrigger 需要鼠标交互才能初始化
3. **使用本地服务器**：克隆后使用 `webthief serve` 预览，避免 file:// 协议限制

---

## Canvas 应用

### 支持的 Canvas 类型

- **2D Canvas**：Canvas 2D 上下文绘制的内容
- **WebGL Canvas**：Three.js、Babylon.js 等 3D 渲染
- **动态 Canvas**：动画、游戏、数据可视化

### 捕获模式

#### 1. 静态截图（默认）
捕获 Canvas 当前帧并保存为 PNG 图像：

```bash
webthief clone https://canvas-site.com --canvas-recording -o ./output
```

#### 2. 多帧录制（高级）
录制 Canvas 动画序列：

```bash
# 录制 3 秒，每秒 30 帧
webthief clone https://canvas-site.com \
  --canvas-recording \
  --wait 3 \
  -o ./output
```

### Canvas 处理策略

| Canvas 类型 | 处理建议 | 预期效果 |
|------------|---------|---------|
| 静态图表 | `--canvas-recording` | 完美保留 |
| 简单动画 | `--canvas-recording --wait 3` | 捕获关键帧 |
| 交互式可视化 | `--canvas-recording --mouse-simulation` | 捕获交互状态 |
| 复杂游戏 | 所有选项 + 长等待 | 尽可能保留 |
| WebGL 3D | `--canvas-recording` | 截图保存 |

### 使用示例

```bash
# 基础 Canvas 捕获
webthief clone https://chart-site.com --canvas-recording -o ./output

# Canvas 游戏捕获
webthief clone https://game-site.com \
  --canvas-recording \
  --mouse-simulation \
  --wait 5 \
  -o ./output

# 数据可视化捕获
webthief clone https://viz-site.com \
  --canvas-recording \
  --mouse-simulation \
  --animation-analyze \
  --wait 3 \
  -o ./output
```

### 注意事项

1. **WebGL 限制**：某些高级 WebGL 特性可能无法截图
2. **跨域图像**：如果 Canvas 包含跨域图像，截图可能失败
3. **动态内容**：实时数据可视化可能无法完全捕获

---

## Hover 效果

### 检测范围

WebThief 可以检测以下伪类触发的样式变化：

- `:hover` - 鼠标悬停
- `:focus` - 元素聚焦
- `:active` - 元素激活

### 视觉重要性评估

根据 CSS 属性计算重要性权重：

| 属性 | 权重 | 说明 |
|-----|------|------|
| transform | 1.5 | 变换效果视觉影响大 |
| filter | 1.3 | 滤镜效果视觉影响大 |
| opacity | 1.2 | 透明度变化明显 |
| background-color | 1.0 | 背景色变化 |
| box-shadow | 1.1 | 阴影效果 |
| color | 0.8 | 文字颜色变化 |

### 处理策略

```bash
# 基础 Hover 检测
webthief clone https://site.com --animation-analyze -o ./output

# 完整 Hover 捕获（推荐）
webthief clone https://site.com \
  --mouse-simulation \
  --animation-analyze \
  --wait 3 \
  -o ./output
```

### 嵌套 Hover 处理

对于复杂的嵌套菜单和多级 Hover：

```bash
webthief clone https://complex-menu.com \
  --mouse-simulation \
  --animation-analyze \
  --wait 5 \
  -o ./output \
  -v
```

---

## 鼠标跟随动画

### 工作原理

鼠标模拟器通过以下方式激活鼠标跟随动画：

1. **视口分段**：将页面划分为多个区域
2. **贝塞尔曲线**：模拟自然的鼠标移动轨迹
3. **悬停触发**：在每个区域触发 mouseenter/mouseover 事件
4. **随机偏移**：添加随机性避免机械模式

### 配置建议

| 场景 | 建议 |
|-----|------|
| 简单页面 | 默认配置即可 |
| 复杂交互 | 增加 `--wait` 时间 |
| 全屏动画 | 启用 `--scroll-precision` |
| 游戏/应用 | 所有选项全开 |

### 使用示例

```bash
# 基础鼠标模拟
webthief clone https://site.com --mouse-simulation -o ./output

# 完整交互捕获
webthief clone https://interactive-site.com \
  --mouse-simulation \
  --scroll-precision \
  --animation-analyze \
  --wait 5 \
  -o ./output
```

---

## 常见问题解答

### Q1: 克隆后的网站动画效果丢失了？

**可能原因**：
1. 未启用相应的动画捕获选项
2. 等待时间不足，动画未完全加载
3. 使用了 `file://` 协议访问

**解决方案**：
```bash
# 启用所有动画选项并增加等待时间
webthief clone https://site.com \
  --mouse-simulation \
  --scroll-precision \
  --canvas-recording \
  --animation-analyze \
  --wait 5 \
  -o ./output

# 使用本地服务器预览
webthief serve ./output --port 8080
```

### Q2: 视差滚动效果不正确？

**可能原因**：
1. 视差库需要滚动触发初始化
2. 计算样式依赖于实时滚动位置

**解决方案**：
```bash
# 启用高精度滚动和鼠标模拟
webthief clone https://parallax-site.com \
  --scroll-precision \
  --mouse-simulation \
  --wait 5 \
  -o ./output
```

### Q3: Canvas 内容显示为空白？

**可能原因**：
1. Canvas 内容尚未绘制完成
2. 跨域图像导致截图失败
3. WebGL 上下文丢失

**解决方案**：
```bash
# 增加等待时间
webthief clone https://canvas-site.com \
  --canvas-recording \
  --wait 5 \
  -o ./output
```

### Q4: GSAP 动画不工作？

**可能原因**：
1. ScrollTrigger 需要滚动位置触发
2. 动画依赖于特定的滚动进度

**解决方案**：
```bash
# 完整 ScrollTrigger 捕获
webthief clone https://gsap-site.com \
  --scroll-precision \
  --animation-analyze \
  --mouse-simulation \
  --wait 5 \
  -o ./output

# 使用本地服务器预览
webthief serve ./output
```

### Q5: 克隆过程太慢？

**优化建议**：
1. 仅启用需要的动画选项
2. 减少 `--wait` 时间
3. 使用 `--single-page` 模式

```bash
# 仅启用必要的选项
webthief clone https://site.com \
  --animation-analyze \
  --wait 3 \
  -o ./output
```

### Q6: 如何处理复杂的物理引擎动画？

**说明**：
Box2D、Matter.js 等物理引擎的复杂模拟可能无法完全捕获。

**建议**：
1. 使用 `--physics-capture` 尝试捕获
2. 增加等待时间让物理模拟稳定
3. 对于关键帧，使用 `--canvas-recording`

```bash
webthief clone https://physics-site.com \
  --physics-capture \
  --canvas-recording \
  --wait 5 \
  -o ./output
```

### Q7: 克隆后的文件太大？

**优化建议**：
1. 禁用 Canvas 录制（如果不需要）
2. 使用 `--animation-analyze` 自动移除装饰性动画
3. 清理不必要的资源文件

```bash
# 仅保留关键动画
webthief clone https://site.com \
  --animation-analyze \
  -o ./output
```

---

## 高级技巧

### 1. 自定义等待时间策略

根据网站复杂度调整等待时间：

```bash
# 简单网站
webthief clone https://simple-site.com --wait 2 -o ./output

# 中等复杂度
webthief clone https://medium-site.com --wait 5 -o ./output

# 复杂动画网站
webthief clone https://complex-site.com --wait 10 -o ./output
```

### 2. 分阶段克隆

对于特别复杂的网站，可以分阶段克隆：

```bash
# 第一阶段：基础克隆
webthief clone https://site.com -o ./output

# 第二阶段：动画优化（在基础克隆上增强）
webthief clone https://site.com \
  --mouse-simulation \
  --scroll-precision \
  --animation-analyze \
  --wait 5 \
  -o ./output
```

### 3. 调试模式

启用详细日志查看动画处理过程：

```bash
webthief clone https://site.com \
  --animation-analyze \
  --scroll-precision \
  -v \
  -o ./output
```

### 4. 选择性启用功能

根据网站特点选择功能：

```bash
# 纯 CSS 动画网站
webthief clone https://site.com --animation-analyze -o ./output

# 视差滚动网站
webthief clone https://site.com --scroll-precision --mouse-simulation -o ./output

# Canvas 应用
webthief clone https://site.com --canvas-recording --mouse-simulation -o ./output

# 全功能（展示型网站）
webthief clone https://site.com \
  --mouse-simulation \
  --scroll-precision \
  --canvas-recording \
  --physics-capture \
  --animation-analyze \
  --wait 5 \
  -o ./output
```

---

## 故障排除

### 检查清单

在提交问题前，请检查以下事项：

- [ ] 是否启用了适当的动画选项？
- [ ] 是否增加了足够的 `--wait` 时间？
- [ ] 是否使用 `webthief serve` 预览而非直接打开文件？
- [ ] 是否启用了 `-v` 查看详细日志？
- [ ] 目标网站是否需要登录或特殊权限？

### 日志分析

启用 `-v` 选项查看动画处理日志：

```bash
webthief clone https://site.com \
  --animation-analyze \
  --scroll-precision \
  -v \
  -o ./output 2>&1 | tee clone.log
```

关键日志标识：
- `[cyan]  🎬 分析 CSS 动画...[/]` - 开始 CSS 动画分析
- `[green]  ✓ 发现 X 个关键帧规则[/]` - 发现动画规则
- `[cyan]  🔍 检测视差滚动元素...[/]` - 开始视差检测
- `[green]  ✓ 检测到 X 个视差元素[/]` - 视差元素数量
- `[cyan]  🔍 检测滚动触发库...[/]` - 开始 ScrollTrigger 检测

---

## 版本兼容性

本文档适用于 WebThief v4.2.0 及以上版本。

### 功能版本历史

| 功能 | 引入版本 | 说明 |
|-----|---------|------|
| CSS 动画分析 | v4.2.0 | 基础动画检测和保留 |
| 视差滚动捕获 | v4.2.0 | 视差效果检测和转换 |
| ScrollTrigger 支持 | v4.2.0 | GSAP 滚动动画处理 |
| Canvas 录制 | v4.2.0 | Canvas 内容捕获 |
| Hover 效果检测 | v4.2.0 | 悬停效果分析 |
| 鼠标轨迹模拟 | v4.2.0 | 鼠标交互模拟 |

---

*最后更新：2026-02-26*
