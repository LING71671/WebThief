#!/usr/bin/env python3
"""
重新转换 TRAE-Skills-150 为 Trae IDE 兼容的 SKILL.md 格式
"""
import re
import shutil
from pathlib import Path

SOURCE_DIR = Path("A:/TRAE-Skills-150/TRAE-Skills-main")
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


def to_kebab_case(name):
    """将文件名转换为 kebab-case"""
    name = name.replace(".md", "")
    name = re.sub(r'[^\w\s-]', "", name)
    name = re.sub(r'[_\s]+', "-", name.lower())
    name = re.sub(r'-+', "-", name)
    return name.strip("-")


def extract_info(content, filename):
    """从内容中提取 name 和 description"""
    lines = content.split('\n')
    
    title = ""
    for line in lines:
        if line.startswith("# Skill:"):
            title = line.replace("# Skill:", "").strip()
            break
        elif line.startswith("# ") and not title:
            title = line.replace("# ", "").strip()
    
    purpose = ""
    in_purpose = False
    for line in lines:
        if line.strip() == "## Purpose":
            in_purpose = True
            continue
        if in_purpose:
            if line.startswith("##"):
                break
            if line.strip() and not purpose:
                purpose = line.strip()
                break
    
    name = to_kebab_case(filename)
    
    if purpose:
        desc = purpose
    elif title:
        desc = f"Skill for {title}"
    else:
        desc = f"Skill: {filename}"
    
    if len(desc) > 180:
        desc = desc[:177] + "..."
    
    return name, desc


def convert_skill_file(source_path, target_dir):
    """转换单个技能文件"""
    try:
        content = source_path.read_text(encoding='utf-8')
        name, description = extract_info(content, source_path.name)
        
        new_content = f"""---
name: "{name}"
description: "{description}"
---

{content}
"""
        
        skill_dir = target_dir / name
        skill_dir.mkdir(parents=True, exist_ok=True)
        skill_file = skill_dir / "SKILL.md"
        skill_file.write_text(new_content, encoding='utf-8')
        return True
    except Exception as e:
        print(f"转换失败 {source_path}: {e}")
        return False


def main():
    """主函数"""
    print("正在删除旧的技能目录...")
    if TARGET_DIR.exists():
        shutil.rmtree(TARGET_DIR)
    
    total = 0
    success = 0
    failed = 0
    
    print("开始转换技能...")
    for category in CATEGORIES:
        source_category_dir = SOURCE_DIR / category
        target_category_dir = TARGET_DIR / category
        
        if not source_category_dir.exists():
            continue
        
        target_category_dir.mkdir(parents=True, exist_ok=True)
        
        for md_file in source_category_dir.glob("*.md"):
            total += 1
            if convert_skill_file(md_file, target_category_dir):
                success += 1
                print(f"✓ {category}/{md_file.name}")
            else:
                failed += 1
                print(f"✗ {category}/{md_file.name}")
    
    print(f"\n转换完成!")
    print(f"总计: {total}")
    print(f"成功: {success}")
    print(f"失败: {failed}")
    
    if success > 0:
        print(f"\n✅ 技能已转换到: {TARGET_DIR}")
        print("\n请按以下步骤操作:")
        print("1. 完全关闭 Trae IDE")
        print("2. 重新启动 Trae IDE")
        print("3. 刷新技能面板")


if __name__ == "__main__":
    main()
