# Checklist

## Phase 1: 创建目录结构

- [x] core 目录已创建
  - [x] webthief/core/ 目录已创建
  - [x] webthief/core/__init__.py 已创建

- [x] parser 目录已创建
  - [x] webthief/parser/ 目录已创建
  - [x] webthief/parser/__init__.py 已创建

- [x] extractor 目录已创建
  - [x] webthief/extractor/ 目录已创建
  - [x] webthief/extractor/__init__.py 已创建

## Phase 2: 移动文件

- [x] core 模块已移动
  - [x] downloader.py 已移动到 core/
  - [x] storage.py 已移动到 core/

- [x] parser 模块已移动
  - [x] parser_core.py 已移动到 parser/core.py
  - [x] html_parser.py 已移动到 parser/html.py
  - [x] html_extractor.py 已移动到 parser/extractor.py
  - [x] html_rewriter.py 已移动到 parser/rewriter.py
  - [x] html_injector.py 已移动到 parser/injector.py
  - [x] css_parser.py 已移动到 parser/css.py
  - [x] js_parser.py 已移动到 parser/js.py

- [x] extractor 模块已移动
  - [x] tech_analyzer.py 已移动到 extractor/

## Phase 3: 更新导入路径

- [x] core 模块导入已更新
  - [x] core/__init__.py 导出已更新
  - [x] core 内部相对导入已更新

- [x] parser 模块导入已更新
  - [x] parser/__init__.py 导出已更新
  - [x] parser 内部相对导入已更新

- [x] extractor 模块导入已更新
  - [x] extractor/__init__.py 导出已更新

- [x] 根目录文件导入已更新
  - [x] webthief/__init__.py 已更新
  - [x] cli.py 已更新
  - [x] 其他引用文件已更新

## Phase 4: 清理和验证

- [x] 旧文件已清理
  - [x] 已移动的旧文件已删除

- [x] 重构结果已验证
  - [x] 所有模块可以导入
  - [x] CLI 命令正常工作
  - [x] 目录结构正确

## 验收标准

- [x] 目录结构符合目标设计
- [x] 所有导入路径正确
- [x] 无导入错误
- [x] CLI 命令可用
- [x] 向后兼容
