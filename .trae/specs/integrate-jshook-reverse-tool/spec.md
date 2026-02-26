# 配置 JSHook Reverse Tool 到 Trae IDE 规范

## 概述

将 `jshook-reverse-tool` 配置为 Trae IDE 的全局 MCP 工具/技能，使其可以在任何项目中通过自然语言调用 80+ 个 JavaScript 逆向工程工具。

## Why

Trae IDE 目前缺乏专业的浏览器逆向工程能力：
1. **无法动态调试网页** - 需要手动打开 Chrome DevTools
2. **无法自动 Hook 加密算法** - 需要手动编写注入代码
3. **无法自动识别验证码** - 需要人工干预
4. **缺乏反检测自动化** - 需要手动配置 Puppeteer 参数

JSHook Reverse Tool 提供 80+ 个 MCP 工具，可以通过自然语言直接调用，大幅提升逆向工程效率。

## What Changes

### 新增配置
- **MCP 服务器配置** - 在 Trae 配置中添加 JSHook MCP 服务器
- **全局技能配置** - 在 `.trae/skills/` 下创建 JSHook 技能定义
- **环境变量配置** - 配置 OpenAI/Anthropic API Key

### 配置方式
- 通过 Trae 的 MCP 配置界面添加 JSHook
- 通过 `.trae/skills/jshook-reverse-tool/SKILL.md` 定义技能
- 支持 npx 方式运行，无需全局安装

### 使用场景
- 分析任意网站的加密算法
- 自动处理滑块/图形验证码
- Hook 并监控 Fetch/XHR 请求
- 调试 JavaScript 执行流程

## ADDED Requirements

### Requirement: MCP 服务器配置
系统 SHALL 支持在 Trae IDE 中配置 JSHook 作为 MCP 服务器。

#### Scenario: 配置添加
- **GIVEN** 用户已安装 Node.js >= 18
- **WHEN** 在 Trae 设置中添加 MCP 服务器配置
- **THEN** JSHook 工具可用并通过自然语言调用

#### Scenario: 环境变量配置
- **GIVEN** 用户在 Trae 环境变量中设置了 API Key
- **WHEN** 调用 JSHook 工具时
- **THEN** 环境变量正确传递到 MCP 服务器

### Requirement: 全局技能定义
系统 SHALL 在 `.trae/skills/` 下提供 JSHook 技能定义。

#### Scenario: 技能自动加载
- **GIVEN** 技能文件存在于 `.trae/skills/jshook-reverse-tool/`
- **WHEN** Trae 启动时
- **THEN** 自动加载并识别 JSHook 相关指令

#### Scenario: 自然语言调用
- **GIVEN** 用户输入包含逆向工程需求
- **WHEN** 例如"分析这个网站的加密算法"
- **THEN** 自动触发 JSHook 工具执行

### Requirement: 工具分类支持
系统 SHALL 支持 JSHook 的所有工具分类。

#### Scenario: 浏览器自动化
- **WHEN** 用户需要浏览器操作
- **THEN** 可使用 browser_launch, page_navigate 等 35 个工具

#### Scenario: 调试器功能
- **WHEN** 用户需要调试 JavaScript
- **THEN** 可使用 debugger_enable, set_breakpoint 等 38 个工具

#### Scenario: 网络监控
- **WHEN** 用户需要捕获网络请求
- **THEN** 可使用 network_enable, get_requests 等 6 个工具

#### Scenario: Hook 生成
- **WHEN** 用户需要生成 Hook 代码
- **THEN** 可使用 ai_hook_generate, ai_hook_inject 等 7 个工具

## MODIFIED Requirements

无 - 此配置不涉及修改现有代码，仅添加新的 MCP 服务器和技能定义。

## REMOVED Requirements

无

## 技术架构

```
┌─────────────────────────────────────────────────────────────┐
│                      Trae IDE                                │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                 MCP 客户端                           │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  │   │
│  │  │  工具发现    │  │  工具调用    │  │  结果处理    │  │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  │   │
│  └──────────────────────┬──────────────────────────────┘   │
│                         │                                   │
│  ┌──────────────────────┼──────────────────────────────┐   │
│  │                 Skill 系统                           │   │
│  │  ┌───────────────────┼──────────────────────────┐   │   │
│  │  │   jshook-reverse-tool SKILL                  │   │   │
│  │  │   (触发词识别 + 参数解析)                      │   │   │
│  │  └───────────────────┼──────────────────────────┘   │   │
│  └──────────────────────┼──────────────────────────────┘   │
└─────────────────────────┼───────────────────────────────────┘
                          │
                    ┌─────┴─────┐
                    │  MCP 协议  │
                    │  (stdio)  │
                    └─────┬─────┘
                          │
┌─────────────────────────┼───────────────────────────────────┐
│                    Node.js 环境                              │
│  ┌──────────────────────┼────────────────────────────────┐ │
│  │           jshook-reverse-tool (npx)                    │ │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────────┐  │ │
│  │  │Browser  │ │Debugger │ │Network  │ │AI Hook      │  │ │
│  │  │(35工具) │ │(38工具) │ │(6工具)  │ │(7工具)      │  │ │
│  │  └─────────┘ └─────────┘ └─────────┘ └─────────────┘  │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## 配置文件

### 1. MCP 服务器配置

在 Trae 的 MCP 配置中添加：

```json
{
  "mcpServers": {
    "jshook": {
      "command": "npx",
      "args": ["-y", "jshook-reverse-tool"],
      "env": {
        "OPENAI_API_KEY": "${OPENAI_API_KEY}",
        "DEFAULT_LLM_PROVIDER": "openai",
        "PUPPETEER_HEADLESS": "false",
        "PUPPETEER_TIMEOUT": "30000"
      }
    }
  }
}
```

### 2. 技能定义文件

`.trae/skills/jshook-reverse-tool/SKILL.md`:

```markdown
---
name: "jshook-reverse-tool"
description: "JavaScript reverse engineering tool with 80+ MCP tools for browser automation, debugging, and hooking. Invoke when analyzing website encryption, handling captchas, monitoring API calls, or debugging JavaScript."
---

# JSHook Reverse Tool

AI-powered JavaScript reverse engineering tool for browser automation and security research.

## Capabilities

- Browser automation with anti-detection
- JavaScript debugging via Chrome DevTools Protocol
- Network request monitoring
- AI-generated hook code
- Captcha detection and solving

## Trigger Keywords

- "分析加密算法"
- "hook API"
- "调试网页"
- "验证码识别"
- "反爬虫"
- "browser automation"
- "debug javascript"
- "monitor network"
```

### 3. 环境变量配置

在项目 `.env` 文件或 Trae 环境变量中配置：

```bash
# 必需
OPENAI_API_KEY=sk-...
DEFAULT_LLM_PROVIDER=openai

# 或 Anthropic
ANTHROPIC_API_KEY=sk-ant-...
DEFAULT_LLM_PROVIDER=anthropic

# 可选
PUPPETEER_HEADLESS=false
PUPPETEER_TIMEOUT=30000
ENABLE_CACHE=true
LOG_LEVEL=info
```

## 工具分类详情

| 分类 | 数量 | 主要工具 | 使用场景 |
|-----|------|---------|---------|
| 浏览器自动化 | 35 | browser_launch, stealth_inject, page_navigate, page_click, page_type | 自动化操作、反检测 |
| 调试器 | 38 | debugger_enable, set_breakpoint, get_call_stack, watch_add | 调试加密逻辑 |
| 网络监控 | 6 | network_enable, get_requests, get_response_body | 捕获 API 请求 |
| AI Hook | 7 | ai_hook_generate, ai_hook_inject, ai_hook_get_data | 自动生成 Hook |
| 性能分析 | 4 | performance_get_metrics, performance_take_heap_snapshot | 性能分析 |
| 缓存管理 | 6 | get_token_budget_stats, manual_token_cleanup | Token 管理 |

## 使用示例

### 示例 1: 分析网站加密
```
用户：分析 https://example.com 的登录接口加密算法

AI 自动执行：
1. browser_launch()
2. stealth_inject()
3. network_enable()
4. page_navigate("https://example.com")
5. debugger_enable()
6. xhr_breakpoint_set(urlPattern="*/login*")
7. 触发登录请求
8. 分析调用栈和变量
```

### 示例 2: 验证码处理
```
用户：访问 https://login.example.com 并处理验证码

AI 自动执行：
1. browser_launch()
2. page_navigate("https://login.example.com")
3. captcha_detect() → 识别验证码类型
4. captcha_solve() 或 captcha_wait() → 自动处理或等待用户
```

### 示例 3: Hook API 请求
```
用户：监控 https://api.example.com 的所有 Fetch 请求

AI 自动执行：
1. ai_hook_generate({
     target: { type: "api", name: "fetch" },
     condition: { urlPattern: ".*api.example.com.*" }
   })
2. ai_hook_inject(method="evaluateOnNewDocument")
3. page_navigate("https://api.example.com")
4. 用户操作后调用 ai_hook_get_data()
```

## 依赖要求

- **Node.js**: >= 18.0.0
- **npm/npx**: 已安装
- **API Key**: OpenAI 或 Anthropic API Key
- **Chrome/Chromium**: 用于浏览器自动化

## 配置验证

配置完成后，可以通过以下方式验证：

1. **检查 MCP 连接**: 在 Trae 中查看 MCP 服务器状态
2. **测试工具调用**: 输入"启动浏览器并访问 example.com"
3. **检查日志**: 查看 JSHook 输出日志确认正常运行

## 故障排除

| 问题 | 可能原因 | 解决方案 |
|-----|---------|---------|
| MCP 连接失败 | Node.js 未安装 | 安装 Node.js >= 18 |
| 工具调用失败 | API Key 未配置 | 配置 OPENAI_API_KEY |
| 浏览器启动失败 | Chrome 未安装 | 安装 Chrome 或 Chromium |
| 验证码识别失败 | 使用不支持视觉的模型 | 切换到 GPT-4o 或 Claude 3.5 |

## 成功标准

1. ✅ JSHook 出现在 Trae 的 MCP 工具列表中
2. ✅ 可以通过自然语言调用 JSHook 工具
3. ✅ 环境变量正确传递
4. ✅ 浏览器自动化功能正常工作
5. ✅ 调试器功能正常工作
