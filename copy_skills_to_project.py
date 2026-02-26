#!/usr/bin/env python3
"""
将全局技能复制到项目目录
"""
import shutil
from pathlib import Path

SOURCE_DIR = Path.home() / ".trae" / "skills"
TARGET_DIR = Path("b:/WebThief/.trae/skills")

# 要排除的目录（已存在的）
EXCLUDE = {"test-skill"}

def main():
    """主函数"""
    # 确保目标目录存在
    TARGET_DIR.mkdir(parents=True, exist_ok=True)
    
    total = 0
    success = 0
    failed = 0
    
    for skill_dir in SOURCE_DIR.iterdir():
        if not skill_dir.is_dir():
            continue
        
        skill_name = skill_dir.name
        
        # 跳过已存在的
        if skill_name in EXCLUDE:
            print(f"跳过: {skill_name}")
            continue
        
        target_skill_dir = TARGET_DIR / skill_name
        
        try:
            if target_skill_dir.exists():
                shutil.rmtree(target_skill_dir)
            
            shutil.copytree(skill_dir, target_skill_dir)
            success += 1
            print(f"✓ 复制: {skill_name}")
        except Exception as e:
            failed += 1
            print(f"✗ 失败: {skill_name}: {e}")
        
        total += 1
    
    print(f"\n复制完成!")
    print(f"总计: {total}")
    print(f"成功: {success}")
    print(f"失败: {failed}")
    
    if success > 0:
        print(f"\n✅ 技能已复制到: {TARGET_DIR}")
        print("\n请按以下步骤操作:")
        print("1. 在 Trae IDE 中输入相关话题触发技能")
        print("2. 查看'产物汇总'中是否显示技能")
        print("3. 点击'应用到全局'按钮")


if __name__ == "__main__":
    main()
