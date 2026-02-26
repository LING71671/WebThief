# Checklist

## Phase 1: 解决 parser 命名冲突

- [x] parser.py 已整合到 parser 包
  - [x] 根目录 parser.py 已移动到 parser/base.py
  - [x] parser/__init__.py 已导出 Parser 类
  - [x] parser/base.py 内部导入路径已更新

## Phase 2: 归类核心流程文件

- [x] 核心引擎文件已移动到 core/
  - [x] orchestrator.py 已移动到 core/
  - [x] renderer.py 已移动到 core/
  - [x] site_crawler.py 已移动到 core/
  - [x] spa_prerender.py 已移动到 core/
  - [x] sanitizer.py 已移动到 core/
  - [x] core/__init__.py 导出已更新

## Phase 3: 创建拦截器目录

- [x] interceptors 目录已创建
  - [x] webthief/interceptors/ 目录已创建
  - [x] webthief/interceptors/__init__.py 已创建
  - [x] qr_interceptor.py 已移动到 interceptors/
  - [x] react_interceptor.py 已移动到 interceptors/

## Phase 4: 归类杂项文件

- [x] session_store.py 已移动
  - [x] session_store.py 已移动到 session/
  - [x] session/__init__.py 导出已更新

- [x] tech_analyzer.py 已移动
  - [x] tech_analyzer.py 已移动到 extractor/
  - [x] extractor/__init__.py 导出已更新

## Phase 5: 更新导入路径

- [x] 根目录文件导入已更新
  - [x] webthief/__init__.py 已更新
  - [x] cli.py 已更新
  - [x] 其他引用文件已更新

- [x] core 内部导入已更新
  - [x] core/orchestrator.py 导入已更新
  - [x] core/renderer.py 导入已更新
  - [x] core/site_crawler.py 导入已更新
  - [x] core/spa_prerender.py 导入已更新
  - [x] core/sanitizer.py 导入已更新

- [x] parser 内部导入已更新
  - [x] parser/base.py 导入已更新

## Phase 6: 清理和验证

- [x] 旧文件已清理
  - [x] 已移动的旧文件已删除

- [x] 重构结果已验证
  - [x] 所有模块可以导入
  - [x] CLI 命令正常工作
  - [x] 向后兼容

## 验收标准

- [x] 无 parser 命名冲突
- [x] 核心文件已归类到 core/
- [x] 拦截器已归类到 interceptors/
- [x] 杂项文件已归类
- [x] 所有导入路径正确
- [x] CLI 命令可用
- [x] 向后兼容
