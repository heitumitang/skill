#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tts_generate.py — 使用 edge-tts 生成配音音频

用法：
  python tts_generate.py --text "你好世界" --output voice.mp3 [--voice zh-CN-YunxiNeural] [--rate "+0%"]
  python tts_generate.py --srt subtitle.srt --output-dir ./tts_output/ [--voice zh-CN-YunxiNeural]

功能：
  1. 单条文本 → 单个音频文件
  2. SRT 字幕文件 → 按条生成音频文件列表 + 元信息 JSON

支持语音（常用）：
  zh-CN-XiaoxiaoNeural   女声·温柔
  zh-CN-YunxiNeural      男声·阳光
  zh-CN-YunjianNeural    男声·沉稳
  zh-CN-XiaoyiNeural     女声·活泼
  zh-CN-YunyangNeural    男声·新闻播报
  zh-CN-XiaochenNeural   女声·知性
  zh-CN-XiaohanNeural    女声·甜美
  zh-CN-XiaomengNeural   女声·可爱
  zh-CN-XiaomoNeural     女声·御姐
  zh-CN-XiaoruiNeural    女声·自然
  zh-CN-XiaoshuangNeural 女声·儿童
  zh-CN-XiaoxuanNeural   女声·知性2
  zh-CN-XiaozhenNeural   女声·温柔2
  zh-CN-YunfengNeural    男声·自然
  zh-CN-YunhaoNeural     男声·阳光2
  zh-CN-YunxiaNeural     男声·少年
  zh-CN-YunzeNeural      男声·磁性
"""
import argparse
import asyncio
import json
import os
import re
import sys
import time
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def get_audio_duration_us(path: str) -> int:
    """使用 mutagen 获取 MP3 精确时长（微秒）；不可用时回退到文件大小估算。"""
    try:
        from mutagen.mp3 import MP3
        mp3 = MP3(path)
        return int(mp3.info.length * 1_000_000)
    except Exception:
        # 回退: edge-tts 生成约 24kbps MP3
        try:
            file_size = os.path.getsize(path)
            return int(file_size / 3000 * 1_000_000)
        except Exception:
            return 0


async def tts_generate(text: str, output_path: str, voice: str = "zh-CN-YunxiNeural",
                       rate: str = "+0%", pitch: str = "+0Hz", retries: int = 3) -> dict:
    """使用 edge-tts 生成单条配音（带重试），同时收集词级时间戳 WordBoundary。

    返回 dict 中包含:
      - path: 音频文件绝对路径
      - text: 原始文本
      - voice: 使用的语音
      - duration_us: 音频总时长（微秒）
      - word_timings: list of {text, offset_us, duration_us}  ← 词级时间戳
    """
    import edge_tts

    for attempt in range(retries):
        try:
            communicate = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
            duration_us = 0
            word_timings = []
            with open(output_path, "wb") as audio_file:
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        audio_file.write(chunk["data"])
                    elif chunk["type"] == "WordBoundary":
                        offset_100ns = float(chunk.get("offset", 0))
                        dur_100ns = float(chunk.get("duration", 0))
                        word_offset_us = int(offset_100ns / 10)
                        word_dur_us = int(dur_100ns / 10)
                        # 更新总时长
                        duration_us = max(duration_us, word_offset_us + word_dur_us)
                        word_timings.append({
                            "text": chunk.get("text", ""),
                            "offset_us": word_offset_us,
                            "duration_us": word_dur_us,
                        })

            # 验证文件
            if os.path.exists(output_path) and os.path.getsize(output_path) > 100:
                break
            else:
                print(f"[WARN] TTS 生成文件过小，重试 {attempt+1}/{retries}", file=sys.stderr)
                import asyncio as aio
                await aio.sleep(1)
        except Exception as e:
            print(f"[WARN] TTS 生成失败 (attempt {attempt+1}/{retries}): {e}", file=sys.stderr)
            if attempt < retries - 1:
                import asyncio as aio
                await aio.sleep(2)

    # v4.4: 使用 mutagen 获取精确时长，而非粗略的文件大小估算
    if duration_us <= 0 and os.path.exists(output_path):
        duration_us = get_audio_duration_us(output_path)

    return {
        "path": str(Path(output_path).resolve()),
        "text": text,
        "voice": voice,
        "duration_us": duration_us,
        "word_timings": word_timings,
    }


async def tts_from_srt(srt_path: str, output_dir: str, voice: str = "zh-CN-YunxiNeural",
                       rate: str = "+0%") -> list[dict]:
    """从 SRT 字幕文件逐条生成配音"""
    os.makedirs(output_dir, exist_ok=True)
    
    # 解析 SRT
    subtitles = parse_srt(srt_path)
    results = []
    
    for i, sub in enumerate(subtitles):
        out_name = f"tts_{i:04d}.mp3"
        out_path = os.path.join(output_dir, out_name)
        
        print(f"[TTS {i+1}/{len(subtitles)}] {sub['text'][:30]}...", file=sys.stderr)
        
        info = await tts_generate(sub["text"], out_path, voice=voice, rate=rate)
        info["index"] = i
        info["target_start_us"] = sub["start_us"]
        info["target_duration_us"] = sub["duration_us"]
        info["srt_text"] = sub["text"]
        results.append(info)
    
    return results


def parse_srt(srt_path: str) -> list[dict]:
    """解析 SRT 字幕文件"""
    try:
        with open(srt_path, encoding="utf-8-sig") as f:
            content = f.read()
    except UnicodeDecodeError:
        with open(srt_path, encoding="gbk") as f:
            content = f.read()
    
    pattern = r'(\d+)\s+(\d{2}:\d{2}:\d{2}[,\.]\d{3})\s+-->\s+(\d{2}:\d{2}:\d{2}[,\.]\d{3})\s+(.*?)(?=\n\n|\Z)'
    matches = re.findall(pattern, content.strip(), re.DOTALL)
    
    def srt_time_to_us(ts: str) -> int:
        ts = ts.replace(",", ".")
        parts = ts.split(":")
        h, m = int(parts[0]), int(parts[1])
        s_parts = parts[2].split(".")
        s = int(s_parts[0])
        ms = int(s_parts[1]) if len(s_parts) > 1 else 0
        return (h * 3600 + m * 60 + s) * 1_000_000 + ms * 1_000
    
    subtitles = []
    for idx, start_ts, end_ts, text in matches:
        start_us = srt_time_to_us(start_ts)
        end_us = srt_time_to_us(end_ts)
        subtitles.append({
            "index": int(idx),
            "start_us": start_us,
            "duration_us": end_us - start_us,
            "text": text.strip().replace("\n", " ")
        })
    
    return subtitles


async def main_async():
    parser = argparse.ArgumentParser(description="TTS 配音生成")
    parser.add_argument("--text", default=None, help="单条文本内容")
    parser.add_argument("--srt", default=None, help="SRT 字幕文件路径")
    parser.add_argument("--output", default=None, help="输出音频路径（单条模式）")
    parser.add_argument("--output-dir", default=None, help="输出目录（SRT 模式）")
    parser.add_argument("--voice", default="zh-CN-YunxiNeural", help="语音名称")
    parser.add_argument("--rate", default="+0%", help="语速调节，如 +20%% -10%%")
    parser.add_argument("--pitch", default="+0Hz", help="音调调节")
    args = parser.parse_args()
    
    if args.text and args.output:
        # 单条模式
        info = await tts_generate(args.text, args.output, voice=args.voice,
                                  rate=args.rate, pitch=args.pitch)
        print(json.dumps(info, ensure_ascii=False, indent=2))
    elif args.srt and args.output_dir:
        # SRT 模式
        results = await tts_from_srt(args.srt, args.output_dir, voice=args.voice, rate=args.rate)
        # 保存元信息
        meta_path = os.path.join(args.output_dir, "tts_meta.json")
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"[OK] 生成 {len(results)} 条配音，元信息: {meta_path}", file=sys.stderr)
        print(meta_path)
    else:
        parser.print_help()
        sys.exit(1)


def main():
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
