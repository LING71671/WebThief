# 目录重构 Spec

## Why

当前 WebThief 项目的目录结构混乱，parser 相关文件散落在根目录，core 模块缺失，需要重构为更清晰、模块化的结构。

## What Changes

- **创建 core 目录**：将核心功能模块移动到 webthief/core/
- **整理 parser 目录**：将 parser 相关文件统一移动到 webthief/parser/
- **整理 extractor 目录**：将提取器模块移动到 webthief/extractor/
- **更新所有导入路径**：确保重构后所有导入正常工作
- **保持向后兼容**：webthief/__init__.py 继续导出公共 API

## Impact

- Affected specs: 所有 WebThief 模块
- Affected code:
  - `webthief/*.py` - 根目录下的所有模块
  - `webthief/__init__.py` - 需要更新导出
  - 所有引用这些模块的文件

## 目标目录结构

```
webthief/
├── __init__.py              # 主入口，导出公共 API
├── __main__.py              # 命令行入口
├── cli.py                   # 命令行接口
├── config.py                # 配置管理
├── utils.py                 # 工具函数
├── core/                    # 核心模块（新目录）
│   ├── __init__.py
│   ├── browser_manager.py   # 浏览器管理
│   ├── downloader.py        # 下载器
│   ├── orchestrator.py      # 主控器
│   ├── page_interactor.py   # 页面交互
│   ├── renderer.py          # 渲染引擎
│   ├── resource_manager.py  # 资源管理
│   └── storage.py           # 存储管理
├── parser/                  # 解析器模块（新目录）
│   ├── __init__.py
│   ├── core.py              # 核心类和配置
│   ├── html.py              # HTML 解析
│   ├── css.py               # CSS 解析
│   └── js.py                # JS 解析
├── extractor/               # 提取器模块（新目录）
│   ├── __init__.py
│   ├── dom_extractor.py     # DOM 提取
│   └── tech_analyzer.py     # 技术分析
├── sanitizer.py             # HTML 清理器
├── site_crawler.py          # 站点爬虫
├── spa_prerender.py         # SPA 预渲染
├── session_store.py         # 会话存储
├── qr_interceptor.py        # QR 码拦截器
├── react_interceptor.py     # React 拦截器
├── scripts.py               # 脚本配置
├── api_simulator/           # API 模拟器
├── detector/                # 网站类型检测
├── performance/             # 性能优化
├── security/                # 安全处理
├── server/                  # 本地服务器
├── session/                 # 会话管理
├── strategy/                # 克隆策略
└── plugins/                 # 可选插件
```

## ADDED Requirements

### Requirement: 创建 core 目录

The system SHALL organize core modules into webthief/core/ directory.

#### Scenario: 移动核心模块
- **WHEN** refactoring the directory structure
- **THEN** the following files SHALL be moved to webthief/core/:
  - browser_manager.py
  - downloader.py
  - orchestrator.py
  - page_interactor.py
  - renderer.py
  - resource_manager.py
  - storage.py

### Requirement: 整理 parser 目录

The system SHALL organize parser modules into webthief/parser/ directory.

#### Scenario: 移动解析器模块
- **WHEN** refactoring the directory structure
- **THEN** the following files SHALL be moved to webthief/parser/:
  - parser_core.py -> core.py
  - html_parser.py -> html.py
  - html_extractor.py -> extractor.py
  - html_rewriter.py -> rewriter.py
  - html_injector.py -> injector.py
  - css_parser.py -> css.py
  - js_parser.py -> js.py

### Requirement: 整理 extractor 目录

The system SHALL organize extractor modules into webthief/extractor/ directory.

#### Scenario: 移动提取器模块
- **WHEN** refactoring the directory structure
- **THEN** the following files SHALL be moved to webthief/extractor/:
  - dom_extractor.py
  - tech_analyzer.py

### Requirement: 更新导入路径

The system SHALL update all import statements after file movement.

#### Scenario: 更新相对导入
- **WHEN** files are moved to new directories
- **THEN** all relative imports SHALL be updated
- **AND** the code SHALL remain functional

#### Scenario: 更新绝对导入
- **WHEN** files are moved to new directories
- **THEN** all absolute imports SHALL be updated
- **AND** the code SHALL remain functional

### Requirement: 保持向后兼容

The system SHALL maintain backward compatibility for public APIs.

#### Scenario: 公共 API 导出
- **WHEN** importing from webthief
- **THEN** all public classes and functions SHALL remain accessible
- **AND** existing code SHALL continue to work
