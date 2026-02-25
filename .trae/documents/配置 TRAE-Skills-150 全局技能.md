## 配置方案：将 A:\TRAE-Skills-150 转换为 Trae IDE 全局技能

### 目标路径
`%USERPROFILE%\.trae\skills\` (Windows 用户目录下的 .trae/skills/)

### 实施步骤

#### 1. 创建目录结构
创建以下分类目录：
- `ai_engineering/`
- `architecture/`
- `backend/`
- `code_management/`
- `devops/`
- `documentation/`
- `frontend/`
- `mobile/`
- `security/`
- `testing/`

#### 2. 转换文件格式
将每个 `.md` 文件转换为 Trae IDE 兼容的 `SKILL.md` 格式：

**原格式**:
```markdown
# Skill: XXX

## Purpose
...

## When to Use
...
```

**转换后格式**:
```markdown
---
name: "xxx-xxx"
description: "简要描述. 当用户需要...时调用此技能."
---

# XXX

## Purpose
...

## When to Use
...
```

#### 3. 文件命名规范
- 将文件名转换为 kebab-case（短横线连接的小写）
- 例如：`API_REST_Endpoint_Design.md` → `api-rest-endpoint-design/SKILL.md`

#### 4. 转换示例

**JWT_Authentication.md** → `jwt-authentication/SKILL.md`:
```markdown
---
name: "jwt-authentication"
description: "使用 JWT 实现无状态用户认证. 当用户需要实现登录/注册、API 认证或微服务身份共享时调用此技能."
---

# JWT Authentication Implementation
...原内容...
```

#### 5. 批量处理
我将编写脚本自动处理所有 150+ 个技能文件的转换和复制。

### 预期结果
转换完成后，你可以在 Trae IDE 中使用这些技能，它们会出现在技能列表中，可以通过自然语言描述自动触发。

### 确认后执行
请确认此计划，我将立即开始执行配置。