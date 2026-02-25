#!/usr/bin/env python3
"""
修复技能文件的 frontmatter 格式
"""
import re
from pathlib import Path

TARGET_DIR = Path.home() / ".trae" / "skills"

CATEGORIES = [
    "ai_engineering",
    "architecture",
    "backend",
    "code_management",
    "devops",
    "documentation",
    "frontend",
    "mobile",
    "security",
    "testing"
]


def clean_description(desc):
    """清理描述"""
    desc = re.sub(r'\s*当用户需要.*$', '', desc)
    desc = re.sub(r'\s*当用户询问相关主题时调用此技能\.', '', desc)
    desc = desc.rstrip('. ').strip()
    if len(desc) > 180:
        desc = desc[:177] + "..."
    return desc


def fix_skill_file(skill_file):
    """修复单个技能文件"""
    try:
        content = skill_file.read_text(encoding='utf-8')
        lines = content.split('\n')
        
        frontmatter_start = -1
        frontmatter_end = -1
        for i, line in enumerate(lines):
            if line.strip() == "---" and frontmatter_start == -1:
                frontmatter_start = i
            elif line.strip() == "---" and frontmatter_start != -1:
                frontmatter_end = i
                break
        
        if frontmatter_start == -1 or frontmatter_end == -1:
            print(f"警告: 找不到 frontmatter {skill_file}")
            return False
        
        frontmatter_lines = lines[frontmatter_start + 1:frontmatter_end]
        name = ""
        old_desc = ""
        for line in frontmatter_lines:
            if line.strip().startswith('name:'):
                name = line.strip().split(':', 1)[1].strip().strip('"')
            elif line.strip().startswith('description:'):
                old_desc = line.strip().split(':', 1)[1].strip().strip('"')
        
        if not name or not old_desc:
            print(f"警告: 缺少 name 或 description {skill_file}")
            return False
        
        new_desc = clean_description(old_desc)
        new_frontmatter = f"""---
name: "{name}"
description: "{new_desc}"
---
"""
        
        body_lines = lines[frontmatter_end + 1:]
        new_content = new_frontmatter + "\n".join(body_lines)
        skill_file.write_text(new_content, encoding='utf-8')
        print(f"✓ 修复: {skill_file.parent.name}")
        return True
        
    except Exception as e:
        print(f"✗ 失败 {skill_file}: {e}")
        return False


def main():
    """主函数"""
    total = 0
    success = 0
    failed = 0
    
    for category in CATEGORIES:
        category_dir = TARGET_DIR / category
        if not category_dir.exists():
            continue
        
        for skill_dir in category_dir.iterdir():
            if not skill_dir.is_dir():
                continue
            
            skill_file = skill_dir / "SKILL.md"
            if not skill_file.exists():
                continue
            
            total += 1
            if fix_skill_file(skill_file):
                success += 1
            else:
                failed += 1
    
    print(f"\n修复完成!")
    print(f"总计: {total}")
    print(f"成功: {success}")
    print(f"失败: {failed}")


if __name__ == "__main__":
    main()
