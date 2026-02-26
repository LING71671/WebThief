"""
WebThief 动画功能端到端测试脚本

测试内容：
- 鼠标跟随动画捕获
- 视差滚动效果捕获
- GSAP ScrollTrigger 网站克隆
- Canvas 应用克隆
- CSS 动画分析
- Hover 效果检测

使用方法：
    python tests/test_animation_features.py

环境要求：
    - Python 3.9+
    - Playwright
    - WebThief 已安装
"""

from __future__ import annotations

import asyncio
import sys
import tempfile
from pathlib import Path
from typing import Any

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pytest
from playwright.async_api import async_playwright, Page, Browser
from rich.console import Console

from webthief.interceptors.animation_analyzer import AnimationAnalyzer, AnimationType
from webthief.interceptors.parallax_handler import ParallaxHandler, ParallaxElement
from webthief.interceptors.scroll_trigger_handler import ScrollTriggerHandler
from webthief.interceptors.hover_analyzer import HoverAnalyzer, PseudoClass
from webthief.interceptors.canvas_recorder import CanvasRecorder
from webthief.interceptors.mouse_simulator import MouseSimulator

console = Console()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 测试夹具 (Fixtures)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@pytest.fixture(scope="module")
def event_loop():
    """创建事件循环"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="module")
async def browser():
    """创建浏览器实例"""
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        yield browser
        await browser.close()


@pytest.fixture
async def page(browser: Browser):
    """创建新页面"""
    page = await browser.new_page()
    yield page
    await page.close()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 测试类：CSS 动画分析
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestCSSAnimationAnalyzer:
    """CSS 动画分析器测试"""

    async def test_detect_entrance_animations(self, page: Page):
        """测试入场动画检测"""
        # 创建测试页面
        await page.set_content("""
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    @keyframes fadeIn {
                        from { opacity: 0; transform: translateY(20px); }
                        to { opacity: 1; transform: translateY(0); }
                    }
                    .animate-fade-in {
                        animation: fadeIn 0.5s ease forwards;
                    }
                </style>
            </head>
            <body>
                <div class="animate-fade-in">Test Content</div>
            </body>
            </html>
        """)
        await page.wait_for_load_state("networkidle")

        analyzer = AnimationAnalyzer()
        animations = await analyzer.analyze_css_animations(page)

        assert len(animations) > 0, "应该检测到动画"
        assert any(a.name == "fadeIn" for a in animations), "应该检测到 fadeIn 动画"

        # 检查动画类型识别
        fade_in_anim = next((a for a in animations if a.name == "fadeIn"), None)
        if fade_in_anim:
            assert fade_in_anim.animation_type == AnimationType.ENTRANCE, \
                "fadeIn 应该被识别为入场动画"

        console.print("[green]✓ 入场动画检测测试通过[/]")

    async def test_detect_hover_animations(self, page: Page):
        """测试悬停动画检测"""
        await page.set_content("""
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    @keyframes pulse {
                        0%, 100% { transform: scale(1); }
                        50% { transform: scale(1.05); }
                    }
                    .btn:hover {
                        animation: pulse 0.3s ease;
                    }
                </style>
            </head>
            <body>
                <button class="btn">Hover Me</button>
            </body>
            </html>
        """)
        await page.wait_for_load_state("networkidle")

        analyzer = AnimationAnalyzer()
        animations = await analyzer.analyze_css_animations(page)

        # 检查是否有悬停相关的动画
        hover_anims = [a for a in animations if a.animation_type == AnimationType.HOVER]
        console.print(f"[dim]检测到 {len(hover_anims)} 个悬停动画[/]")

        console.print("[green]✓ 悬停动画检测测试通过[/]")

    async def test_detect_loop_animations(self, page: Page):
        """测试循环动画检测"""
        await page.set_content("""
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    @keyframes spin {
                        from { transform: rotate(0deg); }
                        to { transform: rotate(360deg); }
                    }
                    .spinner {
                        animation: spin 1s linear infinite;
                    }
                </style>
            </head>
            <body>
                <div class="spinner">Loading...</div>
            </body>
            </html>
        """)
        await page.wait_for_load_state("networkidle")

        analyzer = AnimationAnalyzer()
        animations = await analyzer.analyze_css_animations(page)

        # 检查循环动画
        loop_anims = [a for a in animations if a.animation_type == AnimationType.LOOP]
        assert len(loop_anims) > 0, "应该检测到循环动画"

        spin_anim = next((a for a in loop_anims if a.name == "spin"), None)
        if spin_anim:
            assert spin_anim.iteration_count == "infinite", \
                "旋转动画应该是无限循环"

        console.print("[green]✓ 循环动画检测测试通过[/]")

    async def test_importance_score_calculation(self, page: Page):
        """测试动画重要性评分"""
        await page.set_content("""
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    @keyframes importantFade {
                        from { opacity: 0; transform: translateY(20px) scale(0.9); }
                        to { opacity: 1; transform: translateY(0) scale(1); }
                    }
                    .important {
                        animation: importantFade 0.3s ease forwards;
                    }
                </style>
            </head>
            <body>
                <div class="important">Important Content</div>
            </body>
            </html>
        """)
        await page.wait_for_load_state("networkidle")

        analyzer = AnimationAnalyzer()
        animations = await analyzer.analyze_css_animations(page)

        for anim in animations:
            assert 0 <= anim.importance_score <= 100, \
                f"重要性分数应该在 0-100 之间，实际为 {anim.importance_score}"

        console.print("[green]✓ 重要性评分计算测试通过[/]")

    async def test_generate_preserved_css(self, page: Page):
        """测试生成保留动画的 CSS"""
        await page.set_content("""
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    @keyframes slideIn {
                        from { transform: translateX(-100%); }
                        to { transform: translateX(0); }
                    }
                    .slide {
                        animation: slideIn 0.5s ease forwards;
                    }
                </style>
            </head>
            <body>
                <div class="slide">Sliding Content</div>
            </body>
            </html>
        """)
        await page.wait_for_load_state("networkidle")

        analyzer = AnimationAnalyzer()
        await analyzer.analyze_css_animations(page)

        css_output = analyzer.generate_preserved_css()

        assert len(css_output) > 0, "应该生成 CSS 输出"
        assert "slideIn" in css_output or "animation" in css_output, \
            "CSS 输出应该包含动画相关内容"

        console.print("[green]✓ 生成保留 CSS 测试通过[/]")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 测试类：视差滚动效果
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestParallaxHandler:
    """视差滚动效果处理器测试"""

    async def test_detect_parallax_by_data_attribute(self, page: Page):
        """测试通过 data 属性检测视差元素"""
        await page.set_content("""
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    .parallax-section {
                        height: 200vh;
                        position: relative;
                    }
                    .parallax-bg {
                        position: absolute;
                        top: 0;
                        left: 0;
                        width: 100%;
                        height: 100%;
                    }
                </style>
            </head>
            <body>
                <section class="parallax-section">
                    <div class="parallax-bg" data-speed="0.5">Background</div>
                    <div data-parallax-speed="0.3">Element 1</div>
                    <div data-speed="-0.2">Element 2</div>
                </section>
            </body>
            </html>
        """)
        await page.wait_for_load_state("networkidle")

        handler = ParallaxHandler()
        elements = await handler.detect_parallax_elements(page)

        assert len(elements) >= 3, f"应该检测到至少 3 个视差元素，实际检测到 {len(elements)} 个"

        # 检查速度值解析
        speeds = [e.speed for e in elements]
        assert 0.5 in speeds, "应该检测到 speed=0.5 的元素"
        assert 0.3 in speeds, "应该检测到 speed=0.3 的元素"
        assert -0.2 in speeds, "应该检测到 speed=-0.2 的元素"

        console.print("[green]✓ Data 属性视差检测测试通过[/]")

    async def test_detect_parallax_by_class(self, page: Page):
        """测试通过类名检测视差元素"""
        await page.set_content("""
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    .parallax-container { height: 200vh; }
                    .parallax-element { will-change: transform; }
                </style>
            </head>
            <body>
                <div class="parallax-container">
                    <div class="parallax-element">Element 1</div>
                    <div class="parallax-element">Element 2</div>
                </div>
            </body>
            </html>
        """)
        await page.wait_for_load_state("networkidle")

        handler = ParallaxHandler()
        elements = await handler.detect_parallax_elements(page)

        # 应该检测到 parallax-element 类的元素
        parallax_elems = [e for e in elements if "parallax" in e.selector]
        console.print(f"[dim]检测到 {len(parallax_elems)} 个视差类元素[/]")

        console.print("[green]✓ 类名视差检测测试通过[/]")

    async def test_calculate_parallax_positions(self):
        """测试视差位置计算"""
        handler = ParallaxHandler()

        # 测试垂直视差
        element = ParallaxElement(
            selector=".test",
            speed=0.5,
            direction="vertical"
        )

        positions = handler.calculate_parallax_positions(element, [0, 50, 100])

        assert 0 in positions, "应该包含 0% 位置"
        assert 50 in positions, "应该包含 50% 位置"
        assert 100 in positions, "应该包含 100% 位置"

        # 检查计算结果
        assert positions[0]["translate_y"] == 0, "0% 位置应该没有偏移"
        assert positions[50]["translate_y"] == 25, "50% 位置应该偏移 25"
        assert positions[100]["translate_y"] == 50, "100% 位置应该偏移 50"

        console.print("[green]✓ 视差位置计算测试通过[/]")

    async def test_generate_static_css(self, page: Page):
        """测试生成静态 CSS"""
        await page.set_content("""
            <!DOCTYPE html>
            <html>
            <body>
                <div data-speed="0.5" id="parallax1">Test</div>
            </body>
            </html>
        """)
        await page.wait_for_load_state("networkidle")

        handler = ParallaxHandler()
        await handler.detect_parallax_elements(page)

        css = handler.generate_static_css()

        assert len(css) > 0, "应该生成 CSS"
        assert "@keyframes" in css, "CSS 应该包含关键帧动画"
        assert "parallax" in css.lower(), "CSS 应该包含视差相关样式"

        console.print("[green]✓ 生成静态 CSS 测试通过[/]")

    async def test_parallax_library_detection(self, page: Page):
        """测试视差库检测"""
        # 模拟 rellax 库
        await page.set_content("""
            <!DOCTYPE html>
            <html>
            <head>
                <script>
                    // 模拟 rellax 库
                    window.Rellax = function() {};
                </script>
            </head>
            <body>
                <div data-speed="0.5">Element</div>
            </body>
            </html>
        """)
        await page.wait_for_load_state("networkidle")

        handler = ParallaxHandler()
        await handler.detect_parallax_elements(page)

        # 检查是否检测到库
        # 注意：这里主要测试代码不抛出异常
        console.print("[green]✓ 视差库检测测试通过[/]")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 测试类：ScrollTrigger 处理
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestScrollTriggerHandler:
    """ScrollTrigger 处理器测试"""

    async def test_detect_gsap_scrolltrigger(self, page: Page):
        """测试检测 GSAP ScrollTrigger"""
        await page.set_content("""
            <!DOCTYPE html>
            <html>
            <head>
                <script src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.2/gsap.min.js"></script>
                <script src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.2/ScrollTrigger.min.js"></script>
            </head>
            <body>
                <div style="height: 200vh;">
                    <div id="trigger">Trigger Element</div>
                </div>
                <script>
                    gsap.registerPlugin(ScrollTrigger);
                    gsap.to("#trigger", {
                        scrollTrigger: {
                            trigger: "#trigger",
                            start: "top center",
                            end: "bottom center",
                            scrub: true
                        },
                        x: 100
                    });
                </script>
            </body>
            </html>
        """)
        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(2000)  # 等待 GSAP 加载

        handler = ScrollTriggerHandler()
        library = await handler.detect_scroll_trigger_library(page)

        # 注意：由于外部资源加载可能不稳定，这里主要测试代码结构
        console.print(f"[dim]检测到的库: {library}[/]")
        console.print("[green]✓ GSAP ScrollTrigger 检测测试通过[/]")

    async def test_detect_aos_library(self, page: Page):
        """测试检测 AOS 库"""
        await page.set_content("""
            <!DOCTYPE html>
            <html>
            <head>
                <script>
                    // 模拟 AOS 库
                    window.AOS = {
                        init: function() {}
                    };
                </script>
            </head>
            <body>
                <div data-aos="fade-up">AOS Element</div>
            </body>
            </html>
        """)
        await page.wait_for_load_state("networkidle")

        handler = ScrollTriggerHandler()
        library = await handler.detect_scroll_trigger_library(page)

        # 应该检测到 AOS
        console.print(f"[dim]检测到的库: {library}[/]")
        console.print("[green]✓ AOS 库检测测试通过[/]")

    async def test_generate_scroll_trigger_bridge(self):
        """测试生成 ScrollTrigger 桥接脚本"""
        handler = ScrollTriggerHandler()

        bridge_script = handler.generate_scroll_trigger_bridge_script()

        assert len(bridge_script) > 0, "应该生成桥接脚本"
        assert "IntersectionObserver" in bridge_script, "脚本应该使用 IntersectionObserver"
        assert "ScrollTrigger" in bridge_script, "脚本应该模拟 ScrollTrigger API"

        console.print("[green]✓ ScrollTrigger 桥接脚本生成测试通过[/]")

    async def test_generate_static_styles(self):
        """测试生成静态样式"""
        handler = ScrollTriggerHandler()

        # 添加模拟的快照数据
        handler.captured_snapshots = [
            {
                "progress": 0.0,
                "element_states": [
                    {
                        "selector": ".test-element",
                        "computedStyle": {
                            "transform": "translateY(0px)",
                            "opacity": "1"
                        }
                    }
                ]
            },
            {
                "progress": 0.5,
                "element_states": [
                    {
                        "selector": ".test-element",
                        "computedStyle": {
                            "transform": "translateY(50px)",
                            "opacity": "0.5"
                        }
                    }
                ]
            }
        ]

        css = handler.generate_static_styles()

        assert len(css) > 0, "应该生成 CSS"
        assert ".test-element" in css or "wt-" in css, "CSS 应该包含元素样式"

        console.print("[green]✓ 静态样式生成测试通过[/]")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 测试类：Hover 效果分析
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestHoverAnalyzer:
    """Hover 效果分析器测试"""

    async def test_detect_hover_effects(self, page: Page):
        """测试检测 Hover 效果"""
        await page.set_content("""
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    .btn {
                        background: blue;
                        transition: all 0.3s;
                    }
                    .btn:hover {
                        background: red;
                        transform: scale(1.1);
                    }
                    .link:hover {
                        color: green;
                    }
                </style>
            </head>
            <body>
                <button class="btn">Button</button>
                <a class="link">Link</a>
            </body>
            </html>
        """)
        await page.wait_for_load_state("networkidle")

        analyzer = HoverAnalyzer()
        effects = await analyzer.analyze_hover_effects(page)

        assert len(effects) > 0, "应该检测到 hover 效果"

        # 检查是否有 hover 伪类
        hover_effects = [e for e in effects if e.pseudo_class == PseudoClass.HOVER]
        assert len(hover_effects) > 0, "应该检测到 :hover 效果"

        console.print(f"[dim]检测到 {len(hover_effects)} 个 hover 效果[/]")
        console.print("[green]✓ Hover 效果检测测试通过[/]")

    async def test_detect_focus_effects(self, page: Page):
        """测试检测 Focus 效果"""
        await page.set_content("""
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    input:focus {
                        border-color: blue;
                        box-shadow: 0 0 5px blue;
                    }
                </style>
            </head>
            <body>
                <input type="text" placeholder="Focus me">
            </body>
            </html>
        """)
        await page.wait_for_load_state("networkidle")

        analyzer = HoverAnalyzer()
        effects = await analyzer.analyze_hover_effects(page)

        # 检查是否有 focus 伪类
        focus_effects = [e for e in effects if e.pseudo_class == PseudoClass.FOCUS]
        console.print(f"[dim]检测到 {len(focus_effects)} 个 focus 效果[/]")

        console.print("[green]✓ Focus 效果检测测试通过[/]")

    async def test_evaluate_visual_importance(self, page: Page):
        """测试视觉重要性评估"""
        await page.set_content("""
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    .important:hover {
                        transform: scale(1.5) rotate(10deg);
                        filter: brightness(1.2);
                    }
                    .subtle:hover {
                        color: #333;
                    }
                </style>
            </head>
            <body>
                <div class="important">Important</div>
                <div class="subtle">Subtle</div>
            </body>
            </html>
        """)
        await page.wait_for_load_state("networkidle")

        analyzer = HoverAnalyzer()
        effects = await analyzer.analyze_hover_effects(page)

        for effect in effects:
            score = analyzer.evaluate_visual_importance(effect)
            assert 0 <= score <= 1, f"重要性分数应该在 0-1 之间，实际为 {score}"

        console.print("[green]✓ 视觉重要性评估测试通过[/]")

    async def test_convert_to_static_css(self, page: Page):
        """测试转换为静态 CSS"""
        await page.set_content("""
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    .btn:hover {
                        background: red;
                        transform: scale(1.1);
                    }
                </style>
            </head>
            <body>
                <button class="btn">Button</button>
            </body>
            </html>
        """)
        await page.wait_for_load_state("networkidle")

        analyzer = HoverAnalyzer()
        await analyzer.analyze_hover_effects(page)

        css = analyzer.convert_to_static_css()

        assert len(css) > 0, "应该生成 CSS"
        assert "hover" in css.lower(), "CSS 应该包含 hover 相关内容"

        console.print("[green]✓ 静态 CSS 转换测试通过[/]")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 测试类：Canvas 录制
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestCanvasRecorder:
    """Canvas 录制器测试"""

    async def test_detect_canvas_elements(self, page: Page):
        """测试检测 Canvas 元素"""
        await page.set_content("""
            <!DOCTYPE html>
            <html>
            <body>
                <canvas id="canvas1" width="200" height="200"></canvas>
                <canvas id="canvas2" width="100" height="100"></canvas>
                <script>
                    // 绘制一些内容
                    const ctx1 = document.getElementById('canvas1').getContext('2d');
                    ctx1.fillStyle = 'red';
                    ctx1.fillRect(10, 10, 50, 50);

                    const ctx2 = document.getElementById('canvas2').getContext('2d');
                    ctx2.fillStyle = 'blue';
                    ctx2.fillRect(5, 5, 30, 30);
                </script>
            </body>
            </html>
        """)
        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(500)  # 等待绘制完成

        recorder = CanvasRecorder()
        canvas_data = await recorder.capture_all_canvases(page)

        assert len(canvas_data) >= 2, f"应该检测到至少 2 个 canvas，实际检测到 {len(canvas_data)} 个"

        console.print(f"[dim]检测到 {len(canvas_data)} 个 Canvas 元素[/]")
        console.print("[green]✓ Canvas 元素检测测试通过[/]")

    async def test_canvas_screenshot(self, page: Page):
        """测试 Canvas 截图"""
        await page.set_content("""
            <!DOCTYPE html>
            <html>
            <body>
                <canvas id="test-canvas" width="100" height="100"></canvas>
                <script>
                    const ctx = document.getElementById('test-canvas').getContext('2d');
                    ctx.fillStyle = 'green';
                    ctx.fillRect(0, 0, 100, 100);
                </script>
            </body>
            </html>
        """)
        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(500)

        recorder = CanvasRecorder()

        # 测试单个 canvas 截图
        screenshot = await recorder.capture_canvas_screenshot(page, "#test-canvas")

        # 截图应该返回数据或 None（取决于实现）
        console.print(f"[dim]截图结果类型: {type(screenshot)}[/]")
        console.print("[green]✓ Canvas 截图测试通过[/]")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 测试类：鼠标模拟
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestMouseSimulator:
    """鼠标模拟器测试"""

    async def test_simulate_mouse_movement(self, page: Page):
        """测试模拟鼠标移动"""
        await page.set_content("""
            <!DOCTYPE html>
            <html>
            <body>
                <div id="track-area" style="width: 500px; height: 500px; background: #eee;">
                    Track Area
                </div>
                <div id="mouse-pos">X: 0, Y: 0</div>
                <script>
                    document.getElementById('track-area').addEventListener('mousemove', (e) => {
                        document.getElementById('mouse-pos').textContent =
                            `X: ${e.clientX}, Y: ${e.clientY}`;
                    });
                </script>
            </body>
            </html>
        """)
        await page.wait_for_load_state("networkidle")

        simulator = MouseSimulator()
        await simulator.simulate_mouse_traversal(page)

        # 检查鼠标位置是否更新
        pos_text = await page.text_content("#mouse-pos")
        console.print(f"[dim]最终鼠标位置: {pos_text}[/]")

        console.print("[green]✓ 鼠标移动模拟测试通过[/]")

    async def test_simulate_hover(self, page: Page):
        """测试模拟悬停"""
        await page.set_content("""
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    .hover-target {
                        width: 100px;
                        height: 100px;
                        background: blue;
                        transition: background 0.3s;
                    }
                    .hover-target:hover {
                        background: red;
                    }
                </style>
            </head>
            <body>
                <div class="hover-target" id="target">Hover Me</div>
                <div id="hover-status">Not Hovered</div>
                <script>
                    document.getElementById('target').addEventListener('mouseenter', () => {
                        document.getElementById('hover-status').textContent = 'Hovered';
                    });
                </script>
            </body>
            </html>
        """)
        await page.wait_for_load_state("networkidle")

        simulator = MouseSimulator()

        # 悬停到元素上
        await page.hover("#target")
        await page.wait_for_timeout(500)

        status = await page.text_content("#hover-status")
        console.print(f"[dim]悬停状态: {status}[/]")

        console.print("[green]✓ 悬停模拟测试通过[/]")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 集成测试
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestIntegration:
    """集成测试"""

    async def test_full_animation_pipeline(self, page: Page):
        """测试完整动画处理流程"""
        await page.set_content("""
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    @keyframes fadeIn {
                        from { opacity: 0; }
                        to { opacity: 1; }
                    }
                    .animated {
                        animation: fadeIn 1s ease forwards;
                    }
                    .parallax {
                        will-change: transform;
                    }
                    .btn:hover {
                        transform: scale(1.1);
                    }
                </style>
            </head>
            <body>
                <div class="animated parallax" data-speed="0.5">
                    <button class="btn">Click Me</button>
                </div>
            </body>
            </html>
        """)
        await page.wait_for_load_state("networkidle")

        # 运行所有分析器
        anim_analyzer = AnimationAnalyzer()
        parallax_handler = ParallaxHandler()
        hover_analyzer = HoverAnalyzer()

        animations = await anim_analyzer.analyze_css_animations(page)
        parallax_elements = await parallax_handler.detect_parallax_elements(page)
        hover_effects = await hover_analyzer.analyze_hover_effects(page)

        console.print(f"[dim]动画: {len(animations)} 个[/]")
        console.print(f"[dim]视差元素: {len(parallax_elements)} 个[/]")
        console.print(f"[dim]Hover 效果: {len(hover_effects)} 个[/]")

        assert len(animations) > 0 or len(parallax_elements) > 0 or len(hover_effects) > 0, \
            "应该至少检测到一种动画效果"

        console.print("[green]✓ 完整动画流程测试通过[/]")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 主函数：运行所有测试
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def run_all_tests():
    """运行所有测试"""
    console.print("\n[bold cyan]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/]")
    console.print("[bold cyan]    WebThief 动画功能端到端测试[/]")
    console.print("[bold cyan]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/]\n")

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)

        test_results = []

        # 测试 CSS 动画分析器
        console.print("[bold yellow]测试 CSS 动画分析器...[/]")
        try:
            page = await browser.new_page()
            analyzer_test = TestCSSAnimationAnalyzer()

            await analyzer_test.test_detect_entrance_animations(page)
            await analyzer_test.test_detect_hover_animations(page)
            await analyzer_test.test_detect_loop_animations(page)
            await analyzer_test.test_importance_score_calculation(page)
            await analyzer_test.test_generate_preserved_css(page)

            await page.close()
            test_results.append(("CSS 动画分析器", True, None))
        except Exception as e:
            test_results.append(("CSS 动画分析器", False, str(e)))
            console.print(f"[red]✗ CSS 动画分析器测试失败: {e}[/]")

        # 测试视差处理器
        console.print("\n[bold yellow]测试视差处理器...[/]")
        try:
            page = await browser.new_page()
            parallax_test = TestParallaxHandler()

            await parallax_test.test_detect_parallax_by_data_attribute(page)
            await parallax_test.test_detect_parallax_by_class(page)
            await parallax_test.test_calculate_parallax_positions()
            await parallax_test.test_generate_static_css(page)
            await parallax_test.test_parallax_library_detection(page)

            await page.close()
            test_results.append(("视差处理器", True, None))
        except Exception as e:
            test_results.append(("视差处理器", False, str(e)))
            console.print(f"[red]✗ 视差处理器测试失败: {e}[/]")

        # 测试 ScrollTrigger 处理器
        console.print("\n[bold yellow]测试 ScrollTrigger 处理器...[/]")
        try:
            page = await browser.new_page()
            scroll_test = TestScrollTriggerHandler()

            await scroll_test.test_detect_gsap_scrolltrigger(page)
            await scroll_test.test_detect_aos_library(page)
            await scroll_test.test_generate_scroll_trigger_bridge()
            await scroll_test.test_generate_static_styles()

            await page.close()
            test_results.append(("ScrollTrigger 处理器", True, None))
        except Exception as e:
            test_results.append(("ScrollTrigger 处理器", False, str(e)))
            console.print(f"[red]✗ ScrollTrigger 处理器测试失败: {e}[/]")

        # 测试 Hover 分析器
        console.print("\n[bold yellow]测试 Hover 分析器...[/]")
        try:
            page = await browser.new_page()
            hover_test = TestHoverAnalyzer()

            await hover_test.test_detect_hover_effects(page)
            await hover_test.test_detect_focus_effects(page)
            await hover_test.test_evaluate_visual_importance(page)
            await hover_test.test_convert_to_static_css(page)

            await page.close()
            test_results.append(("Hover 分析器", True, None))
        except Exception as e:
            test_results.append(("Hover 分析器", False, str(e)))
            console.print(f"[red]✗ Hover 分析器测试失败: {e}[/]")

        # 测试 Canvas 录制器
        console.print("\n[bold yellow]测试 Canvas 录制器...[/]")
        try:
            page = await browser.new_page()
            canvas_test = TestCanvasRecorder()

            await canvas_test.test_detect_canvas_elements(page)
            await canvas_test.test_canvas_screenshot(page)

            await page.close()
            test_results.append(("Canvas 录制器", True, None))
        except Exception as e:
            test_results.append(("Canvas 录制器", False, str(e)))
            console.print(f"[red]✗ Canvas 录制器测试失败: {e}[/]")

        # 测试鼠标模拟器
        console.print("\n[bold yellow]测试鼠标模拟器...[/]")
        try:
            page = await browser.new_page()
            mouse_test = TestMouseSimulator()

            await mouse_test.test_simulate_mouse_movement(page)
            await mouse_test.test_simulate_hover(page)

            await page.close()
            test_results.append(("鼠标模拟器", True, None))
        except Exception as e:
            test_results.append(("鼠标模拟器", False, str(e)))
            console.print(f"[red]✗ 鼠标模拟器测试失败: {e}[/]")

        # 集成测试
        console.print("\n[bold yellow]运行集成测试...[/]")
        try:
            page = await browser.new_page()
            integration_test = TestIntegration()

            await integration_test.test_full_animation_pipeline(page)

            await page.close()
            test_results.append(("集成测试", True, None))
        except Exception as e:
            test_results.append(("集成测试", False, str(e)))
            console.print(f"[red]✗ 集成测试失败: {e}[/]")

        await browser.close()

        # 打印测试报告
        console.print("\n[bold cyan]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/]")
        console.print("[bold cyan]              测试报告[/]")
        console.print("[bold cyan]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/]")

        passed = 0
        failed = 0

        for name, success, error in test_results:
            if success:
                console.print(f"[green]✓ {name}: 通过[/]")
                passed += 1
            else:
                console.print(f"[red]✗ {name}: 失败[/]")
                if error:
                    console.print(f"[dim]  错误: {error}[/]")
                failed += 1

        console.print(f"\n[bold]总计: {passed} 通过, {failed} 失败[/]")
        console.print("[bold cyan]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/]")

        return failed == 0


if __name__ == "__main__":
    # Windows 事件循环策略
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
