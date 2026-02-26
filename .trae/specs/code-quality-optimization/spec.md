# 代码质量优化 Spec

## Why

使用 radon 库对 WebThief 代码进行质量测试，检测代码复杂度（Cyclomatic Complexity）和可维护性指数（Maintainability Index），对不合格的代码进行优化。

## What Changes

- 使用 radon 库测试代码复杂度
- 识别复杂度过高的函数和类
- 优化不合格的代码
- 确保代码质量符合标准

## Impact

- Affected specs: 所有 WebThief 模块
- Affected code: 
  - `webthief/server/`
  - `webthief/session/`
  - `webthief/security/`
  - `webthief/performance/`
  - `webthief/api_simulator/`
  - `webthief/detector/`
  - `webthief/strategy/`
  - `webthief/core/` (orchestrator, renderer, parser, downloader)

## ADDED Requirements

### Requirement: 代码复杂度测试

The system SHALL pass radon code complexity tests.

#### Scenario: 测试圈复杂度
- **WHEN** running `radon cc webthief -a`
- **THEN** all functions SHALL have complexity grade A or B
- **AND** average complexity SHALL be less than 5

#### Scenario: 测试可维护性指数
- **WHEN** running `radon mi webthief`
- **THEN** all files SHALL have maintainability index > 20
- **AND** average maintainability index SHALL be > 50

### Requirement: 代码优化

The system SHALL optimize code that fails quality tests.

#### Scenario: 优化高复杂度函数
- **WHEN** a function has complexity grade C or worse
- **THEN** the function SHALL be refactored
- **AND** complexity SHALL be reduced to grade A or B

#### Scenario: 优化低可维护性文件
- **WHEN** a file has maintainability index < 20
- **THEN** the file SHALL be refactored
- **AND** maintainability index SHALL be improved

## 质量标准

| 指标 | 标准 | 说明 |
|------|------|------|
| 圈复杂度 | A 或 B | A: 1-5, B: 6-10, C: 11-20, D: 21-30, E: 31-40, F: 41+ |
| 可维护性指数 | > 20 | 0-9: 极低, 10-19: 低, 20-100: 正常 |

## 优化策略

1. **拆分大函数**：将复杂函数拆分为多个小函数
2. **减少嵌套层级**：使用早返回、提取方法等技巧
3. **简化条件逻辑**：使用多态、策略模式等
4. **移除重复代码**：提取公共方法
