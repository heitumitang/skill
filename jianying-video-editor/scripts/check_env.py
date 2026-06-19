#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_env.py — 检查 jianying-video-editor skill 运行环境
"""
import os
import sys
import shutil
import subprocess

# 强制 stdout 使用 UTF-8（Windows 控制台默认 gbk 会导致乱码）
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

DRAFT_DIR = os.path.join(
    os.environ.get("LOCALAPPDATA", ""),
    "JianyingPro", "User Data", "Projects", "com.lveditor.draft"
)

def check_ffprobe():
    if shutil.which("ffprobe"):
        result = subprocess.run(["ffprobe", "-version"], capture_output=True, text=True)
        version_line = result.stdout.splitlines()[0] if result.stdout else "unknown"
        print(f"[OK] ffprobe: {version_line}")
        return True
    else:
        print("[FAIL] ffprobe not found. Install ffmpeg: https://ffmpeg.org/download.html")
        return False

def check_draft_dir():
    if os.path.isdir(DRAFT_DIR):
        writable = os.access(DRAFT_DIR, os.W_OK)
        print(f"[OK] 草稿目录存在: {DRAFT_DIR}")
        print(f"[{'OK' if writable else 'FAIL'}] 目录可写: {writable}")
        return writable
    else:
        print(f"[FAIL] 草稿目录不存在: {DRAFT_DIR}")
        print("      请确认剪映已安装且曾创建过草稿")
        return False

def check_python():
    print(f"[OK] Python: {sys.version.split()[0]} at {sys.executable}")
    return True

if __name__ == "__main__":
    print("=== jianying-video-editor 环境检查 ===\n")
    ok = True
    ok &= check_python()
    ok &= check_ffprobe()
    ok &= check_draft_dir()
    print(f"\n{'所有检查通过，可以开始使用' if ok else '存在问题，请根据提示修复后再使用'}")
    sys.exit(0 if ok else 1)
