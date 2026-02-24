# WebThief 高级功能使用指南

> 文档维护更新（2026-02-24）：已清理仓库测试脚本与测试产物目录，本文档内容已同步调整。


## 🎯 新增功能概览

WebThief v3.0 引入了两个革命性的高级功能，实现了真正的"1:1 动态还原"：

1. **实时二维码克隆** (Live QR Code Cloning)
2. **完全体交互菜单** (Full Interactive Menus with React Interception)

---

## 🔐 功能 1: 实时二维码克隆

### 功能说明

传统的网页克隆工具只能捕获静态二维码图片，无法保留二维码的刷新逻辑和与服务器的通信能力。WebThief 的二维码拦截器通过以下技术实现了"活的"二维码克隆：

#### 核心技术

1. **API 请求拦截**
   - 自动识别二维码相关的 API 端点（包含 `qrcode`, `qr_code`, `login/qr` 等关键字）
   - 拦截并记录所有二维码请求的 URL、方法和参数

2. **图片生成捕获**
   - 监听动态生成的 `<img>` 标签的 `src` 变化
   - 拦截 Canvas `toDataURL()` 调用（二维码生成库常用方法）
   - 捕获 Data URI 和 Blob URL 格式的二维码

3. **脚本生命周期保留**
   - 识别并保留二维码核心脚本（避免被净化层移除）
   - 注入桥接脚本，使克隆页面能与原站服务器通信

4. **CORS 代理层**
   - 自动处理跨域请求
   - 保留原站的认证 Cookie 和 Token

### 使用方法

```bash
# 基本用法（默认启用）
webthief https://example.com/login

# 显式启用二维码拦截
webthief https://example.com/login --enable-qr-intercept

# 禁用二维码拦截（如果不需要）
webthief https://example.com/login --no-enable-qr-intercept
```

### 适用场景

- Steam 登录页面
- 微信/QQ 扫码登录
- 支付宝/微信支付二维码
- 任何需要实时刷新的二维码页面

### 技术细节

#### 拦截的数据结构

```javascript
{
  requests: [
    {
      url: "https://api.example.com/qr/generate",
      method: "POST",
      timestamp: 1234567890
    }
  ],
  images: [
    {
      src: "data:image/png;base64,...",
      timestamp: 1234567890
    }
  ],
  canvas: [
    {
      dataUrl: "data:image/png;base64,...",
      width: 256,
      height: 256,
      timestamp: 1234567890
    }
  ]
}
```

#### 桥接脚本功能

克隆页面中注入的桥接脚本会：
1. 重写 `fetch` 和 `XMLHttpRequest`，将二维码请求代理到原站
2. 自动添加 CORS 头和认证信息
3. 提供 `window.__webthief_qr_refresh()` 函数手动触发刷新

---

## ⚛️ 功能 2: 完全体交互菜单（React 组件拦截）

### 功能说明

现代网站（尤其是使用 React/Vue 等框架的 SPA）的下拉菜单和交互元素通常在鼠标离开后会被 JavaScript 销毁。WebThief 的 React 拦截器通过劫持组件卸载机制，实现了菜单的永久保留和交互恢复。

#### 核心技术

1. **React Unmount 拦截**
   - 劫持 `ReactDOM.unmountComponentAtNode`
   - 拦截 Fiber 节点的 `commitUnmount`
   - 阻止 `Element.removeChild` 删除 React 管理的节点

2. **自动菜单触发**
   - 遍历所有可能的菜单触发器（`.dropdown`, `.nav-item`, `[role="menu"]` 等）
   - 模拟鼠标事件（`mouseenter`, `mouseover`, `click` 等）
   - 等待异步内容加载完成

3. **状态冻结**
   - 强制所有展开的菜单保持可见（`display: block !important`）
   - 防止 JavaScript 再次隐藏菜单
   - 添加 `data-webthief-frozen` 标记

4. **JS 到 CSS 转换**
   - 将 JavaScript 驱动的显隐逻辑转换为纯 CSS `:hover` 规则
   - 注入菜单保留运行时脚本到克隆页面
   - 恢复悬停交互能力

### 使用方法

```bash
# 基本用法（默认启用）
webthief https://example.com

# 显式启用 React 拦截
webthief https://example.com --enable-react-intercept

# 禁用 React 拦截（如果不需要）
webthief https://example.com --no-enable-react-intercept

# 同时启用两个高级功能
webthief https://example.com --enable-qr-intercept --enable-react-intercept
```

### 适用场景

- Steam 商店的分类菜单（Mega Menu）
- 电商网站的多级导航
- SaaS 应用的下拉菜单
- 任何使用 React/Vue 构建的动态菜单

### 技术细节

#### 拦截的组件类型

- Bootstrap Dropdown
- Material-UI Menu
- Ant Design Dropdown
- 自定义 React 组件

#### 生成的 CSS 规则

```css
/* 强制显示触发过的菜单 */
[data-webthief-expanded="true"],
[data-webthief-frozen="true"] {
    display: block !important;
    visibility: visible !important;
    opacity: 1 !important;
}

/* 悬停时显示子菜单 */
.dropdown:hover > .dropdown-menu,
.nav-item:hover > .submenu {
    display: block !important;
}
```

#### 运行时脚本功能

克隆页面中注入的运行时脚本会：
1. 为所有菜单触发器添加悬停事件监听
2. 实现延迟隐藏（给用户时间移动到子菜单）
3. 恢复原生的菜单交互体验

---

## 🚀 组合使用示例

### 示例 1: 克隆 Steam 登录页（二维码 + 菜单）

```bash
webthief https://store.steampowered.com/login/ \
  --enable-qr-intercept \
  --enable-react-intercept \
  --wait 5 \
  -o ./steam_clone \
  -v
```

### 示例 2: 克隆电商网站（仅菜单）

```bash
webthief https://www.amazon.com \
  --enable-react-intercept \
  --no-enable-qr-intercept \
  -o ./amazon_clone
```

### 示例 3: 克隆扫码支付页（仅二维码）

```bash
webthief https://pay.example.com/qrcode \
  --enable-qr-intercept \
  --no-enable-react-intercept \
  --keep-js \
  -o ./payment_clone
```

---

## 🔧 高级配置

### 在代码中使用

```python
from webthief.orchestrator import Orchestrator
import asyncio

async def clone_with_advanced_features():
    orchestrator = Orchestrator(
        url="https://example.com",
        output_dir="./output",
        enable_qr_intercept=True,      # 启用二维码拦截
        enable_react_intercept=True,   # 启用 React 拦截
        keep_js=True,                  # 保留 JS 执行能力
        verbose=True
    )
    
    await orchestrator.run()

asyncio.run(clone_with_advanced_features())
```

### 自定义二维码检测关键字

编辑 `webthief/qr_interceptor.py`：

```python
# 在 inject_qr_proxy 方法中修改
const QR_KEYWORDS = [
    'qrcode', 'qr_code', 'login/qr', 'auth/qr',
    'getqr', 'qrlogin', 'qrscan', 'qrcheck',
    'steamqr', 'wechatqr', 'qqlogin',
    'your_custom_keyword'  # 添加自定义关键字
];
```

### 自定义菜单选择器

编辑 `webthief/react_interceptor.py`：

```python
# 在 trigger_all_menus 方法中修改
const menuSelectors = [
    '.dropdown', '.dropdown-toggle', '.dropdown-menu',
    '.your-custom-menu-class',  # 添加自定义选择器
    // ...
];
```

---

## 📊 性能影响

### 二维码拦截
- **额外时间**: +0.5-1 秒（注入脚本和数据捕获）
- **内存占用**: +5-10 MB（存储拦截数据）
- **网络请求**: 无额外请求

### React 拦截
- **额外时间**: +2-5 秒（触发所有菜单）
- **内存占用**: +10-20 MB（保留组件状态）
- **DOM 大小**: +10-30%（保留的菜单元素）

---

## ⚠️ 注意事项

### 二维码拦截

1. **CORS 限制**: 某些网站可能有严格的 CORS 策略，导致克隆页面无法与原站通信
2. **认证失效**: 如果原站的认证 Token 过期，二维码刷新可能失败
3. **协议限制**: `file://` 协议下无法发起 HTTPS 请求，建议使用本地服务器

### React 拦截

1. **布局问题**: 保留的菜单可能导致页面布局变化（通过 CSS 调整）
2. **性能影响**: 大量保留的组件会增加 DOM 大小和渲染时间
3. **框架兼容性**: 目前主要针对 React，Vue/Angular 支持有限

---

## 🐛 故障排除

### 二维码未被拦截

1. 检查是否启用了 `--enable-qr-intercept`
2. 查看详细日志：`-v` 选项
3. 确认二维码 API 包含关键字（或添加自定义关键字）

### 菜单未被保留

1. 确认启用了 `--enable-react-intercept`
2. 增加等待时间：`--wait 10`
3. 检查菜单选择器是否匹配（添加自定义选择器）

### 克隆页面二维码无法刷新

1. 使用本地服务器而非 `file://` 协议
2. 检查浏览器控制台的 CORS 错误
3. 确认原站 API 未更改

---

## 📚 相关文档

- [ROADMAP.md](./ROADMAP.md) - 功能路线图
- [AI_CONTEXT.md](./AI_CONTEXT.md) - 技术架构说明
- [README.md](./README.md) - 基本使用指南

---

## 🎉 成功案例

### Steam 登录页克隆

- ✅ 二维码实时刷新
- ✅ 分类菜单完整保留
- ✅ 悬停交互正常工作

### 电商网站克隆

- ✅ 多级导航菜单保留
- ✅ Mega Menu 完整展示
- ✅ 产品分类可交互

---

**注意**: 这些高级功能仅供学习研究使用，请遵守目标网站的服务条款和 robots.txt。

