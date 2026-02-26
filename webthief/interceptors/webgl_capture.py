"""
WebGL 状态捕获与拦截模块
目标：捕获 WebGL 上下文状态、资源（shader、buffer、texture）和渲染结果
支持 WebGL 1.0 和 WebGL 2.0
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from playwright.async_api import Page
from rich.console import Console

console = Console()


@dataclass
class WebGLResourceInfo:
    """WebGL 资源信息基类"""
    id: str
    type: str
    created_at: int = field(default_factory=lambda: int(__import__('time').time() * 1000))


@dataclass
class ShaderProgramInfo(WebGLResourceInfo):
    """Shader Program 信息"""
    vertex_shader_source: str = ""
    fragment_shader_source: str = ""
    attributes: dict[str, Any] = field(default_factory=dict)
    uniforms: dict[str, Any] = field(default_factory=dict)


@dataclass
class BufferInfo(WebGLResourceInfo):
    """Buffer 信息"""
    target: int = 0
    usage: int = 0
    size: int = 0
    data_type: str = ""


@dataclass
class TextureInfo(WebGLResourceInfo):
    """Texture 信息"""
    target: int = 0
    width: int = 0
    height: int = 0
    internal_format: int = 0
    format_type: int = 0
    data_type: int = 0
    has_mipmaps: bool = False


@dataclass
class FramebufferInfo(WebGLResourceInfo):
    """Framebuffer 信息"""
    width: int = 0
    height: int = 0
    attachments: dict[str, Any] = field(default_factory=dict)


@dataclass
class WebGLContextInfo:
    """WebGL 上下文信息"""
    version: str = ""
    vendor: str = ""
    renderer: str = ""
    shading_language_version: str = ""
    max_texture_size: int = 0
    max_viewport_dims: list[int] = field(default_factory=list)
    extensions: list[str] = field(default_factory=list)
    parameters: dict[str, Any] = field(default_factory=dict)


class WebGLCapture:
    """
    WebGL 状态捕获器
    负责：
    1. 拦截 WebGL 上下文创建
    2. 记录 WebGL 资源（shader、buffer、texture、framebuffer）
    3. 捕获 WebGL 渲染结果
    4. 生成 WebGL 兼容层脚本
    """

    # WebGL 常量映射
    WEBGL_CONSTANTS = {
        # Buffer targets
        0x8892: "ARRAY_BUFFER",
        0x8893: "ELEMENT_ARRAY_BUFFER",
        # Buffer usage
        0x88E0: "STATIC_DRAW",
        0x88E4: "DYNAMIC_DRAW",
        0x88E8: "STREAM_DRAW",
        # Texture targets
        0x0DE1: "TEXTURE_2D",
        0x8513: "TEXTURE_CUBE_MAP",
        # Texture formats
        0x1902: "DEPTH_COMPONENT",
        0x1906: "ALPHA",
        0x1907: "RGB",
        0x1908: "RGBA",
        0x1909: "LUMINANCE",
        0x190A: "LUMINANCE_ALPHA",
        # Framebuffer attachments
        0x8CE0: "COLOR_ATTACHMENT0",
        0x8D00: "DEPTH_ATTACHMENT",
        0x8D20: "STENCIL_ATTACHMENT",
        0x821A: "DEPTH_STENCIL_ATTACHMENT",
    }

    def __init__(self):
        self.shader_programs: dict[str, ShaderProgramInfo] = {}
        self.buffers: dict[str, BufferInfo] = {}
        self.textures: dict[str, TextureInfo] = {}
        self.framebuffers: dict[str, FramebufferInfo] = {}
        self.context_info: WebGLContextInfo | None = None
        self.captured_screenshots: list[dict[str, Any]] = []
        self.webgl_contexts: list[dict[str, Any]] = []

    async def inject_webgl_tracker(self, page: Page) -> None:
        """
        注入 WebGL 追踪层脚本
        在页面加载前注入，拦截所有 WebGL 上下文创建和调用
        """
        console.print("[cyan]  🎨 注入 WebGL 追踪层...[/]")

        tracker_script = """
        (function() {
            'use strict';
            // ━━━ WebThief WebGL Tracker Layer ━━━
            
            // WebGL 资源存储
            window.__webthief_webgl = {
                contexts: [],
                shaderPrograms: {},
                buffers: {},
                textures: {},
                framebuffers: {},
                renderbuffers: {},
                callHistory: [],
                maxHistorySize: 1000
            };
            
            // 生成唯一 ID
            function generateId() {
                return 'webgl_' + Math.random().toString(36).substr(2, 9) + '_' + Date.now();
            }
            
            // 记录 WebGL 调用
            function logWebGLCall(method, args, context) {
                const entry = {
                    method: method,
                    args: args ? Array.from(args).map(arg => {
                        if (arg instanceof WebGLBuffer) return { type: 'WebGLBuffer', id: arg.__webthief_id };
                        if (arg instanceof WebGLTexture) return { type: 'WebGLTexture', id: arg.__webthief_id };
                        if (arg instanceof WebGLShader) return { type: 'WebGLShader', id: arg.__webthief_id };
                        if (arg instanceof WebGLProgram) return { type: 'WebGLProgram', id: arg.__webthief_id };
                        if (arg instanceof WebGLFramebuffer) return { type: 'WebGLFramebuffer', id: arg.__webthief_id };
                        if (arg instanceof WebGLRenderbuffer) return { type: 'WebGLRenderbuffer', id: arg.__webthief_id };
                        if (arg instanceof ArrayBuffer || arg instanceof Uint8Array) return { type: 'ArrayBuffer', length: arg.byteLength };
                        if (arg instanceof HTMLImageElement) return { type: 'HTMLImageElement', src: arg.src?.substring(0, 100) };
                        if (arg instanceof HTMLCanvasElement) return { type: 'HTMLCanvasElement', width: arg.width, height: arg.height };
                        if (arg instanceof ImageData) return { type: 'ImageData', width: arg.width, height: arg.height };
                        return arg;
                    }) : [],
                    timestamp: Date.now(),
                    contextId: context?.__webthief_id
                };
                
                window.__webthief_webgl.callHistory.push(entry);
                if (window.__webthief_webgl.callHistory.length > window.__webthief_webgl.maxHistorySize) {
                    window.__webthief_webgl.callHistory.shift();
                }
            }
            
            // 拦截 getContext 以捕获 WebGL 上下文
            const _origGetContext = HTMLCanvasElement.prototype.getContext;
            HTMLCanvasElement.prototype.getContext = function(contextType, contextAttributes) {
                const isWebGL = contextType === 'webgl' || contextType === 'experimental-webgl' || 
                               contextType === 'webgl2' || contextType === 'experimental-webgl2';
                
                if (isWebGL) {
                    console.log('[WebThief WebGL] 检测到 WebGL 上下文创建:', contextType);
                    
                    const gl = _origGetContext.call(this, contextType, contextAttributes);
                    if (!gl) return null;
                    
                    // 标记上下文
                    gl.__webthief_id = generateId();
                    gl.__webthief_type = contextType;
                    gl.__webthief_canvas = this;
                    
                    // 存储上下文信息
                    const contextInfo = {
                        id: gl.__webthief_id,
                        type: contextType,
                        attributes: contextAttributes || {},
                        canvas: { width: this.width, height: this.height },
                        createdAt: Date.now()
                    };
                    window.__webthief_webgl.contexts.push(contextInfo);
                    
                    // 拦截 WebGL 方法
                    interceptWebGLMethods(gl, contextType);
                    
                    return gl;
                }
                
                return _origGetContext.apply(this, arguments);
            };
            
            // 拦截 WebGL 方法
            function interceptWebGLMethods(gl, contextType) {
                const isWebGL2 = contextType.includes('webgl2');
                
                // 拦截 createShader
                const _origCreateShader = gl.createShader;
                gl.createShader = function(type) {
                    const shader = _origCreateShader.call(this, type);
                    if (shader) {
                        shader.__webthief_id = generateId();
                        shader.__webthief_type = type === gl.VERTEX_SHADER ? 'VERTEX_SHADER' : 'FRAGMENT_SHADER';
                        shader.__webthief_context = this.__webthief_id;
                    }
                    logWebGLCall('createShader', arguments, this);
                    return shader;
                };
                
                // 拦截 shaderSource
                const _origShaderSource = gl.shaderSource;
                gl.shaderSource = function(shader, source) {
                    if (shader) {
                        shader.__webthief_source = source;
                    }
                    logWebGLCall('shaderSource', arguments, this);
                    return _origShaderSource.call(this, shader, source);
                };
                
                // 拦截 createProgram
                const _origCreateProgram = gl.createProgram;
                gl.createProgram = function() {
                    const program = _origCreateProgram.call(this);
                    if (program) {
                        program.__webthief_id = generateId();
                        program.__webthief_context = this.__webthief_id;
                        program.__webthief_shaders = [];
                    }
                    logWebGLCall('createProgram', arguments, this);
                    return program;
                };
                
                // 拦截 attachShader
                const _origAttachShader = gl.attachShader;
                gl.attachShader = function(program, shader) {
                    if (program && shader) {
                        if (!program.__webthief_shaders) program.__webthief_shaders = [];
                        program.__webthief_shaders.push({
                            id: shader.__webthief_id,
                            type: shader.__webthief_type,
                            source: shader.__webthief_source
                        });
                    }
                    logWebGLCall('attachShader', arguments, this);
                    return _origAttachShader.call(this, program, shader);
                };
                
                // 拦截 linkProgram
                const _origLinkProgram = gl.linkProgram;
                gl.linkProgram = function(program) {
                    const result = _origLinkProgram.call(this, program);
                    if (program) {
                        // 获取 active attributes
                        const numAttribs = gl.getProgramParameter(program, gl.ACTIVE_ATTRIBUTES);
                        program.__webthief_attributes = {};
                        for (let i = 0; i < numAttribs; i++) {
                            const info = gl.getActiveAttrib(program, i);
                            if (info) {
                                program.__webthief_attributes[info.name] = {
                                    location: gl.getAttribLocation(program, info.name),
                                    size: info.size,
                                    type: info.type
                                };
                            }
                        }
                        
                        // 获取 active uniforms
                        const numUniforms = gl.getProgramParameter(program, gl.ACTIVE_UNIFORMS);
                        program.__webthief_uniforms = {};
                        for (let i = 0; i < numUniforms; i++) {
                            const info = gl.getActiveUniform(program, i);
                            if (info) {
                                program.__webthief_uniforms[info.name] = {
                                    location: gl.getUniformLocation(program, info.name),
                                    size: info.size,
                                    type: info.type
                                };
                            }
                        }
                        
                        // 存储到全局
                        window.__webthief_webgl.shaderPrograms[program.__webthief_id] = {
                            id: program.__webthief_id,
                            contextId: this.__webthief_id,
                            shaders: program.__webthief_shaders,
                            attributes: program.__webthief_attributes,
                            uniforms: program.__webthief_uniforms,
                            linkedAt: Date.now()
                        };
                    }
                    logWebGLCall('linkProgram', arguments, this);
                    return result;
                };
                
                // 拦截 createBuffer
                const _origCreateBuffer = gl.createBuffer;
                gl.createBuffer = function() {
                    const buffer = _origCreateBuffer.call(this);
                    if (buffer) {
                        buffer.__webthief_id = generateId();
                        buffer.__webthief_context = this.__webthief_id;
                    }
                    logWebGLCall('createBuffer', arguments, this);
                    return buffer;
                };
                
                // 拦截 bindBuffer
                const _origBindBuffer = gl.bindBuffer;
                gl.bindBuffer = function(target, buffer) {
                    this.__webthief_current_buffer_target = target;
                    if (buffer) {
                        buffer.__webthief_target = target;
                    }
                    logWebGLCall('bindBuffer', arguments, this);
                    return _origBindBuffer.call(this, target, buffer);
                };
                
                // 拦截 bufferData
                const _origBufferData = gl.bufferData;
                gl.bufferData = function(target, data, usage) {
                    // 找到当前绑定的 buffer
                    const buffer = this.getParameter(target === this.ELEMENT_ARRAY_BUFFER ? 
                        this.ELEMENT_ARRAY_BUFFER_BINDING : this.ARRAY_BUFFER_BINDING);
                    if (buffer && buffer.__webthief_id) {
                        window.__webthief_webgl.buffers[buffer.__webthief_id] = {
                            id: buffer.__webthief_id,
                            target: target,
                            usage: usage,
                            size: data?.byteLength || data,
                            dataType: data?.constructor?.name || 'number',
                            updatedAt: Date.now()
                        };
                    }
                    logWebGLCall('bufferData', arguments, this);
                    return _origBufferData.call(this, target, data, usage);
                };
                
                // 拦截 createTexture
                const _origCreateTexture = gl.createTexture;
                gl.createTexture = function() {
                    const texture = _origCreateTexture.call(this);
                    if (texture) {
                        texture.__webthief_id = generateId();
                        texture.__webthief_context = this.__webthief_id;
                    }
                    logWebGLCall('createTexture', arguments, this);
                    return texture;
                };
                
                // 拦截 bindTexture
                const _origBindTexture = gl.bindTexture;
                gl.bindTexture = function(target, texture) {
                    if (texture) {
                        texture.__webthief_target = target;
                    }
                    logWebGLCall('bindTexture', arguments, this);
                    return _origBindTexture.call(this, target, texture);
                };
                
                // 拦截 texImage2D
                const _origTexImage2D = gl.texImage2D;
                gl.texImage2D = function(target, level, internalFormat, width, height, border, format, type, pixels) {
                    const texture = this.getParameter(this.TEXTURE_BINDING_2D);
                    if (texture && texture.__webthief_id) {
                        const w = typeof width === 'number' ? width : (pixels?.width || 0);
                        const h = typeof height === 'number' ? height : (pixels?.height || 0);
                        window.__webthief_webgl.textures[texture.__webthief_id] = {
                            id: texture.__webthief_id,
                            target: target,
                            internalFormat: internalFormat,
                            format: format,
                            type: type,
                            width: w,
                            height: h,
                            hasMipmaps: level > 0,
                            updatedAt: Date.now()
                        };
                    }
                    logWebGLCall('texImage2D', arguments, this);
                    return _origTexImage2D.apply(this, arguments);
                };
                
                // 拦截 createFramebuffer
                const _origCreateFramebuffer = gl.createFramebuffer;
                gl.createFramebuffer = function() {
                    const fb = _origCreateFramebuffer.call(this);
                    if (fb) {
                        fb.__webthief_id = generateId();
                        fb.__webthief_context = this.__webthief_id;
                    }
                    logWebGLCall('createFramebuffer', arguments, this);
                    return fb;
                };
                
                // 拦截 bindFramebuffer
                const _origBindFramebuffer = gl.bindFramebuffer;
                gl.bindFramebuffer = function(target, framebuffer) {
                    if (framebuffer) {
                        framebuffer.__webthief_target = target;
                    }
                    logWebGLCall('bindFramebuffer', arguments, this);
                    return _origBindFramebuffer.call(this, target, framebuffer);
                };
                
                // 拦截 framebufferTexture2D
                const _origFramebufferTexture2D = gl.framebufferTexture2D;
                gl.framebufferTexture2D = function(target, attachment, textarget, texture, level) {
                    const fb = this.getParameter(this.FRAMEBUFFER_BINDING);
                    if (fb && fb.__webthief_id) {
                        if (!window.__webthief_webgl.framebuffers[fb.__webthief_id]) {
                            window.__webthief_webgl.framebuffers[fb.__webthief_id] = {
                                id: fb.__webthief_id,
                                attachments: {}
                            };
                        }
                        window.__webthief_webgl.framebuffers[fb.__webthief_id].attachments[attachment] = {
                            type: 'texture',
                            textureId: texture?.__webthief_id,
                            target: textarget,
                            level: level
                        };
                    }
                    logWebGLCall('framebufferTexture2D', arguments, this);
                    return _origFramebufferTexture2D.call(this, target, attachment, textarget, texture, level);
                };
                
                // 拦截 drawArrays 和 drawElements
                const _origDrawArrays = gl.drawArrays;
                gl.drawArrays = function(mode, first, count) {
                    logWebGLCall('drawArrays', arguments, this);
                    return _origDrawArrays.call(this, mode, first, count);
                };
                
                const _origDrawElements = gl.drawElements;
                gl.drawElements = function(mode, count, type, offset) {
                    logWebGLCall('drawElements', arguments, this);
                    return _origDrawElements.call(this, mode, count, type, offset);
                };
                
                // 拦截 viewport
                const _origViewport = gl.viewport;
                gl.viewport = function(x, y, width, height) {
                    this.__webthief_viewport = { x, y, width, height };
                    logWebGLCall('viewport', arguments, this);
                    return _origViewport.call(this, x, y, width, height);
                };
                
                // 拦截 clear
                const _origClear = gl.clear;
                gl.clear = function(mask) {
                    logWebGLCall('clear', arguments, this);
                    return _origClear.call(this, mask);
                };
                
                // WebGL2 特定方法
                if (isWebGL2) {
                    // 拦截 createVertexArray
                    if (gl.createVertexArray) {
                        const _origCreateVAO = gl.createVertexArray;
                        gl.createVertexArray = function() {
                            const vao = _origCreateVAO.call(this);
                            if (vao) {
                                vao.__webthief_id = generateId();
                                vao.__webthief_context = this.__webthief_id;
                            }
                            logWebGLCall('createVertexArray', arguments, this);
                            return vao;
                        };
                    }
                    
                    // 拦截 texStorage2D
                    if (gl.texStorage2D) {
                        const _origTexStorage2D = gl.texStorage2D;
                        gl.texStorage2D = function(target, levels, internalFormat, width, height) {
                            const texture = this.getParameter(this.TEXTURE_BINDING_2D);
                            if (texture && texture.__webthief_id) {
                                window.__webthief_webgl.textures[texture.__webthief_id] = {
                                    id: texture.__webthief_id,
                                    target: target,
                                    internalFormat: internalFormat,
                                    width: width,
                                    height: height,
                                    levels: levels,
                                    isImmutable: true,
                                    updatedAt: Date.now()
                                };
                            }
                            logWebGLCall('texStorage2D', arguments, this);
                            return _origTexStorage2D.call(this, target, levels, internalFormat, width, height);
                        };
                    }
                }
            }
            
            console.log('[WebThief WebGL] WebGL 追踪层已激活');
        })();
        """

        await page.add_init_script(tracker_script)

    async def capture_webgl_screenshot(self, page: Page, selector: str = "canvas") -> dict[str, Any] | None:
        """
        捕获 WebGL 场景截图
        通过读取 canvas 像素数据作为 fallback 方案
        
        Args:
            page: Playwright Page 对象
            selector: Canvas 元素选择器
            
        Returns:
            截图信息字典，包含 base64 图片数据和元数据
        """
        console.print(f"[cyan]  📸 捕获 WebGL 截图: {selector}[/]")

        screenshot_data = await page.evaluate(
            """
            (selector) => {
                const canvas = document.querySelector(selector);
                if (!canvas) {
                    return { error: 'Canvas not found' };
                }
                
                try {
                    // 尝试使用 toDataURL 获取截图
                    const dataUrl = canvas.toDataURL('image/png');
                    
                    // 获取 canvas 尺寸
                    const rect = canvas.getBoundingClientRect();
                    
                    // 尝试获取 WebGL 上下文信息
                    let glInfo = null;
                    const gl = canvas.getContext('webgl') || canvas.getContext('webgl2') || 
                               canvas.getContext('experimental-webgl') || canvas.getContext('experimental-webgl2');
                    
                    if (gl) {
                        glInfo = {
                            version: gl.getParameter(gl.VERSION),
                            vendor: gl.getParameter(gl.VENDOR),
                            renderer: gl.getParameter(gl.RENDERER),
                            maxTextureSize: gl.getParameter(gl.MAX_TEXTURE_SIZE),
                            maxViewportDims: gl.getParameter(gl.MAX_VIEWPORT_DIMS)
                        };
                    }
                    
                    return {
                        success: true,
                        dataUrl: dataUrl,
                        width: canvas.width,
                        height: canvas.height,
                        displayWidth: rect.width,
                        displayHeight: rect.height,
                        glInfo: glInfo,
                        timestamp: Date.now()
                    };
                } catch (e) {
                    return { error: e.message };
                }
            }
            """,
            selector
        )

        if screenshot_data.get("success"):
            self.captured_screenshots.append(screenshot_data)
            console.print(f"[green]  ✓ WebGL 截图已捕获: {screenshot_data['width']}x{screenshot_data['height']}[/]")
        else:
            console.print(f"[red]  ✗ 截图失败: {screenshot_data.get('error', 'Unknown error')}[/]")

        return screenshot_data

    async def get_webgl_info(self, page: Page, selector: str = "canvas") -> WebGLContextInfo | None:
        """
        获取 WebGL 上下文详细信息
        
        Args:
            page: Playwright Page 对象
            selector: Canvas 元素选择器
            
        Returns:
            WebGLContextInfo 对象，包含版本、扩展、参数等信息
        """
        console.print(f"[cyan]  ℹ️  获取 WebGL 信息...[/]")

        webgl_info = await page.evaluate(
            """
            (selector) => {
                const canvas = document.querySelector(selector);
                if (!canvas) {
                    return { error: 'Canvas not found' };
                }
                
                // 尝试获取 WebGL2 上下文，回退到 WebGL1
                let gl = canvas.getContext('webgl2') || canvas.getContext('experimental-webgl2');
                let version = 'WebGL 2.0';
                
                if (!gl) {
                    gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
                    version = 'WebGL 1.0';
                }
                
                if (!gl) {
                    return { error: 'WebGL not supported' };
                }
                
                // 获取扩展列表
                const extensions = gl.getSupportedExtensions() || [];
                
                // 获取常用参数
                const parameters = {
                    MAX_TEXTURE_SIZE: gl.getParameter(gl.MAX_TEXTURE_SIZE),
                    MAX_CUBE_MAP_TEXTURE_SIZE: gl.getParameter(gl.MAX_CUBE_MAP_TEXTURE_SIZE),
                    MAX_RENDERBUFFER_SIZE: gl.getParameter(gl.MAX_RENDERBUFFER_SIZE),
                    MAX_VIEWPORT_DIMS: gl.getParameter(gl.MAX_VIEWPORT_DIMS),
                    MAX_VERTEX_ATTRIBS: gl.getParameter(gl.MAX_VERTEX_ATTRIBS),
                    MAX_VERTEX_UNIFORM_VECTORS: gl.getParameter(gl.MAX_VERTEX_UNIFORM_VECTORS),
                    MAX_FRAGMENT_UNIFORM_VECTORS: gl.getParameter(gl.MAX_FRAGMENT_UNIFORM_VECTORS),
                    MAX_TEXTURE_IMAGE_UNITS: gl.getParameter(gl.MAX_TEXTURE_IMAGE_UNITS),
                    MAX_VERTEX_TEXTURE_IMAGE_UNITS: gl.getParameter(gl.MAX_VERTEX_TEXTURE_IMAGE_UNITS),
                    MAX_COMBINED_TEXTURE_IMAGE_UNITS: gl.getParameter(gl.MAX_COMBINED_TEXTURE_IMAGE_UNITS),
                    MAX_DRAW_BUFFERS: gl.getParameter(gl.MAX_DRAW_BUFFERS),
                    RED_BITS: gl.getParameter(gl.RED_BITS),
                    GREEN_BITS: gl.getParameter(gl.GREEN_BITS),
                    BLUE_BITS: gl.getParameter(gl.BLUE_BITS),
                    ALPHA_BITS: gl.getParameter(gl.ALPHA_BITS),
                    DEPTH_BITS: gl.getParameter(gl.DEPTH_BITS),
                    STENCIL_BITS: gl.getParameter(gl.STENCIL_BITS),
                    SAMPLE_BUFFERS: gl.getParameter(gl.SAMPLE_BUFFERS),
                    SAMPLES: gl.getParameter(gl.SAMPLES)
                };
                
                // WebGL2 特有参数
                if (version === 'WebGL 2.0') {
                    parameters.MAX_3D_TEXTURE_SIZE = gl.getParameter(gl.MAX_3D_TEXTURE_SIZE);
                    parameters.MAX_ARRAY_TEXTURE_LAYERS = gl.getParameter(gl.MAX_ARRAY_TEXTURE_LAYERS);
                    parameters.MAX_COLOR_ATTACHMENTS = gl.getParameter(gl.MAX_COLOR_ATTACHMENTS);
                    parameters.MAX_UNIFORM_BUFFER_BINDINGS = gl.getParameter(gl.MAX_UNIFORM_BUFFER_BINDINGS);
                }
                
                return {
                    version: version,
                    vendor: gl.getParameter(gl.VENDOR),
                    renderer: gl.getParameter(gl.RENDERER),
                    shadingLanguageVersion: gl.getParameter(gl.SHADING_LANGUAGE_VERSION),
                    maxTextureSize: gl.getParameter(gl.MAX_TEXTURE_SIZE),
                    maxViewportDims: gl.getParameter(gl.MAX_VIEWPORT_DIMS),
                    extensions: extensions,
                    parameters: parameters,
                    contextAttributes: gl.getContextAttributes()
                };
            }
            """,
            selector
        )

        if webgl_info.get("error"):
            console.print(f"[red]  ✗ 获取 WebGL 信息失败: {webgl_info['error']}[/]")
            return None

        self.context_info = WebGLContextInfo(
            version=webgl_info.get("version", ""),
            vendor=webgl_info.get("vendor", ""),
            renderer=webgl_info.get("renderer", ""),
            shading_language_version=webgl_info.get("shadingLanguageVersion", ""),
            max_texture_size=webgl_info.get("maxTextureSize", 0),
            max_viewport_dims=webgl_info.get("maxViewportDims", []),
            extensions=webgl_info.get("extensions", []),
            parameters=webgl_info.get("parameters", {})
        )

        console.print(f"[green]  ✓ WebGL 信息已获取: {self.context_info.version}[/]")
        console.print(f"[dim]     Vendor: {self.context_info.vendor}[/]")
        console.print(f"[dim]     Renderer: {self.context_info.renderer}[/]")
        console.print(f"[dim]     Extensions: {len(self.context_info.extensions)}[/]")

        return self.context_info

    async def capture_webgl_resources(self, page: Page) -> dict[str, Any]:
        """
        捕获页面中所有的 WebGL 资源
        
        Args:
            page: Playwright Page 对象
            
        Returns:
            包含所有 WebGL 资源的字典
        """
        console.print("[cyan]  📦 捕获 WebGL 资源...[/]")

        resources = await page.evaluate("""
            () => {
                const data = window.__webthief_webgl || {
                    contexts: [],
                    shaderPrograms: {},
                    buffers: {},
                    textures: {},
                    framebuffers: {},
                    callHistory: []
                };
                
                return {
                    contextCount: data.contexts.length,
                    shaderProgramCount: Object.keys(data.shaderPrograms).length,
                    bufferCount: Object.keys(data.buffers).length,
                    textureCount: Object.keys(data.textures).length,
                    framebufferCount: Object.keys(data.framebuffers).length,
                    callHistoryLength: data.callHistory.length,
                    contexts: data.contexts,
                    shaderPrograms: data.shaderPrograms,
                    buffers: data.buffers,
                    textures: data.textures,
                    framebuffers: data.framebuffers,
                    recentCalls: data.callHistory.slice(-50)
                };
            }
        """)

        # 更新本地存储
        for prog_id, prog_data in resources.get("shaderPrograms", {}).items():
            self.shader_programs[prog_id] = ShaderProgramInfo(
                id=prog_id,
                type="program",
                vertex_shader_source=next(
                    (s.get("source", "") for s in prog_data.get("shaders", []) if s.get("type") == "VERTEX_SHADER"),
                    ""
                ),
                fragment_shader_source=next(
                    (s.get("source", "") for s in prog_data.get("shaders", []) if s.get("type") == "FRAGMENT_SHADER"),
                    ""
                ),
                attributes=prog_data.get("attributes", {}),
                uniforms=prog_data.get("uniforms", {})
            )

        for buf_id, buf_data in resources.get("buffers", {}).items():
            self.buffers[buf_id] = BufferInfo(
                id=buf_id,
                type="buffer",
                target=buf_data.get("target", 0),
                usage=buf_data.get("usage", 0),
                size=buf_data.get("size", 0),
                data_type=buf_data.get("dataType", "")
            )

        for tex_id, tex_data in resources.get("textures", {}).items():
            self.textures[tex_id] = TextureInfo(
                id=tex_id,
                type="texture",
                target=tex_data.get("target", 0),
                width=tex_data.get("width", 0),
                height=tex_data.get("height", 0),
                internal_format=tex_data.get("internalFormat", 0),
                format_type=tex_data.get("format", 0),
                data_type=tex_data.get("type", 0),
                has_mipmaps=tex_data.get("hasMipmaps", False)
            )

        for fb_id, fb_data in resources.get("framebuffers", {}).items():
            self.framebuffers[fb_id] = FramebufferInfo(
                id=fb_id,
                type="framebuffer",
                attachments=fb_data.get("attachments", {})
            )

        console.print(f"[green]  ✓ 捕获 {resources['contextCount']} 个 WebGL 上下文[/]")
        console.print(f"[green]  ✓ 捕获 {resources['shaderProgramCount']} 个 Shader Program[/]")
        console.print(f"[green]  ✓ 捕获 {resources['bufferCount']} 个 Buffer[/]")
        console.print(f"[green]  ✓ 捕获 {resources['textureCount']} 个 Texture[/]")
        console.print(f"[green]  ✓ 捕获 {resources['framebufferCount']} 个 Framebuffer[/]")

        return resources

    def generate_webgl_bridge_script(self, original_domain: str) -> str:
        """
        生成 WebGL 兼容层脚本
        使克隆页面能够正确处理 WebGL 上下文和资源
        
        Args:
            original_domain: 原始域名，用于处理跨域资源
            
        Returns:
            JavaScript 桥接脚本字符串
        """
        bridge_script = f"""
        (function() {{
            'use strict';
            // ━━━ WebThief WebGL Bridge Script ━━━
            
            const ORIGINAL_DOMAIN = '{original_domain}';
            
            // WebGL 资源缓存
            const resourceCache = {{
                textures: new Map(),
                shaders: new Map(),
                programs: new Map()
            }};
            
            // 创建 CORS 代理 URL
            function createCORSProxy(url) {{
                if (!url || typeof url !== 'string') return url;
                if (url.startsWith('data:') || url.startsWith('blob:')) return url;
                
                try {{
                    const urlObj = new URL(url, window.location.href);
                    if (urlObj.origin !== window.location.origin) {{
                        // 跨域资源，使用代理
                        return ORIGINAL_DOMAIN + '/proxy?url=' + encodeURIComponent(url);
                    }}
                    return url;
                }} catch (e) {{
                    return url;
                }}
            }}
            
            // 保存原始 getContext
            const _origGetContext = HTMLCanvasElement.prototype.getContext;
            
            // 拦截 getContext
            HTMLCanvasElement.prototype.getContext = function(contextType, contextAttributes) {{
                const isWebGL = contextType === 'webgl' || contextType === 'experimental-webgl' || 
                               contextType === 'webgl2' || contextType === 'experimental-webgl2';
                
                if (isWebGL) {{
                    console.log('[WebThief WebGL Bridge] 创建 WebGL 上下文:', contextType);
                    
                    // 尝试创建上下文，添加 failIfMajorPerformanceCaveat: false 以提高兼容性
                    const attrs = contextAttributes || {{}};
                    attrs.failIfMajorPerformanceCaveat = false;
                    attrs.powerPreference = attrs.powerPreference || 'default';
                    
                    const gl = _origGetContext.call(this, contextType, attrs);
                    
                    if (!gl) {{
                        console.warn('[WebThief WebGL Bridge] WebGL 上下文创建失败');
                        return null;
                    }}
                    
                    // 包装 WebGL 上下文
                    return wrapWebGLContext(gl, contextType);
                }}
                
                return _origGetContext.apply(this, arguments);
            }};
            
            // 包装 WebGL 上下文
            function wrapWebGLContext(gl, contextType) {{
                const isWebGL2 = contextType.includes('webgl2');
                
                // 拦截 texImage2D 以处理跨域图片
                const _origTexImage2D = gl.texImage2D;
                gl.texImage2D = function(target, level, internalFormat, width, height, border, format, type, pixels) {{
                    // 如果 pixels 是图片元素，处理 CORS
                    if (pixels instanceof HTMLImageElement) {{
                        if (!pixels.complete) {{
                            console.warn('[WebThief WebGL Bridge] 图片未加载完成');
                        }}
                        if (pixels.crossOrigin !== 'anonymous' && pixels.src) {{
                            console.log('[WebThief WebGL Bridge] 处理跨域纹理:', pixels.src.substring(0, 50));
                        }}
                    }}
                    
                    try {{
                        return _origTexImage2D.apply(this, arguments);
                    }} catch (e) {{
                        if (e.message && e.message.includes('cross-origin')) {{
                            console.warn('[WebThief WebGL Bridge] 跨域纹理加载失败，使用占位符');
                            // 创建 1x1 的占位纹理
                            const placeholder = new Uint8Array([255, 0, 255, 255]); // 洋红色
                            return _origTexImage2D.call(this, target, level, gl.RGBA, 1, 1, 0, gl.RGBA, gl.UNSIGNED_BYTE, placeholder);
                        }}
                        throw e;
                    }}
                }};
                
                // 拦截 shaderSource 以注入兼容性代码
                const _origShaderSource = gl.shaderSource;
                gl.shaderSource = function(shader, source) {{
                    // 检测并修复 GLSL 版本
                    let modifiedSource = source;
                    
                    if (isWebGL2) {{
                        // WebGL2: 确保使用 #version 300 es
                        if (!source.includes('#version 300 es')) {{
                            // 转换 WebGL1 shader 到 WebGL2
                            if (source.includes('attribute')) {{
                                modifiedSource = source
                                    .replace(/\\battribute\\b/g, 'in')
                                    .replace(/\\bvarying\\b/g, 'in')
                                    .replace(/\\bgl_FragColor\\b/g, 'fragColor')
                                    .replace(/\\btexture2D\\b/g, 'texture')
                                    .replace(/\\btextureCube\\b/g, 'texture');
                                
                                // 添加 precision 和 output 声明
                                if (!modifiedSource.includes('precision')) {{
                                    modifiedSource = 'precision mediump float;\\n' + modifiedSource;
                                }}
                                if (!modifiedSource.includes('out vec4 fragColor')) {{
                                    modifiedSource = 'out vec4 fragColor;\\n' + modifiedSource;
                                }}
                            }}
                        }}
                    }}
                    
                    return _origShaderSource.call(this, shader, modifiedSource);
                }};
                
                // WebGL2 特定处理
                if (isWebGL2) {{
                    // 确保 VAO 支持
                    if (!gl.createVertexArray) {{
                        console.warn('[WebThief WebGL Bridge] WebGL2 VAO 不可用');
                    }}
                }}
                
                // 添加上下文恢复支持
                const canvas = gl.canvas;
                if (canvas) {{
                    canvas.addEventListener('webglcontextlost', function(e) {{
                        console.warn('[WebThief WebGL Bridge] WebGL 上下文丢失');
                        e.preventDefault();
                    }}, false);
                    
                    canvas.addEventListener('webglcontextrestored', function(e) {{
                        console.log('[WebThief WebGL Bridge] WebGL 上下文已恢复');
                    }}, false);
                }}
                
                return gl;
            }}
            
            // 拦截 Image 加载以处理 CORS
            const _origImageSrcSetter = Object.getOwnPropertyDescriptor(HTMLImageElement.prototype, 'src').set;
            Object.defineProperty(HTMLImageElement.prototype, 'src', {{
                set: function(value) {{
                    // 自动设置 crossOrigin
                    if (value && typeof value === 'string' && !value.startsWith('data:') && !value.startsWith('blob:')) {{
                        try {{
                            const url = new URL(value, window.location.href);
                            if (url.origin !== window.location.origin) {{
                                this.crossOrigin = 'anonymous';
                            }}
                        }} catch (e) {{}}
                    }}
                    return _origImageSrcSetter.call(this, value);
                }},
                get: function() {{
                    return this.getAttribute('src');
                }}
            }});
            
            // 提供纹理加载辅助函数
            window.__webthief_loadTexture = function(gl, url, options = {{}}) {{
                return new Promise((resolve, reject) => {{
                    const texture = gl.createTexture();
                    const image = new Image();
                    
                    image.onload = function() {{
                        gl.bindTexture(gl.TEXTURE_2D, texture);
                        gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, image);
                        
                        if (options.mipmaps !== false) {{
                            gl.generateMipmap(gl.TEXTURE_2D);
                        }}
                        
                        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, options.wrapS || gl.CLAMP_TO_EDGE);
                        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, options.wrapT || gl.CLAMP_TO_EDGE);
                        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, options.minFilter || gl.LINEAR_MIPMAP_LINEAR);
                        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, options.magFilter || gl.LINEAR);
                        
                        resolve({{ texture, image, width: image.width, height: image.height }});
                    }};
                    
                    image.onerror = function() {{
                        reject(new Error('Failed to load texture: ' + url));
                    }};
                    
                    image.src = url;
                }});
            }};
            
            // 提供 shader 编译辅助函数
            window.__webthief_createShader = function(gl, type, source) {{
                const shader = gl.createShader(type);
                gl.shaderSource(shader, source);
                gl.compileShader(shader);
                
                if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {{
                    const error = gl.getShaderInfoLog(shader);
                    gl.deleteShader(shader);
                    throw new Error('Shader compilation error: ' + error);
                }}
                
                return shader;
            }};
            
            // 提供 program 链接辅助函数
            window.__webthief_createProgram = function(gl, vertexSource, fragmentSource) {{
                const vertexShader = window.__webthief_createShader(gl, gl.VERTEX_SHADER, vertexSource);
                const fragmentShader = window.__webthief_createShader(gl, gl.FRAGMENT_SHADER, fragmentSource);
                
                const program = gl.createProgram();
                gl.attachShader(program, vertexShader);
                gl.attachShader(program, fragmentShader);
                gl.linkProgram(program);
                
                if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {{
                    const error = gl.getProgramInfoLog(program);
                    gl.deleteProgram(program);
                    throw new Error('Program linking error: ' + error);
                }}
                
                return program;
            }};
            
            console.log('[WebThief WebGL Bridge] WebGL 桥接脚本已激活');
        }})();
        """
        return bridge_script

    def get_constant_name(self, value: int) -> str:
        """
        获取 WebGL 常量的名称
        
        Args:
            value: WebGL 常量值
            
        Returns:
            常量名称字符串
        """
        return self.WEBGL_CONSTANTS.get(value, f"0x{{value:04X}}")

    def export_resources(self) -> dict[str, Any]:
        """
        导出所有捕获的 WebGL 资源
        
        Returns:
            包含所有资源的字典
        """
        return {{
            "context_info": self.context_info.__dict__ if self.context_info else None,
            "shader_programs": {{k: v.__dict__ for k, v in self.shader_programs.items()}},
            "buffers": {{k: v.__dict__ for k, v in self.buffers.items()}},
            "textures": {{k: v.__dict__ for k, v in self.textures.items()}},
            "framebuffers": {{k: v.__dict__ for k, v in self.framebuffers.items()}},
            "screenshots": self.captured_screenshots
        }}

    def save_resources_to_file(self, filepath: str) -> None:
        """
        将捕获的资源保存到 JSON 文件
        
        Args:
            filepath: 输出文件路径
        """
        resources = self.export_resources()
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(resources, f, indent=2, ensure_ascii=False, default=str)
        console.print(f"[green]  ✓ WebGL 资源已保存到: {{filepath}}[/]")
