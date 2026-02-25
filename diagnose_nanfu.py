#!/usr/bin/env python3
"""诊断南孚官网克隆的问题"""

from pathlib import Path

# 读取 index.html
html_path = Path("nanfu_test_v3/index.html")

if not html_path.exists():
    print(f"❌ 文件不存在: {html_path}")
    exit(1)

# 读取文件内容
content = html_path.read_text(encoding='utf-8')

print("=" * 60)
print("📄 文件信息")
print("=" * 60)
print(f"文件路径: {html_path.absolute()}")
print(f"文件大小: {len(content):,} 字符")
print(f"文件大小: {html_path.stat().st_size:,} 字节")
print()

print("=" * 60)
print("📝 前 500 个字符")
print("=" * 60)
print(content[:500])
print()

print("=" * 60)
print("🔍 检查关键标签")
print("=" * 60)
print(f"✓ 包含 <!DOCTYPE html>: {'<!DOCTYPE html>' in content}")
print(f"✓ 包含 <html: {'<html' in content}")
print(f"✓ 包含 <head>: {'<head>' in content}")
print(f"✓ 包含 <body: {'<body' in content}")
print(f"✓ 包含 </html>: {'</html>' in content}")
print()

# 检查是否有异常字符
print("=" * 60)
print("🔍 检查异常内容")
print("=" * 60)
print(f"✓ 包含 'content-type': {'content-type' in content.lower()}")
print(f"✓ 包含 'text/html': {'text/html' in content.lower()}")
print(f"✓ 包含转义的换行符 \\n\\n: {repr('\\n\\n') in content}")
print()

# 检查文件开头是否有 BOM 或其他字符
first_bytes = html_path.read_bytes()[:100]
print("=" * 60)
print("🔍 文件开头字节 (前 100 字节)")
print("=" * 60)
print(first_bytes)
print()
print("十六进制:")
print(first_bytes.hex(' ', 1))
