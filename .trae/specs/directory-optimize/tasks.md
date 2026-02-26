# Tasks

## Phase 1: 解决 parser 命名冲突

- [x] Task 1: 整合 parser.py 到 parser 包
  - [x] SubTask 1.1: 将根目录 parser.py 移动到 parser/base.py
  - [x] SubTask 1.2: 更新 parser/__init__.py 导出 Parser 类
  - [x] SubTask 1.3: 更新 parser/base.py 内部的导入路径

## Phase 2: 归类核心流程文件

- [x] Task 2: 移动核心引擎文件到 core/
  - [x] SubTask 2.1: 移动 orchestrator.py 到 core/
  - [x] SubTask 2.2: 移动 renderer.py 到 core/
  - [x] SubTask 2.3: 移动 site_crawler.py 到 core/
  - [x] SubTask 2.4: 移动 spa_prerender.py 到 core/
  - [x] SubTask 2.5: 移动 sanitizer.py 到 core/
  - [x] SubTask 2.6: 更新 core/__init__.py 导出

## Phase 3: 创建拦截器目录

- [x] Task 3: 创建 interceptors 目录
  - [x] SubTask 3.1: 创建 webthief/interceptors/ 目录
  - [x] SubTask 3.2: 创建 webthief/interceptors/__init__.py
  - [x] SubTask 3.3: 移动 qr_interceptor.py 到 interceptors/
  - [x] SubTask 3.4: 移动 react_interceptor.py 到 interceptors/

## Phase 4: 归类杂项文件

- [x] Task 4: 移动 session_store.py
  - [x] SubTask 4.1: 移动 session_store.py 到 session/
  - [x] SubTask 4.2: 更新 session/__init__.py 导出

- [x] Task 5: 移动 tech_analyzer.py
  - [x] SubTask 5.1: 移动 tech_analyzer.py 到 extractor/
  - [x] SubTask 5.2: 更新 extractor/__init__.py 导出

## Phase 5: 更新导入路径

- [x] Task 6: 更新根目录文件的导入
  - [x] SubTask 6.1: 更新 webthief/__init__.py
  - [x] SubTask 6.2: 更新 cli.py
  - [x] SubTask 6.3: 更新其他引用文件

- [x] Task 7: 更新 core 内部导入
  - [x] SubTask 7.1: 更新 core/orchestrator.py 导入
  - [x] SubTask 7.2: 更新 core/renderer.py 导入
  - [x] SubTask 7.3: 更新 core/site_crawler.py 导入
  - [x] SubTask 7.4: 更新 core/spa_prerender.py 导入
  - [x] SubTask 7.5: 更新 core/sanitizer.py 导入

- [x] Task 8: 更新 parser 内部导入
  - [x] SubTask 8.1: 更新 parser/base.py 导入

## Phase 6: 清理和验证

- [x] Task 9: 清理旧文件
  - [x] SubTask 9.1: 删除已移动的旧文件

- [x] Task 10: 验证重构结果
  - [x] SubTask 10.1: 验证所有模块可以导入
  - [x] SubTask 10.2: 验证 CLI 命令正常工作
  - [x] SubTask 10.3: 验证向后兼容

# Task Dependencies

- Task 2, Task 3, Task 4, Task 5 can be done in parallel after Task 1
- Task 6, Task 7, Task 8 can be done in parallel after Task 2, Task 3, Task 4, Task 5
- Task 9 depends on Task 6, Task 7, Task 8
- Task 10 depends on Task 9
