"""
WebThief 前端架构适配模块：
- 微前端架构检测与处理（qiankun、single-spa、Module Federation）
- React Server Components 检测与处理
- JavaScript 模块依赖图分析
- 复杂依赖关系解析与循环依赖处理
- 模块加载顺序优化
"""

from __future__ import annotations

from .dependency_resolver import (
    DependencyGraph,
    DependencyResolver,
    ModuleInfo,
    ModuleType,
)
from .frontend_adapter import (
    FrontendAdapter,
    FrontendArchitecture,
    FrontendConfig,
)
from .micro_frontend_handler import (
    MicroFrontendHandler,
    MicroFrontendType,
    ModuleFederationConfig,
    SubAppInfo,
)
from .server_component_handler import (
    ReactServerComponent,
    ServerComponentHandler,
    ServerComponentType,
)

__all__ = [
    # FrontendAdapter
    "FrontendAdapter",
    "FrontendArchitecture",
    "FrontendConfig",
    # MicroFrontendHandler
    "MicroFrontendHandler",
    "MicroFrontendType",
    "ModuleFederationConfig",
    "SubAppInfo",
    # ServerComponentHandler
    "ServerComponentHandler",
    "ServerComponentType",
    "ReactServerComponent",
    # DependencyResolver
    "DependencyResolver",
    "DependencyGraph",
    "ModuleInfo",
    "ModuleType",
]
