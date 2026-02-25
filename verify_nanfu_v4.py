#!/usr/bin/env python3
"""验证南孚官网克隆结果 (v4 修复后版本)"""

from pathlib import Path

# 读取 index.html
html_path = Path("nanfu_test_v4/index.html")

if not html_path.exists():
    print(f"❌ 文件不存在: {html_path}")
    exit(1)

# 读取文件内容
content = html_path.read_text(encoding='utf-8')

print("=" * 60)
print("📄 文件信息 (修复后版本 v4)")
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
print(f"✗ 包含转义的换行符 \\n\\n: {repr('\\n\\n') in content}")
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
print()

# 最终验证
print("=" * 60)
print("✅ 最终验证结果")
print("=" * 60)
is_valid_html = (
    content.startswith('<!DOCTYPE html>') and
    '<html' in content and
    '<body' in content and
    '</html>' in content and
    repr('\\n\\n') not in content[:1000]
)

if is_valid_html:
    print("🎉 成功！HTML 文件格式正确")
    print("   - 正确的 DOCTYPE 声明")
    print("   - 包含完整的 HTML 结构")
    print("   - 不包含 JSON 格式的错误内容")
else:
    print("❌ 失败！HTML 文件可能存在问题")
