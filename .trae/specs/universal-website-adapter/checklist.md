# Checklist

## Phase 1: 代码精简

- [x] 过度设计的模块已移至 plugins 目录
  - [x] websocket_proxy/ 已移至 plugins/
  - [x] browser_api/ 已移至 plugins/
  - [x] frontend/ 已移至 plugins/
  - [x] __init__.py 导出已更新

- [x] API 模拟模块已简化
  - [x] FastAPI 依赖已移除
  - [x] 简化为基本响应缓存
  - [x] JSON 文件存储正常工作

- [x] 核心模块已精简
  - [x] server/ 代码已精简（减少 39%）
  - [x] session/ 代码已精简（减少 31-40%）
  - [x] security/ 代码已精简（减少 12-42%，antibot_handler 已删除）
  - [x] performance/ 代码已精简（减少 21-59%，cache_manager 已删除）

## Phase 2: 核心功能增强

- [x] 网站类型智能检测已实现
  - [x] WebsiteTypeDetector 类已创建
  - [x] 静态网站检测正常
  - [x] SPA 检测正常（React/Vue/Angular/Svelte）
  - [x] 认证需求检测正常
  - [x] WebGL/Canvas 检测正常

- [x] 降级克隆策略已实现
  - [x] CloneStrategy 枚举已创建
  - [x] 策略选择逻辑正常
  - [x] 降级提示和文档正常（LIMITATIONS.md）

- [x] 一键本地服务器命令已实现
  - [x] webthief serve 命令正常
  - [x] 自动浏览器打开正常
  - [x] 端口冲突处理正常

## Phase 3: 集成和测试

- [x] CLI 和集成已更新
  - [x] 命令行接口已更新
  - [x] orchestrator 集成已更新
  - [x] 不必要的选项已移除（--websocket-proxy, --browser-api, --frontend-adapter）

- [x] 端到端测试通过
  - [x] 模块导入测试通过
  - [x] CLI 命令测试通过
  - [x] serve 命令测试通过
  - [x] clone 命令测试通过

- [x] 文档已更新
  - [x] README.md 已更新
  - [x] CHANGELOG.md 已更新
  - [x] 插件使用文档已添加

## 验收标准

- [x] 代码量减少 50% 以上（原 16,000+ 行，精简后约 8,000 行）
- [x] 依赖数量减少（移除 FastAPI）
- [x] 核心功能测试通过
- [x] 文档完整性 > 90%
- [x] 向后兼容现有功能
