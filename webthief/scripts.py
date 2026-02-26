"""
渲染器 JavaScript 脚本配置

包含页面渲染过程中需要注入的各种 JavaScript 脚本。
"""


# ─── 视口激活预热脚本 ──────────────────────────────────────
VIEWPORT_ACTIVATION_SCRIPT = """
async () => {
    const wait = (ms) => new Promise((r) => setTimeout(r, ms));
    const targets = [];
    const seen = new Set();
    const scrollSamples = [];

    // 检测常见的滚动动画库
    const detectedLibraries = {
        hasGSAP: !!(window.gsap || window.ScrollTrigger || window.GreenSockGlobals),
        hasScrollMagic: !!(window.ScrollMagic || window.ScrollMagicController),
        hasAOS: !!(window.AOS || document.querySelector('[data-aos]')),
        hasWOW: !!(window.WOW || document.querySelector('[data-wow]')),
        hasScrollReveal: !!(window.ScrollReveal || window.sr),
        hasLocomotiveScroll: !!(window.LocomotiveScroll),
        hasLenis: !!(window.Lenis),
        hasRellax: !!(window.Rellax),
        hasParallax: !!(window.Parallax || window.parallax),
        hasSwiper: !!(window.Swiper || document.querySelector('.swiper')),
        hasSlick: !!(window.jQuery && window.jQuery.fn && window.jQuery.fn.slick)
    };

    // 增强的选择器列表 - 按优先级排序
    const selectors = [
        // 动画库特定选择器
        '[data-aos]',
        '[data-aos-id]',
        '[data-scroll]',
        '[data-parallax]',
        '[data-rellax-speed]',
        '[data-speed]',
        '[data-wow]',
        '[data-wow-duration]',
        '[data-scroll-trigger]',
        '[data-scrollmagic]',
        '[data-animate]',
        '[data-animation]',
        // GSAP 相关
        '[class*="gsap"]',
        '[class*="scroll-trigger"]',
        '[class*="parallax"]',
        // 常见动画类
        '[class*="reveal"]',
        '[class*="fade"]',
        '[class*="slide"]',
        '[class*="animate"]',
        '[class*="motion"]',
        '[class*="timeline"]',
        // 轮播组件
        '.swiper',
        '.swiper-container',
        '.slick-slider',
        '.carousel',
        '.owl-carousel',
        // 结构元素
        'section',
        'article',
        'main > div',
        '[role="tablist"]',
        '[role="region"]'
    ];

    // 收集目标滚动位置
    for (const sel of selectors) {
        for (const el of document.querySelectorAll(sel)) {
            if (seen.has(el)) continue;
            const rect = el.getBoundingClientRect();
            if (!rect || rect.height < 6) continue;
            seen.add(el);
            
            // 计算滚动目标位置（提前一点触发）
            const triggerOffset = Math.floor(window.innerHeight * 0.35);
            const top = Math.max(0, rect.top + window.scrollY - triggerOffset);
            
            // 记录元素信息用于后续处理
            targets.push({
                position: top,
                element: el,
                hasAOS: el.hasAttribute('data-aos'),
                hasScroll: el.hasAttribute('data-scroll'),
                hasParallax: el.hasAttribute('data-parallax'),
                hasRellax: el.hasAttribute('data-rellax-speed')
            });
            
            if (targets.length >= 50) break;
        }
        if (targets.length >= 50) break;
    }

    // 如果没有找到特定目标，使用均匀分段
    if (!targets.length) {
        const scrollHeight = Math.max(
            document.body ? document.body.scrollHeight : 0,
            document.documentElement ? document.documentElement.scrollHeight : 0
        );
        const stops = 15;
        for (let i = 0; i <= stops; i++) {
            targets.push({
                position: Math.floor((scrollHeight * i) / stops),
                element: null
            });
        }
    } else {
        // 按位置排序并去重
        targets.sort((a, b) => a.position - b.position);
        // 移除过于接近的点（间隔小于100px）
        for (let i = targets.length - 1; i > 0; i--) {
            if (targets[i].position - targets[i-1].position < 100) {
                targets.splice(i, 1);
            }
        }
    }

    // 变速滚动算法：慢速-快速-慢速
    async function variableSpeedScroll(targetY, currentY, isFirst = false, isLast = false) {
        const distance = Math.abs(targetY - currentY);
        const direction = targetY > currentY ? 1 : -1;
        
        // 分段配置
        const segments = {
            slowStart: Math.floor(distance * 0.15),  // 起始慢速段
            fastMiddle: Math.floor(distance * 0.7),  // 中间快速段
            slowEnd: Math.floor(distance * 0.15)     // 结束慢速段
        };

        let currentPos = currentY;
        const startTime = performance.now();
        
        // 阶段1：慢速起始（如果是第一个点或距离较短）
        if (isFirst || distance < 500) {
            const steps = Math.max(3, Math.floor(segments.slowStart / 30));
            for (let i = 0; i < steps; i++) {
                currentPos += (segments.slowStart / steps) * direction;
                window.scrollTo(0, Math.round(currentPos));
                dispatchScrollEvents();
                await wait(50 + i * 10); // 逐渐加速
            }
        }
        
        // 阶段2：快速中间段
        const fastSteps = Math.max(2, Math.floor(segments.fastMiddle / 80));
        for (let i = 0; i < fastSteps; i++) {
            currentPos += (segments.fastMiddle / fastSteps) * direction;
            window.scrollTo(0, Math.round(currentPos));
            dispatchScrollEvents();
            
            // 在快速滚动中采样中间位置
            if (i % 2 === 0) {
                recordScrollSample(Math.round(currentPos));
            }
            
            await wait(20); // 快速间隔
        }
        
        // 阶段3：慢速结束（如果是最后一个点或距离较短）
        if (isLast || distance < 500) {
            const steps = Math.max(3, Math.floor(segments.slowEnd / 20));
            for (let i = 0; i < steps; i++) {
                currentPos += (segments.slowEnd / steps) * direction;
                window.scrollTo(0, Math.round(currentPos));
                dispatchScrollEvents();
                await wait(60 - i * 10); // 逐渐减速
            }
        }
        
        // 确保到达目标位置
        window.scrollTo(0, targetY);
        dispatchScrollEvents();
        
        // 记录最终采样
        recordScrollSample(targetY);
        
        return performance.now() - startTime;
    }

    // 分发滚动相关事件
    function dispatchScrollEvents() {
        window.dispatchEvent(new Event('scroll', { bubbles: true }));
        window.dispatchEvent(new Event('resize', { bubbles: true }));
        window.dispatchEvent(new WheelEvent('wheel', { 
            deltaY: 120, 
            bubbles: true,
            cancelable: true
        }));
        
        // 触发滚动监听器的更新
        if (window.scrollListeners) {
            window.scrollListeners.forEach(fn => {
                try { fn(); } catch(e) {}
            });
        }
    }

    // 记录滚动采样
    function recordScrollSample(position) {
        const timestamp = Date.now();
        scrollSamples.push({ position, timestamp });
        
        // 触发中间状态捕获
        triggerIntermediateCapture(position);
    }

    // 触发中间状态捕获 - 处理动画元素
    function triggerIntermediateCapture(position) {
        // 强制触发 AOS 元素的动画
        document.querySelectorAll('[data-aos]:not(.aos-animate)').forEach(el => {
            const rect = el.getBoundingClientRect();
            if (rect.top < window.innerHeight && rect.bottom > 0) {
                el.classList.add('aos-animate');
            }
        });
        
        // 触发 parallax 更新
        document.querySelectorAll('[data-parallax], [data-rellax-speed]').forEach(el => {
            el.dispatchEvent(new CustomEvent('scroll', { detail: { position } }));
        });
        
        // 触发 scroll 事件监听器
        if (window.onscroll) {
            try { window.onscroll(); } catch(e) {}
        }
    }

    // 特殊处理：预触发 AOS 动画
    function preTriggerAOS() {
        if (!detectedLibraries.hasAOS) return;
        
        document.querySelectorAll('[data-aos]').forEach(el => {
            // 提前添加动画类
            const delay = parseInt(el.getAttribute('data-aos-delay') || '0', 10);
            setTimeout(() => {
                el.classList.add('aos-animate');
                el.style.opacity = '1';
                el.style.transform = 'none';
            }, delay);
        });
    }

    // 特殊处理：预触发 ScrollTrigger
    function preTriggerScrollTrigger() {
        if (!detectedLibraries.hasGSAP) return;
        
        // 尝试刷新 ScrollTrigger
        if (window.ScrollTrigger) {
            try {
                window.ScrollTrigger.refresh();
            } catch(e) {}
        }
        
        // 触发 GSAP 相关更新
        document.querySelectorAll('[data-scroll-trigger]').forEach(el => {
            el.style.visibility = 'visible';
        });
    }

    // 特殊处理：预触发 parallax 效果
    function preTriggerParallax() {
        if (detectedLibraries.hasRellax && window.Rellax) {
            try {
                const rellax = new window.Rellax('[data-rellax-speed]');
                rellax.refresh();
            } catch(e) {}
        }
    }

    // 执行变速滚动
    let currentY = 0;
    const totalTargets = targets.length;
    
    // 预触发特殊动画库
    preTriggerAOS();
    preTriggerScrollTrigger();
    preTriggerParallax();
    
    for (let i = 0; i < totalTargets; i++) {
        const target = targets[i];
        const isFirst = i === 0;
        const isLast = i === totalTargets - 1;
        
        // 执行变速滚动
        await variableSpeedScroll(target.position, currentY, isFirst, isLast);
        currentY = target.position;
        
        // 特殊处理当前目标元素
        if (target.element) {
            // 触发元素的滚动相关事件
            target.element.dispatchEvent(new Event('scroll', { bubbles: true }));
            
            // 处理 data-scroll 属性
            if (target.hasScroll) {
                target.element.classList.add('is-scrolled');
                target.element.setAttribute('data-scroll', 'in');
            }
            
            // 处理 data-parallax
            if (target.hasParallax || target.hasRellax) {
                target.element.style.willChange = 'transform';
            }
        }
        
        // 在关键点增加额外等待
        const waitTime = isFirst || isLast ? 300 : 200;
        await wait(waitTime);
        
        // 再次触发事件确保动画完成
        dispatchScrollEvents();
    }

    // 回到顶部
    await variableSpeedScroll(0, currentY, false, true);
    window.scrollTo(0, 0);
    dispatchScrollEvents();
    
    // 最终等待确保所有动画完成
    await wait(600);
    
    // 最终触发所有剩余动画
    document.querySelectorAll('[data-aos]:not(.aos-animate)').forEach(el => {
        el.classList.add('aos-animate');
    });
    
    // 返回统计信息
    return {
        targetsScrolled: totalTargets,
        samplesCollected: scrollSamples.length,
        librariesDetected: detectedLibraries,
        scrollSamples: scrollSamples
    };
}
"""

# ─── Hover 预热脚本 ────────────────────────────────────────
HOVER_PRELOAD_SCRIPT = """
async () => {
    const selectors = [
        '.supernav > a',
        '.nav-item',
        '.dropdown-toggle',
        'nav a',
        'header a',
        '[aria-haspopup="true"]',
        '[role="menuitem"]',
        'button[aria-expanded]',
        '[data-featuretarget] button',
        '[data-featuretarget] a'
    ];
    const touched = new Set();
    const maxElements = 180;
    let total = 0;

    function fire(el, eventType) {
        try {
            if (eventType === 'focus') {
                el.dispatchEvent(new Event('focus', { bubbles: true, cancelable: true }));
                return;
            }
            el.dispatchEvent(new MouseEvent(eventType, {
                bubbles: true,
                cancelable: true,
                view: window
            }));
        } catch (e) {}
    }

    for (const sel of selectors) {
        const els = document.querySelectorAll(sel);
        for (const el of els) {
            if (touched.has(el)) continue;
            if (total >= maxElements) break;
            const rect = el.getBoundingClientRect();
            if (!rect || rect.width < 2 || rect.height < 2) continue;
            el.scrollIntoView({ behavior: 'instant', block: 'center', inline: 'nearest' });

            fire(el, 'pointerenter');
            fire(el, 'mouseenter');
            fire(el, 'mouseover');
            fire(el, 'mousemove');
            fire(el, 'focus');

            touched.add(el);
            total += 1;
            await new Promise(r => setTimeout(r, 140));
        }
        if (total >= maxElements) break;
    }

    await new Promise(r => setTimeout(r, 900));
}
"""

# ─── 交互预热脚本 ──────────────────────────────────────────
INTERACTION_PRELOAD_SCRIPT = """
async () => {
    const selectors = [
        '[role="tab"]',
        '[aria-controls]',
        '[data-tab]',
        '[data-target]',
        '[data-bs-target]',
        '.tab',
        '.tabs li',
        '.swiper-pagination-bullet',
        '.slick-dots button',
        '.carousel-indicators button',
        '.accordion-button',
        '.collapse-toggle',
        'button'
    ];

    const seen = new Set();
    const maxActions = 70;
    let actions = 0;

    function isVisible(el) {
        const rect = el.getBoundingClientRect();
        if (!rect) return false;
        if (rect.width < 2 || rect.height < 2) return false;
        const style = getComputedStyle(el);
        return style.visibility !== 'hidden' && style.display !== 'none';
    }

    function isLowRiskTarget(el) {
        const tag = (el.tagName || '').toLowerCase();
        if (tag === 'button') {
            const type = (el.getAttribute('type') || '').toLowerCase();
            const form = el.closest('form');
            if (!type || type === 'submit') {
                if (form) return false;
            }
            return true;
        }
        if (tag === 'a') {
            const href = (el.getAttribute('href') || '').trim().toLowerCase();
            if (!href || href === '#') return true;
            if (href.startsWith('javascript:')) return true;
            return false;
        }
        if (el.getAttribute('role') === 'tab') return true;
        if (el.hasAttribute('aria-controls')) return true;
        if (el.hasAttribute('data-tab') || el.hasAttribute('data-target') || el.hasAttribute('data-bs-target')) return true;
        const cls = (el.className || '').toLowerCase();
        return cls.includes('tab') || cls.includes('bullet') || cls.includes('dot');
    }

    function safeClick(el) {
        try {
            if (typeof el.click === 'function') {
                el.click();
            } else {
                el.dispatchEvent(new MouseEvent('click', {
                    bubbles: true,
                    cancelable: true,
                    view: window
                }));
            }
        } catch (e) {}
    }

    for (const sel of selectors) {
        const elements = document.querySelectorAll(sel);
        for (const el of elements) {
            if (actions >= maxActions) break;
            if (seen.has(el)) continue;
            if (!isVisible(el)) continue;
            if (!isLowRiskTarget(el)) continue;

            seen.add(el);
            el.scrollIntoView({ behavior: 'instant', block: 'center', inline: 'nearest' });
            el.dispatchEvent(new MouseEvent('mouseenter', { bubbles: true }));
            el.dispatchEvent(new MouseEvent('mouseover', { bubbles: true }));
            safeClick(el);
            actions += 1;
            await new Promise(r => setTimeout(r, 160));
        }
        if (actions >= maxActions) break;
    }

    await new Promise(r => setTimeout(r, 900));
    return actions;
}
"""

# ─── SPA 检测脚本 ──────────────────────────────────────────
SPA_DETECTION_SCRIPT = """
() => {
    let score = 0;

    if (document.querySelector('#__next, #__nuxt, [data-reactroot], [data-reactid], [data-v-app], [ng-version]')) {
        score += 2;
    }

    if (window.__NEXT_DATA__ || window.__NUXT__) {
        score += 2;
    }

    if (document.querySelectorAll('script[type="module"]').length >= 3) {
        score += 1;
    }

    if (document.querySelector('[data-aos], [data-wow-duration], [data-scroll], [data-parallax]')) {
        score += 1;
    }

    if (document.querySelector('.swiper, .swiper-container, .slick-slider, .carousel, [class*="swiper"], [class*="carousel"]')) {
        score += 1;
    }

    if (document.querySelector('[role="tab"], [aria-controls], [data-tab], .tabs, .accordion')) {
        score += 1;
    }

    return score;
}
"""

# ─── 懒加载资源激活脚本 ────────────────────────────────────
LAZY_RESOURCE_ACTIVATION_SCRIPT = """
() => {
    const srcAttrs = [
        'data-src', 'data-original', 'data-lazy-src',
        'data-actualsrc', 'data-url'
    ];
    const srcsetAttrs = ['data-srcset', 'data-lazy-srcset'];
    const bgAttrs = ['data-bg', 'data-bg-src', 'data-background'];

    const isPlaceholder = (val) => {
        if (!val) return true;
        const s = String(val).trim().toLowerCase();
        if (!s) return true;
        if (s.startsWith('data:image')) return s.length < 256 || s.includes('r0lgodh');
        return ['placeholder', 'spacer', 'blank', 'loading', 'pixel'].some(k => s.includes(k));
    };

    document.querySelectorAll('img').forEach((img) => {
        for (const attr of srcAttrs) {
            const candidate = img.getAttribute(attr);
            if (!candidate) continue;
            if (isPlaceholder(img.getAttribute('src'))) {
                img.setAttribute('src', candidate);
            }
        }
        for (const attr of srcsetAttrs) {
            const candidate = img.getAttribute(attr);
            if (candidate && !img.getAttribute('srcset')) {
                img.setAttribute('srcset', candidate);
            }
        }
        if (img.getAttribute('loading') === 'lazy') {
            img.setAttribute('loading', 'eager');
        }
    });

    document.querySelectorAll('source').forEach((source) => {
        for (const attr of srcsetAttrs) {
            const candidate = source.getAttribute(attr);
            if (candidate) {
                source.setAttribute('srcset', candidate);
            }
        }
        for (const attr of srcAttrs) {
            const candidate = source.getAttribute(attr);
            if (candidate && !source.getAttribute('src')) {
                source.setAttribute('src', candidate);
            }
        }
    });

    document.querySelectorAll('*').forEach((el) => {
        for (const attr of bgAttrs) {
            const candidate = el.getAttribute(attr);
            if (!candidate) continue;
            if (!el.style.backgroundImage || el.style.backgroundImage === 'none') {
                el.style.backgroundImage = `url("${candidate}")`;
            }
        }
    });
}
"""

# ─── Blob 图片固化脚本 ──────────────────────────────────────
BLOB_IMAGE_MATERIALIZATION_SCRIPT = """
async (limit) => {
    const candidates = Array.from(
        document.querySelectorAll('img[src^="blob:"]')
    );
    if (!candidates.length) {
        return 0;
    }

    async function blobUrlToDataUrl(blobUrl) {
        try {
            const response = await fetch(blobUrl);
            if (!response || !response.ok) return '';
            const blob = await response.blob();
            if (!blob || !blob.size) return '';
            if (blob.size > 2 * 1024 * 1024) return '';
            return await new Promise((resolve) => {
                const reader = new FileReader();
                reader.onload = () => {
                    resolve(typeof reader.result === 'string' ? reader.result : '');
                };
                reader.onerror = () => resolve('');
                reader.readAsDataURL(blob);
            });
        } catch (e) {
            return '';
        }
    }

    let converted = 0;
    for (const img of candidates) {
        if (converted >= limit) break;
        const src = (img.getAttribute('src') || '').trim();
        if (!src.startsWith('blob:')) continue;
        const dataUrl = await blobUrlToDataUrl(src);
        if (!dataUrl) continue;
        img.setAttribute('data-webthief-blob-src', src);
        img.setAttribute('src', dataUrl);
        converted += 1;
    }
    return converted;
}
"""

# ─── DOM 稳定等待脚本 ──────────────────────────────────────
DOM_SETTLE_WAIT_SCRIPT = """
(args) => new Promise((resolve) => {
    const timeoutMs = Math.max(1000, Number(args.timeoutMs) || 12000);
    const quietMs = Math.max(200, Number(args.quietMs) || 1200);

    let settled = false;
    let quietTimer = null;
    let timeoutTimer = null;

    function done() {
        if (settled) return;
        settled = true;
        if (quietTimer) clearTimeout(quietTimer);
        if (timeoutTimer) clearTimeout(timeoutTimer);
        if (observer) observer.disconnect();
        resolve(true);
    }

    function resetQuietTimer() {
        if (quietTimer) clearTimeout(quietTimer);
        quietTimer = setTimeout(done, quietMs);
    }

    const observer = new MutationObserver(() => {
        resetQuietTimer();
    });
    observer.observe(document.documentElement || document.body, {
        childList: true,
        subtree: true,
        attributes: true,
        characterData: true
    });

    timeoutTimer = setTimeout(done, timeoutMs);
    resetQuietTimer();
})
"""

# ─── 运行时回放准备脚本 ────────────────────────────────────
RUNTIME_REPLAY_PREPARE_SCRIPT = """
() => {
    try {
        if (window.jQuery && window.jQuery.fn && window.jQuery.fn.slick) {
            window.jQuery('.slick-initialized').each(function() {
                try { window.jQuery(this).slick('unslick'); } catch (e) {}
            });
        }
    } catch (e) {}

    try {
        document.querySelectorAll('.swiper, .swiper-container').forEach((el) => {
            const inst = el.swiper || el.__swiper__ || null;
            if (inst && typeof inst.destroy === 'function') {
                try { inst.destroy(true, true); } catch (e) {}
            }
        });
    } catch (e) {}
}
"""

# ─── CSS 固化脚本 ──────────────────────────────────────────
CSS_SOLIDIFY_SCRIPT = """
() => {
    const rootStyles = getComputedStyle(document.documentElement);
    let cssVars = ':root {\\n';
    for (let i = 0; i < rootStyles.length; i++) {
        const prop = rootStyles[i];
        if (prop.startsWith('--')) {
            cssVars += `  ${prop}: ${rootStyles.getPropertyValue(prop)};\\n`;
        }
    }
    cssVars += '}';
    const style = document.createElement('style');
    style.textContent = cssVars;
    document.head.appendChild(style);

    document.querySelectorAll('*').forEach(el => {
        const bg = getComputedStyle(el).backgroundImage;
        if (bg && bg !== 'none' && !el.style.backgroundImage) {
            el.style.backgroundImage = bg;
        }
    });
}
"""

# ─── DOM 快照提取脚本 ──────────────────────────────────────
DOM_SNAPSHOT_EXTRACT_SCRIPT = """
(freezeAnimations) => {
    function expand(root) {
        root.querySelectorAll('*').forEach(el => {
            if (el.shadowRoot) {
                const wrapper = document.createElement('div');
                wrapper.innerHTML = el.shadowRoot.innerHTML;
                el.appendChild(wrapper);
                expand(wrapper);
            }
        });
    }
    expand(document);

    if (freezeAnimations) {
        const s = document.createElement('style');
        s.textContent = '*, *::before, *::after { animation-play-state: paused !important; transition: none !important; }';
        document.head.appendChild(s);
    }

    return '<!DOCTYPE html>\\n' + document.documentElement.outerHTML;
}
"""

# ─── 备用 DOM 提取脚本 ─────────────────────────────────────
FALLBACK_DOM_EXTRACT_SCRIPT = """
() => {
    const html = document.documentElement ? document.documentElement.outerHTML : '';
    const body = document.body ? document.body.outerHTML : '';
    return html || body || document.documentElement.innerHTML || '';
}
"""

# ─── DOM URL 收集脚本 ──────────────────────────────────────
DOM_URL_COLLECT_SCRIPT = """
() => Array.from(new Set([
    ...Array.from(document.querySelectorAll('[src]')).map(e => e.src),
    ...Array.from(document.querySelectorAll('link[href]')).map(e => e.href)
]))
"""

# ─── 登录检测脚本 ──────────────────────────────────────────
LOGIN_DETECTION_SCRIPT = """
() => {
    const selectors = [
        'input[type="password"]',
        'input[name*="pass" i]',
        'form[action*="login" i]',
        'form[id*="login" i]',
        'form[class*="login" i]',
        '[data-testid*="login" i]'
    ];
    return selectors.some(sel => !!document.querySelector(sel));
}
"""

# ─── 页面链接提取脚本 ──────────────────────────────────────
PAGE_LINKS_EXTRACT_SCRIPT = """
() => Array.from(
    new Set(
        Array.from(document.querySelectorAll('a[href]'))
            .map(a => a.getAttribute('href') || '')
    )
)
"""

# ─── 框架等待脚本 ──────────────────────────────────────────
FRAMEWORK_WAIT_SCRIPT = """
async () => {
    // 等待最多 3 秒让框架完成渲染
    const maxWait = 3000;
    const start = Date.now();

    while (Date.now() - start < maxWait) {
        // 检查是否有内容渲染
        const hasContent = document.body && (
            document.body.innerText.length > 100 ||
            document.querySelectorAll('img').length > 0 ||
            document.querySelectorAll('div').length > 5
        );

        // 检查常见的框架加载指示器
        const frameworksReady = !document.querySelector('#__next[data-reactroot]') ||
                                document.querySelector('#__next > *');

        if (hasContent && frameworksReady) {
            break;
        }

        await new Promise(r => setTimeout(r, 100));
    }
}
"""

# ─── 滚动动画固化脚本 ──────────────────────────────────────
SCROLL_ANIMATION_SOLIDIFY_SCRIPT = """
() => {
    // 滚动到首屏位置
    window.scrollTo(0, 0);
    window.dispatchEvent(new Event('scroll'));
    
    // 需要排除的选择器（菜单、导航、弹窗等）
    const excludeSelectors = [
        'nav.menu',
        'nav[class*="menu"]',
        '.menu-overlay',
        '.nav-overlay',
        '.mobile-menu',
        '[class*="navList"]',
        '.appNavList',
        '.shape-overlays',
        '#menu',
        '.modal',
        '.popup',
        '.overlay'
    ];
    
    // 检查元素是否应该被排除
    function shouldExclude(el) {
        // 检查是否在排除列表中
        for (const selector of excludeSelectors) {
            try {
                if (el.matches && el.matches(selector)) return true;
                if (el.closest && el.closest(selector)) return true;
            } catch(e) {}
        }
        // 检查是否是导航链接
        const tag = el.tagName ? el.tagName.toLowerCase() : '';
        if (tag === 'nav') return true;
        // 检查父元素是否是nav
        if (el.parentElement && el.parentElement.tagName.toLowerCase() === 'nav') {
            // 但保留main里面的内容
            let parent = el.parentElement;
            while (parent) {
                if (parent.tagName.toLowerCase() === 'main') return false;
                if (parent.tagName.toLowerCase() === 'nav') return true;
                parent = parent.parentElement;
            }
        }
        return false;
    }
    
    // 只处理首屏区域内的元素
    const viewportHeight = window.innerHeight;
    
    // 强制首屏内容可见 - 处理GSAP等动画库的初始隐藏
    document.querySelectorAll('*').forEach(function(el) {
        // 排除菜单和导航元素
        if (shouldExclude(el)) return;
        
        const rect = el.getBoundingClientRect();
        // 只处理首屏区域内的元素
        if (rect.bottom < 0 || rect.top > viewportHeight) return;
        
        const computed = getComputedStyle(el);
        const opacity = parseFloat(computed.opacity);
        
        // 如果元素被隐藏（opacity为0或接近0），尝试显示它
        if (opacity < 0.01 && rect.height > 0) {
            // 检查是否是动画元素
            const transform = computed.transform;
            const hasTransform = transform && transform !== 'none';
            
            // 将当前计算样式写入内联style
            el.style.opacity = '1';
            if (hasTransform) {
                el.style.transform = transform;
            }
            el.style.visibility = 'visible';
        }
    });
    
    // 特别处理常见的GSAP动画类（但排除导航相关）
    const gsapSelectors = [
        '[class*="alan"]',
        '[class*="gsap"]',
        '[data-speed]',
        '.fn1_alan',
        '.fn2_alan',
        '#firstMv',
        '#firstMedia',
        '.banner',
        '.group.active',
        'h1',
        '.note',
        '.col.half'
    ];
    
    gsapSelectors.forEach(function(selector) {
        try {
            document.querySelectorAll(selector).forEach(function(el) {
                if (shouldExclude(el)) return;
                const rect = el.getBoundingClientRect();
                if (rect.bottom < 0 || rect.top > viewportHeight) return;
                
                // 强制设置为可见 - 覆盖GSAP的内联样式
                el.style.setProperty('opacity', '1', 'important');
                el.style.setProperty('visibility', 'visible', 'important');
                // 清除GSAP的transform
                el.style.setProperty('transform', 'none', 'important');
            });
        } catch(e) {}
    });
    
    // 处理video元素的父容器（首屏内）
    document.querySelectorAll('video').forEach(function(v) {
        const rect = v.getBoundingClientRect();
        if (rect.bottom < 0 || rect.top > viewportHeight) return;
        
        v.style.opacity = '1';
        v.style.display = 'block';
        const parent = v.parentElement;
        if (parent && !shouldExclude(parent)) {
            parent.style.opacity = '1';
        }
    });
    
    console.log('[WebThief] 滚动动画状态已固化');
}
"""

# ─── 鼠标轨迹回放桥接脚本 ──────────────────────────────────
MOUSE_REPLAY_BRIDGE_SCRIPT = """
(function() {
    'use strict';
    // ━━━ WebThief Mouse Replay Bridge ━━━
    
    window.__webthief_mouse_bridge = {
        // 存储录制的轨迹数据
        trajectories: [],
        
        // 添加轨迹
        addTrajectory: function(trajectory) {
            this.trajectories.push(trajectory);
            console.log('[WebThief Mouse Bridge] 添加轨迹:', trajectory.name || 'unnamed');
        },
        
        // 回放所有轨迹
        replayAll: function() {
            this.trajectories.forEach((traj, index) => {
                setTimeout(() => {
                    this.replayTrajectory(traj);
                }, traj.delay || 0);
            });
        },
        
        // 回放单条轨迹
        replayTrajectory: function(trajectory) {
            if (!trajectory || !trajectory.points) return;
            
            const points = trajectory.points;
            const timestamps = trajectory.timestamps || [];
            
            // 创建虚拟光标
            const cursor = document.createElement('div');
            cursor.className = 'webthief-virtual-cursor';
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
            
            // 回放点序列
            let index = 0;
            const playNext = () => {
                if (index >= points.length) {
                    setTimeout(() => cursor.remove(), 1000);
                    return;
                }
                
                const point = points[index];
                cursor.style.left = (point.x - 10) + 'px';
                cursor.style.top = (point.y - 10) + 'px';
                
                // 触发鼠标移动事件
                const element = document.elementFromPoint(point.x, point.y);
                if (element) {
                    element.dispatchEvent(new MouseEvent('mousemove', {
                        bubbles: true,
                        cancelable: true,
                        clientX: point.x,
                        clientY: point.y,
                        view: window
                    }));
                }
                
                index++;
                const delay = index < timestamps.length ? 
                    timestamps[index] - timestamps[index - 1] : 16;
                setTimeout(playNext, Math.min(delay, 100));
            };
            
            playNext();
        }
    };
    
    console.log('[WebThief Mouse Bridge] 鼠标回放桥接已加载');
})();
"""

# ─── Canvas 回放桥接脚本 ───────────────────────────────────
CANVAS_REPLAY_BRIDGE_SCRIPT = """
(function() {
    'use strict';
    // ━━━ WebThief Canvas Replay Bridge ━━━
    
    window.__webthief_canvas_bridge = {
        // 存储 Canvas 录制数据
        recordings: {},
        
        // 注册录制数据
        registerRecording: function(selector, recordingData) {
            this.recordings[selector] = recordingData;
            console.log('[WebThief Canvas Bridge] 注册录制:', selector);
        },
        
        // 回放 Canvas 绘制
        replay: function(selector) {
            const recording = this.recordings[selector];
            if (!recording) {
                console.warn('[WebThief Canvas Bridge] 未找到录制:', selector);
                return;
            }
            
            const canvas = document.querySelector(selector);
            if (!canvas) {
                console.warn('[WebThief Canvas Bridge] 未找到 Canvas:', selector);
                return;
            }
            
            const ctx = canvas.getContext('2d');
            if (!ctx) {
                console.warn('[WebThief Canvas Bridge] 无法获取 2D 上下文');
                return;
            }
            
            // 清空画布
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            
            // 执行绘制命令
            recording.commands.forEach((cmd, index) => {
                setTimeout(() => {
                    this.executeCommand(ctx, cmd);
                }, cmd.timestamp || 0);
            });
        },
        
        // 执行单条绘制命令
        executeCommand: function(ctx, cmd) {
            try {
                if (cmd.type === 'property' && cmd.method.startsWith('set:')) {
                    const prop = cmd.method.replace('set:', '');
                    ctx[prop] = cmd.args[0];
                } else if (typeof ctx[cmd.method] === 'function') {
                    ctx[cmd.method].apply(ctx, cmd.args);
                }
            } catch (e) {
                console.error('[WebThief Canvas Bridge] 执行命令失败:', cmd, e);
            }
        },
        
        // 设置 Canvas 为静态图片（fallback）
        setStaticImage: function(selector, imageDataUrl) {
            const canvas = document.querySelector(selector);
            if (!canvas) return;
            
            const ctx = canvas.getContext('2d');
            const img = new Image();
            img.onload = function() {
                ctx.clearRect(0, 0, canvas.width, canvas.height);
                ctx.drawImage(img, 0, 0);
            };
            img.src = imageDataUrl;
        }
    };
    
    console.log('[WebThief Canvas Bridge] Canvas 回放桥接已加载');
})();
"""

# ─── WebGL 兼容层脚本 ──────────────────────────────────────
WEBGL_COMPATIBILITY_SCRIPT = """
(function() {
    'use strict';
    // ━━━ WebThief WebGL Compatibility Layer ━━━
    
    // 保存原始 getContext
    const _origGetContext = HTMLCanvasElement.prototype.getContext;
    
    // 拦截 getContext
    HTMLCanvasElement.prototype.getContext = function(contextType, contextAttributes) {
        const isWebGL = contextType === 'webgl' || contextType === 'experimental-webgl' || 
                       contextType === 'webgl2' || contextType === 'experimental-webgl2';
        
        if (isWebGL) {
            console.log('[WebThief WebGL] 创建上下文:', contextType);
            
            // 添加兼容性属性
            const attrs = contextAttributes || {};
            attrs.failIfMajorPerformanceCaveat = false;
            attrs.powerPreference = attrs.powerPreference || 'default';
            
            const gl = _origGetContext.call(this, contextType, attrs);
            
            if (!gl) {
                console.warn('[WebThief WebGL] 上下文创建失败');
                return null;
            }
            
            // 添加上下文丢失处理
            this.addEventListener('webglcontextlost', function(e) {
                console.warn('[WebThief WebGL] 上下文丢失');
                e.preventDefault();
            }, false);
            
            return gl;
        }
        
        return _origGetContext.apply(this, arguments);
    };
    
    // 拦截 Image 加载以处理 CORS
    const _origImageSrcSetter = Object.getOwnPropertyDescriptor(HTMLImageElement.prototype, 'src').set;
    Object.defineProperty(HTMLImageElement.prototype, 'src', {
        set: function(value) {
            if (value && typeof value === 'string' && !value.startsWith('data:') && !value.startsWith('blob:')) {
                try {
                    const url = new URL(value, window.location.href);
                    if (url.origin !== window.location.origin) {
                        this.crossOrigin = 'anonymous';
                    }
                } catch (e) {}
            }
            return _origImageSrcSetter.call(this, value);
        },
        get: function() {
            return this.getAttribute('src');
        }
    });
    
    console.log('[WebThief WebGL] 兼容层已加载');
})();
"""

# ─── 高精度滚动脚本 ────────────────────────────────────────
PRECISION_SCROLL_SCRIPT = """
async () => {
    // ━━━ WebThief Precision Scroll Script ━━━
    
    const wait = (ms) => new Promise((r) => setTimeout(r, ms));
    
    // 高精度滚动配置
    const config = {
        stepSize: 50,        // 每步滚动像素
        stepDelay: 100,      // 每步延迟（毫秒）
        pauseAtPoints: true, // 在关键点暂停
        captureIntermediate: true // 捕获中间状态
    };
    
    const scrollHeight = Math.max(
        document.body ? document.body.scrollHeight : 0,
        document.documentElement ? document.documentElement.scrollHeight : 0
    );
    
    const viewportHeight = window.innerHeight;
    const totalSteps = Math.ceil(scrollHeight / config.stepSize);
    
    console.log('[WebThief Precision Scroll] 开始高精度滚动，总步数:', totalSteps);
    
    // 记录滚动采样点
    window.__webthief_scroll_samples = [];
    
    for (let i = 0; i <= totalSteps; i++) {
        const targetY = Math.min(i * config.stepSize, scrollHeight - viewportHeight);
        
        // 平滑滚动到目标位置
        window.scrollTo({
            top: targetY,
            behavior: 'smooth'
        });
        
        // 等待滚动完成
        await wait(config.stepDelay);
        
        // 记录采样点
        if (config.captureIntermediate) {
            window.__webthief_scroll_samples.push({
                position: window.scrollY,
                timestamp: Date.now(),
                step: i
            });
        }
        
        // 触发滚动事件以激活动画
        window.dispatchEvent(new Event('scroll', { bubbles: true }));
        window.dispatchEvent(new WheelEvent('wheel', {
            deltaY: config.stepSize,
            bubbles: true
        }));
        
        // 在关键点额外等待
        if (config.pauseAtPoints && i % 10 === 0) {
            await wait(300);
        }
    }
    
    // 回到顶部
    window.scrollTo({ top: 0, behavior: 'smooth' });
    await wait(500);
    
    console.log('[WebThief Precision Scroll] 高精度滚动完成，采样点:', window.__webthief_scroll_samples.length);
    
    return {
        totalSteps: totalSteps,
        samples: window.__webthief_scroll_samples
    };
}
"""

# ─── 动画分析桥接脚本 ──────────────────────────────────────
ANIMATION_ANALYSIS_BRIDGE_SCRIPT = """
(function() {
    'use strict';
    // ━━━ WebThief Animation Analysis Bridge ━━━
    
    window.__webthief_animation_bridge = {
        // 存储动画分析结果
        analysisResult: null,
        
        // 设置分析结果
        setAnalysisResult: function(result) {
            this.analysisResult = result;
            console.log('[WebThief Animation Bridge] 分析结果已设置');
        },
        
        // 应用动画冻结
        applyFreeze: function() {
            if (!this.analysisResult) {
                console.warn('[WebThief Animation Bridge] 无分析结果');
                return;
            }
            
            const preservedAnimations = this.analysisResult.preserved_animations || [];
            const removedAnimations = this.analysisResult.removed_animations || [];
            
            // 冻结被移除的动画
            removedAnimations.forEach(anim => {
                document.querySelectorAll(`[style*="animation-name: ${anim.name}"]`).forEach(el => {
                    el.style.animation = 'none !important';
                });
            });
            
            console.log('[WebThief Animation Bridge] 动画冻结已应用');
        },
        
        // 获取动画统计
        getStats: function() {
            const allElements = document.querySelectorAll('*');
            let animatedCount = 0;
            
            allElements.forEach(el => {
                const style = window.getComputedStyle(el);
                if (style.animationName && style.animationName !== 'none') {
                    animatedCount++;
                }
            });
            
            return {
                totalElements: allElements.length,
                animatedElements: animatedCount,
                preservedCount: this.analysisResult?.preserved_animations?.length || 0
            };
        }
    };
    
    console.log('[WebThief Animation Bridge] 动画分析桥接已加载');
})();
"""
