# 🎨 WebThief v3.0 视觉检验指南

## 🌐 访问克隆页面

### 步骤 1: 启动本地服务器

服务器已启动！访问地址：

```
http://localhost:8000/index.html
```

或者使用 IPv6：
```
http://[::]:8000/index.html
```

---

## ✅ 视觉检验清单

### 1. 页面基础检查

#### 1.1 页面加载
- [ ] 页面能否正常打开
- [ ] 是否显示 Steam 登录界面
- [ ] 页面布局是否完整
- [ ] 是否有明显的样式缺失

#### 1.2 样式完整性
- [ ] Steam Logo 是否显示
- [ ] 背景颜色是否正确（深色主题）
- [ ] 字体是否正确加载
- [ ] 按钮样式是否正常

---

### 2. 二维码功能检查 🔐

#### 2.1 二维码显示
- [ ] 二维码图片是否显示
- [ ] 二维码位置是否正确
- [ ] 二维码大小是否合适
- [ ] 二维码周围的文字说明是否显示

#### 2.2 二维码拦截功能测试

**打开浏览器开发者工具** (F12)

1. **查看控制台日志**
   ```
   预期看到:
   [WebThief Shim] 运行时兼容层已激活
   [WebThief QR Bridge] 二维码桥接脚本已激活
   [WebThief Menu] 菜单交互已激活
   ```

2. **测试二维码刷新接口**
   
   在控制台输入：
   ```javascript
   window.__webthief_qr_refresh()
   ```
   
   预期结果：
   - [ ] 返回 `true` 或 `false`
   - [ ] 控制台显示 `[WebThief QR Bridge] 触发二维码刷新`
   - [ ] 如果找到刷新函数，显示调用的函数名

3. **检查拦截的数据**
   
   在控制台输入：
   ```javascript
   window.__webthief_qr_requests
   window.__webthief_qr_images
   window.__webthief_qr_canvas
   ```
   
   预期结果：
   - [ ] 显示拦截到的二维码请求数组
   - [ ] 显示捕获的二维码图片数组
   - [ ] 显示 Canvas 生成的二维码数组

---

### 3. React 组件拦截检查 ⚛️

#### 3.1 菜单显示
- [ ] 顶部导航栏是否显示
- [ ] 菜单项是否完整
- [ ] 下拉菜单图标是否显示

#### 3.2 菜单交互测试

1. **悬停测试**
   - [ ] 鼠标悬停在菜单上
   - [ ] 检查是否有下拉菜单展开
   - [ ] 移开鼠标，菜单是否延迟隐藏

2. **检查冻结的菜单**
   
   在控制台输入：
   ```javascript
   document.querySelectorAll('[data-webthief-frozen="true"]')
   ```
   
   预期结果：
   - [ ] 返回冻结的菜单元素列表
   - [ ] 显示元素数量

3. **检查 React 拦截**
   
   在控制台输入：
   ```javascript
   document.querySelectorAll('[data-webthief-preserved="true"]')
   ```
   
   预期结果：
   - [ ] 返回保留的 React 组件列表

---

### 4. 运行时兼容层检查 🛡️

#### 4.1 Location 伪造测试

在控制台输入：
```javascript
console.log('hostname:', window.location.hostname);
console.log('origin:', window.location.origin);
console.log('protocol:', window.location.protocol);
```

预期结果：
- [ ] `hostname` 显示 `store.steampowered.com`
- [ ] `origin` 显示 `https://store.steampowered.com`
- [ ] `protocol` 显示 `https:`

#### 4.2 Storage 安全代理测试

在控制台输入：
```javascript
localStorage.setItem('test', 'value');
console.log(localStorage.getItem('test'));
```

预期结果：
- [ ] 不抛出 SecurityError
- [ ] 成功存储和读取数据

#### 4.3 跳转拦截测试

在控制台输入：
```javascript
window.location.href = 'https://store.steampowered.com/';
```

预期结果：
- [ ] 控制台显示 `[WebThief Shim] 已拦截跳转`
- [ ] 页面不跳转

---

### 5. 资源加载检查 📦

#### 5.1 图片资源
- [ ] Steam Logo 是否显示
- [ ] 背景图片是否加载
- [ ] 图标是否显示
- [ ] 二维码图片是否清晰

#### 5.2 字体资源
- [ ] 中文字体是否正确显示
- [ ] 英文字体是否正确显示
- [ ] 字体粗细是否正常

#### 5.3 CSS 资源
- [ ] 页面布局是否正确
- [ ] 颜色是否正确
- [ ] 动画是否被冻结（应该没有动画）

#### 5.4 检查网络请求

打开开发者工具 → Network 标签页

- [ ] 查看是否有失败的请求（红色）
- [ ] 检查资源是否从本地加载（localhost:8000）
- [ ] 确认没有向原站发起请求

---

### 6. 脚本注入验证 💉

#### 6.1 查看页面源代码

右键 → 查看页面源代码

查找以下标记：

1. **运行时 Shim**
   ```html
   <script data-webthief="shim">
   ```
   - [ ] 在 `<head>` 最前面
   - [ ] 包含 `WebThief Runtime Shim v1.0`

2. **二维码桥接脚本**
   ```html
   <script data-webthief="qr-bridge">
   ```
   - [ ] 在 `<head>` 末尾
   - [ ] 包含 `WebThief QR Bridge Script`
   - [ ] 包含 `ORIGINAL_DOMAIN`

3. **菜单保留脚本**
   ```html
   <script data-webthief="menu-preservation">
   ```
   - [ ] 在 `<head>` 末尾
   - [ ] 包含 `WebThief Menu Preservation Runtime`

#### 6.2 检查 CSS 注入

查找以下 CSS 规则：

```css
[data-webthief-expanded="true"],
[data-webthief-frozen="true"] {
    display: block !important;
    visibility: visible !important;
    opacity: 1 !important;
}
```

- [ ] CSS 规则已注入
- [ ] 包含菜单保留样式

---

### 7. 功能对比测试 🔄

#### 7.1 打开原始 Steam 登录页

在新标签页打开：
```
https://store.steampowered.com/login/
```

#### 7.2 对比检查

| 项目 | 原始页面 | 克隆页面 | 状态 |
|------|---------|---------|------|
| 页面布局 | ✓ | ? | [ ] |
| 二维码显示 | ✓ | ? | [ ] |
| 颜色主题 | ✓ | ? | [ ] |
| 字体样式 | ✓ | ? | [ ] |
| Logo 显示 | ✓ | ? | [ ] |
| 按钮样式 | ✓ | ? | [ ] |
| 输入框样式 | ✓ | ? | [ ] |

---

### 8. 高级功能测试 🚀

#### 8.1 二维码刷新测试（需要原站支持）

**注意**: 由于 CORS 限制，此功能可能无法完全工作

1. 打开控制台
2. 输入：
   ```javascript
   // 查看拦截的二维码 API
   console.log(window.__webthief_qr_requests);
   
   // 尝试手动刷新
   window.__webthief_qr_refresh();
   ```

3. 观察：
   - [ ] 是否有网络请求发出
   - [ ] 是否有 CORS 错误
   - [ ] 二维码是否更新

#### 8.2 菜单交互测试

1. 悬停在顶部菜单上
2. 观察：
   - [ ] 菜单是否展开
   - [ ] 展开速度是否自然
   - [ ] 移开鼠标后是否延迟隐藏

---

### 9. 性能检查 ⚡

#### 9.1 页面加载速度

打开开发者工具 → Network 标签页 → 刷新页面

- [ ] 记录 DOMContentLoaded 时间
- [ ] 记录 Load 时间
- [ ] 检查是否有慢速资源

#### 9.2 内存占用

打开开发者工具 → Performance Monitor

- [ ] 查看 JavaScript 堆大小
- [ ] 查看 DOM 节点数量
- [ ] 检查是否有内存泄漏

---

### 10. 兼容性测试 🌍

#### 10.1 浏览器测试

在不同浏览器中打开：

- [ ] Chrome/Edge (Chromium)
- [ ] Firefox
- [ ] Safari (如果可用)

#### 10.2 协议测试

1. **HTTP 协议** (当前)
   ```
   http://localhost:8000/index.html
   ```
   - [ ] 页面正常显示
   - [ ] 功能正常工作

2. **File 协议**
   
   直接打开文件：
   ```
   file:///B:/WebThief/steam_login_clone/index.html
   ```
   
   预期：
   - [ ] 页面可以显示
   - [ ] localStorage 使用安全代理
   - [ ] 部分功能受限（CORS）

---

## 📸 截图建议

建议截取以下内容作为测试证据：

1. **完整页面截图**
   - 显示整个 Steam 登录页

2. **二维码特写**
   - 显示二维码清晰度

3. **控制台日志**
   - 显示 WebThief 的日志输出

4. **网络请求**
   - 显示资源加载情况

5. **源代码视图**
   - 显示注入的脚本标记

---

## 🐛 常见问题排查

### 问题 1: 页面显示空白

**可能原因**:
- 服务器未启动
- 端口被占用
- 浏览器缓存问题

**解决方案**:
```bash
# 重启服务器
cd steam_login_clone
python -m http.server 8000

# 清除浏览器缓存
Ctrl + Shift + Delete
```

### 问题 2: 二维码不显示

**可能原因**:
- 图片资源未下载
- 路径重写错误

**解决方案**:
- 检查 Network 标签页，查看图片请求
- 查看控制台是否有 404 错误

### 问题 3: 样式错乱

**可能原因**:
- CSS 文件未加载
- CSS 变量未固化

**解决方案**:
- 检查 `<style>` 标签是否包含 CSS 变量
- 查看 Network 标签页，确认 CSS 文件已加载

### 问题 4: 控制台没有 WebThief 日志

**可能原因**:
- 脚本未注入
- 脚本执行错误

**解决方案**:
- 查看页面源代码，确认脚本标记存在
- 检查控制台是否有 JavaScript 错误

---

## ✅ 检验完成标准

### 必须通过项 (10/10)

- [ ] 页面正常显示
- [ ] 二维码图片显示
- [ ] 控制台有 WebThief 日志
- [ ] 三个脚本标记存在
- [ ] Location 伪造工作
- [ ] Storage 安全代理工作
- [ ] 跳转拦截工作
- [ ] 资源从本地加载
- [ ] 无严重样式错误
- [ ] 无 JavaScript 错误

### 可选通过项 (5/5)

- [ ] 二维码刷新功能
- [ ] 菜单交互功能
- [ ] React 组件保留
- [ ] 性能表现良好
- [ ] 多浏览器兼容

---

## 📝 检验报告模板

```markdown
# Steam 登录页视觉检验报告

**检验时间**: YYYY-MM-DD HH:MM
**浏览器**: Chrome/Firefox/Safari
**操作系统**: Windows/macOS/Linux

## 基础检查
- 页面显示: ✅/❌
- 二维码显示: ✅/❌
- 样式完整: ✅/❌

## 功能检查
- 二维码拦截: ✅/❌
- React 拦截: ✅/❌
- 运行时 Shim: ✅/❌

## 问题记录
1. [问题描述]
2. [问题描述]

## 总体评价
[优秀/良好/一般/差]

## 建议
[改进建议]
```

---

## 🎉 开始检验

现在你可以：

1. **打开浏览器**，访问 `http://localhost:8000/index.html`
2. **按照清单逐项检查**
3. **记录检验结果**
4. **截图保存证据**

祝检验顺利！ 🚀
