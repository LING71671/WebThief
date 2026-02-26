# WebThief 版本日志 (CHANGELOG)

> 文档维护更新（2026-02-26）：v4.2.0 动画优化版发布。

## v4.2.0 (2026-02-26) - 动画优化版 (Animation Optimization)

这是一个专注于动画处理的重大版本，新增 6 大动画捕获和优化模块，将 WebThief 的克隆能力提升到新的高度。

### 🚀 新增功能

#### 🎬 CSS 动画分析与保留 (CSS Animation Analyzer)
- **智能动画检测**：
    - 自动识别 6 种动画类型：入场动画、悬停动画、滚动动画、循环动画、退出动画、过渡动画
    - 通过关键字匹配和属性分析识别动画类型
    - 支持 `@keyframes` 规则提取和解析
- **重要性评分系统**：
    - 基于动画类型、持续时间、关键属性计算重要性分数（0-100）
    - 入场动画和悬停动画获得更高权重
    - 循环装饰性动画自动降低权重
- **选择性保留策略**：
    - 智能保留关键动画（分数 >= 40）
    - 自动移除装饰性动画减少页面负担
    - 生成保留动画的静态 CSS 样式
- **冻结点计算**：
    - 计算最优动画冻结点（0-100%）
    - 入场动画冻结在结束状态（100%）
    - 悬停动画冻结在默认状态（0%）
    - 循环动画冻结在视觉平衡点（50%）

#### 🌊 视差滚动效果捕获 (Parallax Handler)
- **多属性支持**：
    - 支持 `data-speed`、`data-parallax`、`data-parallax-speed` 属性
    - 支持 `data-parallax-x`、`data-parallax-y`、`data-parallax-direction` 属性
    - 支持通过 CSS 类名检测（`.parallax`、`.parallax-bg` 等）
- **视差库检测**：
    - 自动检测 rellax、skrollr、simpleParallax、parallax.js 等库
    - 识别库版本和配置
- **位置计算引擎**：
    - 精确计算不同滚动位置的视差层偏移
    - 支持垂直、水平、双向视差
    - 处理正负速度值（反向视差）
- **静态转换**：
    - 将视差效果转换为 CSS `@keyframes` 动画
    - 使用 `animation-timeline: scroll()` 实现滚动驱动
    - 提供降级方案（`position: sticky`）

#### 📜 GSAP ScrollTrigger 支持 (ScrollTrigger Handler)
- **滚动动画库检测**：
    - 检测 GSAP ScrollTrigger（含版本识别）
    - 检测 ScrollMagic、ScrollReveal、AOS
    - 检测 Locomotive Scroll、Lenis、Skrollr
- **配置解析**：
    - 提取 `scrub`、`pin`、`trigger`、`start`、`end` 等配置
    - 解析动画持续时间、缓动函数、变换属性
    - 支持批量动画配置提取
- **状态捕获系统**：
    - 在多个滚动位置（0%、25%、50%、75%、100%）采样动画状态
    - 记录元素的 `transform`、`opacity`、`filter` 等计算样式
    - 捕获 ScrollTrigger 进度信息
- **桥接脚本生成**：
    - 生成 ScrollTrigger API 兼容层
    - 使用 IntersectionObserver 实现滚动触发动画
    - 提供 `WebThiefScrollBridge` 全局对象

#### 🎨 Canvas 应用克隆 (Canvas Recorder)
- **Canvas 检测**：
    - 自动检测页面中的所有 Canvas 元素
    - 识别 2D 和 WebGL 上下文
    - 获取 Canvas 尺寸和绘制状态
- **内容捕获**：
    - 使用 Playwright 截图 API 捕获 Canvas 内容
    - 支持捕获单个或多个 Canvas 元素
    - 将截图转换为 Base64 或文件保存
- **动态录制**：
    - 支持录制 Canvas 动画序列
    - 可配置录制帧率和持续时间
    - 生成视频或帧序列
- **静态替换**：
    - 将动态 Canvas 替换为静态图像
    - 保留原始 Canvas 尺寸和位置
    - 添加数据属性标记

#### 🖱️ Hover 效果检测 (Hover Analyzer)
- **伪类分析**：
    - 检测 `:hover`、`:focus`、`:active` 伪类触发的样式变化
    - 分析 CSS 规则中的样式差异
    - 支持复杂选择器嵌套
- **视觉重要性评估**：
    - 基于属性类型计算权重（transform > opacity > color）
    - 根据变化幅度计算分数（0-1）
    - 识别动画过渡效果
- **静态转换**：
    - 将 hover 效果转换为静态 CSS 类
    - 生成 `.webthief-hover-*` 替代类
    - 保留原始过渡效果
- **批量处理**：
    - 支持批量应用高重要性 hover 效果
    - 可配置重要性阈值
    - 生成 hover 效果分析报告

#### 🖲️ 鼠标轨迹模拟 (Mouse Simulator)
- **智能遍历算法**：
    - 模拟自然鼠标移动轨迹（贝塞尔曲线）
    - 分段式视口遍历策略
    - 随机偏移避免机械模式
- **悬停触发**：
    - 自动触发元素的 `mouseenter`、`mouseover` 事件
    - 支持嵌套悬停元素
    - 等待异步内容加载
- **交互激活**：
    - 激活鼠标跟随动画
    - 触发 CSS `:hover` 伪类
    - 支持自定义鼠标路径

### 🔧 架构改进

#### 新增拦截器模块
- `interceptors/animation_analyzer.py` - CSS 动画分析器
- `interceptors/parallax_handler.py` - 视差滚动处理器
- `interceptors/scroll_trigger_handler.py` - ScrollTrigger 处理器
- `interceptors/hover_analyzer.py` - Hover 效果分析器
- `interceptors/canvas_recorder.py` - Canvas 录制器
- `interceptors/mouse_simulator.py` - 鼠标模拟器
- `interceptors/animation_sync.py` - 动画同步器
- `interceptors/pointer_interceptor.py` - 指针拦截器
- `interceptors/webgl_capture.py` - WebGL 捕获器
- `interceptors/particle_handler.py` - 粒子效果处理器
- `interceptors/physics_capture.py` - 物理引擎捕获器
- `interceptors/nested_hover_handler.py` - 嵌套悬停处理器

#### CLI 增强
- 新增 5 个动画相关命令行选项：
    - `--mouse-simulation`：启用鼠标轨迹模拟
    - `--scroll-precision`：启用高精度滚动
    - `--canvas-recording`：启用 Canvas 录制
    - `--physics-capture`：启用物理引擎捕获
    - `--animation-analyze`：启用 CSS 动画分析

#### Orchestrator 集成
- 模块化动画处理流程
- 可选动画功能开关
- 统一的动画报告生成

### 📚 文档更新
- `README.md`：添加动画优化功能完整说明
- `CHANGELOG.md`：记录 v4.2.0 版本变更详情
- `docs/animation_best_practices.md`：新增动画处理最佳实践指南
- `tests/test_animation_features.py`：新增动画功能端到端测试

### 🎯 适用场景
- **展示型网站克隆**：完整保留入场动画、滚动动画效果
- **视差滚动网站**：精确捕获视差层位置和滚动响应
- **GSAP 动画网站**：保留 ScrollTrigger 驱动的复杂动画
- **Canvas 应用**：捕获游戏、数据可视化、艺术创作
- **交互式菜单**：保留悬停效果和下拉动画
- **鼠标跟随效果**：激活并捕获鼠标交互动画

### ⚠️ 已知限制
- **复杂物理引擎**：Box2D、Matter.js 等复杂物理模拟可能无法完全捕获
- **WebGL 高级特性**：某些高级 WebGL 着色器效果可能无法截图
- **实时动画同步**：需要预先录制，不支持实时双向同步
- **性能影响**：启用所有动画功能会增加 3-8 秒处理时间

---

## v4.1.0 (2026-02-26) - 精简优化版 (Streamlined Optimization)

这是一个架构优化版本，移除了过度设计的功能，精简了模块结构，提升了代码可维护性。

### 🚀 新增功能

#### 🖥️ 独立服务器命令 (Standalone Server Command)
- **新增 `webthief serve` 命令**：
    - 独立启动本地 HTTP 服务器预览克隆结果
    - 支持自定义端口 (`--port`) 和主机地址 (`--host`)
    - 内置 CORS 配置支持，方便前端开发调试
    - 可选自动打开浏览器 (`--no-browser` 禁用)
    - 使用示例：
        ```bash
        webthief serve ./output --port 8080
        webthief serve ./output --host 0.0.0.0 --no-cors
        ```

#### 📦 CLI 架构重构 (CLI Architecture Refactoring)
- **多命令架构**：
    - 使用 `click.group` 实现子命令模式
    - `clone` 和 `serve` 作为独立子命令
    - 更清晰的命令分组和帮助信息
- **命令变更**：
    - 原 `webthief URL` 改为 `webthief clone URL`
    - 原 `webthief --local-server` 改为独立的 `webthief serve` 命令

### 🔧 精简模块

#### 移除过度设计功能
- **API 模拟系统简化**：
    - 移除复杂的请求匹配引擎（精确匹配、模糊匹配、参数化匹配）
    - 移除延迟与错误模拟功能
    - 保留基础的 API 响应缓存 (`--api-simulation`)
- **会话管理简化**：
    - 移除多会话支持、标签分类系统
    - 保留核心的 Cookie/LocalStorage 管理
    - 保留 Playwright 集成的会话导入导出

#### 插件系统优化
- **模块重组**：
    - WebSocket 代理移至 `plugins/websocket/`
    - 浏览器 API 模拟移至 `plugins/browser_api/`
    - 前端架构适配移至 `plugins/frontend/`
- **按需加载**：
    - 插件默认禁用，通过 CLI 选项显式启用
    - 减少核心模块的依赖复杂度
    - 可用插件选项：
        - `--api-simulation`: API 响应缓存
        - `--websocket-proxy`: WebSocket 消息记录
        - `--security-handler`: 指纹轮换、反爬虫绕过
        - `--frontend-adapter`: 微前端、SSR 检测
        - `--browser-api`: Service Worker、IndexedDB 模拟
        - `--performance-optimizer`: 动态并发、内存管理

### 📚 文档更新
- **README.md**：
    - 精简功能列表，突出核心能力
    - 添加 `webthief serve` 命令完整说明
    - 添加插件使用说明和示例
    - 更新 CLI 选项表格
- **CHANGELOG.md**：记录 v4.1.0 版本变更详情

### 🎯 适用场景
- **本地预览**：快速启动服务器预览克隆结果
- **开发调试**：CORS 支持方便前端开发
- **插件扩展**：按需启用高级功能

### ⚠️ 变更说明
- **命令变更**：原 `webthief URL` 改为 `webthief clone URL`
- **向后兼容**：旧命令仍可使用，但建议迁移到新格式
- **插件默认禁用**：高级插件需显式启用

---

## v4.0.0 (2026-02-26) - 企业级功能增强版 (Enterprise Feature Enhancement)

这是一个重大版本更新，新增 8 大核心模块，将 WebThief 从网站克隆工具升级为完整的离线运行环境平台。

### 🚀 核心新功能

#### 🖥️ 本地服务器增强 (Local Server Enhancement)
- **HTTP/HTTPS 双协议支持**：
    - 支持 HTTP 和 HTTPS 协议切换
    - 自签名 SSL 证书自动生成（基于 cryptography 库）
    - 浏览器安全警告提示
- **WebSocket 原生支持**：
    - 完整的 WebSocket 协议实现
    - 连接建立、消息收发、心跳检测
    - 支持文本和二进制消息
- **智能端口管理**：
    - 自动检测端口可用性
    - 冲突时自动切换到可用端口
    - 可配置最大尝试次数
- **开发者友好**：
    - 浏览器自动打开
    - CORS 配置支持
    - 自定义响应头注入
    - 请求日志记录

#### 🔄 API 模拟系统 (API Simulation System)
- **FastAPI 集成**：
    - 完整的 REST API 模拟服务器
    - 自动 CORS 中间件
    - 健康检查和统计端点
- **请求匹配引擎**：
    - 精确匹配：URL 完全匹配
    - 模糊匹配：支持通配符和正则表达式
    - 参数化匹配：`/api/users/{userId}` 风格路由
- **响应缓存**：
    - 内存 + 磁盘二级缓存
    - TTL 过期机制
    - 从 Renderer 自动导入响应
- **延迟与错误模拟**：
    - 可配置响应延迟
    - 随机延迟抖动
    - 错误率模拟
    - 自定义错误场景

#### 🔌 WebSocket 代理 (WebSocket Proxy)
- **消息记录器**：
    - 完整记录双向消息
    - 支持文本和二进制消息
    - 自动保存到文件
    - 消息搜索和过滤
- **消息回放器**：
    - 多种回放模式（实时/加速/单步）
    - 可配置回放间隔
    - 支持暂停/恢复
- **连接管理器**：
    - 连接状态监控
    - 自动清理断开连接
    - 连接统计信息
- **代理模式**：
    - 被动模式：仅记录，不干预
    - 主动模式：可修改消息
    - 阻断模式：阻止连接
    - 回放模式：回放录制消息

#### 📦 会话管理增强 (Enhanced Session Management)
- **统一存储管理**：
    - Cookie 独立存储
    - LocalStorage 管理
    - SessionStorage 管理
- **多会话支持**：
    - 会话创建、切换、删除
    - 会话元数据管理
    - 标签分类系统
- **过期管理**：
    - 自动过期检测
    - 过期会话清理
    - 有效期延长
- **导入/导出**：
    - JSON 格式导出
    - 跨设备迁移支持
    - 批量导入导出
- **Playwright 集成**：
    - 从上下文保存会话
    - 加载会话到上下文
    - 自动匹配 origin 应用

#### 🌐 浏览器 API 模拟 (Browser API Simulation)
- **Service Worker 模拟**：
    - 拦截 Service Worker 注册
    - 模拟 install/activate 事件
    - 缓存 API 模拟
- **IndexedDB 模拟**：
    - 完整的 IndexedDB API 模拟
    - 数据持久化到文件系统
    - 事务支持
- **Web Crypto API 模拟**：
    - SubtleCrypto 接口模拟
    - 常用加密算法支持
- **其他 API 模拟**：
    - Geolocation API（可配置位置）
    - Notification API（权限模拟）
    - API 调用记录和回放

#### 🔒 安全处理优化 (Security Handling)
- **CSP 分析器**：
    - 解析 Content-Security-Policy 头
    - 识别限制性指令
    - 提供绕过建议
- **浏览器指纹生成**：
    - 生成真实浏览器指纹
    - User-Agent 轮换
    - 设备特征模拟
- **反爬虫处理**：
    - 检测常见反爬虫技术
    - 人类行为模拟（鼠标移动、滚动）
    - 随机延迟和噪声
- **请求头管理**：
    - 真实浏览器请求头
    - Sec-CH-UA 系列头
    - 自动 Referer/Origin

#### 🏗️ 前端架构适配 (Frontend Architecture Adapter)
- **微前端检测**：
    - qiankun 框架检测
    - single-spa 框架检测
    - Module Federation 检测
    - iframe 微前端检测
- **Server Components 支持**：
    - Next.js App Router 检测
    - Remix 框架检测
    - React Server Components 检测
    - Flight 数据流处理
- **依赖解析**：
    - 构建依赖图
    - 关键路径分析
    - 加载优化建议
- **智能渲染策略**：
    - 根据架构自动调整参数
    - SSR Hydration 等待
    - 微前端子应用等待

#### ⚡ 性能优化 (Performance Optimization)
- **动态并发控制**：
    - 根据响应时间自动调整
    - 内存压力感知
    - 自适应并发算法
- **内存管理**：
    - 实时内存监控
    - 内存压力检测
    - 自动垃圾回收触发
- **多级缓存**：
    - 内存缓存（LRU 策略）
    - 磁盘缓存
    - 缓存命中率统计
- **资源去重**：
    - SHA256 内容哈希
    - 重复资源检测
    - 存储空间优化
- **性能报告**：
    - 详细的性能指标
    - 下载速度统计
    - 资源使用报告

### 🔧 架构改进
- **新增模块目录**：
    - `server/` - 本地服务器管理
    - `api_simulator/` - API 模拟系统
    - `websocket_proxy/` - WebSocket 代理
    - `session/` - 会话管理
    - `browser_api/` - 浏览器 API 模拟
    - `security/` - 安全处理
    - `frontend/` - 前端架构适配
    - `performance/` - 性能优化
- **CLI 增强**：
    - 新增 8 个命令行选项
    - 参数分组显示
    - 更清晰的帮助信息
- **Orchestrator 重构**：
    - 模块化集成
    - 可选功能开关
    - 统一的生命周期管理

### 📚 文档更新
- `README.md`：完整的功能列表和参数说明
- `CHANGELOG.md`：详细的版本变更记录

### 🎯 适用场景
- **离线演示**：完整的离线运行环境
- **API 测试**：模拟后端 API 响应
- **安全研究**：反爬虫绕过测试
- **性能分析**：网站性能瓶颈分析
- **微前端克隆**：复杂架构网站克隆

### ⚠️ 已知限制
- **HTTPS 证书**：自签名证书会触发浏览器警告
- **WebSocket 回放**：需要预先录制消息
- **Service Worker**：部分复杂 SW 逻辑可能无法完全模拟

---

## v3.2.0 (2026-02-26) - 技术栈分析与 SPA 预渲染版 (Tech Stack Analysis & SPA Prerendering)

### 🚀 核心新功能

#### 🔍 技术栈分析 (Tech Stack Analysis)
- **自动技术检测**：
    - 支持 50+ 技术指纹检测（前端框架、UI 库、动画库、CMS、CDN 等）
    - 检测 Angular、React、Vue.js、Bootstrap、GSAP、Three.js 等主流技术
    - 三种检测方式：URL 模式匹配、HTTP 响应头分析、DOM 结构检测
- **智能渲染策略**：
    - 根据检测到的技术栈自动调整渲染参数
    - SPA 框架 → 启用路由预渲染
    - SSR 框架 → 增加 hydration 等待时间
    - 动画库 → 启用滚动触发动画
- **CLI 可视化输出**：
    - 美观的表格展示检测到的技术栈
    - 显示置信度和检测证据
    - 提供渲染策略建议

#### 🔄 SPA 路由预渲染 (SPA Route Prerendering)
- **框架支持**：
    - Angular：自动提取路由配置，预渲染所有路由状态
    - React Router：支持 React/Vue Router 路由预渲染
    - Vue Router：通用方案支持其他 SPA 框架
- **目录结构优化**：
    - 路由页面保存到 `pages/` 子目录
    - 保持原始 URL 结构：`/home` → `pages/home/index.html`
    - 多级路由支持：`/product/pricing` → `pages/product/pricing/index.html`
- **资源路径修复**：
    - 自动修复子目录中 HTML 的资源引用路径
    - 确保所有路由页面资源加载正确

#### 📦 动态导入提取 (Dynamic Import Extraction)
- **JS 懒加载模块发现**：
    - 提取 `import()` 动态导入的 JS 模块
    - 支持 Vue.js、React 懒加载组件
    - 自动下载并替换为本地路径

### 🔧 架构改进
- **新增模块**：
    - `tech_analyzer.py` - 技术栈分析器
    - `spa_prerender.py` - SPA 路由预渲染器
- **渲染器增强**：
    - 集成技术栈分析到渲染流程
    - 支持 SPA 预渲染选项（`enable_spa_prerender`）
    - 扩展 `RenderResult` 包含路由 HTML 集合
- **下载器增强**：
    - 支持 JS 动态导入模块提取
    - 新增 `JS_DYNAMIC_IMPORT_RE` 正则表达式

### 📚 文档更新
- `README.md`：添加技术栈分析和 SPA 预渲染特性说明
- `CHANGELOG.md`：记录 v3.2.0 版本变更

### 🎯 适用场景
- **SPA 克隆**：Angular、React、Vue 单页应用的完整克隆
- **技术栈识别**：快速了解网站使用的技术栈
- **离线文档**：将文档型 SPA 转换为静态多页站点

### ⚠️ 已知限制
- **WebGL/Canvas**：file:// 协议下部分 WebGL 功能受限，建议使用本地 HTTP 服务器
- **动态路由**：某些动态生成的路由可能无法预渲染

---

## v3.1.0 (2026-02-26) - 运行时重放与自适应交互版 (Runtime Replay & Adaptive Interaction)

这是一个重大性能与兼容性升级版本，将 WebThief 从静态镜像工具提升为"运行时环境重放"引擎。

### 🚀 核心新功能

#### 🔄 运行时兼容层 v1.0 (Runtime Shim v1.0)
- **网络响应镜像化 (Network Response Mirroring)**：
    - 自动拦截并缓存所有动态 API 调用（XHR/fetch）的 body 与 Content-Type。
    - 将响应映射注入页面 `window.__WEBTHIEF_RESPONSE_MAP__`。
    - 运行时 Shim 接管网络请求，实现真正的全动态站点离线运行（如 Next.js/Nuxt 水合）。
- **Proxy 代理级位置欺骗 (Location Spoofing)**：
    - 使用 JavaScript `Proxy` 深度伪装 `window.location`。
    - 使脚本在 `file://` 或 `localhost` 下仍能看到原始域名的 `hostname` 与 `origin`。
    - 绕过环境检测逻辑，防止克隆页因域名不匹配导致的报错或重定向。
- **资源 Content-Type 还原**：
    - 在镜像文件夹中不仅存储文件，还记录原始 MIME 类型，确保重放时浏览器以正确方式解析。

#### 🧠 自适应交互引擎 (Adaptive Interaction Engine)
- **视口激活预热 (Viewport Activation Preload)**：
    - 弃用传统的匀速滚动，采用分段式视口激活。
    - 自动分段触发 `scroll`、`resize`、`wheel` 事件，完美激活 `IntersectionObserver` 驱动的动效与懒加载。
- **DOM 稳定监测 (DOM Settle Monitoring)**：
    - 集成 `MutationObserver` 机制。
    - 智能等待异步渲染和数据注入完成，直至 DOM 进入"寂静期"后再获取快照，大幅减少克隆页面的空白块和布局截断。
- **技术栈自适应评分 (Adaptive Scoring)**：
    - 自动探测 React/Next.js/Vue/Nuxt 等现代框架。
    - 根据站点复杂度自动决定"激进预热"策略，在效率与高保真之间取得最佳平衡。

### 🔧 架构与组件增强
- **CSS 解析升级**：集成 `tinycss2` 进行更稳健的 CSS AST 解析，大幅提升复杂样式表中的资源提取成功率。
- **JS 深度发现**：增强 `parse_external_js_assets`，能够发现硬编码在混淆 JS 文件中的图片与字体资源。
- **下载器健壮性**：优化了 `_sync_resource_map_with_download_results`，更好地处理并发下载中的边缘失败情况。

### 📚 文档更新
- `README.md`：同步更新"高保真重放引擎"架构图与核心特性。
- `ADVANCED_FEATURES.md`：详细记录"视口激活"与"运行时镜像"的技术实现细节及验证清单。

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

这是 WebThief 的重大升级版本，旨在解决现代网页克隆中常见的"视觉破碎"和"动态内容丢失"问题。

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
