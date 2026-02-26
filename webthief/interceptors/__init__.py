"""
WebThief Interceptors 模块

包含拦截器模块：
- qr_interceptor: 二维码拦截器
- react_interceptor: React 组件拦截器
- mouse_simulator: 鼠标轨迹模拟器
- pointer_interceptor: Pointer 事件拦截器
- canvas_recorder: Canvas 录制器
- webgl_capture: WebGL 捕获器
- animation_analyzer: CSS 动画分析器
- physics_capture: 物理引擎捕获器
"""

from .animation_analyzer import AnimationAnalyzer, AnimationInfo, AnimationReport, AnimationType
from .canvas_recorder import CanvasRecorder
from .mouse_simulator import MouseSimulator, MouseTrajectory, Point, TrajectoryType, MouseEventType
from .physics_capture import (
    PhysicsCapture,
    PhysicsEngineType,
    PhysicsBodyState,
    PhysicsWorldState,
    PhysicsCaptureSession
)
from .pointer_interceptor import PointerInterceptor, PointerEventData
from .qr_interceptor import QRInterceptor
from .react_interceptor import ReactInterceptor
from .webgl_capture import WebGLCapture, WebGLContextInfo, WebGLResourceInfo

__all__ = [
    # 动画分析
    "AnimationAnalyzer",
    "AnimationInfo",
    "AnimationReport",
    "AnimationType",
    # Canvas 录制
    "CanvasRecorder",
    # 鼠标模拟
    "MouseSimulator",
    "MouseTrajectory",
    "Point",
    "TrajectoryType",
    "MouseEventType",
    # 物理引擎捕获
    "PhysicsCapture",
    "PhysicsEngineType",
    "PhysicsBodyState",
    "PhysicsWorldState",
    "PhysicsCaptureSession",
    # Pointer 拦截
    "PointerInterceptor",
    "PointerEventData",
    # QR 拦截
    "QRInterceptor",
    # React 拦截
    "ReactInterceptor",
    # WebGL 捕获
    "WebGLCapture",
    "WebGLContextInfo",
    "WebGLResourceInfo",
]
