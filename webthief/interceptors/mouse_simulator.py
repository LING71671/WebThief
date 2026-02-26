"""
鼠标轨迹模拟与回放模块
目标：生成自然的人类鼠标移动轨迹，记录和回放鼠标事件序列
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from playwright.async_api import Page
from rich.console import Console

console = Console()


class TrajectoryType(Enum):
    """轨迹类型枚举"""
    STRAIGHT = "straight"       # 直线
    BEZIER = "bezier"          # 贝塞尔曲线
    RANDOM = "random"          # 随机轨迹
    HUMAN_LIKE = "human_like"  # 拟人化轨迹


class MouseEventType(Enum):
    """鼠标事件类型枚举"""
    MOVE = "mousemove"
    ENTER = "mouseenter"
    LEAVE = "mouseleave"
    DOWN = "mousedown"
    UP = "mouseup"
    CLICK = "click"


@dataclass
class Point:
    """坐标点"""
    x: float
    y: float

    def __add__(self, other: Point) -> Point:
        return Point(self.x + other.x, self.y + other.y)

    def __sub__(self, other: Point) -> Point:
        return Point(self.x - other.x, self.y - other.y)

    def __mul__(self, scalar: float) -> Point:
        return Point(self.x * scalar, self.y * scalar)

    def distance_to(self, other: Point) -> float:
        """计算到另一点的距离"""
        return math.sqrt((self.x - other.x) ** 2 + (self.y - other.y) ** 2)


@dataclass
class MouseEvent:
    """鼠标事件记录"""
    event_type: MouseEventType
    point: Point
    timestamp: int
    target_selector: str | None = None
    button: int = 0
    modifiers: dict[str, bool] = field(default_factory=dict)


@dataclass
class MouseTrajectory:
    """
    鼠标轨迹数据结构
    包含坐标点序列、时间戳、事件类型
    """
    points: list[Point] = field(default_factory=list)
    timestamps: list[int] = field(default_factory=list)
    events: list[MouseEvent] = field(default_factory=list)
    trajectory_type: TrajectoryType = TrajectoryType.HUMAN_LIKE
    metadata: dict[str, Any] = field(default_factory=dict)

    def add_point(self, point: Point, timestamp: int | None = None) -> None:
        """添加轨迹点"""
        self.points.append(point)
        self.timestamps.append(timestamp or self._get_current_time())

    def add_event(self, event: MouseEvent) -> None:
        """添加鼠标事件"""
        self.events.append(event)

    def get_duration(self) -> int:
        """获取轨迹总时长（毫秒）"""
        if len(self.timestamps) < 2:
            return 0
        return self.timestamps[-1] - self.timestamps[0]

    def get_total_distance(self) -> float:
        """获取轨迹总距离"""
        total_distance = 0.0
        for i in range(1, len(self.points)):
            total_distance += self.points[i - 1].distance_to(self.points[i])
        return total_distance

    def _get_current_time(self) -> int:
        """获取当前时间戳（毫秒）"""
        import time
        return int(time.time() * 1000)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式"""
        return {
            "points": [{"x": p.x, "y": p.y} for p in self.points],
            "timestamps": self.timestamps,
            "events": [
                {
                    "type": e.event_type.value,
                    "x": e.point.x,
                    "y": e.point.y,
                    "timestamp": e.timestamp,
                    "target": e.target_selector,
                    "button": e.button
                }
                for e in self.events
            ],
            "trajectory_type": self.trajectory_type.value,
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MouseTrajectory:
        """从字典创建轨迹对象"""
        trajectory = cls(
            trajectory_type=TrajectoryType(data.get("trajectory_type", "human_like")),
            metadata=data.get("metadata", {})
        )

        for p in data.get("points", []):
            trajectory.points.append(Point(p["x"], p["y"]))

        trajectory.timestamps = data.get("timestamps", [])

        for e in data.get("events", []):
            event = MouseEvent(
                event_type=MouseEventType(e["type"]),
                point=Point(e["x"], e["y"]),
                timestamp=e["timestamp"],
                target_selector=e.get("target"),
                button=e.get("button", 0)
            )
            trajectory.events.append(event)

        return trajectory


class MouseSimulator:
    """
    鼠标模拟器
    负责：
    1. 生成自然的鼠标移动轨迹
    2. 记录鼠标事件序列
    3. 生成轨迹回放 JavaScript 脚本
    4. 集成到拦截器系统
    """

    # 默认配置参数
    DEFAULT_MIN_STEPS = 10
    DEFAULT_MAX_STEPS = 30
    DEFAULT_MIN_DELAY = 10
    DEFAULT_MAX_DELAY = 50
    DEFAULT_NOISE_FACTOR = 0.3

    def __init__(self):
        self.recorded_trajectories: list[MouseTrajectory] = []
        self.current_recording: MouseTrajectory | None = None
        self.is_recording = False

    def generate_trajectory(
        self,
        start: Point,
        end: Point,
        trajectory_type: TrajectoryType = TrajectoryType.HUMAN_LIKE,
        **kwargs: Any
    ) -> MouseTrajectory:
        """
        生成鼠标移动轨迹

        Args:
            start: 起始点
            end: 结束点
            trajectory_type: 轨迹类型
            **kwargs: 额外参数
                - steps: 轨迹步数
                - min_delay: 最小延迟（毫秒）
                - max_delay: 最大延迟（毫秒）
                - noise_factor: 噪声因子（0-1）
                - control_points: 贝塞尔曲线控制点

        Returns:
            MouseTrajectory: 生成的轨迹对象
        """
        if trajectory_type == TrajectoryType.STRAIGHT:
            return self._generate_straight_trajectory(start, end, **kwargs)
        elif trajectory_type == TrajectoryType.BEZIER:
            return self._generate_bezier_trajectory(start, end, **kwargs)
        elif trajectory_type == TrajectoryType.RANDOM:
            return self._generate_random_trajectory(start, end, **kwargs)
        else:
            return self._generate_human_like_trajectory(start, end, **kwargs)

    def _generate_straight_trajectory(
        self,
        start: Point,
        end: Point,
        **kwargs: Any
    ) -> MouseTrajectory:
        """生成直线轨迹"""
        steps = kwargs.get("steps", self.DEFAULT_MIN_STEPS)
        min_delay = kwargs.get("min_delay", self.DEFAULT_MIN_DELAY)
        max_delay = kwargs.get("max_delay", self.DEFAULT_MAX_DELAY)

        trajectory = MouseTrajectory(trajectory_type=TrajectoryType.STRAIGHT)
        current_time = self._get_current_time()

        for i in range(steps + 1):
            t = i / steps
            point = Point(
                start.x + (end.x - start.x) * t,
                start.y + (end.y - start.y) * t
            )
            delay = random.randint(min_delay, max_delay)
            current_time += delay
            trajectory.add_point(point, current_time)

        return trajectory

    def _generate_bezier_trajectory(
        self,
        start: Point,
        end: Point,
        **kwargs: Any
    ) -> MouseTrajectory:
        """生成贝塞尔曲线轨迹"""
        steps = kwargs.get("steps", self.DEFAULT_MAX_STEPS)
        min_delay = kwargs.get("min_delay", self.DEFAULT_MIN_DELAY)
        max_delay = kwargs.get("max_delay", self.DEFAULT_MAX_DELAY)
        control_points = kwargs.get("control_points", None)

        # 自动生成控制点
        if control_points is None:
            mid_x = (start.x + end.x) / 2
            mid_y = (start.y + end.y) / 2
            offset_x = random.uniform(-100, 100)
            offset_y = random.uniform(-100, 100)
            control_points = [
                Point(mid_x + offset_x, start.y),
                Point(mid_x, end.y + offset_y)
            ]

        trajectory = MouseTrajectory(trajectory_type=TrajectoryType.BEZIER)
        current_time = self._get_current_time()

        for i in range(steps + 1):
            t = i / steps
            # 三次贝塞尔曲线
            p0, p1, p2, p3 = start, control_points[0], control_points[1], end
            point = self._cubic_bezier(t, p0, p1, p2, p3)
            delay = random.randint(min_delay, max_delay)
            current_time += delay
            trajectory.add_point(point, current_time)

        return trajectory

    def _generate_random_trajectory(
        self,
        start: Point,
        end: Point,
        **kwargs: Any
    ) -> MouseTrajectory:
        """生成随机轨迹"""
        steps = kwargs.get("steps", random.randint(15, 40))
        min_delay = kwargs.get("min_delay", self.DEFAULT_MIN_DELAY)
        max_delay = kwargs.get("max_delay", self.DEFAULT_MAX_DELAY)
        noise_factor = kwargs.get("noise_factor", self.DEFAULT_NOISE_FACTOR)

        trajectory = MouseTrajectory(trajectory_type=TrajectoryType.RANDOM)
        current_time = self._get_current_time()

        # 生成随机路径点
        waypoints = [start]
        num_waypoints = random.randint(2, 5)

        for i in range(num_waypoints):
            t = (i + 1) / (num_waypoints + 1)
            base_x = start.x + (end.x - start.x) * t
            base_y = start.y + (end.y - start.y) * t
            noise_x = random.uniform(-50, 50) * noise_factor
            noise_y = random.uniform(-50, 50) * noise_factor
            waypoints.append(Point(base_x + noise_x, base_y + noise_y))

        waypoints.append(end)

        # 在路径点之间插值
        points_per_segment = steps // (len(waypoints) - 1)

        for i in range(len(waypoints) - 1):
            for j in range(points_per_segment):
                t = j / points_per_segment
                point = Point(
                    waypoints[i].x + (waypoints[i + 1].x - waypoints[i].x) * t,
                    waypoints[i].y + (waypoints[i + 1].y - waypoints[i].y) * t
                )
                delay = random.randint(min_delay, max_delay)
                current_time += delay
                trajectory.add_point(point, current_time)

        trajectory.add_point(end, current_time + random.randint(min_delay, max_delay))
        return trajectory

    def _generate_human_like_trajectory(
        self,
        start: Point,
        end: Point,
        **kwargs: Any
    ) -> MouseTrajectory:
        """
        生成拟人化轨迹
        模拟真实人类鼠标移动：
        1. 起始慢（加速）
        2. 中间快
        3. 结束慢（减速）
        4. 添加轻微抖动
        """
        steps = kwargs.get("steps", random.randint(self.DEFAULT_MIN_STEPS, self.DEFAULT_MAX_STEPS))
        min_delay = kwargs.get("min_delay", self.DEFAULT_MIN_DELAY)
        max_delay = kwargs.get("max_delay", self.DEFAULT_MAX_DELAY)

        trajectory = MouseTrajectory(trajectory_type=TrajectoryType.HUMAN_LIKE)
        current_time = self._get_current_time()

        # 计算距离和方向
        distance = start.distance_to(end)
        angle = math.atan2(end.y - start.y, end.x - start.x)

        # 添加轻微曲线偏移（人类不会完全直线移动）
        curve_offset = random.uniform(-30, 30)

        for i in range(steps + 1):
            t = i / steps

            # 使用缓动函数模拟加速和减速
            eased_t = self._ease_in_out_cubic(t)

            # 基础位置
            base_x = start.x + (end.x - start.x) * eased_t
            base_y = start.y + (end.y - start.y) * eased_t

            # 添加曲线偏移（中间最大，两端为0）
            curve_factor = math.sin(t * math.pi)
            offset_x = -math.sin(angle) * curve_offset * curve_factor
            offset_y = math.cos(angle) * curve_offset * curve_factor

            # 添加微小抖动（模拟手部抖动）
            jitter_x = random.uniform(-2, 2) * (1 - t * 0.5)  # 越接近目标抖动越小
            jitter_y = random.uniform(-2, 2) * (1 - t * 0.5)

            point = Point(base_x + offset_x + jitter_x, base_y + offset_y + jitter_y)

            # 动态延迟：起始和结束慢，中间快
            if t < 0.2 or t > 0.8:
                delay = random.randint(max_delay - 10, max_delay + 10)
            else:
                delay = random.randint(min_delay, max_delay)

            current_time += delay
            trajectory.add_point(point, current_time)

        return trajectory

    def _cubic_bezier(self, t: float, p0: Point, p1: Point, p2: Point, p3: Point) -> Point:
        """计算三次贝塞尔曲线点"""
        u = 1 - t
        return Point(
            u ** 3 * p0.x + 3 * u ** 2 * t * p1.x + 3 * u * t ** 2 * p2.x + t ** 3 * p3.x,
            u ** 3 * p0.y + 3 * u ** 2 * t * p1.y + 3 * u * t ** 2 * p2.y + t ** 3 * p3.y
        )

    def _ease_in_out_cubic(self, t: float) -> float:
        """三次缓动函数"""
        if t < 0.5:
            return 4 * t * t * t
        else:
            return 1 - pow(-2 * t + 2, 3) / 2

    def _get_current_time(self) -> int:
        """获取当前时间戳（毫秒）"""
        import time
        return int(time.time() * 1000)

    async def start_recording(self, page: Page) -> None:
        """
        开始记录鼠标事件
        """
        console.print("[cyan]  🖱️  开始记录鼠标事件...[/]")

        self.current_recording = MouseTrajectory()
        self.is_recording = True

        recording_script = """
        (function() {
            'use strict';
            // ━━━ WebThief Mouse Event Recorder ━━━
            
            window.__webthief_mouse_events = [];
            window.__webthief_is_recording = true;
            
            function recordEvent(type, event) {
                if (!window.__webthief_is_recording) return;
                
                const target = event.target;
                const targetSelector = target ? 
                    (target.id ? '#' + target.id : 
                     target.className ? '.' + target.className.split(' ')[0] : 
                     target.tagName.toLowerCase()) : null;
                
                window.__webthief_mouse_events.push({
                    type: type,
                    x: event.clientX,
                    y: event.clientY,
                    timestamp: Date.now(),
                    target: targetSelector,
                    button: event.button,
                    modifiers: {
                        ctrl: event.ctrlKey,
                        shift: event.shiftKey,
                        alt: event.altKey,
                        meta: event.metaKey
                    }
                });
            }
            
            // 监听鼠标移动
            document.addEventListener('mousemove', function(e) {
                // 节流：每 50ms 记录一次
                if (!window.__webthief_last_move_time || 
                    Date.now() - window.__webthief_last_move_time > 50) {
                    recordEvent('mousemove', e);
                    window.__webthief_last_move_time = Date.now();
                }
            }, true);
            
            // 监听鼠标进入
            document.addEventListener('mouseenter', function(e) {
                recordEvent('mouseenter', e);
            }, true);
            
            // 监听鼠标离开
            document.addEventListener('mouseleave', function(e) {
                recordEvent('mouseleave', e);
            }, true);
            
            // 监听鼠标按下
            document.addEventListener('mousedown', function(e) {
                recordEvent('mousedown', e);
            }, true);
            
            // 监听鼠标释放
            document.addEventListener('mouseup', function(e) {
                recordEvent('mouseup', e);
            }, true);
            
            // 监听点击
            document.addEventListener('click', function(e) {
                recordEvent('click', e);
            }, true);
            
            console.log('[WebThief Mouse] 鼠标事件记录器已激活');
        })();
        """

        await page.add_init_script(recording_script)
        console.print("[green]  ✓ 鼠标事件记录器已注入[/]")

    async def stop_recording(self, page: Page) -> MouseTrajectory | None:
        """
        停止记录并返回轨迹数据
        """
        if not self.is_recording:
            return None

        console.print("[cyan]  🛑 停止记录鼠标事件...[/]")

        events_data = await page.evaluate("""
            () => {
                window.__webthief_is_recording = false;
                return window.__webthief_mouse_events || [];
            }
        """)

        trajectory = MouseTrajectory()

        for event_data in events_data:
            event = MouseEvent(
                event_type=MouseEventType(event_data["type"]),
                point=Point(event_data["x"], event_data["y"]),
                timestamp=event_data["timestamp"],
                target_selector=event_data.get("target"),
                button=event_data.get("button", 0),
                modifiers=event_data.get("modifiers", {})
            )
            trajectory.add_event(event)
            trajectory.add_point(event.point, event.timestamp)

        self.recorded_trajectories.append(trajectory)
        self.is_recording = False
        self.current_recording = None

        console.print(f"[green]  ✓ 记录了 {len(trajectory.events)} 个鼠标事件[/]")

        return trajectory

    def generate_replay_script(self, trajectory: MouseTrajectory) -> str:
        """
        生成鼠标轨迹回放 JavaScript 脚本
        """
        events_js = []

        for event in trajectory.events:
            events_js.append({
                "type": event.event_type.value,
                "x": event.point.x,
                "y": event.point.y,
                "timestamp": event.timestamp,
                "target": event.target_selector,
                "button": event.button,
                "modifiers": event.modifiers
            })

        script = f"""
        (function() {{
            'use strict';
            // ━━━ WebThief Mouse Trajectory Replay ━━━
            
            const events = {events_js};
            
            // 创建虚拟鼠标光标
            function createVirtualCursor() {{
                const cursor = document.createElement('div');
                cursor.id = 'webthief-virtual-cursor';
                cursor.style.cssText = `
                    position: fixed;
                    width: 20px;
                    height: 20px;
                    border: 2px solid #ff0000;
                    border-radius: 50%;
                    pointer-events: none;
                    z-index: 999999;
                    transition: none;
                    box-shadow: 0 0 10px rgba(255, 0, 0, 0.5);
                `;
                document.body.appendChild(cursor);
                return cursor;
            }}
            
            // 触发鼠标事件
            function dispatchMouseEvent(eventData, cursor) {{
                const element = document.elementFromPoint(eventData.x, eventData.y);
                
                const eventInit = {{
                    bubbles: true,
                    cancelable: true,
                    clientX: eventData.x,
                    clientY: eventData.y,
                    screenX: eventData.x + window.screenX,
                    screenY: eventData.y + window.screenY,
                    button: eventData.button,
                    ctrlKey: eventData.modifiers?.ctrl || false,
                    shiftKey: eventData.modifiers?.shift || false,
                    altKey: eventData.modifiers?.alt || false,
                    metaKey: eventData.modifiers?.meta || false,
                    view: window
                }};
                
                let event;
                switch(eventData.type) {{
                    case 'mousemove':
                        event = new MouseEvent('mousemove', eventInit);
                        break;
                    case 'mouseenter':
                        event = new MouseEvent('mouseenter', eventInit);
                        break;
                    case 'mouseleave':
                        event = new MouseEvent('mouseleave', eventInit);
                        break;
                    case 'mousedown':
                        event = new MouseEvent('mousedown', eventInit);
                        break;
                    case 'mouseup':
                        event = new MouseEvent('mouseup', eventInit);
                        break;
                    case 'click':
                        event = new MouseEvent('click', eventInit);
                        break;
                    default:
                        event = new MouseEvent(eventData.type, eventInit);
                }}
                
                const target = element || document.body;
                target.dispatchEvent(event);
                
                // 更新虚拟光标位置
                if (cursor) {{
                    cursor.style.left = (eventData.x - 10) + 'px';
                    cursor.style.top = (eventData.y - 10) + 'px';
                }}
            }}
            
            // 回放轨迹
            async function replayTrajectory() {{
                console.log('[WebThief Mouse] 开始回放鼠标轨迹');
                
                const cursor = createVirtualCursor();
                let lastTimestamp = events.length > 0 ? events[0].timestamp : 0;
                
                for (const eventData of events) {{
                    const delay = eventData.timestamp - lastTimestamp;
                    
                    if (delay > 0) {{
                        await new Promise(resolve => setTimeout(resolve, delay));
                    }}
                    
                    dispatchMouseEvent(eventData, cursor);
                    lastTimestamp = eventData.timestamp;
                }}
                
                console.log('[WebThief Mouse] 轨迹回放完成');
                
                // 3秒后移除虚拟光标
                setTimeout(() => {{
                    cursor.remove();
                }}, 3000);
            }}
            
            // 立即开始回放
            replayTrajectory();
            
            // 导出回放控制函数
            window.__webthief_mouse_replay = {{
                replay: replayTrajectory,
                getEvents: () => events
            }};
        }})();
        """

        return script

    def generate_trajectory_replay_script(
        self,
        trajectory: MouseTrajectory,
        show_cursor: bool = True
    ) -> str:
        """
        生成平滑轨迹回放脚本（基于轨迹点而非事件）
        """
        points_js = [{"x": p.x, "y": p.y} for p in trajectory.points]
        timestamps_js = trajectory.timestamps

        script = f"""
        (function() {{
            'use strict';
            // ━━━ WebThief Smooth Trajectory Replay ━━━
            
            const points = {points_js};
            const timestamps = {timestamps_js};
            const showCursor = {str(show_cursor).lower()};
            
            let cursor = null;
            
            // 创建虚拟光标
            function createCursor() {{
                if (!showCursor) return null;
                
                const el = document.createElement('div');
                el.id = 'webthief-trajectory-cursor';
                el.style.cssText = `
                    position: fixed;
                    width: 12px;
                    height: 12px;
                    background: radial-gradient(circle, #ff4444, #cc0000);
                    border: 2px solid #fff;
                    border-radius: 50%;
                    pointer-events: none;
                    z-index: 999999;
                    box-shadow: 0 0 15px rgba(255, 68, 68, 0.6);
                    transform: translate(-50%, -50%);
                `;
                document.body.appendChild(el);
                return el;
            }}
            
            // 平滑移动到指定点
            function moveTo(x, y) {{
                if (cursor) {{
                    cursor.style.left = x + 'px';
                    cursor.style.top = y + 'px';
                }}
                
                // 触发鼠标移动事件
                const element = document.elementFromPoint(x, y);
                if (element) {{
                    const event = new MouseEvent('mousemove', {{
                        bubbles: true,
                        cancelable: true,
                        clientX: x,
                        clientY: y,
                        screenX: x + window.screenX,
                        screenY: y + window.screenY,
                        view: window
                    }});
                    element.dispatchEvent(event);
                }}
            }}
            
            // 回放轨迹
            async function replay() {{
                console.log('[WebThief] 开始轨迹回放，共 ' + points.length + ' 个点');
                
                cursor = createCursor();
                
                for (let i = 0; i < points.length; i++) {{
                    const point = points[i];
                    const timestamp = timestamps[i];
                    
                    moveTo(point.x, point.y);
                    
                    // 计算到下一个点的延迟
                    if (i < points.length - 1) {{
                        const nextTimestamp = timestamps[i + 1];
                        const delay = nextTimestamp - timestamp;
                        if (delay > 0) {{
                            await new Promise(resolve => setTimeout(resolve, delay));
                        }}
                    }}
                }}
                
                console.log('[WebThief] 轨迹回放完成');
                
                // 清理
                setTimeout(() => {{
                    if (cursor) cursor.remove();
                }}, 2000);
            }}
            
            // 启动回放
            replay();
            
            // 导出控制接口
            window.__webthief_trajectory_replay = {{
                replay: replay,
                stop: () => {{ if (cursor) cursor.remove(); }}
            }};
        }})();
        """

        return script

    async def simulate_mouse_movement(
        self,
        page: Page,
        start: Point,
        end: Point,
        trajectory_type: TrajectoryType = TrajectoryType.HUMAN_LIKE
    ) -> None:
        """
        在页面上模拟鼠标移动
        """
        trajectory = self.generate_trajectory(start, end, trajectory_type)
        replay_script = self.generate_trajectory_replay_script(trajectory)

        await page.evaluate(replay_script)
        console.print(f"[green]  ✓ 鼠标移动模拟完成: ({start.x}, {start.y}) -> ({end.x}, {end.y})[/]")

    def get_statistics(self, trajectory: MouseTrajectory) -> dict[str, Any]:
        """
        获取轨迹统计信息
        """
        if not trajectory.points:
            return {}

        durations = []
        for i in range(1, len(trajectory.timestamps)):
            durations.append(trajectory.timestamps[i] - trajectory.timestamps[i - 1])

        avg_delay = sum(durations) / len(durations) if durations else 0

        return {
            "total_points": len(trajectory.points),
            "total_events": len(trajectory.events),
            "total_duration_ms": trajectory.get_duration(),
            "total_distance_px": round(trajectory.get_total_distance(), 2),
            "average_delay_ms": round(avg_delay, 2),
            "trajectory_type": trajectory.trajectory_type.value,
            "start_point": {"x": trajectory.points[0].x, "y": trajectory.points[0].y},
            "end_point": {"x": trajectory.points[-1].x, "y": trajectory.points[-1].y}
        }
