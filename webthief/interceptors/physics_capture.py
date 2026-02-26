"""
物理引擎捕获与静态化模块
目标：检测和捕获网页中的物理引擎（Matter.js、Planck.js、Cannon.js、Box2D 等），
      拦截物理世界更新循环，记录物理体状态，并生成物理模拟的静态表示
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from playwright.async_api import Page
from rich.console import Console

console = Console()


class PhysicsEngineType(Enum):
    """物理引擎类型枚举"""
    MATTER_JS = "matter.js"           # Matter.js
    PLANCK_JS = "planck.js"           # Planck.js (Box2D 移植)
    CANNON_JS = "cannon.js"           # Cannon.js
    BOX2D = "box2d"                   # Box2D
    BOX2DWEB = "box2dweb"             # Box2DWeb
    P2_JS = "p2.js"                   # p2.js
    PHYSICS_JS = "physics.js"         # PhysicsJS
    AMMO_JS = "ammo.js"               # Ammo.js (Bullet 移植)
    UNKNOWN = "unknown"               # 未知引擎


@dataclass
class PhysicsBodyState:
    """物理体状态数据"""
    body_id: str                      # 物理体唯一标识
    body_type: str                    # 类型: dynamic, static, kinematic
    position: dict[str, float]        # 位置 {x, y}
    velocity: dict[str, float]        # 速度 {x, y}
    angle: float                      # 旋转角度（弧度）
    angular_velocity: float           # 角速度
    mass: float                       # 质量
    bounds: dict[str, Any] | None     # 边界框
    vertices: list[dict[str, float]] | None  # 顶点坐标
    timestamp: int                    # 时间戳（毫秒）

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式"""
        return {
            "body_id": self.body_id,
            "body_type": self.body_type,
            "position": self.position,
            "velocity": self.velocity,
            "angle": self.angle,
            "angular_velocity": self.angular_velocity,
            "mass": self.mass,
            "bounds": self.bounds,
            "vertices": self.vertices,
            "timestamp": self.timestamp
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PhysicsBodyState:
        """从字典创建状态对象"""
        return cls(
            body_id=data["body_id"],
            body_type=data["body_type"],
            position=data["position"],
            velocity=data["velocity"],
            angle=data["angle"],
            angular_velocity=data["angular_velocity"],
            mass=data["mass"],
            bounds=data.get("bounds"),
            vertices=data.get("vertices"),
            timestamp=data["timestamp"]
        )


@dataclass
class PhysicsWorldState:
    """物理世界状态快照"""
    timestamp: int                    # 时间戳
    engine_type: PhysicsEngineType    # 引擎类型
    bodies: list[PhysicsBodyState]    # 物理体列表
    gravity: dict[str, float]         # 重力 {x, y}
    time_scale: float                 # 时间缩放
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式"""
        return {
            "timestamp": self.timestamp,
            "engine_type": self.engine_type.value,
            "bodies": [body.to_dict() for body in self.bodies],
            "gravity": self.gravity,
            "time_scale": self.time_scale,
            "metadata": self.metadata
        }


@dataclass
class PhysicsCaptureSession:
    """物理捕获会话"""
    session_id: str
    start_time: int
    engine_type: PhysicsEngineType
    states: list[PhysicsWorldState] = field(default_factory=list)
    capture_interval: int = 16        # 默认 16ms (约 60fps)
    is_active: bool = False

    def add_state(self, state: PhysicsWorldState) -> None:
        """添加状态快照"""
        self.states.append(state)

    def get_duration(self) -> int:
        """获取会话总时长（毫秒）"""
        if len(self.states) < 2:
            return 0
        return self.states[-1].timestamp - self.states[0].timestamp

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式"""
        return {
            "session_id": self.session_id,
            "start_time": self.start_time,
            "engine_type": self.engine_type.value,
            "capture_interval": self.capture_interval,
            "is_active": self.is_active,
            "duration_ms": self.get_duration(),
            "state_count": len(self.states),
            "states": [state.to_dict() for state in self.states]
        }


class PhysicsCapture:
    """
    物理引擎捕获器
    负责：
    1. 检测页面中使用的物理引擎类型
    2. 拦截物理世界更新循环
    3. 记录物理体位置、速度、角度、角速度等状态
    4. 在多个时间点捕获物理状态
    5. 生成物理模拟的静态表示（将动态物理转换为静态 CSS 或 Canvas）
    6. 提供物理引擎报告
    """

    # 物理引擎检测签名
    ENGINE_SIGNATURES: dict[PhysicsEngineType, list[str]] = {
        PhysicsEngineType.MATTER_JS: ["Matter", "Matter.Engine", "Matter.World"],
        PhysicsEngineType.PLANCK_JS: ["planck", "pl", "pl.World"],
        PhysicsEngineType.CANNON_JS: ["CANNON", "CANNON.World"],
        PhysicsEngineType.BOX2D: ["Box2D", "b2World"],
        PhysicsEngineType.BOX2DWEB: ["Box2DWeb", "b2World"],
        PhysicsEngineType.P2_JS: ["p2", "p2.World"],
        PhysicsEngineType.PHYSICS_JS: ["Physics", "Physics.world"],
        PhysicsEngineType.AMMO_JS: ["Ammo", "Ammo.btDiscreteDynamicsWorld"]
    }

    # 默认捕获配置
    DEFAULT_CAPTURE_INTERVAL = 16     # 16ms = 约 60fps
    DEFAULT_CAPTURE_DURATION = 5000   # 默认捕获 5 秒
    MAX_CAPTURE_STATES = 1000         # 最大状态数

    def __init__(self):
        self.detected_engine: PhysicsEngineType | None = None
        self.sessions: list[PhysicsCaptureSession] = []
        self.current_session: PhysicsCaptureSession | None = None
        self.is_capturing = False
        self.capture_config: dict[str, Any] = {
            "interval": self.DEFAULT_CAPTURE_INTERVAL,
            "max_duration": self.DEFAULT_CAPTURE_DURATION,
            "record_velocity": True,
            "record_angular_velocity": True,
            "record_vertices": True
        }

    async def detect_physics_engine(self, page: Page) -> PhysicsEngineType | None:
        """
        检测页面中使用的物理引擎类型

        Args:
            page: Playwright Page 对象

        Returns:
            检测到的物理引擎类型，如果未检测到则返回 None
        """
        console.print("[cyan]  🔍 检测物理引擎...[/]")

        detection_script = """
        () => {
            const engines = {
                "matter.js": () => typeof Matter !== 'undefined' && Matter.Engine,
                "planck.js": () => typeof planck !== 'undefined' && planck.World,
                "cannon.js": () => typeof CANNON !== 'undefined' && CANNON.World,
                "box2d": () => typeof Box2D !== 'undefined' && (typeof b2World !== 'undefined' || Box2D.b2World),
                "box2dweb": () => typeof Box2DWeb !== 'undefined',
                "p2.js": () => typeof p2 !== 'undefined' && p2.World,
                "physics.js": () => typeof Physics !== 'undefined',
                "ammo.js": () => typeof Ammo !== 'undefined' && (Ammo.btDiscreteDynamicsWorld || Ammo.btDynamicsWorld)
            };
            
            const detected = [];
            for (const [name, check] of Object.entries(engines)) {
                try {
                    if (check()) {
                        detected.push(name);
                    }
                } catch (e) {
                    // 忽略检测错误
                }
            }
            
            return {
                detected: detected,
                hasPhysics: detected.length > 0,
                windowKeys: Object.keys(window).filter(k => 
                    /matter|planck|cannon|box2d|physics|ammo|p2/i.test(k)
                ).slice(0, 20)
            };
        }
        """

        result = await page.evaluate(detection_script)

        if result.get("hasPhysics"):
            detected_engines = result.get("detected", [])
            if detected_engines:
                # 取第一个检测到的引擎
                engine_name = detected_engines[0]
                try:
                    self.detected_engine = PhysicsEngineType(engine_name)
                except ValueError:
                    self.detected_engine = PhysicsEngineType.UNKNOWN

                console.print(f"[green]  ✓ 检测到物理引擎: {self.detected_engine.value}[/]")
                if len(detected_engines) > 1:
                    console.print(f"[yellow]  ⚠ 同时检测到其他引擎: {', '.join(detected_engines[1:])}[/]")
            else:
                self.detected_engine = PhysicsEngineType.UNKNOWN
                console.print("[yellow]  ⚠ 发现可能的物理引擎但未明确识别[/]")
        else:
            self.detected_engine = None
            console.print("[yellow]  ⚠ 未检测到物理引擎[/]")

        return self.detected_engine

    async def inject_physics_tracker(self, page: Page) -> bool:
        """
        注入物理追踪脚本，拦截物理世界更新循环

        Args:
            page: Playwright Page 对象

        Returns:
            是否成功注入
        """
        if not self.detected_engine:
            console.print("[red]  ✗ 未检测到物理引擎，无法注入追踪器[/]")
            return False

        console.print(f"[cyan]  🎯 注入物理追踪器 ({self.detected_engine.value})...[/]")

        tracker_script = self._generate_tracker_script()

        try:
            await page.add_init_script(tracker_script)
            console.print("[green]  ✓ 物理追踪器已注入[/]")
            return True
        except Exception as e:
            console.print(f"[red]  ✗ 注入失败: {e}[/]")
            return False

    def _generate_tracker_script(self) -> str:
        """生成物理追踪 JavaScript 脚本"""
        return """
        (function() {
            'use strict';
            // ━━━ WebThief Physics Tracker Layer ━━━
            
            window.__webthief_physics = {
                is_tracking: false,
                states: [],
                engine_type: null,
                original_step: null,
                capture_interval: 16,
                last_capture_time: 0,
                world_ref: null,
                bodies_cache: new Map()
            };
            
            // 序列化物理体状态
            function serializeBody(body, engine_type) {
                const state = {
                    body_id: body.id || body.m_id || Math.random().toString(36).substr(2, 9),
                    body_type: 'dynamic',
                    position: { x: 0, y: 0 },
                    velocity: { x: 0, y: 0 },
                    angle: 0,
                    angular_velocity: 0,
                    mass: 1,
                    bounds: null,
                    vertices: null,
                    timestamp: Date.now()
                };
                
                try {
                    // Matter.js
                    if (engine_type === 'matter.js' || (typeof Matter !== 'undefined' && body.position)) {
                        state.position = { x: body.position.x, y: body.position.y };
                        state.velocity = { x: body.velocity.x, y: body.velocity.y };
                        state.angle = body.angle || 0;
                        state.angular_velocity = body.angularVelocity || 0;
                        state.mass = body.mass || 1;
                        state.body_type = body.isStatic ? 'static' : (body.isSleeping ? 'sleeping' : 'dynamic');
                        
                        if (body.bounds) {
                            state.bounds = {
                                min: { x: body.bounds.min.x, y: body.bounds.min.y },
                                max: { x: body.bounds.max.x, y: body.bounds.max.y }
                            };
                        }
                        
                        if (body.vertices) {
                            state.vertices = body.vertices.map(v => ({ x: v.x, y: v.y }));
                        }
                    }
                    // Planck.js / Box2D
                    else if (engine_type === 'planck.js' || engine_type === 'box2d' || engine_type === 'box2dweb') {
                        const pos = body.getPosition ? body.getPosition() : body.m_position;
                        const vel = body.getLinearVelocity ? body.getLinearVelocity() : body.m_linearVelocity;
                        
                        if (pos) {
                            state.position = { x: pos.x, y: pos.y };
                        }
                        if (vel) {
                            state.velocity = { x: vel.x, y: vel.y };
                        }
                        
                        state.angle = body.getAngle ? body.getAngle() : (body.m_angle || 0);
                        state.angular_velocity = body.getAngularVelocity ? body.getAngularVelocity() : (body.m_angularVelocity || 0);
                        state.mass = body.getMass ? body.getMass() : (body.m_mass || 1);
                        state.body_type = body.isStatic ? 'static' : 'dynamic';
                    }
                    // Cannon.js
                    else if (engine_type === 'cannon.js' || (typeof CANNON !== 'undefined' && body.position)) {
                        state.position = { x: body.position.x, y: body.position.y };
                        state.velocity = { x: body.velocity.x, y: body.velocity.y };
                        state.angle = body.quaternion ? (2 * Math.acos(body.quaternion.w)) : 0;
                        state.angular_velocity = body.angularVelocity ? 
                            Math.sqrt(body.angularVelocity.x ** 2 + body.angularVelocity.y ** 2) : 0;
                        state.mass = body.mass || 1;
                        state.body_type = body.type === CANNON.Body.STATIC ? 'static' : 'dynamic';
                    }
                    // p2.js
                    else if (engine_type === 'p2.js' || (typeof p2 !== 'undefined' && body.position)) {
                        state.position = { x: body.position[0], y: body.position[1] };
                        state.velocity = { x: body.velocity[0], y: body.velocity[1] };
                        state.angle = body.angle || 0;
                        state.angular_velocity = body.angularVelocity || 0;
                        state.mass = body.mass || 1;
                        state.body_type = body.motionState === p2.Body.STATIC ? 'static' : 'dynamic';
                    }
                } catch (e) {
                    console.warn('[Physics Tracker] 序列化物理体失败:', e);
                }
                
                return state;
            }
            
            // 捕获世界状态
            function captureWorldState(world, engine_type) {
                const state = {
                    timestamp: Date.now(),
                    engine_type: engine_type,
                    bodies: [],
                    gravity: { x: 0, y: 0 },
                    time_scale: 1
                };
                
                try {
                    // Matter.js
                    if (engine_type === 'matter.js' && world.bodies) {
                        state.gravity = world.gravity || { x: 0, y: 1 };
                        state.time_scale = world.timing ? world.timing.timeScale : 1;
                        world.bodies.forEach(body => {
                            state.bodies.push(serializeBody(body, engine_type));
                        });
                    }
                    // Planck.js
                    else if (engine_type === 'planck.js' && world.getBodyList) {
                        state.gravity = world.getGravity ? world.getGravity() : { x: 0, y: -10 };
                        for (let body = world.getBodyList(); body; body = body.getNext()) {
                            state.bodies.push(serializeBody(body, engine_type));
                        }
                    }
                    // Cannon.js
                    else if (engine_type === 'cannon.js' && world.bodies) {
                        state.gravity = world.gravity ? { x: world.gravity.x, y: world.gravity.y } : { x: 0, y: -9.82 };
                        state.time_scale = world.timeStep || 1;
                        world.bodies.forEach(body => {
                            state.bodies.push(serializeBody(body, engine_type));
                        });
                    }
                    // p2.js
                    else if (engine_type === 'p2.js' && world.bodies) {
                        state.gravity = world.gravity ? { x: world.gravity[0], y: world.gravity[1] } : { x: 0, y: -9.82 };
                        state.time_scale = world.timeStep || 1;
                        world.bodies.forEach(body => {
                            state.bodies.push(serializeBody(body, engine_type));
                        });
                    }
                } catch (e) {
                    console.warn('[Physics Tracker] 捕获世界状态失败:', e);
                }
                
                return state;
            }
            
            // 拦截 Matter.js
            function interceptMatterJS() {
                if (typeof Matter === 'undefined' || !Matter.Engine) return false;
                
                console.log('[Physics Tracker] 拦截 Matter.js');
                window.__webthief_physics.engine_type = 'matter.js';
                
                const originalUpdate = Matter.Engine.update;
                Matter.Engine.update = function(engine, delta, correction) {
                    const result = originalUpdate.apply(this, arguments);
                    
                    if (window.__webthief_physics.is_tracking && engine.world) {
                        const now = Date.now();
                        if (now - window.__webthief_physics.last_capture_time >= window.__webthief_physics.capture_interval) {
                            const state = captureWorldState(engine.world, 'matter.js');
                            window.__webthief_physics.states.push(state);
                            window.__webthief_physics.last_capture_time = now;
                        }
                    }
                    
                    return result;
                };
                
                return true;
            }
            
            // 拦截 Planck.js
            function interceptPlanckJS() {
                if (typeof planck === 'undefined' || !planck.World) return false;
                
                console.log('[Physics Tracker] 拦截 Planck.js');
                window.__webthief_physics.engine_type = 'planck.js';
                
                const originalStep = planck.World.prototype.step;
                planck.World.prototype.step = function(dt, velocityIterations, positionIterations) {
                    const result = originalStep.apply(this, arguments);
                    
                    if (window.__webthief_physics.is_tracking) {
                        const now = Date.now();
                        if (now - window.__webthief_physics.last_capture_time >= window.__webthief_physics.capture_interval) {
                            const state = captureWorldState(this, 'planck.js');
                            window.__webthief_physics.states.push(state);
                            window.__webthief_physics.last_capture_time = now;
                        }
                    }
                    
                    return result;
                };
                
                return true;
            }
            
            // 拦截 Cannon.js
            function interceptCannonJS() {
                if (typeof CANNON === 'undefined' || !CANNON.World) return false;
                
                console.log('[Physics Tracker] 拦截 Cannon.js');
                window.__webthief_physics.engine_type = 'cannon.js';
                
                const originalStep = CANNON.World.prototype.step;
                CANNON.World.prototype.step = function(dt, timeSinceLastCalled, maxSubSteps) {
                    const result = originalStep.apply(this, arguments);
                    
                    if (window.__webthief_physics.is_tracking) {
                        const now = Date.now();
                        if (now - window.__webthief_physics.last_capture_time >= window.__webthief_physics.capture_interval) {
                            const state = captureWorldState(this, 'cannon.js');
                            window.__webthief_physics.states.push(state);
                            window.__webthief_physics.last_capture_time = now;
                        }
                    }
                    
                    return result;
                };
                
                return true;
            }
            
            // 拦截 p2.js
            function interceptP2JS() {
                if (typeof p2 === 'undefined' || !p2.World) return false;
                
                console.log('[Physics Tracker] 拦截 p2.js');
                window.__webthief_physics.engine_type = 'p2.js';
                
                const originalStep = p2.World.prototype.step;
                p2.World.prototype.step = function(dt, timeSinceLastCalled, maxSubSteps) {
                    const result = originalStep.apply(this, arguments);
                    
                    if (window.__webthief_physics.is_tracking) {
                        const now = Date.now();
                        if (now - window.__webthief_physics.last_capture_time >= window.__webthief_physics.capture_interval) {
                            const state = captureWorldState(this, 'p2.js');
                            window.__webthief_physics.states.push(state);
                            window.__webthief_physics.last_capture_time = now;
                        }
                    }
                    
                    return result;
                };
                
                return true;
            }
            
            // 尝试拦截所有支持的引擎
            function initInterception() {
                const results = {
                    matter: interceptMatterJS(),
                    planck: interceptPlanckJS(),
                    cannon: interceptCannonJS(),
                    p2: interceptP2JS()
                };
                
                const intercepted = Object.entries(results).filter(([k, v]) => v).map(([k, v]) => k);
                
                if (intercepted.length > 0) {
                    console.log('[Physics Tracker] 成功拦截:', intercepted.join(', '));
                } else {
                    console.log('[Physics Tracker] 未找到可拦截的物理引擎，将在 1 秒后重试...');
                    setTimeout(initInterception, 1000);
                }
            }
            
            // 延迟初始化，等待页面加载完成
            if (document.readyState === 'loading') {
                document.addEventListener('DOMContentLoaded', initInterception);
            } else {
                initInterception();
            }
            
            // 暴露控制接口
            window.__webthief_physics_control = {
                start: function(interval) {
                    window.__webthief_physics.is_tracking = true;
                    window.__webthief_physics.capture_interval = interval || 16;
                    window.__webthief_physics.last_capture_time = Date.now();
                    console.log('[Physics Tracker] 捕获已启动，间隔:', window.__webthief_physics.capture_interval + 'ms');
                },
                stop: function() {
                    window.__webthief_physics.is_tracking = false;
                    const states = window.__webthief_physics.states;
                    console.log('[Physics Tracker] 捕获已停止，共', states.length, '个状态');
                    return states;
                },
                clear: function() {
                    window.__webthief_physics.states = [];
                    console.log('[Physics Tracker] 状态已清空');
                },
                getStates: function() {
                    return window.__webthief_physics.states;
                },
                getLatestState: function() {
                    const states = window.__webthief_physics.states;
                    return states.length > 0 ? states[states.length - 1] : null;
                },
                setInterval: function(interval) {
                    window.__webthief_physics.capture_interval = interval;
                }
            };
            
            console.log('[Physics Tracker] 物理追踪层已加载');
        })();
        """

    async def start_capture(
        self,
        page: Page,
        duration: int | None = None,
        interval: int | None = None
    ) -> PhysicsCaptureSession | None:
        """
        开始捕获物理状态

        Args:
            page: Playwright Page 对象
            duration: 捕获持续时间（毫秒），默认使用配置值
            interval: 捕获间隔（毫秒），默认 16ms

        Returns:
            捕获会话对象
        """
        if not self.detected_engine:
            console.print("[red]  ✗ 未检测到物理引擎，无法开始捕获[/]")
            return None

        capture_interval = interval or self.capture_config["interval"]
        capture_duration = duration or self.capture_config["max_duration"]

        console.print(f"[cyan]  ▶️ 开始物理状态捕获 (间隔: {capture_interval}ms, 时长: {capture_duration}ms)...[/]")

        # 创建新会话
        session_id = f"physics_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(self.sessions)}"
        self.current_session = PhysicsCaptureSession(
            session_id=session_id,
            start_time=int(datetime.now().timestamp() * 1000),
            engine_type=self.detected_engine,
            capture_interval=capture_interval,
            is_active=True
        )
        self.sessions.append(self.current_session)
        self.is_capturing = True

        # 启动页面端捕获
        await page.evaluate(f"""
            () => {{
                if (window.__webthief_physics_control) {{
                    window.__webthief_physics_control.clear();
                    window.__webthief_physics_control.start({capture_interval});
                }} else {{
                    console.warn('[Physics Tracker] 控制接口未就绪');
                }}
            }}
        """)

        console.print("[green]  ✓ 物理状态捕获已启动[/]")

        return self.current_session

    async def capture_physics_state(self, page: Page) -> PhysicsWorldState | None:
        """
        捕获当前物理状态（单帧）

        Args:
            page: Playwright Page 对象

        Returns:
            当前物理世界状态
        """
        state_data = await page.evaluate("""
            () => {
                if (window.__webthief_physics_control) {
                    return window.__webthief_physics_control.getLatestState();
                }
                return null;
            }
        """)

        if state_data:
            bodies = [PhysicsBodyState.from_dict(b) for b in state_data.get("bodies", [])]
            state = PhysicsWorldState(
                timestamp=state_data.get("timestamp", int(datetime.now().timestamp() * 1000)),
                engine_type=self.detected_engine or PhysicsEngineType.UNKNOWN,
                bodies=bodies,
                gravity=state_data.get("gravity", {"x": 0, "y": 0}),
                time_scale=state_data.get("time_scale", 1.0)
            )
            return state

        return None

    async def stop_capture(self, page: Page) -> PhysicsCaptureSession | None:
        """
        停止捕获并返回会话数据

        Args:
            page: Playwright Page 对象

        Returns:
            捕获会话对象
        """
        if not self.is_capturing or not self.current_session:
            return None

        console.print("[cyan]  ⏹️ 停止物理状态捕获...[/]")

        # 获取捕获的状态数据
        states_data = await page.evaluate("""
            () => {
                if (window.__webthief_physics_control) {
                    return window.__webthief_physics_control.stop();
                }
                return [];
            }
        """)

        # 转换为状态对象
        for state_data in states_data:
            bodies = [PhysicsBodyState.from_dict(b) for b in state_data.get("bodies", [])]
            state = PhysicsWorldState(
                timestamp=state_data.get("timestamp", 0),
                engine_type=self.detected_engine or PhysicsEngineType.UNKNOWN,
                bodies=bodies,
                gravity=state_data.get("gravity", {"x": 0, "y": 0}),
                time_scale=state_data.get("time_scale", 1.0)
            )
            self.current_session.add_state(state)

        self.current_session.is_active = False
        self.is_capturing = False

        console.print(f"[green]  ✓ 捕获完成，共 {len(self.current_session.states)} 个状态快照[/]")

        return self.current_session

    def generate_static_representation(
        self,
        session: PhysicsCaptureSession | None = None,
        output_format: str = "canvas"
    ) -> str:
        """
        生成物理模拟的静态表示
        将动态物理转换为静态 CSS 或 Canvas

        Args:
            session: 捕获会话，如果为 None 则使用当前会话
            output_format: 输出格式，"canvas" 或 "css"

        Returns:
            静态表示的 JavaScript/HTML 代码
        """
        target_session = session or self.current_session

        if not target_session or not target_session.states:
            console.print("[yellow]  ⚠️ 没有捕获数据可供生成静态表示[/]")
            return ""

        console.print(f"[cyan]  🎨 生成静态表示 (格式: {output_format})...[/]")

        if output_format == "canvas":
            return self._generate_canvas_representation(target_session)
        elif output_format == "css":
            return self._generate_css_representation(target_session)
        else:
            console.print(f"[red]  ✗ 不支持的输出格式: {output_format}[/]")
            return ""

    def _generate_canvas_representation(self, session: PhysicsCaptureSession) -> str:
        """生成 Canvas 静态表示"""
        states_data = json.dumps([s.to_dict() for s in session.states], ensure_ascii=False)

        script = f"""
        (function() {{
            'use strict';
            // ━━━ WebThief Physics Static Canvas Representation ━━━
            
            const PHYSICS_STATES = {states_data};
            const FPS = 60;
            
            // 创建 Canvas 容器
            function createCanvas() {{
                const canvas = document.createElement('canvas');
                canvas.id = 'webthief-physics-canvas';
                canvas.width = window.innerWidth;
                canvas.height = window.innerHeight;
                canvas.style.cssText = `
                    position: fixed;
                    top: 0;
                    left: 0;
                    width: 100%;
                    height: 100%;
                    pointer-events: none;
                    z-index: 999998;
                `;
                document.body.appendChild(canvas);
                return canvas;
            }}
            
            // 绘制物理体
            function drawBody(ctx, body) {{
                ctx.save();
                
                // 设置样式
                ctx.fillStyle = 'rgba(100, 150, 255, 0.6)';
                ctx.strokeStyle = 'rgba(50, 100, 200, 0.8)';
                ctx.lineWidth = 2;
                
                // 应用变换
                ctx.translate(body.position.x, body.position.y);
                ctx.rotate(body.angle);
                
                // 绘制顶点
                if (body.vertices && body.vertices.length > 0) {{
                    ctx.beginPath();
                    ctx.moveTo(body.vertices[0].x - body.position.x, body.vertices[0].y - body.position.y);
                    for (let i = 1; i < body.vertices.length; i++) {{
                        ctx.lineTo(body.vertices[i].x - body.position.x, body.vertices[i].y - body.position.y);
                    }}
                    ctx.closePath();
                    ctx.fill();
                    ctx.stroke();
                }} else if (body.bounds) {{
                    // 使用边界框绘制
                    const width = body.bounds.max.x - body.bounds.min.x;
                    const height = body.bounds.max.y - body.bounds.min.y;
                    ctx.fillRect(-width/2, -height/2, width, height);
                    ctx.strokeRect(-width/2, -height/2, width, height);
                }} else {{
                    // 绘制圆形占位
                    ctx.beginPath();
                    ctx.arc(0, 0, 20, 0, Math.PI * 2);
                    ctx.fill();
                    ctx.stroke();
                }}
                
                // 绘制方向指示
                ctx.strokeStyle = 'rgba(255, 100, 100, 0.8)';
                ctx.lineWidth = 2;
                ctx.beginPath();
                ctx.moveTo(0, 0);
                ctx.lineTo(25, 0);
                ctx.stroke();
                
                ctx.restore();
            }}
            
            // 绘制单帧状态
            function drawState(ctx, state) {{
                ctx.clearRect(0, 0, ctx.canvas.width, ctx.canvas.height);
                
                // 绘制背景
                ctx.fillStyle = 'rgba(240, 240, 240, 0.1)';
                ctx.fillRect(0, 0, ctx.canvas.width, ctx.canvas.height);
                
                // 绘制所有物理体
                if (state.bodies) {{
                    state.bodies.forEach(body => drawBody(ctx, body));
                }}
                
                // 绘制信息
                ctx.fillStyle = 'rgba(0, 0, 0, 0.7)';
                ctx.font = '14px monospace';
                ctx.fillText(`Bodies: ${{state.bodies ? state.bodies.length : 0}}`, 10, 20);
                ctx.fillText(`Time: ${{state.timestamp}}`, 10, 40);
            }}
            
            // 播放状态序列
            async function playStates(canvas) {{
                const ctx = canvas.getContext('2d');
                const states = PHYSICS_STATES;
                
                if (!states || states.length === 0) {{
                    console.warn('[Physics Static] 没有状态数据');
                    return;
                }}
                
                console.log('[Physics Static] 开始播放，共', states.length, '帧');
                
                let frameIndex = 0;
                
                function render() {{
                    if (frameIndex >= states.length) {{
                        frameIndex = 0;  // 循环播放
                    }}
                    
                    drawState(ctx, states[frameIndex]);
                    frameIndex++;
                    
                    setTimeout(() => requestAnimationFrame(render), 1000 / FPS);
                }}
                
                render();
            }}
            
            // 生成静态快照（单帧）
            function generateSnapshot(frameIndex = 0) {{
                const canvas = createCanvas();
                const ctx = canvas.getContext('2d');
                
                if (PHYSICS_STATES && PHYSICS_STATES.length > frameIndex) {{
                    drawState(ctx, PHYSICS_STATES[frameIndex]);
                }}
                
                // 转换为图片
                const dataUrl = canvas.toDataURL('image/png');
                console.log('[Physics Static] 快照已生成');
                
                return dataUrl;
            }}
            
            // 初始化
            function init() {{
                const canvas = createCanvas();
                
                // 启动播放
                playStates(canvas);
                
                // 暴露控制接口
                window.__webthief_physics_static = {{
                    canvas: canvas,
                    play: () => playStates(canvas),
                    snapshot: generateSnapshot,
                    getStates: () => PHYSICS_STATES
                }};
                
                console.log('[Physics Static] Canvas 静态表示已创建');
            }}
            
            // 启动
            if (document.readyState === 'loading') {{
                document.addEventListener('DOMContentLoaded', init);
            }} else {{
                init();
            }}
        }})();
        """

        console.print(f"[green]  ✓ 已生成 Canvas 静态表示 ({len(session.states)} 帧)[/]")
        return script

    def _generate_css_representation(self, session: PhysicsCaptureSession) -> str:
        """生成 CSS 静态表示"""
        if not session.states:
            return ""

        # 使用最后一帧作为静态表示
        final_state = session.states[-1]

        css_rules = []
        html_elements = []

        for i, body in enumerate(final_state.bodies):
            body_id = f"physics-body-{i}"
            pos = body.position
            angle = body.angle

            # 生成 CSS
            css_rules.append(f"""
            #{body_id} {{
                position: absolute;
                left: {pos['x']}px;
                top: {pos['y']}px;
                transform: translate(-50%, -50%) rotate({angle}rad);
                width: 40px;
                height: 40px;
                background: rgba(100, 150, 255, 0.6);
                border: 2px solid rgba(50, 100, 200, 0.8);
                border-radius: 4px;
                pointer-events: none;
                z-index: 999998;
            }}
            """)

            html_elements.append(f'<div id="{body_id}"></div>')

        html = f"""
        <!-- WebThief Physics Static CSS Representation -->
        <style>
            #webthief-physics-container {{
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                pointer-events: none;
                z-index: 999998;
            }}
            {' '.join(css_rules)}
        </style>
        <div id="webthief-physics-container">
            {' '.join(html_elements)}
        </div>
        """

        console.print(f"[green]  ✓ 已生成 CSS 静态表示 ({len(final_state.bodies)} 个物理体)[/]")
        return html

    async def get_physics_report(self, page: Page | None = None) -> dict[str, Any]:
        """
        获取物理引擎报告

        Args:
            page: 可选的 Playwright Page 对象

        Returns:
            物理引擎报告字典
        """
        report: dict[str, Any] = {
            "detection": {
                "engine_detected": self.detected_engine is not None,
                "engine_type": self.detected_engine.value if self.detected_engine else None,
                "detection_time": datetime.now().isoformat()
            },
            "capture": {
                "is_capturing": self.is_capturing,
                "total_sessions": len(self.sessions),
                "capture_config": self.capture_config
            },
            "sessions": []
        }

        # 添加会话信息
        for session in self.sessions:
            session_info = {
                "session_id": session.session_id,
                "engine_type": session.engine_type.value,
                "state_count": len(session.states),
                "duration_ms": session.get_duration(),
                "is_active": session.is_active
            }

            # 添加统计信息
            if session.states:
                total_bodies = sum(len(s.bodies) for s in session.states)
                avg_bodies = total_bodies / len(session.states)
                session_info["statistics"] = {
                    "average_bodies": round(avg_bodies, 2),
                    "max_bodies": max(len(s.bodies) for s in session.states),
                    "min_bodies": min(len(s.bodies) for s in session.states)
                }

            report["sessions"].append(session_info)

        # 如果提供了 page，获取实时状态
        if page:
            try:
                latest_state = await self.capture_physics_state(page)
                if latest_state:
                    report["realtime"] = {
                        "timestamp": latest_state.timestamp,
                        "body_count": len(latest_state.bodies),
                        "gravity": latest_state.gravity,
                        "time_scale": latest_state.time_scale
                    }
            except Exception as e:
                report["realtime_error"] = str(e)

        return report

    def export_session(
        self,
        session: PhysicsCaptureSession | None = None,
        output_path: str | None = None
    ) -> dict[str, Any]:
        """
        导出会话数据到文件

        Args:
            session: 要导出的会话，如果为 None 则导出当前会话
            output_path: 输出文件路径

        Returns:
            导出的数据字典
        """
        target_session = session or self.current_session

        if not target_session:
            console.print("[yellow]  ⚠️ 没有可导出的会话[/]")
            return {}

        export_data = {
            "version": "1.0.0",
            "export_time": datetime.now().isoformat(),
            "session": target_session.to_dict()
        }

        if output_path:
            import os
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)

            console.print(f"[green]  ✓ 会话数据已导出: {output_path}[/]")

        return export_data

    def clear_sessions(self) -> None:
        """清空所有会话数据"""
        self.sessions = []
        self.current_session = None
        self.is_capturing = False
        console.print("[cyan]  🗑️ 所有会话数据已清空[/]")
