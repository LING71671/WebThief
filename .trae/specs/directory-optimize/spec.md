# 目录结构优化 Spec

## Why

根据 AI 代码审查建议，当前 WebThief 项目目录结构存在以下问题：
1. **命名冲突**：根目录 `parser.py` 与 `parser/` 文件夹同名，导致导入混乱
2. **核心文件散落**：orchestrator.py、renderer.py 等核心流程文件散落在根目录
3. **拦截器未归类**：qr_interceptor.py、react_interceptor.py 需要统一管理
4. **杂项文件未归类**：session_store.py、tech_analyzer.py、sanitizer.py 位置不当

## What Changes

- **解决命名冲突**：将根目录 `parser.py` 整合到 `parser/` 包中
- **归类核心流程文件**：将 orchestrator.py、renderer.py 等移动到 `core/` 目录
- **创建拦截器目录**：新建 `interceptors/` 目录存放拦截器
- **归类杂项文件**：将 session_store.py、tech_analyzer.py 移动到合适位置

## Impact

- Affected specs: 所有 WebThief 模块
- Affected code:
  - `webthief/parser.py` - 需要整合到 parser/ 包
  - `webthief/orchestrator.py` - 移动到 core/
  - `webthief/renderer.py` - 移动到 core/
  - `webthief/site_crawler.py` - 移动到 core/
  - `webthief/spa_prerender.py` - 移动到 core/
  - `webthief/qr_interceptor.py` - 移动到 interceptors/
  - `webthief/react_interceptor.py` - 移动到 interceptors/
  - `webthief/session_store.py` - 移动到 session/
  - `webthief/tech_analyzer.py` - 移动到 extractor/
  - `webthief/sanitizer.py` - 移动到 core/

## 优化后的目录结构

```
webthief/
├── __init__.py              # 主入口，导出公共 API
├── __main__.py              # 命令行入口
├── cli.py                   # 命令行接口
├── config.py                # 配置管理
├── utils.py                 # 工具函数
├── core/                    # 核心引擎模块
│   ├── __init__.py
│   ├── browser_manager.py   # 浏览器管理
│   ├── downloader.py        # 下载器
│   ├── orchestrator.py      # 主控器/调度器
│   ├── page_interactor.py   # 页面交互
│   ├── renderer.py          # 渲染引擎
│   ├── resource_manager.py  # 资源管理
│   ├── sanitizer.py         # HTML 清理器
│   ├── site_crawler.py      # 整站爬虫
│   ├── spa_prerender.py     # SPA 预渲染
│   └── storage.py           # 存储管理
├── parser/                  # 解析器模块
│   ├── __init__.py          # 导出 Parser 主类
│   ├── base.py              # Parser 主类（原 parser.py）
│   ├── core.py              # 解析器核心类
│   ├── html.py              # HTML 解析
│   ├── extractor.py         # HTML 资源提取
│   ├── rewriter.py          # HTML 重写
│   ├── injector.py          # 浏览器 API 垫片注入
│   ├── css.py               # CSS 解析
│   └── js.py                # JS 解析
├── extractor/               # 提取器模块
│   ├── __init__.py
│   ├── dom_extractor.py     # DOM 提取
│   └── tech_analyzer.py     # 技术栈分析
├── interceptors/            # 拦截器模块（新）
│   ├── __init__.py
│   ├── qr_interceptor.py    # 二维码拦截
│   └── react_interceptor.py # React 拦截
├── api_simulator/           # API 模拟器
├── detector/                # 网站类型检测
├── performance/             # 性能优化
├── security/                # 安全处理
├── server/                  # 本地服务器
├── session/                 # 会话管理
│   ├── __init__.py
│   ├── cookie_store.py
│   ├── local_storage_manager.py
│   ├── session_manager.py
│   └── session_store.py     # 会话存储（从根目录移入）
├── strategy/                # 克隆策略
└── plugins/                 # 可选插件
```

## ADDED Requirements

### Requirement: 解决 parser 命名冲突

The system SHALL resolve the naming conflict between `parser.py` and `parser/` directory.

#### Scenario: 整合 parser.py 到 parser 包
- **WHEN** refactoring the directory structure
- **THEN** `parser.py` SHALL be moved to `parser/base.py`
- **AND** `parser/__init__.py` SHALL export the Parser class
- **AND** imports like `from webthief import Parser` SHALL continue to work

### Requirement: 归类核心流程文件

The system SHALL organize core workflow files into the `core/` directory.

#### Scenario: 移动核心引擎文件
- **WHEN** refactoring the directory structure
- **THEN** the following files SHALL be moved to `core/`:
  - orchestrator.py
  - renderer.py
  - site_crawler.py
  - spa_prerender.py
  - sanitizer.py

### Requirement: 创建拦截器目录

The system SHALL create an `interceptors/` directory for interceptor modules.

#### Scenario: 移动拦截器文件
- **WHEN** refactoring the directory structure
- **THEN** an `interceptors/` directory SHALL be created
- **AND** `qr_interceptor.py` SHALL be moved to `interceptors/`
- **AND** `react_interceptor.py` SHALL be moved to `interceptors/`

### Requirement: 归类杂项文件

The system SHALL move miscellaneous files to appropriate directories.

#### Scenario: 移动 session_store.py
- **WHEN** refactoring the directory structure
- **THEN** `session_store.py` SHALL be moved to `session/`

#### Scenario: 移动 tech_analyzer.py
- **WHEN** refactoring the directory structure
- **THEN** `tech_analyzer.py` SHALL be moved to `extractor/`

### Requirement: 更新所有导入路径

The system SHALL update all import statements after file movement.

#### Scenario: 更新导入路径
- **WHEN** files are moved to new directories
- **THEN** all import statements SHALL be updated
- **AND** the code SHALL remain functional
- **AND** backward compatibility SHALL be maintained
