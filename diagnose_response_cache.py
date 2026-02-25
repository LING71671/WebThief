#!/usr/bin/env python3
"""诊断 response_cache 中是否包含 HTML 内容"""

import json
import re
from pathlib import Path

# 读取 index.html 文件
html_path = Path("nanfu_test_v4/index.html")
content = html_path.read_text(encoding='utf-8')

# 查找 __WEBTHIEF_RESPONSE_MAP__ 的内容
pattern = r'window\.__WEBTHIEF_RESPONSE_MAP__\s*=\s*(\{.*?\});'
match = re.search(pattern, content, re.DOTALL)

if match:
    print("=" * 60)
    print("🔍 找到 __WEBTHIEF_RESPONSE_MAP__")
    print("=" * 60)

    # 提取 JSON 字符串
    json_str = match.group(1)

    # 查找所有包含 body 的条目
    body_pattern = r'"body":\s*"([^"]*(?:\\.[^"]*)*)"'
    bodies = re.findall(body_pattern, json_str)

    print(f"\n找到 {len(bodies)} 个缓存的响应体\n")

    for i, body in enumerate(bodies[:5]):  # 只显示前5个
        print(f"--- 响应体 {i+1} ---")
        # 解码转义字符
        decoded = body.encode('utf-8').decode('unicode_escape')
        print(f"前 200 字符: {decoded[:200]}")
        print(f"包含 <!DOCTYPE html>: {'<!DOCTYPE html>' in decoded}")
        print(f"包含 <html: {'<html' in decoded}")
        print()

    # 检查是否有 HTML 被错误缓存
    html_count = 0
    for body in bodies:
        decoded = body.encode('utf-8').decode('unicode_escape')
        if '<!DOCTYPE html>' in decoded or '<html' in decoded:
            html_count += 1

    print(f"\n⚠️  发现 {html_count} 个响应体包含 HTML 内容")
    print("这些 HTML 内容不应该被缓存为 API 响应！")
else:
    print("❌ 未找到 __WEBTHIEF_RESPONSE_MAP__")
