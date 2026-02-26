"""
Canvas 录制与回放模块
目标：捕获 Canvas 2D 绘制操作和用户交互，支持回放和截图
"""

from __future__ import annotations

import json
import base64
from datetime import datetime
from typing import Any

from playwright.async_api import Page
from rich.console import Console

console = Console()


class CanvasRecorder:
    """
    Canvas 录制器
    负责：
    1. 拦截 Canvas 2D 上下文绘制方法
    2. 记录绘制命令序列
    3. 捕获用户交互事件
    4. 生成回放脚本
    5. 捕获 Canvas 截图作为 fallback
    """

    # Canvas 2D 上下文需要拦截的绘制方法
    CANVAS_2D_METHODS = [
        # 矩形绘制
        "fillRect", "strokeRect", "clearRect",
        # 路径绘制
        "beginPath", "closePath", "moveTo", "lineTo", "bezierCurveTo",
        "quadraticCurveTo", "arc", "arcTo", "ellipse", "rect",
        "fill", "stroke", "clip",
        # 样式设置
        "fillStyle", "strokeStyle", "lineWidth", "lineCap", "lineJoin",
        "miterLimit", "globalAlpha", "globalCompositeOperation",
        # 文本绘制
        "fillText", "strokeText", "font", "textAlign", "textBaseline",
        # 图像绘制
        "drawImage",
        # 变换
        "scale", "rotate", "translate", "transform", "setTransform",
        "resetTransform", "save", "restore",
        # 其他
        "clearRect", "createLinearGradient", "createRadialGradient",
        "createPattern"
    ]

    # 需要记录的鼠标事件
    MOUSE_EVENTS = ["click", "mousedown", "mouseup", "mousemove"]

    def __init__(self):
        self.recording_data: list[dict[str, Any]] = []
        self.is_recording = False
        self.start_time: float | None = None
        self.canvas_selectors: list[str] = []

    async def inject_canvas_tracker(self, page: Page, canvas_selector: str = "canvas") -> None:
        """
        注入 Canvas 追踪脚本
        拦截 Canvas 2D 上下文的所有绘制方法

        Args:
            page: Playwright Page 对象
            canvas_selector: Canvas 元素的选择器，默认为 "canvas"
        """
        console.print(f"[cyan]  🎨 注入 Canvas 追踪器 (目标: {canvas_selector})...[/]")

        self.canvas_selectors.append(canvas_selector)

        tracker_script = f"""
        (function() {{
            'use strict';
            // ━━━ WebThief Canvas Tracker Layer ━━━
            
            const CANVAS_SELECTOR = '{canvas_selector}';
            const RECORDING_KEY = '__webthief_canvas_recording_' + CANVAS_SELECTOR.replace(/[^a-zA-Z0-9]/g, '_');
            
            // 需要拦截的 Canvas 2D 方法
            const INTERCEPT_METHODS = [
                'fillRect', 'strokeRect', 'clearRect',
                'beginPath', 'closePath', 'moveTo', 'lineTo', 
                'bezierCurveTo', 'quadraticCurveTo', 'arc', 'arcTo', 
                'ellipse', 'rect', 'fill', 'stroke', 'clip',
                'fillText', 'strokeText', 'drawImage'
            ];
            
            // 需要拦截的属性
            const INTERCEPT_PROPERTIES = [
                'fillStyle', 'strokeStyle', 'lineWidth', 'lineCap', 
                'lineJoin', 'miterLimit', 'globalAlpha', 'globalCompositeOperation',
                'font', 'textAlign', 'textBaseline'
            ];
            
            // 变换方法
            const TRANSFORM_METHODS = [
                'scale', 'rotate', 'translate', 'transform', 
                'setTransform', 'resetTransform', 'save', 'restore'
            ];
            
            // 序列化参数（处理特殊类型）
            function serializeArg(arg) {{
                if (arg === null || arg === undefined) return null;
                if (typeof arg === 'number' || typeof arg === 'boolean' || typeof arg === 'string') {{
                    return arg;
                }}
                if (arg instanceof HTMLImageElement || arg instanceof HTMLCanvasElement || arg instanceof HTMLVideoElement) {{
                    return {{ 
                        __type: 'element', 
                        tagName: arg.tagName,
                        width: arg.width,
                        height: arg.height
                    }};
                }}
                if (arg instanceof ImageData) {{
                    return {{
                        __type: 'ImageData',
                        width: arg.width,
                        height: arg.height
                    }};
                }}
                if (arg instanceof CanvasGradient) {{
                    return {{ __type: 'CanvasGradient' }};
                }}
                if (arg instanceof CanvasPattern) {{
                    return {{ __type: 'CanvasPattern' }};
                }}
                if (typeof arg === 'object') {{
                    try {{
                        return JSON.parse(JSON.stringify(arg));
                    }} catch (e) {{
                        return {{ __type: 'object', __string: String(arg) }};
                    }}
                }}
                return String(arg);
            }}
            
            // 记录绘制命令
            function recordCommand(methodName, args, isProperty = false) {{
                if (!window[RECORDING_KEY]) {{
                    window[RECORDING_KEY] = [];
                }}
                
                const serializedArgs = Array.from(args).map(serializeArg);
                
                window[RECORDING_KEY].push({{
                    type: isProperty ? 'property' : 'method',
                    method: methodName,
                    args: serializedArgs,
                    timestamp: Date.now(),
                    relativeTime: window.__webthief_recording_start ? 
                        Date.now() - window.__webthief_recording_start : 0
                }});
            }}
            
            // 拦截 Canvas 2D 上下文
            function interceptCanvas2D(canvas) {{
                if (!canvas || canvas.__webthief_intercepted) return;
                
                const ctx = canvas.getContext('2d');
                if (!ctx) return;
                
                // 标记已拦截
                canvas.__webthief_intercepted = true;
                
                // 拦截方法
                INTERCEPT_METHODS.forEach(methodName => {{
                    if (typeof ctx[methodName] === 'function') {{
                        const originalMethod = ctx[methodName];
                        ctx[methodName] = function(...args) {{
                            recordCommand(methodName, args);
                            return originalMethod.apply(this, args);
                        }};
                    }}
                }});
                
                // 拦截变换方法
                TRANSFORM_METHODS.forEach(methodName => {{
                    if (typeof ctx[methodName] === 'function') {{
                        const originalMethod = ctx[methodName];
                        ctx[methodName] = function(...args) {{
                            recordCommand('transform:' + methodName, args);
                            return originalMethod.apply(this, args);
                        }};
                    }}
                }});
                
                // 拦截属性设置
                INTERCEPT_PROPERTIES.forEach(propName => {{
                    const descriptor = Object.getOwnPropertyDescriptor(ctx.__proto__, propName) || 
                                       Object.getOwnPropertyDescriptor(CanvasRenderingContext2D.prototype, propName);
                    if (descriptor && descriptor.set) {{
                        const originalSetter = descriptor.set;
                        Object.defineProperty(ctx, propName, {{
                            set: function(value) {{
                                recordCommand('set:' + propName, [value], true);
                                return originalSetter.call(this, value);
                            }},
                            get: descriptor.get,
                            configurable: true
                        }});
                    }}
                }});
                
                console.log('[WebThief Canvas Tracker] Canvas 2D 上下文已拦截:', canvas);
            }}
            
            // 监听鼠标事件
            function attachMouseEvents(canvas) {{
                const MOUSE_EVENTS = ['click', 'mousedown', 'mouseup', 'mousemove'];
                
                MOUSE_EVENTS.forEach(eventType => {{
                    canvas.addEventListener(eventType, function(event) {{
                        const rect = canvas.getBoundingClientRect();
                        const mouseData = {{
                            type: 'mouse',
                            eventType: eventType,
                            x: event.clientX - rect.left,
                            y: event.clientY - rect.top,
                            clientX: event.clientX,
                            clientY: event.clientY,
                            button: event.button,
                            timestamp: Date.now(),
                            relativeTime: window.__webthief_recording_start ? 
                                Date.now() - window.__webthief_recording_start : 0
                        }};
                        
                        if (!window[RECORDING_KEY]) {{
                            window[RECORDING_KEY] = [];
                        }}
                        window[RECORDING_KEY].push(mouseData);
                    }});
                }});
            }}
            
            // 查找并拦截所有匹配的 Canvas
            function findAndInterceptCanvas() {{
                const canvases = document.querySelectorAll(CANVAS_SELECTOR);
                canvases.forEach(canvas => {{
                    interceptCanvas2D(canvas);
                    attachMouseEvents(canvas);
                }});
            }}
            
            // 监听动态添加的 Canvas
            const observer = new MutationObserver(function(mutations) {{
                mutations.forEach(function(mutation) {{
                    mutation.addedNodes.forEach(function(node) {{
                        if (node.nodeType === Node.ELEMENT_NODE) {{
                            if (node.matches && node.matches(CANVAS_SELECTOR)) {{
                                interceptCanvas2D(node);
                                attachMouseEvents(node);
                            }}
                            if (node.querySelectorAll) {{
                                const canvases = node.querySelectorAll(CANVAS_SELECTOR);
                                canvases.forEach(interceptCanvas2D);
                                canvases.forEach(attachMouseEvents);
                            }}
                        }}
                    }});
                }});
            }});
            
            // 启动录制
            window.__webthief_recording_start = Date.now();
            
            // 初始拦截
            findAndInterceptCanvas();
            
            // 开始监听 DOM 变化
            observer.observe(document.body, {{ childList: true, subtree: true }});
            
            // 暴露控制接口
            window.__webthief_canvas_control = {{
                start: function() {{
                    window.__webthief_recording_start = Date.now();
                    window[RECORDING_KEY] = [];
                    console.log('[WebThief Canvas Tracker] 录制已启动');
                }},
                stop: function() {{
                    const data = window[RECORDING_KEY] || [];
                    console.log('[WebThief Canvas Tracker] 录制已停止，共', data.length, '条记录');
                    return data;
                }},
                clear: function() {{
                    window[RECORDING_KEY] = [];
                    console.log('[WebThief Canvas Tracker] 录制数据已清空');
                }},
                getData: function() {{
                    return window[RECORDING_KEY] || [];
                }}
            }};
            
            console.log('[WebThief Canvas Tracker] Canvas 追踪层已激活，选择器:', CANVAS_SELECTOR);
        }})();
        """

        await page.add_init_script(tracker_script)
        self.is_recording = True
        self.start_time = datetime.now().timestamp()

    async def start_recording(self, page: Page) -> None:
        """
        开始录制 Canvas 操作

        Args:
            page: Playwright Page 对象
        """
        console.print("[cyan]  ▶️ 开始 Canvas 录制...[/]")

        await page.evaluate("""
            () => {
                if (window.__webthief_canvas_control) {
                    window.__webthief_canvas_control.start();
                } else {
                    window.__webthief_recording_start = Date.now();
                    console.warn('[WebThief Canvas Tracker] 控制接口未就绪');
                }
            }
        """)

        self.is_recording = True
        self.start_time = datetime.now().timestamp()

    async def stop_recording(self, page: Page) -> list[dict[str, Any]]:
        """
        停止录制并返回录制数据

        Args:
            page: Playwright Page 对象

        Returns:
            录制数据列表
        """
        console.print("[cyan]  ⏹️ 停止 Canvas 录制...[/]")

        recording_data = await page.evaluate("""
            () => {
                if (window.__webthief_canvas_control) {
                    return window.__webthief_canvas_control.stop();
                }
                return [];
            }
        """)

        self.recording_data = recording_data
        self.is_recording = False

        console.print(f"[green]  ✓ 录制完成，共 {len(recording_data)} 条记录[/]")

        return recording_data

    async def get_recording_data(self, page: Page) -> list[dict[str, Any]]:
        """
        获取当前录制数据（不停止录制）

        Args:
            page: Playwright Page 对象

        Returns:
            当前录制数据列表
        """
        data = await page.evaluate("""
            () => {
                if (window.__webthief_canvas_control) {
                    return window.__webthief_canvas_control.getData();
                }
                return [];
            }
        """)

        self.recording_data = data
        return data

    def generate_replay_script(
        self,
        recording_data: list[dict[str, Any]] | None = None,
        canvas_selector: str = "canvas"
    ) -> str:
        """
        生成 Canvas 回放脚本

        Args:
            recording_data: 录制数据，如果为 None 则使用实例中保存的数据
            canvas_selector: Canvas 元素选择器

        Returns:
            可执行的 JavaScript 回放脚本
        """
        data = recording_data or self.recording_data

        if not data:
            console.print("[yellow]  ⚠️ 没有录制数据可供回放[/]")
            return ""

        # 序列化录制数据
        serialized_data = json.dumps(data, ensure_ascii=False)

        replay_script = f"""
        (function() {{
            'use strict';
            // ━━━ WebThief Canvas Replay Script ━━━
            
            const RECORDING_DATA = {serialized_data};
            const CANVAS_SELECTOR = '{canvas_selector}';
            
            // 反序列化参数
            function deserializeArg(arg, ctx) {{
                if (arg === null || arg === undefined) return arg;
                if (typeof arg !== 'object') return arg;
                if (arg.__type === 'element') {{
                    // 创建占位元素
                    const img = new Image();
                    img.width = arg.width || 0;
                    img.height = arg.height || 0;
                    return img;
                }}
                return arg;
            }}
            
            // 执行单条命令
            function executeCommand(ctx, cmd) {{
                try {{
                    if (cmd.type === 'mouse') {{
                        // 鼠标事件 - 仅记录，不实际触发
                        console.log('[Canvas Replay] 鼠标事件:', cmd.eventType, '位置:', cmd.x, cmd.y);
                        return;
                    }}
                    
                    if (cmd.type === 'property' && cmd.method.startsWith('set:')) {{
                        const propName = cmd.method.replace('set:', '');
                        const value = deserializeArg(cmd.args[0], ctx);
                        ctx[propName] = value;
                        return;
                    }}
                    
                    if (cmd.method.startsWith('transform:')) {{
                        const methodName = cmd.method.replace('transform:', '');
                        const args = cmd.args.map(arg => deserializeArg(arg, ctx));
                        if (typeof ctx[methodName] === 'function') {{
                            ctx[methodName].apply(ctx, args);
                        }}
                        return;
                    }}
                    
                    // 普通方法调用
                    const args = cmd.args.map(arg => deserializeArg(arg, ctx));
                    if (typeof ctx[cmd.method] === 'function') {{
                        ctx[cmd.method].apply(ctx, args);
                    }}
                }} catch (e) {{
                    console.error('[Canvas Replay] 执行命令失败:', cmd.method, e);
                }}
            }}
            
            // 回放录制数据
            function replayRecording(canvas) {{
                if (!canvas) {{
                    console.error('[Canvas Replay] 未找到 Canvas 元素');
                    return;
                }}
                
                const ctx = canvas.getContext('2d');
                if (!ctx) {{
                    console.error('[Canvas Replay] 无法获取 2D 上下文');
                    return;
                }}
                
                console.log('[Canvas Replay] 开始回放，共', RECORDING_DATA.length, '条命令');
                
                let index = 0;
                function playNext() {{
                    if (index >= RECORDING_DATA.length) {{
                        console.log('[Canvas Replay] 回放完成');
                        return;
                    }}
                    
                    const cmd = RECORDING_DATA[index];
                    const nextCmd = RECORDING_DATA[index + 1];
                    
                    executeCommand(ctx, cmd);
                    index++;
                    
                    // 计算下一条命令的延迟
                    if (nextCmd && nextCmd.relativeTime && cmd.relativeTime) {{
                        const delay = nextCmd.relativeTime - cmd.relativeTime;
                        // 限制最大延迟为 100ms，加速回放
                        const actualDelay = Math.min(delay, 100);
                        setTimeout(playNext, actualDelay);
                    }} else {{
                        // 无延迟或最后一条，立即执行
                        playNext();
                    }}
                }}
                
                // 清空画布
                ctx.clearRect(0, 0, canvas.width, canvas.height);
                
                // 开始回放
                playNext();
            }}
            
            // 立即回放或等待 Canvas 就绪
            function startReplay() {{
                const canvas = document.querySelector(CANVAS_SELECTOR);
                if (canvas) {{
                    replayRecording(canvas);
                }} else {{
                    console.log('[Canvas Replay] 等待 Canvas 元素...');
                    const observer = new MutationObserver(function() {{
                        const canvas = document.querySelector(CANVAS_SELECTOR);
                        if (canvas) {{
                            observer.disconnect();
                            replayRecording(canvas);
                        }}
                    }});
                    observer.observe(document.body, {{ childList: true, subtree: true }});
                }}
            }}
            
            // 启动回放
            if (document.readyState === 'loading') {{
                document.addEventListener('DOMContentLoaded', startReplay);
            }} else {{
                startReplay();
            }}
            
            // 暴露控制接口
            window.__webthief_canvas_replay = {{
                start: function() {{ startReplay(); }},
                replay: function(canvas) {{ replayRecording(canvas); }}
            }};
            
            console.log('[Canvas Replay] 回放脚本已加载');
        }})();
        """

        console.print(f"[green]  ✓ 生成回放脚本，包含 {len(data)} 条命令[/]")

        return replay_script

    async def capture_canvas_screenshot(
        self,
        page: Page,
        canvas_selector: str = "canvas",
        output_path: str | None = None
    ) -> str | None:
        """
        捕获 Canvas 截图作为 fallback

        Args:
            page: Playwright Page 对象
            canvas_selector: Canvas 元素选择器
            output_path: 截图保存路径，如果为 None 则返回 base64 数据

        Returns:
            如果 output_path 为 None，返回 base64 编码的图片数据；
            否则返回保存的文件路径
        """
        console.print(f"[cyan]  📸 捕获 Canvas 截图 ({canvas_selector})...[/]")

        try:
            # 获取 Canvas 数据 URL
            data_url = await page.evaluate(f"""
                (selector) => {{
                    const canvas = document.querySelector(selector);
                    if (!canvas) return null;
                    try {{
                        return canvas.toDataURL('image/png');
                    }} catch (e) {{
                        console.error('Canvas 截图失败:', e);
                        return null;
                    }}
                }}
            """, canvas_selector)

            if not data_url:
                console.print("[red]  ✗ 无法获取 Canvas 数据[/]")
                return None

            # 提取 base64 数据
            base64_data = data_url.split(',')[1]

            if output_path:
                # 保存到文件
                import os
                os.makedirs(os.path.dirname(output_path), exist_ok=True)

                with open(output_path, 'wb') as f:
                    f.write(base64.b64decode(base64_data))

                console.print(f"[green]  ✓ 截图已保存: {output_path}[/]")
                return output_path
            else:
                console.print("[green]  ✓ 截图已捕获 (base64)[/]")
                return base64_data

        except Exception as e:
            console.print(f"[red]  ✗ 截图失败: {e}[/]")
            return None

    async def export_recording(
        self,
        page: Page,
        output_path: str,
        include_screenshot: bool = True
    ) -> dict[str, Any]:
        """
        导出完整录制数据（包括截图）

        Args:
            page: Playwright Page 对象
            output_path: 导出文件路径
            include_screenshot: 是否包含截图

        Returns:
            导出数据字典
        """
        console.print(f"[cyan]  💾 导出录制数据到 {output_path}...[/]")

        recording_data = await self.get_recording_data(page)

        export_data: dict[str, Any] = {
            "version": "1.0.0",
            "export_time": datetime.now().isoformat(),
            "recording": recording_data,
            "metadata": {
                "command_count": len(recording_data),
                "canvas_selectors": self.canvas_selectors,
                "start_time": self.start_time
            }
        }

        if include_screenshot:
            screenshot_data = await self.capture_canvas_screenshot(page)
            if screenshot_data:
                export_data["screenshot"] = {
                    "format": "png",
                    "data": screenshot_data
                }

        # 保存到文件
        import os
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)

        console.print(f"[green]  ✓ 录制数据已导出: {output_path}[/]")

        return export_data

    def clear_recording(self, page: Page | None = None) -> None:
        """
        清空录制数据

        Args:
            page: 可选的 Playwright Page 对象，如果提供则同时清空页面端数据
        """
        self.recording_data = []
        self.start_time = None

        if page:
            # 异步清空页面端数据
            import asyncio
            asyncio.create_task(page.evaluate("""
                () => {
                    if (window.__webthief_canvas_control) {
                        window.__webthief_canvas_control.clear();
                    }
                }
            """))

        console.print("[cyan]  🗑️ 录制数据已清空[/]")
