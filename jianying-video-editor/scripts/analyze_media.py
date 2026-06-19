#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
analyze_media.py — 使用 ffprobe 分析视频/音频素材基本信息

用法：
  python analyze_media.py --files video1.mp4 video2.mp4 [--output result.json]

输出 JSON 格式：
  [
    {
      "path": "absolute/path/to/video.mp4",
      "filename": "video.mp4",
      "duration_us": 10000000,       # 微秒 (1s = 1_000_000us)
      "duration_sec": 10.0,
      "width": 1920,
      "height": 1080,
      "fps": 30.0,
      "has_audio": true,
      "has_video": true,
      "type": "video"                 # "video" / "audio" / "image"
    }
  ]
"""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def _find_ffprobe() -> str | None:
    """尝试找到 ffprobe 可执行文件"""
    # 1. 系统 PATH
    from shutil import which
    path = which("ffprobe")
    if path:
        return path
    # 2. 已下载到 workbuddy 的 ffmpeg
    fb_dir = Path.home() / ".workbuddy" / "binaries" / "ffmpeg"
    if fb_dir.exists():
        for p in fb_dir.rglob("ffprobe.exe"):
            return str(p)
    return None


def _probe_cv2(file_path: str) -> dict | None:
    """使用 cv2 作为回退方案分析视频文件"""
    try:
        import cv2
    except ImportError:
        return None
    abs_path = str(Path(file_path).resolve())
    ext = Path(abs_path).suffix.lower()
    
    if ext in (".mp3", ".wav", ".aac", ".flac", ".m4a", ".ogg"):
        return {
            "path": abs_path, "filename": os.path.basename(abs_path),
            "duration_us": 0, "duration_sec": 0.0,
            "width": 0, "height": 0, "fps": 0.0,
            "has_audio": True, "has_video": False, "type": "audio",
        }
    if ext in (".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif"):
        return {
            "path": abs_path, "filename": os.path.basename(abs_path),
            "duration_us": 0, "duration_sec": 0.0,
            "width": 0, "height": 0, "fps": 0.0,
            "has_audio": False, "has_video": True, "type": "image",
        }
    
    cap = cv2.VideoCapture(abs_path)
    if not cap.isOpened():
        return None
    
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration_sec = frame_count / fps if fps > 0 else 0.0
    cap.release()
    
    return {
        "path": abs_path, "filename": os.path.basename(abs_path),
        "duration_us": int(duration_sec * 1_000_000),
        "duration_sec": round(duration_sec, 3),
        "width": width, "height": height,
        "fps": round(fps, 3),
        "has_audio": True, "has_video": True, "type": "video",
    }


def probe_file(file_path: str) -> dict:
    """使用 ffprobe 获取媒体文件信息，回退到 cv2"""
    abs_path = str(Path(file_path).resolve())
    
    ffprobe_path = _find_ffprobe()
    
    if not ffprobe_path:
        print(f"[INFO] ffprobe 未找到，尝试 cv2 回退分析: {abs_path}", file=sys.stderr)
        result = _probe_cv2(file_path)
        if result is None:
            print(f"[ERROR] cv2 也无法分析: {abs_path}", file=sys.stderr)
        return result
    
    cmd = [
        ffprobe_path, "-v", "quiet",
        "-print_format", "json",
        "-show_format", "-show_streams",
        abs_path
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            print(f"[WARN] ffprobe 分析失败，尝试 cv2 回退: {abs_path}", file=sys.stderr)
            return _probe_cv2(file_path)
        
        data = json.loads(result.stdout)
    except (subprocess.TimeoutExpired, json.JSONDecodeError) as e:
        print(f"[WARN] ffprobe 异常，尝试 cv2 回退: {abs_path}: {e}", file=sys.stderr)
        return _probe_cv2(file_path)
    except Exception as e:
        print(f"[ERROR] 分析文件失败 {abs_path}: {e}", file=sys.stderr)
        return _probe_cv2(file_path)
    
    streams = data.get("streams", [])
    fmt = data.get("format", {})
    
    # 提取视频流信息
    video_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
    audio_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)
    
    has_video = video_stream is not None
    has_audio = audio_stream is not None
    
    # 时长（优先 format，再从 video stream）
    duration_sec = 0.0
    if "duration" in fmt:
        duration_sec = float(fmt["duration"])
    elif video_stream and "duration" in video_stream:
        duration_sec = float(video_stream["duration"])
    elif audio_stream and "duration" in audio_stream:
        duration_sec = float(audio_stream["duration"])
    
    duration_us = int(duration_sec * 1_000_000)  # 转换为微秒
    
    # 分辨率
    width = int(video_stream.get("width", 0)) if video_stream else 0
    height = int(video_stream.get("height", 0)) if video_stream else 0
    
    # 帧率
    fps = 30.0
    if video_stream:
        fps_str = video_stream.get("r_frame_rate", "30/1")
        try:
            num, den = fps_str.split("/")
            fps = round(float(num) / float(den), 3)
        except Exception:
            fps = 30.0
    
    # 文件类型判断
    ext = Path(abs_path).suffix.lower()
    if ext in (".mp3", ".wav", ".aac", ".flac", ".m4a", ".ogg"):
        file_type = "audio"
    elif ext in (".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif"):
        file_type = "image"
    else:
        file_type = "video" if has_video else "audio"
    
    return {
        "path": abs_path,
        "filename": os.path.basename(abs_path),
        "duration_us": duration_us,
        "duration_sec": round(duration_sec, 3),
        "width": width,
        "height": height,
        "fps": fps,
        "has_audio": has_audio,
        "has_video": has_video,
        "type": file_type,
    }


def analyze_files(file_paths: list[str]) -> list[dict]:
    results = []
    for fp in file_paths:
        if not os.path.exists(fp):
            print(f"[WARN] 文件不存在，跳过: {fp}", file=sys.stderr)
            continue
        info = probe_file(fp)
        if info:
            results.append(info)
            print(f"[OK] {info['filename']}: {info['duration_sec']}s, "
                  f"{info['width']}x{info['height']}, fps={info['fps']}, "
                  f"audio={info['has_audio']}", file=sys.stderr)
    return results


def main():
    parser = argparse.ArgumentParser(description="分析媒体素材信息")
    parser.add_argument("--files", nargs="+", required=True, help="素材文件路径列表")
    parser.add_argument("--output", default=None, help="输出 JSON 文件路径（默认输出到 stdout）")
    args = parser.parse_args()
    
    results = analyze_files(args.files)
    
    output_json = json.dumps(results, ensure_ascii=False, indent=2)
    
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output_json)
        print(f"[OK] 分析结果已保存到: {args.output}", file=sys.stderr)
    else:
        print(output_json)


if __name__ == "__main__":
    main()
