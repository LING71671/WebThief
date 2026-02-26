"""
粒子系统拦截与处理模块
目标：检测并捕获网页中的粒子系统（particles.js、tsParticles、particle.js等），
      拦截粒子更新，将动态粒子转换为静态 SVG 或 Canvas 以保持视觉一致性
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from playwright.async_api import Page
from rich.console import Console

console = Console()


@dataclass
class ParticleConfig:
    """粒子配置数据类"""
    particle_count: int = 0
    particle_color: str = "#ffffff"
    particle_size: dict = field(default_factory=lambda: {"min": 1, "max": 3})
    particle_opacity: dict = field(default_factory=lambda: {"min": 0.1, "max": 1.0})
    particle_shape: str = "circle"
    line_linked: bool = False
    line_color: str = "#ffffff"
    line_opacity: float = 0.4
    move_speed: float = 1.0
    move_direction: str = "none"
    interactivity: dict = field(default_factory=dict)
    background_color: str = "transparent"


@dataclass
class ParticleState:
    """粒子状态数据类"""
    x: float = 0.0
    y: float = 0.0
    size: float = 1.0
    color: str = "#ffffff"
    opacity: float = 1.0
    vx: float = 0.0
    vy: float = 0.0


class ParticleHandler:
    """
    粒子系统处理器
    负责：
    1. 检测页面中的粒子系统库（particles.js、tsParticles、particle.js等）
    2. 拦截粒子系统的更新和渲染
    3. 捕获粒子位置、大小、颜色、透明度等属性
    4. 将动态粒子转换为静态 SVG 或 Canvas
    5. 保持视觉外观一致性
    """

    # 粒子库特征关键字
    PARTICLE_LIBRARY_KEYWORDS = [
        "particles.js",
        "tsparticles",
        "particle.js",
        "particlesjs",
        "particles.min.js",
        "ts-particles",
        "react-particles",
        "vue-particles",
        "angular-particles",
        "particles.vue",
    ]

    # 粒子容器选择器
    PARTICLE_CONTAINER_SELECTORS = [
        "#particles-js",
        "#tsparticles",
        ".particles-js",
        ".tsparticles",
        "[id*='particle']",
        "[class*='particle']",
        "canvas[data-particle]",
    ]

    def __init__(self):
        self.detected_libraries: list[str] = []
        self.particle_configs: list[ParticleConfig] = []
        self.captured_particles: list[ParticleState] = []
        self.container_elements: list[dict] = []
        self.is_interceptor_injected: bool = False

    async def detect_particle_system(self, page: Page) -> dict[str, Any]:
        """
        检测页面中的粒子系统
        识别 particles.js、tsParticles、particle.js 等粒子库

        Returns:
            检测结果字典，包含检测到的库、配置信息等
        """
        console.print("[cyan]  🔍 检测粒子系统...[/]")

        detection_script = """
        () => {
            const results = {
                libraries: [],
                containers: [],
                globalObjects: [],
                canvasElements: []
            };
            
            // 检测全局粒子对象
            const particleGlobals = [
                'particlesJS', 'pJSDom', 'tsParticles', 
                'Particles', 'particleJS', 'pJS'
            ];
            
            particleGlobals.forEach(name => {
                if (window[name] !== undefined) {
                    results.globalObjects.push({
                        name: name,
                        type: typeof window[name]
                    });
                }
            });
            
            // 检测粒子容器元素
            const containerSelectors = [
                '#particles-js', '#tsparticles', '.particles-js', '.tsparticles',
                '[id*="particle"]', '[class*="particle"]'
            ];
            
            containerSelectors.forEach(selector => {
                const elements = document.querySelectorAll(selector);
                elements.forEach(el => {
                    results.containers.push({
                        selector: selector,
                        id: el.id,
                        className: el.className,
                        tagName: el.tagName,
                        dimensions: {
                            width: el.offsetWidth,
                            height: el.offsetHeight
                        }
                    });
                });
            });
            
            // 检测 Canvas 粒子
            document.querySelectorAll('canvas').forEach(canvas => {
                const ctx = canvas.getContext('2d');
                if (ctx) {
                    // 检查是否有粒子特征
                    const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
                    const hasContent = imageData.data.some((val, idx) => 
                        idx % 4 === 3 && val > 0
                    );
                    
                    if (hasContent) {
                        results.canvasElements.push({
                            id: canvas.id,
                            className: canvas.className,
                            width: canvas.width,
                            height: canvas.height,
                            parentId: canvas.parentElement?.id,
                            parentClass: canvas.parentElement?.className
                        });
                    }
                }
            });
            
            // 检测脚本引用
            document.querySelectorAll('script[src]').forEach(script => {
                const src = script.src.toLowerCase();
                if (src.includes('particle') || src.includes('tsparticle')) {
                    results.libraries.push(script.src);
                }
            });
            
            return results;
        }
        """

        detection_result = await page.evaluate(detection_script)

        self.detected_libraries = detection_result.get("libraries", [])
        self.container_elements = detection_result.get("containers", [])

        console.print(f"[green]  ✓ 检测到 {len(self.detected_libraries)} 个粒子库[/]")
        console.print(f"[green]  ✓ 检测到 {len(self.container_elements)} 个粒子容器[/]")
        console.print(f"[green]  ✓ 检测到 {len(detection_result.get('globalObjects', []))} 个全局粒子对象[/]")

        return detection_result

    async def inject_particle_tracker(self, page: Page) -> None:
        """
        注入粒子系统追踪器
        拦截粒子系统的更新和渲染，捕获粒子属性
        """
        console.print("[cyan]  🔬 注入粒子追踪器...[/]")

        tracker_script = """
        (function() {
            'use strict';
            // ━━━ WebThief Particle Tracker Layer ━━━
            
            window.__webthief_particles = {
                data: [],
                configs: [],
                snapshots: [],
                isTracking: false
            };
            
            // 存储原始方法
            const _origRequestAnimationFrame = window.requestAnimationFrame;
            const _origCanvasRender = HTMLCanvasElement.prototype.getContext;
            
            // 粒子属性捕获
            function captureParticle(particle) {
                return {
                    x: particle.x || particle.position?.x || 0,
                    y: particle.y || particle.position?.y || 0,
                    size: particle.radius || particle.size || particle.radius_bubble || 1,
                    color: particle.color?.value || particle.color || '#ffffff',
                    opacity: particle.opacity?.value || particle.opacity || 1,
                    vx: particle.vx || particle.velocity?.x || 0,
                    vy: particle.vy || particle.velocity?.y || 0
                };
            }
            
            // 拦截 particlesJS
            if (window.particlesJS) {
                const _origParticlesJS = window.particlesJS;
                window.particlesJS = function(tag_id, params) {
                    console.log('[WebThief Particle Tracker] 拦截 particlesJS 初始化:', tag_id);
                    
                    window.__webthief_particles.configs.push({
                        library: 'particles.js',
                        containerId: tag_id,
                        config: params,
                        timestamp: Date.now()
                    });
                    
                    // 保存配置引用
                    window.__webthief_particles.currentConfig = params;
                    
                    return _origParticlesJS.apply(this, arguments);
                };
            }
            
            // 拦截 tsParticles
            if (window.tsParticles) {
                const _origTsParticlesLoad = window.tsParticles.load;
                window.tsParticles.load = function(tag_id, options) {
                    console.log('[WebThief Particle Tracker] 拦截 tsParticles 初始化:', tag_id);
                    
                    window.__webthief_particles.configs.push({
                        library: 'tsParticles',
                        containerId: tag_id,
                        config: options,
                        timestamp: Date.now()
                    });
                    
                    return _origTsParticlesLoad.apply(this, arguments);
                };
            }
            
            // 拦截 Canvas 2D Context 以捕获粒子绘制
            HTMLCanvasElement.prototype.getContext = function(type) {
                const ctx = _origCanvasRender.call(this, type);
                
                if (type === '2d' && ctx) {
                    // 检查是否为粒子画布
                    const isParticleCanvas = this.id?.includes('particle') || 
                                            this.className?.includes('particle') ||
                                            this.parentElement?.id?.includes('particle');
                    
                    if (isParticleCanvas && !this._webthief_tracked) {
                        this._webthief_tracked = true;
                        console.log('[WebThief Particle Tracker] 追踪 Canvas:', this.id || this.className);
                        
                        // 拦截 arc 方法（绘制圆形粒子）
                        const _origArc = ctx.arc;
                        ctx.arc = function(x, y, radius, startAngle, endAngle) {
                            window.__webthief_particles.data.push({
                                type: 'arc',
                                x: x,
                                y: y,
                                radius: radius,
                                timestamp: Date.now()
                            });
                            return _origArc.apply(this, arguments);
                        };
                        
                        // 拦截 fillRect 方法（绘制方形粒子）
                        const _origFillRect = ctx.fillRect;
                        ctx.fillRect = function(x, y, width, height) {
                            window.__webthief_particles.data.push({
                                type: 'rect',
                                x: x,
                                y: y,
                                width: width,
                                height: height,
                                timestamp: Date.now()
                            });
                            return _origFillRect.apply(this, arguments);
                        };
                        
                        // 拦截 fillStyle 以捕获颜色
                        let currentFillStyle = '#000000';
                        const _origFillStyle = Object.getOwnPropertyDescriptor(
                            CanvasRenderingContext2D.prototype, 'fillStyle'
                        );
                        
                        Object.defineProperty(ctx, 'fillStyle', {
                            get: function() {
                                return currentFillStyle;
                            },
                            set: function(value) {
                                currentFillStyle = value;
                                if (_origFillStyle && _origFillStyle.set) {
                                    _origFillStyle.set.call(this, value);
                                }
                            }
                        });
                    }
                }
                
                return ctx;
            };
            
            // 从 pJSDom 提取粒子数据
            function extractParticlesFromPJSDom() {
                if (window.pJSDom && window.pJSDom.length > 0) {
                    window.pJSDom.forEach((pjs, index) => {
                        if (pjs.pJS && pjs.pJS.particles) {
                            const particles = pjs.pJS.particles.array;
                            if (particles && particles.length > 0) {
                                const snapshot = particles.map(p => captureParticle(p));
                                window.__webthief_particles.snapshots.push({
                                    source: 'pJSDom[' + index + ']',
                                    particles: snapshot,
                                    count: particles.length,
                                    timestamp: Date.now()
                                });
                            }
                        }
                    });
                }
            }
            
            // 定期捕获粒子状态
            setInterval(function() {
                extractParticlesFromPJSDom();
            }, 1000);
            
            // 捕获粒子配置
            function captureParticleConfig() {
                // particles.js 配置
                if (window.pJSDom && window.pJSDom[0] && window.pJSDom[0].pJS) {
                    const pJS = window.pJSDom[0].pJS;
                    return {
                        library: 'particles.js',
                        particle_count: pJS.particles?.array?.length || 0,
                        particle_color: pJS.particles?.color?.value || '#ffffff',
                        particle_size: {
                            min: pJS.particles?.size?.value || 1,
                            max: pJS.particles?.size?.value || 3
                        },
                        particle_opacity: {
                            min: pJS.particles?.opacity?.value || 0.1,
                            max: pJS.particles?.opacity?.value || 1.0
                        },
                        particle_shape: pJS.particles?.shape?.type || 'circle',
                        line_linked: pJS.particles?.line_linked?.enable || false,
                        line_color: pJS.particles?.line_linked?.color?.value || '#ffffff',
                        line_opacity: pJS.particles?.line_linked?.opacity || 0.4,
                        move_speed: pJS.particles?.move?.speed || 1.0,
                        move_direction: pJS.particles?.move?.direction || 'none',
                        interactivity: pJS.interactivity || {},
                        background_color: pJS.canvas?.el?.style?.backgroundColor || 'transparent'
                    };
                }
                
                // tsParticles 配置
                if (window.tsParticles && window.tsParticles.domItem) {
                    const container = window.tsParticles.domItem(0);
                    if (container && container.options) {
                        const opts = container.options;
                        return {
                            library: 'tsParticles',
                            particle_count: container.particles?.count || 0,
                            particle_color: opts.particles?.color?.value || '#ffffff',
                            particle_size: {
                                min: opts.particles?.size?.value?.min || 1,
                                max: opts.particles?.size?.value?.max || 3
                            },
                            particle_opacity: {
                                min: opts.particles?.opacity?.value?.min || 0.1,
                                max: opts.particles?.opacity?.value?.max || 1.0
                            },
                            particle_shape: opts.particles?.shape?.type || 'circle',
                            line_linked: opts.particles?.links?.enable || false,
                            line_color: opts.particles?.links?.color?.value || '#ffffff',
                            line_opacity: opts.particles?.links?.opacity || 0.4,
                            move_speed: opts.particles?.move?.speed || 1.0,
                            move_direction: opts.particles?.move?.direction || 'none',
                            interactivity: opts.interactivity || {},
                            background_color: opts.background?.color?.value || 'transparent'
                        };
                    }
                }
                
                return null;
            }
            
            window.__webthief_particles.getConfig = captureParticleConfig;
            window.__webthief_particles.extractParticles = extractParticlesFromPJSDom;
            
            console.log('[WebThief Particle Tracker] 粒子追踪器已激活');
        })();
        """

        await page.add_init_script(tracker_script)
        self.is_interceptor_injected = True

        console.print("[green]  ✓ 粒子追踪器注入完成[/]")

    async def capture_particle_state(self, page: Page) -> list[ParticleState]:
        """
        捕获当前粒子状态
        获取所有粒子的位置、大小、颜色、透明度等属性

        Returns:
            粒子状态列表
        """
        console.print("[cyan]  📸 捕获粒子状态...[/]")

        capture_script = """
        () => {
            const particles = [];
            
            // 从追踪器获取数据
            if (window.__webthief_particles) {
                // 触发粒子提取
                if (window.__webthief_particles.extractParticles) {
                    window.__webthief_particles.extractParticles();
                }
                
                // 获取快照
                const snapshots = window.__webthief_particles.snapshots || [];
                snapshots.forEach(snapshot => {
                    if (snapshot.particles) {
                        particles.push(...snapshot.particles);
                    }
                });
            }
            
            // 直接从 pJSDom 获取
            if (window.pJSDom) {
                window.pJSDom.forEach(pjs => {
                    if (pjs.pJS && pjs.pJS.particles && pjs.pJS.particles.array) {
                        pjs.pJS.particles.array.forEach(p => {
                            particles.push({
                                x: p.x || 0,
                                y: p.y || 0,
                                size: p.radius || 1,
                                color: typeof p.color === 'object' ? p.color.value : p.color,
                                opacity: p.opacity?.value || p.opacity || 1,
                                vx: p.vx || 0,
                                vy: p.vy || 0
                            });
                        });
                    }
                });
            }
            
            // 获取配置
            const config = window.__webthief_particles?.getConfig ? 
                          window.__webthief_particles.getConfig() : null;
            
            return {
                particles: particles,
                config: config,
                canvasData: particles.length > 0 ? null : captureCanvasData()
            };
            
            function captureCanvasData() {
                const canvasData = [];
                document.querySelectorAll('canvas').forEach(canvas => {
                    if (canvas.id?.includes('particle') || canvas.className?.includes('particle')) {
                        try {
                            const dataUrl = canvas.toDataURL('image/png');
                            canvasData.push({
                                id: canvas.id,
                                width: canvas.width,
                                height: canvas.height,
                                dataUrl: dataUrl
                            });
                        } catch (e) {
                            console.warn('无法捕获 canvas:', e);
                        }
                    }
                });
                return canvasData;
            }
        }
        """

        result = await page.evaluate(capture_script)

        particle_data = result.get("particles", [])
        config_data = result.get("config", {})

        # 转换为 ParticleState 对象
        self.captured_particles = [
            ParticleState(
                x=p.get("x", 0),
                y=p.get("y", 0),
                size=p.get("size", p.get("radius", 1)),
                color=p.get("color", "#ffffff"),
                opacity=p.get("opacity", 1.0),
                vx=p.get("vx", 0),
                vy=p.get("vy", 0),
            )
            for p in particle_data
        ]

        # 保存配置
        if config_data:
            self.particle_configs.append(ParticleConfig(
                particle_count=config_data.get("particle_count", 0),
                particle_color=config_data.get("particle_color", "#ffffff"),
                particle_size=config_data.get("particle_size", {"min": 1, "max": 3}),
                particle_opacity=config_data.get("particle_opacity", {"min": 0.1, "max": 1.0}),
                particle_shape=config_data.get("particle_shape", "circle"),
                line_linked=config_data.get("line_linked", False),
                line_color=config_data.get("line_color", "#ffffff"),
                line_opacity=config_data.get("line_opacity", 0.4),
                move_speed=config_data.get("move_speed", 1.0),
                move_direction=config_data.get("move_direction", "none"),
                interactivity=config_data.get("interactivity", {}),
                background_color=config_data.get("background_color", "transparent"),
            ))

        console.print(f"[green]  ✓ 捕获 {len(self.captured_particles)} 个粒子[/]")

        return self.captured_particles

    async def convert_to_static(self, page: Page, output_format: str = "svg") -> str:
        """
        将动态粒子转换为静态 SVG 或 Canvas
        保持视觉外观一致性

        Args:
            page: Playwright Page 对象
            output_format: 输出格式，"svg" 或 "canvas"

        Returns:
            生成的静态内容（SVG 字符串或 Canvas 数据 URL）
        """
        console.print(f"[cyan]  🎨 转换为静态 {output_format.upper()}...[/]")

        if not self.captured_particles:
            await self.capture_particle_state(page)

        config = self.particle_configs[0] if self.particle_configs else ParticleConfig()

        if output_format.lower() == "svg":
            return self._generate_svg(config)
        else:
            return await self._generate_canvas(page, config)

    def _generate_svg(self, config: ParticleConfig) -> str:
        """
        生成静态 SVG

        Args:
            config: 粒子配置

        Returns:
            SVG 字符串
        """
        if not self.captured_particles:
            console.print("[yellow]  ⚠ 没有捕获到粒子数据[/]")
            return ""

        # 计算边界
        max_x = max((p.x for p in self.captured_particles), default=800)
        max_y = max((p.y for p in self.captured_particles), default=600)

        svg_width = int(max_x + 50)
        svg_height = int(max_y + 50)

        svg_parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{svg_width}" height="{svg_height}" viewBox="0 0 {svg_width} {svg_height}">',
            f'  <rect width="100%" height="100%" fill="{config.background_color}"/>',
        ]

        # 添加连接线
        if config.line_linked:
            lines = self._calculate_lines()
            for line in lines:
                svg_parts.append(
                    f'  <line x1="{line["x1"]:.1f}" y1="{line["y1"]:.1f}" '
                    f'x2="{line["x2"]:.1f}" y2="{line["y2"]:.1f}" '
                    f'stroke="{config.line_color}" '
                    f'stroke-opacity="{config.line_opacity}" '
                    f'stroke-width="1"/>'
                )

        # 添加粒子
        for particle in self.captured_particles:
            color = particle.color if particle.color else config.particle_color

            if config.particle_shape == "circle":
                svg_parts.append(
                    f'  <circle cx="{particle.x:.1f}" cy="{particle.y:.1f}" '
                    f'r="{particle.size:.1f}" '
                    f'fill="{color}" '
                    f'opacity="{particle.opacity:.2f}"/>'
                )
            elif config.particle_shape == "square":
                half_size = particle.size / 2
                svg_parts.append(
                    f'  <rect x="{particle.x - half_size:.1f}" y="{particle.y - half_size:.1f}" '
                    f'width="{particle.size:.1f}" height="{particle.size:.1f}" '
                    f'fill="{color}" '
                    f'opacity="{particle.opacity:.2f}"/>'
                )
            else:
                # 默认圆形
                svg_parts.append(
                    f'  <circle cx="{particle.x:.1f}" cy="{particle.y:.1f}" '
                    f'r="{particle.size:.1f}" '
                    f'fill="{color}" '
                    f'opacity="{particle.opacity:.2f}"/>'
                )

        svg_parts.append("</svg>")

        return "\n".join(svg_parts)

    async def _generate_canvas(self, page: Page, config: ParticleConfig) -> str:
        """
        生成静态 Canvas 数据 URL

        Args:
            page: Playwright Page 对象
            config: 粒子配置

        Returns:
            Canvas 数据 URL
        """
        canvas_script = """
        (particles, config, width, height) => {
            const canvas = document.createElement('canvas');
            canvas.width = width;
            canvas.height = height;
            const ctx = canvas.getContext('2d');
            
            // 填充背景
            if (config.background_color && config.background_color !== 'transparent') {
                ctx.fillStyle = config.background_color;
                ctx.fillRect(0, 0, width, height);
            }
            
            // 绘制连接线
            if (config.line_linked) {
                ctx.strokeStyle = config.line_color;
                ctx.globalAlpha = config.line_opacity;
                ctx.lineWidth = 1;
                
                for (let i = 0; i < particles.length; i++) {
                    for (let j = i + 1; j < particles.length; j++) {
                        const p1 = particles[i];
                        const p2 = particles[j];
                        const dx = p1.x - p2.x;
                        const dy = p1.y - p2.y;
                        const dist = Math.sqrt(dx * dx + dy * dy);
                        
                        if (dist < 100) {
                            ctx.beginPath();
                            ctx.moveTo(p1.x, p1.y);
                            ctx.lineTo(p2.x, p2.y);
                            ctx.stroke();
                        }
                    }
                }
            }
            
            // 绘制粒子
            particles.forEach(p => {
                ctx.globalAlpha = p.opacity;
                ctx.fillStyle = p.color || config.particle_color;
                
                if (config.particle_shape === 'circle') {
                    ctx.beginPath();
                    ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
                    ctx.fill();
                } else if (config.particle_shape === 'square') {
                    ctx.fillRect(p.x - p.size/2, p.y - p.size/2, p.size, p.size);
                } else {
                    ctx.beginPath();
                    ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
                    ctx.fill();
                }
            });
            
            ctx.globalAlpha = 1.0;
            return canvas.toDataURL('image/png');
        }
        """

        # 计算边界
        max_x = max((p.x for p in self.captured_particles), default=800)
        max_y = max((p.y for p in self.captured_particles), default=600)

        width = int(max_x + 50)
        height = int(max_y + 50)

        # 转换粒子数据为可序列化格式
        particles_data = [
            {
                "x": p.x,
                "y": p.y,
                "size": p.size,
                "color": p.color,
                "opacity": p.opacity,
            }
            for p in self.captured_particles
        ]

        config_data = {
            "particle_color": config.particle_color,
            "particle_shape": config.particle_shape,
            "line_linked": config.line_linked,
            "line_color": config.line_color,
            "line_opacity": config.line_opacity,
            "background_color": config.background_color,
        }

        data_url = await page.evaluate(
            canvas_script, particles_data, config_data, width, height
        )

        return data_url

    def _calculate_lines(self) -> list[dict]:
        """
        计算粒子之间的连接线

        Returns:
            连接线列表
        """
        lines = []
        link_distance = 100  # 连接距离阈值

        particles = self.captured_particles
        for i in range(len(particles)):
            for j in range(i + 1, len(particles)):
                p1 = particles[i]
                p2 = particles[j]

                dx = p1.x - p2.x
                dy = p1.y - p2.y
                distance = (dx ** 2 + dy ** 2) ** 0.5

                if distance < link_distance:
                    lines.append({
                        "x1": p1.x,
                        "y1": p1.y,
                        "x2": p2.x,
                        "y2": p2.y,
                        "distance": distance,
                    })

        return lines

    async def get_particle_report(self, page: Page) -> dict[str, Any]:
        """
        获取粒子系统报告

        Returns:
            包含粒子系统详细信息的报告字典
        """
        console.print("[cyan]  📊 生成粒子系统报告...[/]")

        await self._ensure_data_captured(page)
        config = self._get_current_config()

        report = self._build_report(config)
        self._print_report_summary(report)

        return report

    async def _ensure_data_captured(self, page: Page) -> None:
        """确保粒子数据已被捕获。"""
        if not self.captured_particles:
            await self.capture_particle_state(page)

    def _get_current_config(self) -> ParticleConfig:
        """获取当前粒子配置。"""
        return self.particle_configs[0] if self.particle_configs else ParticleConfig()

    def _build_report(self, config: ParticleConfig) -> dict[str, Any]:
        """构建完整的粒子系统报告。"""
        return {
            "summary": self._build_summary(),
            "configuration": self._build_configuration(config),
            "statistics": self._build_statistics(),
            "raw_data": self._build_raw_data(),
        }

    def _build_summary(self) -> dict[str, Any]:
        """构建报告摘要部分。"""
        return {
            "detected_libraries": self.detected_libraries,
            "container_elements": len(self.container_elements),
            "total_particles": len(self.captured_particles),
            "interceptor_injected": self.is_interceptor_injected,
        }

    def _build_configuration(self, config: ParticleConfig) -> dict[str, Any]:
        """构建报告配置部分。"""
        return {
            "particle_count": config.particle_count,
            "particle_color": config.particle_color,
            "particle_size": config.particle_size,
            "particle_opacity": config.particle_opacity,
            "particle_shape": config.particle_shape,
            "line_linked": config.line_linked,
            "line_color": config.line_color,
            "line_opacity": config.line_opacity,
            "move_speed": config.move_speed,
            "move_direction": config.move_direction,
            "background_color": config.background_color,
        }

    def _build_statistics(self) -> dict[str, Any]:
        """构建报告统计部分。"""
        total = len(self.captured_particles)
        return {
            "average_size": self._calculate_average_size(total),
            "average_opacity": self._calculate_average_opacity(total),
            "color_distribution": self._build_color_distribution(),
            "bounding_box": self._build_bounding_box(),
        }

    def _calculate_average_size(self, total: int) -> float:
        """计算平均粒子大小。"""
        if total == 0:
            return 0.0
        return round(sum(p.size for p in self.captured_particles) / total, 2)

    def _calculate_average_opacity(self, total: int) -> float:
        """计算平均粒子透明度。"""
        if total == 0:
            return 0.0
        return round(sum(p.opacity for p in self.captured_particles) / total, 2)

    def _build_color_distribution(self) -> dict[str, int]:
        """构建颜色分布统计。"""
        distribution: dict[str, int] = {}
        for particle in self.captured_particles:
            color = particle.color or "unknown"
            distribution[color] = distribution.get(color, 0) + 1
        return distribution

    def _build_bounding_box(self) -> dict[str, float]:
        """构建边界框信息。"""
        if not self.captured_particles:
            return {}

        min_x = min(p.x for p in self.captured_particles)
        max_x = max(p.x for p in self.captured_particles)
        min_y = min(p.y for p in self.captured_particles)
        max_y = max(p.y for p in self.captured_particles)

        return {
            "min_x": min_x,
            "max_x": max_x,
            "min_y": min_y,
            "max_y": max_y,
            "width": max_x - min_x,
            "height": max_y - min_y,
        }

    def _build_raw_data(self) -> dict[str, list[dict]]:
        """构建原始数据部分（限制数量）。"""
        return {
            "particles": [
                {
                    "x": p.x,
                    "y": p.y,
                    "size": p.size,
                    "color": p.color,
                    "opacity": p.opacity,
                    "vx": p.vx,
                    "vy": p.vy,
                }
                for p in self.captured_particles[:100]
            ],
        }

    def _print_report_summary(self, report: dict[str, Any]) -> None:
        """打印报告摘要到控制台。"""
        stats = report["statistics"]
        console.print("[green]  ✓ 报告生成完成[/]")
        console.print(f"[dim]     粒子数: {report['summary']['total_particles']}[/]")
        console.print(f"[dim]     平均大小: {stats['average_size']}[/]")
        console.print(f"[dim]     颜色种类: {len(stats['color_distribution'])}[/]")

    def generate_static_replacement_script(self) -> str:
        """
        生成静态替换脚本
        用于在克隆页面中将动态粒子替换为静态版本

        Returns:
            JavaScript 脚本字符串
        """
        svg_content = self._generate_svg(
            self.particle_configs[0] if self.particle_configs else ParticleConfig()
        )
        svg_escaped = json.dumps(svg_content)

        script = f"""
        (function() {{
            'use strict';
            // ━━━ WebThief Particle Static Replacement ━━━
            
            function replaceParticlesWithStatic() {{
                // 停止现有的粒子动画
                if (window.pJSDom) {{
                    window.pJSDom.forEach(function(pjs) {{
                        if (pjs.pJS && pjs.pJS.fn) {{
                            // 停止动画循环
                            pjs.pJS.fn.vendors.draw = function() {{}};
                            if (pjs.pJS.fn.vendors.checkBeforeDraw) {{
                                pjs.pJS.fn.vendors.checkBeforeDraw = function() {{}};
                            }}
                        }}
                    }});
                }}
                
                // 停止 tsParticles
                if (window.tsParticles) {{
                    try {{
                        window.tsParticles.dom().forEach(function(container) {{
                            container.pause();
                            container.stop();
                        }});
                    }} catch (e) {{}}
                }}
                
                // 查找粒子容器
                const selectors = [
                    '#particles-js', '#tsparticles', '.particles-js', '.tsparticles',
                    '[id*="particle"]', '[class*="particle"]'
                ];
                
                selectors.forEach(function(selector) {{
                    const containers = document.querySelectorAll(selector);
                    containers.forEach(function(container) {{
                        // 清空容器
                        container.innerHTML = '';
                        
                        // 插入静态 SVG
                        const svgData = {svg_escaped};
                        if (svgData) {{
                            container.innerHTML = svgData;
                            const svg = container.querySelector('svg');
                            if (svg) {{
                                svg.style.width = '100%';
                                svg.style.height = '100%';
                                svg.style.position = 'absolute';
                                svg.style.top = '0';
                                svg.style.left = '0';
                            }}
                        }}
                        
                        // 设置容器样式
                        container.style.position = 'relative';
                        container.style.overflow = 'hidden';
                    }});
                }});
                
                // 处理 Canvas 粒子
                document.querySelectorAll('canvas').forEach(function(canvas) {{
                    if (canvas.id?.includes('particle') || canvas.className?.includes('particle')) {{
                        const parent = canvas.parentElement;
                        if (parent) {{
                            const svgData = {svg_escaped};
                            if (svgData) {{
                                const div = document.createElement('div');
                                div.innerHTML = svgData;
                                const svg = div.querySelector('svg');
                                if (svg) {{
                                    svg.style.width = canvas.style.width || '100%';
                                    svg.style.height = canvas.style.height || '100%';
                                    parent.replaceChild(svg, canvas);
                                }}
                            }}
                        }}
                    }}
                }});
                
                console.log('[WebThief Particle] 粒子系统已替换为静态版本');
            }}
            
            // 页面加载完成后执行替换
            if (document.readyState === 'loading') {{
                document.addEventListener('DOMContentLoaded', replaceParticlesWithStatic);
            }} else {{
                replaceParticlesWithStatic();
            }}
        }})();
        """

        return script
