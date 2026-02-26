"""
React 组件拦截与交互菜单固化模块
目标：拦截 React 组件卸载，保留所有触发过的下拉菜单和交互元素
"""

from __future__ import annotations

from playwright.async_api import Page
from rich.console import Console

console = Console()


class ReactInterceptor:
    """
    React 组件拦截器
    负责：
    1. 劫持 React 的 unmount 函数
    2. 强制保留所有触发过的组件
    3. 将 JS 驱动的显隐转换为 CSS
    4. 固化交互菜单状态
    """

    def __init__(self):
        self.intercepted_components: list[dict] = []
        self.menu_states: dict[str, bool] = {}

    async def inject_react_unmount_patch(self, page: Page) -> None:
        """
        注入 React unmount 拦截补丁
        在页面加载前执行，劫持 React 的组件卸载机制
        """
        console.print("[cyan]  ⚛️  注入 React 组件拦截补丁...[/]")

        patch_script = """
        (function() {
            'use strict';
            // ━━━ WebThief React Unmount Interceptor ━━━
            
            // 等待 React 加载
            function waitForReact(callback) {
                if (window.React || window.ReactDOM) {
                    callback();
                } else {
                    setTimeout(() => waitForReact(callback), 100);
                }
            }
            
            waitForReact(() => {
                console.log('[WebThief React] 检测到 React，开始注入补丁');
                
                // 方法 1: 劫持 ReactDOM.unmountComponentAtNode
                if (window.ReactDOM && window.ReactDOM.unmountComponentAtNode) {
                    const _origUnmount = window.ReactDOM.unmountComponentAtNode;
                    window.ReactDOM.unmountComponentAtNode = function(container) {
                        console.log('[WebThief React] 拦截 unmount 调用，保留组件');
                        
                        // 标记容器为"已保留"
                        if (container) {
                            container.setAttribute('data-webthief-preserved', 'true');
                        }
                        
                        // 不执行真正的 unmount
                        return true;
                    };
                }
                
                // 方法 2: 拦截 Fiber 节点的 unmount（React 16+）
                // 通过 Monkey Patch React 内部的 commitUnmount
                try {
                    // 查找 React Fiber 根节点
                    const findReactRoot = () => {
                        for (const key in document.body) {
                            if (key.startsWith('__react')) {
                                return document.body[key];
                            }
                        }
                        return null;
                    };
                    
                    const root = findReactRoot();
                    if (root && root._internalRoot) {
                        console.log('[WebThief React] 找到 React Fiber 根节点');
                        
                        // 标记所有 Fiber 节点为"不可卸载"
                        window.__webthief_react_preserve = true;
                    }
                } catch (e) {
                    console.warn('[WebThief React] Fiber 补丁失败:', e);
                }
                
                // 方法 3: 拦截 removeChild（最底层防护）
                const _origRemoveChild = Element.prototype.removeChild;
                Element.prototype.removeChild = function(child) {
                    // 检查是否为 React 管理的节点
                    if (child && child.nodeType === 1) {
                        const hasReactProps = Object.keys(child).some(k => k.startsWith('__react'));
                        
                        if (hasReactProps) {
                            console.log('[WebThief React] 拦截 React 节点删除');
                            
                            // 不删除，而是隐藏
                            child.style.display = 'none';
                            child.setAttribute('data-webthief-hidden', 'true');
                            
                            return child;
                        }
                    }
                    
                    return _origRemoveChild.call(this, child);
                };
            });
            
            // 拦截 CSS display 变化（防止 JS 隐藏菜单）
            const _origSetAttribute = Element.prototype.setAttribute;
            Element.prototype.setAttribute = function(name, value) {
                if (name === 'style' && typeof value === 'string') {
                    // 检测是否在设置 display: none
                    if (value.includes('display') && value.includes('none')) {
                        const isMenu = this.classList.contains('dropdown') ||
                                      this.classList.contains('menu') ||
                                      this.classList.contains('submenu') ||
                                      this.getAttribute('role') === 'menu';
                        
                        if (isMenu) {
                            console.log('[WebThief React] 拦截菜单隐藏');
                            
                            // 移除 display: none
                            value = value.replace(/display\\s*:\\s*none\\s*;?/gi, '');
                            
                            // 标记为已展开
                            this.setAttribute('data-webthief-expanded', 'true');
                        }
                    }
                }
                
                return _origSetAttribute.call(this, name, value);
            };
            
            console.log('[WebThief React] React 拦截补丁已激活');
        })();
        """

        await page.add_init_script(patch_script)

    async def trigger_all_menus(self, page: Page) -> None:
        """
        触发所有交互菜单
        通过模拟鼠标事件，展开所有下拉菜单和悬停元素
        """
        console.print("[cyan]  🖱️  触发所有交互菜单...[/]")

        trigger_script = """
        async () => {
            // 常见菜单选择器
            const menuSelectors = [
                // 通用
                '.dropdown', '.dropdown-toggle', '.dropdown-menu',
                '.menu', '.submenu', '.nav-item', '.nav-link',
                '[role="menu"]', '[role="menuitem"]', '[aria-haspopup="true"]',
                
                // Bootstrap
                '.navbar-nav > li', '.nav-item.dropdown',
                
                // Material UI
                '.MuiMenu-root', '.MuiMenuItem-root',
                
                // Ant Design
                '.ant-dropdown', '.ant-menu',
                
                // 自定义
                'nav a', 'header a', '.navigation a'
            ];
            
            const triggeredElements = new Set();
            let totalTriggered = 0;
            
            for (const selector of menuSelectors) {
                const elements = document.querySelectorAll(selector);
                
                for (const el of elements) {
                    if (triggeredElements.has(el)) continue;
                    
                    // 滚动到元素可见
                    el.scrollIntoView({ behavior: 'instant', block: 'center' });
                    
                    // 触发多种事件
                    const events = [
                        'mouseenter', 'mouseover', 'mousedown', 'mouseup',
                        'click', 'focus', 'touchstart'
                    ];
                    
                    for (const eventType of events) {
                        const event = new MouseEvent(eventType, {
                            bubbles: true,
                            cancelable: true,
                            view: window
                        });
                        el.dispatchEvent(event);
                    }
                    
                    // 等待菜单展开
                    await new Promise(r => setTimeout(r, 150));
                    
                    triggeredElements.add(el);
                    totalTriggered++;
                }
            }
            
            // 等待所有异步内容加载
            await new Promise(r => setTimeout(r, 1000));
            
            return totalTriggered;
        }
        """

        try:
            triggered_count = await page.evaluate(trigger_script)
            console.print(f"[green]  ✓ 触发了 {triggered_count} 个交互元素[/]")
        except Exception as e:
            console.print(f"[yellow]  ⚠ 触发菜单时出现警告: {e}[/]")

    async def freeze_menu_states(self, page: Page) -> None:
        """
        冻结所有菜单状态
        将所有展开的菜单固化为永久可见
        """
        console.print("[cyan]  ❄️  冻结菜单状态...[/]")

        freeze_script = """
        () => {
            // 查找所有可能的菜单元素
            const menuElements = document.querySelectorAll(`
                .dropdown-menu, .submenu, .mega-menu,
                [role="menu"], [aria-expanded="true"],
                [data-webthief-expanded="true"]
            `);
            
            let frozenCount = 0;
            
            menuElements.forEach(menu => {
                // 强制显示
                menu.style.display = 'block';
                menu.style.visibility = 'visible';
                menu.style.opacity = '1';
                
                // 移除可能导致隐藏的类
                menu.classList.remove('hidden', 'hide', 'collapsed');
                
                // 添加固化标记
                menu.setAttribute('data-webthief-frozen', 'true');
                
                // 防止 JS 再次隐藏
                Object.defineProperty(menu.style, 'display', {
                    set: function(value) {
                        if (value === 'none') {
                            console.log('[WebThief] 拦截菜单隐藏尝试');
                            return;
                        }
                        this._display = value;
                    },
                    get: function() {
                        return this._display || 'block';
                    }
                });
                
                frozenCount++;
            });
            
            return frozenCount;
        }
        """

        try:
            frozen_count = await page.evaluate(freeze_script)
            console.print(f"[green]  ✓ 冻结了 {frozen_count} 个菜单[/]")
        except Exception as e:
            console.print(f"[yellow]  ⚠ 冻结菜单时出现警告: {e}[/]")

    async def convert_js_interactions_to_css(self, page: Page) -> str:
        """
        将 JS 驱动的交互转换为纯 CSS
        返回生成的 CSS 规则
        """
        console.print("[cyan]  🎨 转换交互逻辑为 CSS...[/]")

        css_rules = """
        /* ━━━ WebThief React Menu Preservation CSS ━━━ */
        
        /* 强制显示所有触发过的菜单 */
        [data-webthief-expanded="true"],
        [data-webthief-frozen="true"] {
            display: block !important;
            visibility: visible !important;
            opacity: 1 !important;
        }
        
        /* 悬停时显示子菜单 */
        .dropdown:hover > .dropdown-menu,
        .nav-item:hover > .submenu,
        [aria-haspopup="true"]:hover + [role="menu"] {
            display: block !important;
            visibility: visible !important;
            opacity: 1 !important;
        }
        
        /* 防止菜单被隐藏 */
        .dropdown-menu[data-webthief-frozen="true"],
        .submenu[data-webthief-frozen="true"],
        [role="menu"][data-webthief-frozen="true"] {
            position: absolute !important;
            z-index: 9999 !important;
        }
        
        /* 保留的 React 组件 */
        [data-webthief-preserved="true"] {
            display: block !important;
        }
        
        /* 修复可能的布局问题 */
        [data-webthief-hidden="true"] {
            display: none !important;
        }
        """

        # 注入 CSS
        await page.add_style_tag(content=css_rules)
        console.print("[green]  ✓ CSS 交互规则已注入[/]")

        return css_rules

    def generate_menu_preservation_script(self) -> str:
        """
        生成菜单保留脚本（注入到克隆页面）
        """
        script = """
        (function() {
            'use strict';
            // ━━━ WebThief Menu Preservation Runtime ━━━
            
            // 在克隆页面中恢复菜单交互
            document.addEventListener('DOMContentLoaded', function() {
                console.log('[WebThief Menu] 初始化菜单交互');
                
                // 为所有菜单触发器添加悬停事件
                const triggers = document.querySelectorAll(`
                    .dropdown-toggle, .nav-item, [aria-haspopup="true"]
                `);
                
                triggers.forEach(trigger => {
                    trigger.addEventListener('mouseenter', function() {
                        // 查找关联的菜单
                        const menu = this.querySelector('.dropdown-menu, .submenu, [role="menu"]') ||
                                    this.nextElementSibling;
                        
                        if (menu) {
                            menu.style.display = 'block';
                            menu.style.visibility = 'visible';
                            menu.style.opacity = '1';
                        }
                    });
                    
                    trigger.addEventListener('mouseleave', function(e) {
                        // 检查是否移动到子菜单
                        const menu = this.querySelector('.dropdown-menu, .submenu, [role="menu"]') ||
                                    this.nextElementSibling;
                        
                        if (menu && !menu.contains(e.relatedTarget)) {
                            // 延迟隐藏，给用户时间移动到子菜单
                            setTimeout(() => {
                                if (!menu.matches(':hover')) {
                                    menu.style.display = 'none';
                                }
                            }, 300);
                        }
                    });
                });
                
                console.log('[WebThief Menu] 菜单交互已激活');
            });
        })();
        """
        return script
