# WebThief 高级功能快速开始

> 文档维护更新（2026-02-24）：已清理仓库测试脚本与测试产物目录，本文档内容已同步调整。


## 🎯 5 分钟上手指南

### 前提条件

确保已安装 WebThief：

```bash
cd WebThief
pip install -e .
playwright install chromium
```

---

## 场景 1: 克隆带二维码的登录页

### 目标
克隆一个带实时刷新二维码的登录页面（如 Steam、微信扫码登录）

### 命令

```bash
webthief https://store.steampowered.com/login/ \
  --enable-qr-intercept \
  --wait 5 \
  -o ./steam_login_clone \
  -v
```

### 预期结果

1. 浏览器自动打开并加载页面
2. 控制台显示：
   ```
   🔐 注入二维码代理层...
   📸 捕获二维码生命周期...
   ✓ 捕获 X 个二维码 API 请求
   ✓ 捕获 X 个二维码图片
   ```
3. 生成的 `index.html` 中包含：
   - 二维码图片
   - 桥接脚本（用于与原站通信）
   - 刷新逻辑

### 验证

打开 `./steam_login_clone/index.html`：
- 二维码应该显示
- 打开浏览器控制台，输入 `window.__webthief_qr_refresh()` 可手动刷新
- （注意：由于 CORS 限制，可能需要本地服务器）

---

## 场景 2: 克隆带复杂菜单的网站

### 目标
克隆一个使用 React 构建的网站，保留所有下拉菜单和交互

### 命令

```bash
webthief https://store.steampowered.com/ \
  --enable-react-intercept \
  --wait 5 \
  -o ./steam_store_clone \
  -v
```

### 预期结果

1. 控制台显示：
   ```
   ⚛️  注入 React 组件拦截补丁...
   🖱️  触发所有交互菜单...
   ✓ 触发了 X 个交互元素
   ❄️  冻结菜单状态...
   ✓ 冻结了 X 个菜单
   🎨 转换交互逻辑为 CSS...
   ```
2. 生成的 HTML 包含：
   - 所有展开过的菜单（即使原本会被销毁）
   - 菜单保留 CSS 规则
   - 运行时交互脚本

### 验证

打开 `./steam_store_clone/index.html`：
- 悬停在导航栏上，菜单应该展开
- 所有子菜单都应该可以访问
- 布局应该保持完整

---

## 场景 3: 同时启用两个功能

### 目标
克隆一个既有二维码又有复杂菜单的页面

### 命令

```bash
webthief https://store.steampowered.com/login/ \
  --enable-qr-intercept \
  --enable-react-intercept \
  --wait 5 \
  -o ./steam_full_clone \
  -v
```

### 预期结果

同时看到二维码拦截和 React 拦截的日志输出

---

## 🔧 常见问题

### Q1: 二维码不刷新怎么办？

**原因**: CORS 限制或 `file://` 协议限制

**解决方案**: 使用本地服务器

```bash
# 进入输出目录
cd ./steam_login_clone

# 启动简单的 HTTP 服务器
python -m http.server 8000

# 浏览器访问
# http://localhost:8000/index.html
```

### Q2: 菜单没有被保留？

**原因**: 菜单选择器不匹配或等待时间不够

**解决方案**:
1. 增加等待时间：`--wait 10`
2. 查看详细日志：`-v`
3. 自定义菜单选择器（编辑 `react_interceptor.py`）

### Q3: 页面布局错乱？

**原因**: 保留的菜单影响了布局

**解决方案**: 手动调整生成的 CSS
1. 打开 `index.html`
2. 找到 `[data-webthief-frozen="true"]` 的 CSS 规则
3. 调整 `position`, `z-index` 等属性

### Q4: 性能太慢？

**原因**: 高级功能需要额外的处理时间

**解决方案**:
1. 禁用不需要的功能：
   ```bash
   # 只启用二维码拦截
   webthief URL --enable-qr-intercept --no-enable-react-intercept
   
   # 只启用 React 拦截
   webthief URL --enable-react-intercept --no-enable-qr-intercept
   ```
2. 减少并发数：`-c 10`

---

## 📊 性能对比

| 模式 | 时间 | 内存 | DOM 大小 |
|------|------|------|----------|
| 基础模式 | 10s | 100MB | 100% |
| + 二维码拦截 | 11s | 110MB | 100% |
| + React 拦截 | 15s | 120MB | 130% |
| 全功能 | 16s | 130MB | 130% |

---

## 🎓 进阶使用

### 在 Python 代码中使用

```python
from webthief.orchestrator import Orchestrator
from webthief.qr_interceptor import QRInterceptor
from webthief.react_interceptor import ReactInterceptor
import asyncio

async def advanced_clone():
    # 创建编排器
    orchestrator = Orchestrator(
        url="https://example.com",
        output_dir="./output",
        enable_qr_intercept=True,
        enable_react_intercept=True,
        verbose=True
    )
    
    # 运行克隆
    result_path = await orchestrator.run()
    print(f"克隆完成: {result_path}")

# 运行
asyncio.run(advanced_clone())
```

### 自定义二维码关键字

编辑 `webthief/qr_interceptor.py`，在 `inject_qr_proxy` 方法中：

```javascript
const QR_KEYWORDS = [
    'qrcode', 'qr_code', 'login/qr',
    'my_custom_qr_api',  // 添加你的关键字
];
```

### 自定义菜单选择器

编辑 `webthief/react_interceptor.py`，在 `trigger_all_menus` 方法中：

```javascript
const menuSelectors = [
    '.dropdown', '.nav-item',
    '.my-custom-menu',  // 添加你的选择器
];
```

---

## 📚 下一步

- 阅读 [ADVANCED_FEATURES.md](./ADVANCED_FEATURES.md) 了解详细技术细节
- 使用 `webthief URL -v` 直接验证高级功能日志输出
- 参考 [ROADMAP.md](./ROADMAP.md) 了解未来计划

---

## 💡 提示

1. **首次使用建议**: 先用 `-v` 选项查看详细日志，了解每个步骤
2. **测试建议**: 先在简单页面上测试，再尝试复杂网站
3. **调试建议**: 使用浏览器开发者工具查看注入的脚本和 CSS
4. **性能建议**: 如果不需要某个功能，记得禁用它

---

**祝你克隆愉快！** 🎉


