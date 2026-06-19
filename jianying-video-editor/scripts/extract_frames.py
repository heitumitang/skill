#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
extract_frames.py — 从视频素材中提取关键帧，供 AI 视觉分析

用法：
  python extract_frames.py --files video1.mp4 video2.mp4 \
    [--output-dir ./frames] [--frames-per-clip 3] [--format jpg]

输出：
  1. 帧图片保存到 output_dir/ 下
  2. stdout 输出 JSON，包含每段视频的帧路径和元信息

JSON 格式：
  [
    {
      "video_path": "absolute/path/to/video.mp4",
      "filename": "video.mp4",
      "duration_sec": 10.0,
      "width": 1920,
      "height": 1080,
      "frames": [
        {
          "index": 0,
          "time_sec": 1.0,
          "path": "absolute/path/to/frames/video_0_0.jpg"
        }
      ]
    }
  ]
"""
import argparse
import json
import os
import sys
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def extract_frames(video_path: str, output_dir: str, frames_per_clip: int = 3,
                   fmt: str = "jpg", quality: int = 85) -> dict | None:
    """从单个视频提取关键帧"""
    try:
        import cv2
    except ImportError:
        print("[ERROR] 需要 opencv-python-headless，请安装: pip install opencv-python-headless", file=sys.stderr)
        return None

    abs_path = str(Path(video_path).resolve())
    cap = cv2.VideoCapture(abs_path)
    if not cap.isOpened():
        print(f"[WARN] 无法打开视频: {abs_path}", file=sys.stderr)
        return None

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration_sec = frame_count / fps if fps > 0 else 0.0

    if duration_sec <= 0 or frame_count <= 0:
        cap.release()
        print(f"[WARN] 无法获取视频时长: {abs_path}", file=sys.stderr)
        return None

    # 生成帧保存目录
    base_name = Path(abs_path).stem
    safe_name = base_name.replace(" ", "_").replace("(", "").replace(")", "")
    clip_dir = os.path.join(output_dir, safe_name)
    os.makedirs(clip_dir, exist_ok=True)

    frames_info = []

    # 计算采样时间点：均匀分布，跳过首尾 5%
    skip_ratio = 0.05
    start_sec = duration_sec * skip_ratio
    end_sec = duration_sec * (1 - skip_ratio)
    usable_range = end_sec - start_sec

    if frames_per_clip <= 1:
        sample_times = [start_sec + usable_range / 2]
    else:
        step = usable_range / (frames_per_clip + 1)
        sample_times = [start_sec + step * (i + 1) for i in range(frames_per_clip)]

    for i, t in enumerate(sample_times):
        frame_number = int(t * fps)
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
        ret, frame = cap.read()
        if not ret:
            print(f"[WARN] 读取帧失败: {abs_path} @ {t:.1f}s", file=sys.stderr)
            continue

        frame_filename = f"frame_{i:02d}.{fmt}"
        frame_path = os.path.join(clip_dir, frame_filename)

        if fmt == "jpg":
            cv2.imwrite(frame_path, frame, [cv2.IMWRITE_JPEG_QUALITY, quality])
        elif fmt == "png":
            cv2.imwrite(frame_path, frame, [cv2.IMWRITE_PNG_COMPRESSION, 6])
        else:
            cv2.imwrite(frame_path, frame)

        frames_info.append({
            "index": i,
            "time_sec": round(t, 2),
            "path": str(Path(frame_path).resolve())
        })
        print(f"  [帧 {i+1}/{frames_per_clip}] {t:.1f}s → {frame_filename}", file=sys.stderr)

    cap.release()

    return {
        "video_path": abs_path,
        "filename": os.path.basename(abs_path),
        "duration_sec": round(duration_sec, 2),
        "width": width,
        "height": height,
        "frames": frames_info
    }


def main():
    parser = argparse.ArgumentParser(description="从视频素材提取关键帧")
    parser.add_argument("--files", nargs="+", required=True, help="视频素材文件路径")
    parser.add_argument("--output-dir", default="./keyframes",
                        help="帧图片输出目录（默认 ./keyframes）")
    parser.add_argument("--frames-per-clip", type=int, default=3,
                        help="每段视频提取帧数（默认 3）")
    parser.add_argument("--format", default="jpg", choices=["jpg", "png"],
                        help="输出图片格式（默认 jpg）")
    parser.add_argument("--quality", type=int, default=85,
                        help="JPEG 质量 0-100（默认 85）")
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)

    results = []
    for fp in args.files:
        if not os.path.exists(fp):
            print(f"[WARN] 文件不存在，跳过: {fp}", file=sys.stderr)
            continue

        print(f"[INFO] 提取关键帧: {os.path.basename(fp)}", file=sys.stderr)
        info = extract_frames(fp, args.output_dir, args.frames_per_clip,
                              args.format, args.quality)
        if info:
            results.append(info)
            print(f"[OK] {info['filename']}: {len(info['frames'])} 帧已提取", file=sys.stderr)

    output_json = json.dumps(results, ensure_ascii=False, indent=2)
    print(output_json)


if __name__ == "__main__":
    main()
