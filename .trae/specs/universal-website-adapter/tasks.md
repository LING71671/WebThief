# Tasks

## Phase 1: 代码精简

- [x] Task 1: 移除过度设计的模块
  - [x] SubTask 1.1: 将 `websocket_proxy/` 移至 `plugins/` 目录
  - [x] SubTask 1.2: 将 `browser_api/` 移至 `plugins/` 目录
  - [x] SubTask 1.3: 将 `frontend/` 移至 `plugins/` 目录
  - [x] SubTask 1.4: 更新 `__init__.py` 导出

- [x] Task 2: 简化 API 模拟模块
  - [x] SubTask 2.1: 移除 FastAPI 依赖
  - [x] SubTask 2.2: 简化为基本响应缓存
  - [x] SubTask 2.3: 保留 JSON 文件存储

- [x] Task 3: 精简核心模块
  - [x] SubTask 3.1: 精简 `server/` 代码
  - [x] SubTask 3.2: 精简 `session/` 代码
  - [x] SubTask 3.3: 精简 `security/` 代码
  - [x] SubTask 3.4: 精简 `performance/` 代码

## Phase 2: 核心功能增强

- [x] Task 4: 实现网站类型智能检测
  - [x] SubTask 4.1: 创建 `WebsiteTypeDetector` 类
  - [x] SubTask 4.2: 实现静态网站检测
  - [x] SubTask 4.3: 实现 SPA 检测
  - [x] SubTask 4.4: 实现认证需求检测
  - [x] SubTask 4.5: 实现 WebGL/Canvas 检测

- [x] Task 5: 实现降级克隆策略
  - [x] SubTask 5.1: 创建 `CloneStrategy` 枚举
  - [x] SubTask 5.2: 实现策略选择逻辑
  - [x] SubTask 5.3: 实现降级提示和文档

- [x] Task 6: 添加一键本地服务器命令
  - [x] SubTask 6.1: 添加 `webthief serve` 命令
  - [x] SubTask 6.2: 实现自动浏览器打开
  - [x] SubTask 6.3: 实现端口冲突处理

## Phase 3: 集成和测试

- [x] Task 7: 更新 CLI 和集成
  - [x] SubTask 7.1: 更新命令行接口
  - [x] SubTask 7.2: 更新 orchestrator 集成
  - [x] SubTask 7.3: 移除不必要的选项

- [x] Task 8: 端到端测试
  - [x] SubTask 8.1: 测试静态网站克隆
  - [x] SubTask 8.2: 测试 SPA 网站克隆
  - [x] SubTask 8.3: 测试需要登录的网站
  - [x] SubTask 8.4: 测试 WebGL 网站克隆
  - [x] SubTask 8.5: 测试本地服务器命令

- [x] Task 9: 文档更新
  - [x] SubTask 9.1: 更新 README.md
  - [x] SubTask 9.2: 更新 CHANGELOG.md
  - [x] SubTask 9.3: 添加插件使用文档

# Task Dependencies

- Task 4, Task 5, Task 6 can be done in parallel with Task 1, Task 2, Task 3
- Task 7 depends on Task 1, Task 2, Task 3, Task 4, Task 5, Task 6
- Task 8 depends on Task 7
- Task 9 depends on Task 8
