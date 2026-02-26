# WebThief 增强版 Spec

## Why

WebThief 是一款强大的网站克隆工具，目前已支持静态网站、简单 SPA 应用的克隆。但仍有多种类型的网站无法或难以复刻，包括实时协作应用、WebGL 游戏、依赖后端 API 的动态网站等。需要扩展 WebThief 能力，使其能够支持更多类型的网站克隆。

## What Changes

- **新增本地服务器模块**：内置 HTTP 服务器，支持 WebGL/Canvas 运行时环境
- **新增 API 模拟系统**：缓存并模拟 API 响应，支持动态数据加载
- **新增 WebSocket 代理**：支持 WebSocket 连接和消息记录
- **新增会话管理增强**：持久化会话，支持复杂认证流程
- **新增浏览器 API 模拟**：模拟 Service Worker、IndexedDB 等现代浏览器 API
- **新增安全处理优化**：智能处理 CSP，绕过基本反爬虫机制
- **新增前端架构适配**：支持微前端、Server Components 等复杂前端架构
- **性能优化**：提升大型网站克隆速度和稳定性

## Impact

- **Affected specs**: 所有网站克隆功能、资源下载功能、存储功能
- **Affected code**: 
  - `webthief/server/` - 本地服务器模块
  - `webthief/api_simulator/` - API 模拟系统
  - `webthief/websocket_proxy/` - WebSocket 代理
  - `webthief/session/` - 会话管理增强
  - `webthief/browser_api/` - 浏览器 API 模拟
  - `webthief/security/` - 安全处理优化
  - `webthief/frontend/` - 前端架构适配
  - `webthief/performance/` - 性能优化

## ADDED Requirements

### Requirement: 本地服务器增强

The system SHALL provide a built-in HTTP server that supports WebGL/Canvas runtime environment.

#### Scenario: 启动本地服务器
- **WHEN** user clones a website with local server enabled
- **THEN** the system SHALL automatically start an HTTP server on port 8080 (or available port)
- **AND** the server SHALL support HTTPS simulation
- **AND** the server SHALL support WebSocket connections
- **AND** the system SHALL automatically open a browser to access the cloned website

#### Scenario: 处理 WebGL 请求
- **WHEN** the cloned website contains WebGL/Canvas elements
- **THEN** the local server SHALL provide proper runtime environment for WebGL/Canvas
- **AND** the WebGL/Canvas elements SHALL function correctly when accessed via localhost

#### Scenario: 端口冲突处理
- **WHEN** the default port 8080 is occupied
- **THEN** the system SHALL automatically find and use an available port
- **AND** notify the user of the new port number

### Requirement: API 模拟系统

The system SHALL cache and simulate API responses to support dynamic data loading.

#### Scenario: 缓存 API 响应
- **WHEN** the cloned website makes API requests during rendering
- **THEN** the system SHALL intercept and cache all API responses
- **AND** store the cached responses in a structured format
- **AND** generate matching rules for request identification

#### Scenario: 启动 API 模拟服务器
- **WHEN** user starts the local server with API simulation enabled
- **THEN** the system SHALL start an API simulation server
- **AND** the server SHALL match incoming requests to cached responses
- **AND** return the appropriate cached response or default response

#### Scenario: 参数化请求匹配
- **WHEN** API requests contain query parameters or request body
- **THEN** the system SHALL use these parameters for request matching
- **AND** support fuzzy matching for dynamic parameters

### Requirement: WebSocket 代理

The system SHALL support WebSocket connection interception and message recording.

#### Scenario: 记录 WebSocket 消息
- **WHEN** the cloned website establishes WebSocket connections
- **THEN** the system SHALL intercept and record all WebSocket messages
- **AND** store messages with timestamps and direction (client/server)
- **AND** support both text and binary messages

#### Scenario: 回放 WebSocket 消息
- **WHEN** user accesses the cloned website via local server
- **AND** the website attempts to establish WebSocket connection
- **THEN** the WebSocket proxy SHALL accept the connection
- **AND** replay recorded messages according to rules
- **AND** handle client requests appropriately

### Requirement: 会话管理增强

The system SHALL provide persistent session management supporting complex authentication flows.

#### Scenario: 保存会话
- **WHEN** user successfully logs into a website
- **THEN** the system SHALL capture and save all session data
- **AND** save cookies, localStorage, and sessionStorage
- **AND** encrypt sensitive session data
- **AND** store session in a persistent file

#### Scenario: 加载会话
- **WHEN** user wants to clone a website that requires authentication
- **AND** a saved session exists
- **THEN** the system SHALL load the session data
- **AND** apply cookies and localStorage to the browser context
- **AND** verify session validity

#### Scenario: 处理会话过期
- **WHEN** a loaded session has expired
- **THEN** the system SHALL detect the expiration
- **AND** prompt user to re-authenticate
- **OR** attempt automatic re-authentication if credentials are available

### Requirement: 浏览器 API 模拟

The system SHALL simulate modern browser APIs including Service Worker, IndexedDB, etc.

#### Scenario: 模拟 Service Worker
- **WHEN** the cloned website attempts to register a Service Worker
- **THEN** the system SHALL intercept the registration
- **AND** return a mock Service Worker object
- **AND** simulate Service Worker lifecycle events

#### Scenario: 模拟 IndexedDB
- **WHEN** the cloned website uses IndexedDB
- **THEN** the system SHALL intercept IndexedDB operations
- **AND** redirect operations to file-based storage
- **AND** persist data across sessions

#### Scenario: 模拟其他浏览器 API
- **WHEN** the cloned website uses Web Crypto API, Notification API, or Geolocation API
- **THEN** the system SHALL provide mock implementations
- **AND** return appropriate default values or simulate user interactions

### Requirement: 安全处理优化

The system SHALL intelligently handle CSP rules and bypass basic anti-bot mechanisms.

#### Scenario: 处理 CSP 规则
- **WHEN** a website has strict CSP headers
- **THEN** the system SHALL analyze the CSP rules
- **AND** generate compatible CSP rules for local server
- **AND** ensure cloned resources can load correctly

#### Scenario: 绕过基本反爬虫
- **WHEN** a website has basic anti-bot protection (e.g., Cloudflare)
- **THEN** the system SHALL detect the protection
- **AND** generate realistic browser fingerprints
- **AND** simulate human-like behavior
- **AND** rotate User-Agent and headers

#### Scenario: 处理验证码
- **WHEN** a website presents a CAPTCHA
- **THEN** the system SHALL detect the CAPTCHA
- **AND** prompt user for manual input
- **AND** integrate with CAPTCHA solving services (optional)

### Requirement: 前端架构适配

The system SHALL support complex frontend architectures including micro-frontends and Server Components.

#### Scenario: 支持微前端
- **WHEN** the cloned website uses micro-frontend architecture
- **THEN** the system SHALL detect the architecture
- **AND** handle module federation correctly
- **AND** ensure all micro-frontend modules load properly

#### Scenario: 支持 Server Components
- **WHEN** the cloned website uses React Server Components
- **THEN** the system SHALL detect Server Components
- **AND** simulate server-side rendering
- **AND** handle streaming responses

#### Scenario: 解析复杂依赖
- **WHEN** the cloned website has complex dependency relationships
- **THEN** the system SHALL analyze and resolve dependencies
- **AND** ensure correct loading order
- **AND** handle circular dependencies

### Requirement: 性能优化

The system SHALL optimize performance for large website cloning.

#### Scenario: 并发下载优化
- **WHEN** cloning a large website with many resources
- **THEN** the system SHALL use optimal concurrency settings
- **AND** dynamically adjust based on system performance
- **AND** prioritize critical resources

#### Scenario: 资源去重优化
- **WHEN** multiple resources have identical content
- **THEN** the system SHALL detect duplicates using SHA256
- **AND** store only one copy
- **AND" rewrite references to point to the single copy

#### Scenario: 内存使用优化
- **WHEN" processing large files or many resources
- **THEN" the system SHALL use streaming for large files
- **AND" implement memory monitoring
- **AND" automatically release unused memory

## MODIFIED Requirements

### Requirement: 命令行接口

**Existing**: Basic command line interface with limited options

**Modified**: Extended command line interface with new options for enhanced features

- **ADDED**: `--local-server` flag to enable local server
- **ADDED**: `--api-simulation` flag to enable API simulation
- **ADDED**: `--websocket-proxy` flag to enable WebSocket proxy
- **ADDED**: `--session-file` option to specify session file
- **ADDED**: `--port` option to specify local server port
- **ADDED**: `--https` flag to enable HTTPS simulation

## REMOVED Requirements

None. All existing functionality SHALL be preserved.
