# 配置 JSHook Reverse Tool 到 Trae IDE 任务列表

## 任务概览

将 `jshook-reverse-tool` 配置为 Trae IDE 的全局 MCP 工具和技能，支持 80+ 个 JavaScript 逆向工程工具的自然语言调用。

---

## 任务详情

### Task 1: 创建 JSHook 技能目录和定义文件
**描述**: 在 `.trae/skills/jshook-reverse-tool/` 下创建技能定义
**优先级**: 高
**依赖**: 无

- [x] SubTask 1.1: 创建技能目录
  - 创建 `.trae/skills/jshook-reverse-tool/` 目录

- [x] SubTask 1.2: 创建 SKILL.md 文件
  - 编写技能 frontmatter（name, description）
  - 编写技能详细说明
  - 定义触发关键词
  - 列出工具分类和能力

---

### Task 2: 配置 MCP 服务器
**描述**: 在 Trae 中添加 JSHook MCP 服务器配置
**优先级**: 高
**依赖**: 无

- [x] SubTask 2.1: 创建 MCP 配置文件
  - 创建/编辑 `.trae/mcp.json` 或相关配置文件
  - 添加 jshook 服务器配置

- [x] SubTask 2.2: 配置启动命令
  - 设置 command 为 "npx"
  - 设置 args 为 ["-y", "jshook-reverse-tool"]

- [x] SubTask 2.3: 配置环境变量模板
  - 添加 OPENAI_API_KEY 占位符
  - 添加 DEFAULT_LLM_PROVIDER 配置
  - 添加可选的 PUPPETEER 配置

---

### Task 3: 配置环境变量
**描述**: 设置 JSHook 运行所需的环境变量
**优先级**: 高
**依赖**: Task 2

- [x] SubTask 3.1: 创建 .env 模板
  - 创建 `.env.example` 文件
  - 列出所有必需和可选环境变量

- [x] SubTask 3.2: 配置 API Key
  - 指导用户获取 OpenAI/Anthropic API Key
  - 配置到 Trae 环境变量或 `.env` 文件

- [x] SubTask 3.3: 验证环境配置
  - 检查 Node.js 版本 >= 18
  - 检查 npx 可用性
  - 验证 API Key 有效性

---

### Task 4: 创建配置文档
**描述**: 编写详细的配置和使用文档
**优先级**: 中
**依赖**: Task 1-3

- [x] SubTask 4.1: 编写安装指南
  - 环境要求说明
  - 安装步骤
  - 配置步骤

- [x] SubTask 4.2: 编写使用示例
  - 浏览器自动化示例
  - 调试加密算法示例
  - Hook API 请求示例
  - 验证码处理示例

- [x] SubTask 4.3: 编写故障排除指南
  - 常见问题及解决方案
  - 日志查看方法
  - 调试技巧

---

### Task 5: 验证配置
**描述**: 测试 JSHook 配置是否正常工作
**优先级**: 高
**依赖**: Task 1-3

- [ ] SubTask 5.1: 验证 MCP 连接
  - 检查 Trae 是否正确识别 JSHook MCP 服务器
  - 验证工具列表加载

- [ ] SubTask 5.2: 测试基础功能
  - 测试 browser_launch 工具
  - 测试 page_navigate 工具
  - 测试 network_enable 工具

- [ ] SubTask 5.3: 测试高级功能
  - 测试 debugger_enable 工具
  - 测试 ai_hook_generate 工具
  - 测试 captcha_detect 工具

---

## 任务依赖图

```
Task 1 (技能定义)
    │
    ├──► Task 2 (MCP配置) ──► Task 3 (环境变量)
    │                              │
    │                              ▼
    │                         Task 5 (验证配置)
    │
    ▼
Task 4 (文档)
```

## 并行执行建议

- **可并行**: Task 1 和 Task 2 可以同时进行
- **可并行**: Task 4 可以与 Task 3-5 部分并行
- **需串行**: Task 3 依赖 Task 2, Task 5 依赖 Task 3

## 预计工作量

| 任务 | 预计时间 | 复杂度 |
|-----|---------|-------|
| Task 1 | 1h | 低 |
| Task 2 | 1h | 低 |
| Task 3 | 1h | 低 |
| Task 4 | 2h | 低 |
| Task 5 | 1h | 中 |
| **总计** | **6h** | - |
