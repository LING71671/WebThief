"""
Pointer 事件拦截与回放模块
目标：捕获 pointer 事件（鼠标、触摸、触控笔），记录坐标、压力、倾斜等数据，生成回放脚本
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from playwright.async_api import Page
from rich.console import Console

console = Console()


@dataclass
class PointerEventData:
    """
    Pointer 事件数据
    存储单个 pointer 事件的完整信息
    """

    event_type: str
    x: float
    y: float
    pressure: float = 0.5
    tilt_x: float = 0.0
    tilt_y: float = 0.0
    pointer_type: str = "mouse"
    pointer_id: int = 0
    is_primary: bool = True
    button: int = 0
    buttons: int = 0
    timestamp: float = field(default_factory=lambda: 0.0)
    target_selector: str = ""

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式"""
        return {
            "event_type": self.event_type,
            "x": self.x,
            "y": self.y,
            "pressure": self.pressure,
            "tilt_x": self.tilt_x,
            "tilt_y": self.tilt_y,
            "pointer_type": self.pointer_type,
            "pointer_id": self.pointer_id,
            "is_primary": self.is_primary,
            "button": self.button,
            "buttons": self.buttons,
            "timestamp": self.timestamp,
            "target_selector": self.target_selector,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PointerEventData":
        """从字典创建实例"""
        return cls(
            event_type=data.get("event_type", ""),
            x=data.get("x", 0.0),
            y=data.get("y", 0.0),
            pressure=data.get("pressure", 0.5),
            tilt_x=data.get("tilt_x", 0.0),
            tilt_y=data.get("tilt_y", 0.0),
            pointer_type=data.get("pointer_type", "mouse"),
            pointer_id=data.get("pointer_id", 0),
            is_primary=data.get("is_primary", True),
            button=data.get("button", 0),
            buttons=data.get("buttons", 0),
            timestamp=data.get("timestamp", 0.0),
            target_selector=data.get("target_selector", ""),
        )


class PointerInterceptor:
    """
    Pointer 事件拦截器
    负责：
    1. 拦截 pointermove、pointerenter、pointerleave、pointerdown、pointerup 事件
    2. 记录指针事件数据：坐标、压力、倾斜角度、指针类型
    3. 生成指针事件回放 JavaScript 脚本
    4. 通过 Playwright 注入跟踪代码
    """

    def __init__(self):
        self.recorded_events: list[PointerEventData] = []
        self.is_recording: bool = False
        self.start_time: float = 0.0

    async def inject_pointer_tracker(self, page: Page) -> None:
        """
        注入 Pointer 事件跟踪脚本
        在页面加载前注入，拦截所有 pointer 相关事件
        """
        console.print("[cyan]  🖱️ 注入 Pointer 事件跟踪器...[/]")

        tracker_script = """
        (function() {
            'use strict';
            // ━━━ WebThief Pointer Event Tracker ━━━
            
            // 存储原始事件监听方法
            const _origAddEventListener = EventTarget.prototype.addEventListener;
            const _origRemoveEventListener = EventTarget.prototype.removeEventListener;
            
            // Pointer 事件类型
            const POINTER_EVENTS = [
                'pointermove', 'pointerenter', 'pointerleave',
                'pointerdown', 'pointerup', 'pointerover', 'pointerout',
                'pointercancel', 'gotpointercapture', 'lostpointercapture'
            ];
            
            // 生成元素选择器
            function getElementSelector(element) {
                if (!element || element === document.body) return 'body';
                if (element.id) return '#' + element.id;
                
                const tagName = element.tagName.toLowerCase();
                const className = element.className && typeof element.className === 'string' 
                    ? '.' + element.className.split(' ').filter(c => c).join('.')
                    : '';
                
                // 尝试使用 nth-child
                let nthChild = '';
                if (element.parentElement) {
                    const siblings = Array.from(element.parentElement.children);
                    const index = siblings.indexOf(element) + 1;
                    nthChild = `:nth-child(${index})`;
                }
                
                return tagName + className + nthChild;
            }
            
            // 记录 pointer 事件
            function recordPointerEvent(event) {
                const eventData = {
                    event_type: event.type,
                    x: event.clientX,
                    y: event.clientY,
                    pressure: event.pressure || 0.5,
                    tilt_x: event.tiltX || 0,
                    tilt_y: event.tiltY || 0,
                    pointer_type: event.pointerType || 'mouse',
                    pointer_id: event.pointerId || 0,
                    is_primary: event.isPrimary || true,
                    button: event.button || 0,
                    buttons: event.buttons || 0,
                    timestamp: Date.now(),
                    target_selector: getElementSelector(event.target)
                };
                
                // 存储到全局变量
                window.__webthief_pointer_events = window.__webthief_pointer_events || [];
                window.__webthief_pointer_events.push(eventData);
                
                // 可选：实时输出到控制台
                if (window.__webthief_pointer_debug) {
                    console.log('[WebThief Pointer]', event.type, eventData);
                }
            }
            
            // 拦截 addEventListener
            EventTarget.prototype.addEventListener = function(type, listener, options) {
                // 如果监听的是 pointer 事件，同时记录到我们的系统
                if (POINTER_EVENTS.includes(type)) {
                    const wrappedListener = function(event) {
                        recordPointerEvent(event);
                        return listener.apply(this, arguments);
                    };
                    
                    // 保存原始监听器引用以便移除
                    if (!this._webthief_listeners) {
                        this._webthief_listeners = new Map();
                    }
                    this._webthief_listeners.set(listener, wrappedListener);
                    
                    return _origAddEventListener.call(this, type, wrappedListener, options);
                }
                
                return _origAddEventListener.apply(this, arguments);
            };
            
            // 拦截 removeEventListener
            EventTarget.prototype.removeEventListener = function(type, listener, options) {
                if (POINTER_EVENTS.includes(type) && this._webthief_listeners) {
                    const wrappedListener = this._webthief_listeners.get(listener);
                    if (wrappedListener) {
                        this._webthief_listeners.delete(listener);
                        return _origRemoveEventListener.call(this, type, wrappedListener, options);
                    }
                }
                
                return _origRemoveEventListener.apply(this, arguments);
            };
            
            // 全局捕获所有 pointer 事件
            POINTER_EVENTS.forEach(eventType => {
                document.addEventListener(eventType, recordPointerEvent, {
                    capture: true,
                    passive: true
                });
            });
            
            // 提供控制 API
            window.__webthief_pointer = {
                // 获取所有记录的事件
                getEvents: function() {
                    return window.__webthief_pointer_events || [];
                },
                
                // 清空记录
                clear: function() {
                    window.__webthief_pointer_events = [];
                    console.log('[WebThief Pointer] 事件记录已清空');
                },
                
                // 启用/禁用调试输出
                setDebug: function(enabled) {
                    window.__webthief_pointer_debug = enabled;
                    console.log('[WebThief Pointer] 调试模式:', enabled ? '开启' : '关闭');
                },
                
                // 获取统计信息
                getStats: function() {
                    const events = window.__webthief_pointer_events || [];
                    const stats = {
                        total: events.length,
                        by_type: {},
                        by_pointer_type: {}
                    };
                    
                    events.forEach(e => {
                        stats.by_type[e.event_type] = (stats.by_type[e.event_type] || 0) + 1;
                        stats.by_pointer_type[e.pointer_type] = (stats.by_pointer_type[e.pointer_type] || 0) + 1;
                    });
                    
                    return stats;
                }
            };
            
            console.log('[WebThief Pointer] Pointer 事件跟踪器已激活');
            console.log('[WebThief Pointer] 可用 API: window.__webthief_pointer');
        })();
        """

        await page.add_init_script(tracker_script)

    async def capture_pointer_events(self, page: Page, duration_ms: int = 5000) -> list[PointerEventData]:
        """
        捕获指定时间内的 pointer 事件
        
        Args:
            page: Playwright Page 对象
            duration_ms: 捕获持续时间（毫秒）
            
        Returns:
            捕获的 PointerEventData 列表
        """
        console.print(f"[cyan]  🖱️ 捕获 Pointer 事件（{duration_ms}ms）...[/]")

        # 清空之前的事件记录
        await page.evaluate("window.__webthief_pointer && window.__webthief_pointer.clear()")

        # 等待指定时间
        await page.wait_for_timeout(duration_ms)

        # 提取记录的事件
        events_data = await page.evaluate("window.__webthief_pointer && window.__webthief_pointer.getEvents()")

        if events_data:
            self.recorded_events = [PointerEventData.from_dict(e) for e in events_data]
            console.print(f"[green]  ✓ 捕获 {len(self.recorded_events)} 个 pointer 事件[/]")
            
            # 显示统计信息
            stats = await page.evaluate("window.__webthief_pointer && window.__webthief_pointer.getStats()")
            if stats:
                console.print("[dim]  📊 事件统计:[/]")
                for event_type, count in stats.get("by_type", {}).items():
                    console.print(f"[dim]     - {event_type}: {count}[/]")
        else:
            self.recorded_events = []
            console.print("[yellow]  ⚠ 未捕获到 pointer 事件[/]")

        return self.recorded_events

    async def get_recorded_events(self, page: Page) -> list[PointerEventData]:
        """
        从页面获取已记录的 pointer 事件
        
        Args:
            page: Playwright Page 对象
            
        Returns:
            捕获的 PointerEventData 列表
        """
        events_data = await page.evaluate("window.__webthief_pointer && window.__webthief_pointer.getEvents()")
        
        if events_data:
            self.recorded_events = [PointerEventData.from_dict(e) for e in events_data]
        
        return self.recorded_events

    def generate_replay_script(self, events: list[PointerEventData] | None = None) -> str:
        """
        生成 pointer 事件回放 JavaScript 脚本
        
        Args:
            events: 要回放的事件列表，如果为 None 则使用已记录的事件
            
        Returns:
            可执行的 JavaScript 代码字符串
        """
        events_to_replay = events or self.recorded_events
        
        if not events_to_replay:
            console.print("[yellow]  ⚠ 没有可回放的事件[/]")
            return ""

        # 将事件数据序列化为 JSON
        events_json = [
            {
                "event_type": e.event_type,
                "x": e.x,
                "y": e.y,
                "pressure": e.pressure,
                "tilt_x": e.tilt_x,
                "tilt_y": e.tilt_y,
                "pointer_type": e.pointer_type,
                "pointer_id": e.pointer_id,
                "is_primary": e.is_primary,
                "button": e.button,
                "buttons": e.buttons,
                "timestamp": e.timestamp,
                "target_selector": e.target_selector,
            }
            for e in events_to_replay
        ]

        replay_script = f"""
        (function() {{
            'use strict';
            // ━━━ WebThief Pointer Event Replay Script ━━━
            
            const EVENTS = {events_json!r};
            
            // 创建 PointerEvent
            function createPointerEvent(eventData, type) {{
                const props = {{
                    bubbles: true,
                    cancelable: true,
                    composed: true,
                    clientX: eventData.x,
                    clientY: eventData.y,
                    screenX: eventData.x + window.screenX,
                    screenY: eventData.y + window.screenY,
                    pressure: eventData.pressure,
                    tiltX: eventData.tilt_x,
                    tiltY: eventData.tilt_y,
                    pointerType: eventData.pointer_type,
                    pointerId: eventData.pointer_id,
                    isPrimary: eventData.is_primary,
                    button: eventData.button,
                    buttons: eventData.buttons,
                    width: 1,
                    height: 1
                }};
                
                return new PointerEvent(type, props);
            }}
            
            // 查找目标元素
            function findTarget(selector) {{
                if (!selector || selector === 'body') return document.body;
                try {{
                    return document.querySelector(selector) || document.body;
                }} catch (e) {{
                    return document.body;
                }}
            }}
            
            // 回放单个事件
            function replayEvent(eventData) {{
                const target = findTarget(eventData.target_selector);
                const event = createPointerEvent(eventData, eventData.event_type);
                
                target.dispatchEvent(event);
                
                console.log('[WebThief Pointer Replay]', eventData.event_type, 
                    'at (', eventData.x, ',', eventData.y, ')', 
                    'on', eventData.target_selector);
            }}
            
            // 按时间顺序回放所有事件
            function replayAll() {{
                if (!EVENTS || EVENTS.length === 0) {{
                    console.warn('[WebThief Pointer Replay] 没有可回放的事件');
                    return;
                }}
                
                const startTime = EVENTS[0].timestamp;
                
                EVENTS.forEach((eventData, index) => {{
                    const delay = index === 0 ? 0 : eventData.timestamp - startTime;
                    
                    setTimeout(() => {{
                        replayEvent(eventData);
                    }}, delay);
                }});
                
                console.log('[WebThief Pointer Replay] 开始回放', EVENTS.length, '个事件');
            }}
            
            // 逐步回放（返回 Promise）
            async function replayStepByStep(stepDelay = 100) {{
                if (!EVENTS || EVENTS.length === 0) {{
                    console.warn('[WebThief Pointer Replay] 没有可回放的事件');
                    return;
                }}
                
                for (const eventData of EVENTS) {{
                    replayEvent(eventData);
                    await new Promise(resolve => setTimeout(resolve, stepDelay));
                }}
                
                console.log('[WebThief Pointer Replay] 逐步回放完成');
            }}
            
            // 导出回放控制 API
            window.__webthief_pointer_replay = {{
                events: EVENTS,
                replay: replayAll,
                replayStepByStep: replayStepByStep,
                replayEvent: replayEvent
            }};
            
            console.log('[WebThief Pointer Replay] 回放脚本已加载');
            console.log('[WebThief Pointer Replay] 调用 window.__webthief_pointer_replay.replay() 开始回放');
        }})();
        """

        console.print(f"[green]  ✓ 生成回放脚本（{len(events_to_replay)} 个事件）[/]")
        return replay_script

    async def inject_replay_script(self, page: Page, events: list[PointerEventData] | None = None) -> None:
        """
        注入回放脚本到页面
        
        Args:
            page: Playwright Page 对象
            events: 要回放的事件列表，如果为 None 则使用已记录的事件
        """
        replay_script = self.generate_replay_script(events)
        
        if replay_script:
            await page.add_init_script(replay_script)
            console.print("[green]  ✓ 回放脚本已注入页面[/]")

    def export_events_to_json(self, events: list[PointerEventData] | None = None) -> str:
        """
        将事件导出为 JSON 字符串
        
        Args:
            events: 要导出的事件列表，如果为 None 则使用已记录的事件
            
        Returns:
            JSON 格式的字符串
        """
        import json
        
        events_to_export = events or self.recorded_events
        data = [e.to_dict() for e in events_to_export]
        
        return json.dumps(data, indent=2, ensure_ascii=False)

    def get_event_summary(self, events: list[PointerEventData] | None = None) -> dict[str, Any]:
        """
        获取事件摘要统计

        Args:
            events: 要分析的事件列表，如果为 None 则使用已记录的事件

        Returns:
            统计信息字典
        """
        events_to_analyze = events or self.recorded_events

        if not events_to_analyze:
            return {"total": 0}

        return {
            "total": len(events_to_analyze),
            "by_type": self._count_by_event_type(events_to_analyze),
            "by_pointer_type": self._count_by_pointer_type(events_to_analyze),
            "coordinates": self._calculate_coordinate_bounds(events_to_analyze),
            "pressure": self._calculate_pressure_stats(events_to_analyze),
        }

    def _count_by_event_type(self, events: list[PointerEventData]) -> dict[str, int]:
        """按事件类型统计数量。"""
        counts: dict[str, int] = {}
        for event in events:
            counts[event.event_type] = counts.get(event.event_type, 0) + 1
        return counts

    def _count_by_pointer_type(self, events: list[PointerEventData]) -> dict[str, int]:
        """按指针类型统计数量。"""
        counts: dict[str, int] = {}
        for event in events:
            counts[event.pointer_type] = counts.get(event.pointer_type, 0) + 1
        return counts

    def _calculate_coordinate_bounds(self, events: list[PointerEventData]) -> dict[str, float]:
        """计算坐标范围。"""
        return {
            "min_x": min(e.x for e in events),
            "max_x": max(e.x for e in events),
            "min_y": min(e.y for e in events),
            "max_y": max(e.y for e in events),
        }

    def _calculate_pressure_stats(self, events: list[PointerEventData]) -> dict[str, float]:
        """计算压力统计信息。"""
        pressures = [e.pressure for e in events]
        return {
            "min": min(pressures),
            "max": max(pressures),
            "avg": sum(pressures) / len(pressures),
        }

    def clear_recorded_events(self) -> None:
        """清空已记录的事件"""
        self.recorded_events = []
        console.print("[dim]  🗑️ 已清空记录的事件[/]")
