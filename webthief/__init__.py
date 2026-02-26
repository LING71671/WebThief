"""
WebThief - 高级网页克隆与资源提取工具

提供完整的网页克隆解决方案，包括：
- 智能资源提取与本地化
- JavaScript 拦截与模拟
- SPA/SSR 页面处理
- 前端架构适配

使用示例:
---------
命令行方式:
```bash
# 克隆网页
webthief clone https://example.com -o ./output

# 启动本地服务器预览
webthief serve ./output --port 8080
```

Python API 方式:
```python
from webthief import Orchestrator

orchestrator = Orchestrator(
    url="https://example.com",
    output_dir="./output",
)
asyncio.run(orchestrator.run())
```
"""

__version__ = "0.1.0"
__author__ = "WebThief Team"

# 导出主要类（保持向后兼容）
from .core.orchestrator import Orchestrator
from .parser import Parser

__all__ = [
    "__version__",
    "__author__",
    "Orchestrator",
    "Parser",
]
