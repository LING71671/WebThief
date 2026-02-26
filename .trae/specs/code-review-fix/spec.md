# 代码审查与修复 Spec

## Why

之前的重构可能导致代码错误、导入问题或功能异常。需要全面审查代码，修复重构造成的错误，并优化项目目录结构。

## What Changes

- **代码审查**：检查所有重构后的文件，识别潜在错误
- **错误修复**：修复导入错误、语法错误、逻辑错误
- **目录结构优化**：清理重复文件，优化模块组织
- **功能验证**：确保核心功能正常工作

## Impact

- Affected specs: 所有 WebThief 模块
- Affected code:
  - `webthief/parser*.py` - 拆分后的解析器模块
  - `webthief/sanitizer.py` - 重构后的清理器
  - `webthief/renderer.py` - 优化后的渲染器
  - `webthief/orchestrator.py` - 集成模块
  - `webthief/cli.py` - 命令行接口
  - `webthief/plugins/` - 插件目录

## ADDED Requirements

### Requirement: 代码审查

The system SHALL pass code review without critical errors.

#### Scenario: 检查导入错误
- **WHEN** running `python -c "import webthief"`
- **THEN** no ImportError SHALL be raised
- **AND** all modules SHALL be importable

#### Scenario: 检查语法错误
- **WHEN** running `python -m py_compile webthief/*.py`
- **THEN** no SyntaxError SHALL be raised
- **AND** all files SHALL compile successfully

#### Scenario: 检查类型错误
- **WHEN** running type checker (if available)
- **THEN** no critical type errors SHALL be found

### Requirement: 错误修复

The system SHALL fix all identified errors.

#### Scenario: 修复导入错误
- **WHEN** an ImportError is found
- **THEN** the import path SHALL be corrected
- **AND** the module SHALL be importable

#### Scenario: 修复语法错误
- **WHEN** a SyntaxError is found
- **THEN** the syntax SHALL be corrected
- **AND** the file SHALL compile successfully

### Requirement: 目录结构优化

The system SHALL have a clean and organized directory structure.

#### Scenario: 清理重复文件
- **WHEN** duplicate or unused files exist
- **THEN** they SHALL be removed
- **AND** the project SHALL still function correctly

#### Scenario: 优化模块组织
- **WHEN** modules are poorly organized
- **THEN** they SHALL be reorganized logically
- **AND** imports SHALL remain functional

## 审查清单

| 文件/目录 | 检查项 | 优先级 |
|-----------|--------|--------|
| `webthief/__init__.py` | 导出是否正确 | P0 |
| `webthief/parser.py` | 是否能正确导入子模块 | P0 |
| `webthief/parser_*.py` | 是否存在语法/导入错误 | P0 |
| `webthief/sanitizer.py` | 重构后功能是否正常 | P0 |
| `webthief/renderer.py` | 是否能正常工作 | P0 |
| `webthief/orchestrator.py` | 集成是否正确 | P0 |
| `webthief/cli.py` | 命令是否能正常执行 | P0 |
| `webthief/plugins/` | 插件是否能正确导入 | P1 |
| `webthief/core/` | 核心模块是否正常 | P0 |

## 目录结构优化目标

```
webthief/
├── __init__.py          # 主入口，导出公共 API
├── __main__.py          # 命令行入口
├── cli.py               # 命令行接口
├── config.py            # 配置管理
├── orchestrator.py      # 主控器
├── renderer.py          # 渲染引擎
├── parser/              # 解析器包（新目录）
│   ├── __init__.py
│   ├── core.py          # 核心类和配置
│   ├── html.py          # HTML 解析
│   ├── css.py           # CSS 解析
│   └── js.py            # JS 解析
├── sanitizer.py         # HTML 清理器
├── downloader.py        # 下载器
├── extractor/           # 提取器包
│   ├── __init__.py
│   ├── dom_extractor.py
│   └── tech_analyzer.py
├── server/              # 服务器模块
├── session/             # 会话管理
├── security/            # 安全处理
├── performance/         # 性能优化
├── api_simulator/       # API 模拟
├── detector/            # 网站类型检测
├── strategy/            # 克隆策略
├── plugins/             # 可选插件
└── utils.py             # 工具函数
```
