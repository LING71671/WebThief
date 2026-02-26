"""
网站类型检测模块

提供智能网站类型检测功能，包括：
- 静态网站检测
- SPA 应用检测（Angular/React/Vue）
- 认证需求检测
- WebGL/Canvas 应用检测

使用示例:
---------
```python
from webthief.detector import WebsiteTypeDetector

detector = WebsiteTypeDetector()
result = await detector.detect(page)
print(f"网站类型: {result.website_type}")
print(f"检测到的框架: {result.frameworks}")
```
"""

from webthief.detector.website_type_detector import (
    WebsiteType,
    WebsiteTypeResult,
    WebsiteTypeDetector,
)

__all__ = [
    "WebsiteType",
    "WebsiteTypeResult",
    "WebsiteTypeDetector",
]
