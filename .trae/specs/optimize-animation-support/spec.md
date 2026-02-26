# WebThief 动画与动效支持优化 Spec

## Why

WebThief 在处理现代网页的动画和动效时存在明显局限性，包括：鼠标跟随动画无法复刻、复杂滚动联动效果不准确、物理引擎动画只能截图、WebGL/Canvas 交互受限等。这些局限性导致克隆结果的交互体验与原始网站存在差距，需要针对性优化。

## What Changes

- **增强鼠标/指针事件模拟**：实现连续鼠标轨迹模拟，支持鼠标跟随动画
- **优化滚动触发动画**：改进视口激活算法，支持更复杂的滚动联动效果
- **增强 Canvas/WebGL 支持**：实现交互式 Canvas 录制和回放
- **优化 CSS 动画处理**：智能识别和保留关键动画，支持动画时间轴同步
- **增强物理引擎动画支持**：实现基于时间的动画状态捕获
- **改进 Hover 状态保留**：更智能的悬停状态检测和固化

## Impact

- **Affected specs**: 渲染策略、资源嗅探、DOM 处理、动画冻结/保留逻辑
- **Affected code**:
  - `webthief/core/renderer.py` - 渲染流程增强
  - `webthief/scripts.py` - JavaScript 注入脚本优化
  - `webthief/extractor/tech_analyzer.py` - 动画库检测增强
  - `webthief/strategy/clone_strategy.py` - 动画处理策略
  - `webthief/interceptors/` - 新增动画拦截器

## ADDED Requirements

### Requirement: 鼠标/指针事件模拟增强

The system SHALL provide enhanced mouse/pointer event simulation to support mouse-following animations.

#### Scenario: 鼠标跟随动画捕获
- **WHEN** the cloned website contains mouse-following animations
- **THEN** the system SHALL simulate continuous mouse movement trajectories
- **AND** capture the animation states at different mouse positions
- **AND** inject a runtime script that replays mouse movement patterns

#### Scenario: 指针事件序列记录
- **WHEN** the website uses pointer events (pointermove, pointerenter, etc.)
- **THEN** the system SHALL record the sequence of pointer events
- **AND** store the event data including coordinates, pressure, tilt
- **AND** replay the events during cloning to trigger animations

### Requirement: 滚动触发动画优化

The system SHALL improve scroll-triggered animation capture with advanced viewport activation.

#### Scenario: 复杂滚动联动效果
- **WHEN** the website uses complex scroll-linked animations (parallax, pin, scrub)
- **THEN** the system SHALL detect scroll trigger libraries (GSAP ScrollTrigger, ScrollMagic)
- **AND** execute scroll sequences with variable speeds
- **AND** capture intermediate animation states
- **AND** preserve scroll position-dependent styles

#### Scenario: 视差滚动效果
- **WHEN** the website contains parallax scrolling effects
- **THEN** the system SHALL calculate parallax layer positions at multiple scroll points
- **AND** convert parallax effects to CSS transforms
- **AND** ensure visual consistency across different viewport sizes

### Requirement: Canvas/WebGL 交互增强

The system SHALL enhance Canvas/WebGL support for interactive content.

#### Scenario: 交互式 Canvas 录制
- **WHEN** the website contains interactive Canvas elements
- **THEN** the system SHALL record Canvas method calls (drawImage, fillRect, etc.)
- **AND** capture user interaction events on Canvas
- **AND** generate a replay script for offline viewing

#### Scenario: WebGL 状态捕获
- **WHEN** the website uses WebGL for 3D rendering
- **THEN** the system SHALL capture WebGL context state
- **AND** record shader programs and buffer data
- **AND** provide a fallback to screenshot for unsupported features

### Requirement: CSS 动画智能处理

The system SHALL intelligently handle CSS animations with better state preservation.

#### Scenario: 关键动画识别
- **WHEN** the website has CSS animations
- **THEN** the system SHALL identify critical animations (entrance, hover, scroll)
- **AND** calculate optimal animation freeze points
- **AND** preserve animation keyframes in the cloned output

#### Scenario: 动画时间轴同步
- **WHEN** multiple elements have synchronized animations
- **THEN** the system SHALL maintain animation timing relationships
- **AND** inject CSS animation-delay adjustments
- **AND** ensure animations play in correct sequence

### Requirement: 物理引擎动画支持

The system SHALL provide better support for physics-based animations.

#### Scenario: 物理动画状态捕获
- **WHEN** the website uses physics engines (Matter.js, Planck.js)
- **THEN** the system SHALL capture physics world state at multiple timestamps
- **AND** record body positions, velocities, and forces
- **AND** generate static representations of physics simulations

#### Scenario: 粒子效果处理
- **WHEN** the website contains particle systems
- **THEN** the system SHALL capture particle positions at stable states
- **AND** convert dynamic particles to static SVG or Canvas
- **AND** preserve visual appearance while removing simulation logic

### Requirement: Hover 状态智能保留

The system SHALL improve hover state detection and preservation.

#### Scenario: 复杂 Hover 效果
- **WHEN** the website has complex hover effects (transforms, filters, transitions)
- **THEN** the system SHALL detect all hover-triggered style changes
- **AND** apply the most visually significant hover state
- **AND** convert hover effects to static CSS or persistent classes

#### Scenario: 嵌套 Hover 状态
- **WHEN** elements have nested hover states (parent hover affects children)
- **THEN** the system SHALL trace hover state dependencies
- **AND** apply consistent hover states across related elements
- **AND** preserve hover-triggered visibility changes

## MODIFIED Requirements

### Requirement: 渲染策略增强

**Existing**: Basic render strategy with simple scroll and animation handling

**Modified**: Enhanced render strategy with animation-specific optimizations

- **ADDED**: `mouse_simulation` flag for mouse-following animations
- **ADDED**: `scroll_precision` option for scroll-linked animations
- **ADDED**: `canvas_recording` flag for interactive Canvas
- **ADDED**: `physics_capture` flag for physics-based animations
- **MODIFIED**: `animation_freeze` logic to support selective freezing

### Requirement: 技术栈检测增强

**Existing**: Basic animation library detection (GSAP, Lottie, Anime.js)

**Modified**: Comprehensive animation technology detection

- **ADDED**: Detection of physics engines (Matter.js, Planck.js, Cannon.js)
- **ADDED**: Detection of scroll trigger libraries (ScrollTrigger, ScrollMagic)
- **ADDED**: Detection of particle systems (particles.js, tsParticles)
- **ADDED**: Detection of mouse interaction libraries
- **ADDED**: Animation complexity scoring

## REMOVED Requirements

None. All existing functionality SHALL be preserved.
