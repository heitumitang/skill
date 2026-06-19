#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
jianying_edit.py — 一键剪辑入口脚本（完整版）

支持：视频拼接 + 转场 + 字幕 + TTS配音 + BGM + 入场动画

用法：
  python jianying_edit.py \
    --name "我的视频" \
    --files video1.mp4 video2.mp4 \
    [--bgm bgm.mp3] [--bgm-volume 0.5] \
    [--srt subtitle.srt] \
    [--tts] [--tts-voice zh-CN-YunxiNeural] [--tts-rate "+0%"] \
    [--transitions dissolve] [--transition-duration 500000] \
    [--subtitle-style default] \
    [--duration 120] \
    [--style vlog] \
    [--resolution 1920x1080] \
    [--fps 30] \
    [--cut-mode sequential] \
    [--no-inject]

输出：
  自动尝试写入剪映草稿目录（打开剪映即可看到）
  如果注入失败，保存到本地目录并提供手动导入指引
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

PYTHON = r"C:\Users\ASUS\.workbuddy\binaries\python\envs\jianying\Scripts\python.exe"
SKILLS_DIR = r"C:\Users\ASUS\.workbuddy\skills\jianying-video-editor\scripts"

ANALYZE_SCRIPT = os.path.join(SKILLS_DIR, "analyze_media.py")
BUILD_SCRIPT = os.path.join(SKILLS_DIR, "build_draft.py")
TTS_SCRIPT = os.path.join(SKILLS_DIR, "tts_generate.py")
INJECT_SCRIPT = os.path.join(SKILLS_DIR, "inject_draft.py")
ASSETS_DIR = r"C:\Users\ASUS\.workbuddy\skills\jianying-video-editor\assets"


def run(cmd: list, label: str) -> str:
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    if result.returncode != 0:
        print(f"[ERROR] {label} 失败", file=sys.stderr)
        print(result.stderr, file=sys.stderr)
        sys.exit(1)
    return result.stdout.strip()


def smart_cut(media_info: list, target_duration_us: int, style: str) -> list:
    total_avail = sum(m["duration_us"] for m in media_info)
    segments = []

    if target_duration_us <= 0 or target_duration_us >= total_avail:
        for m in media_info:
            segments.append({
                "path": m["path"],
                "source_start_us": 0,
                "source_duration_us": m["duration_us"],
                "speed": 1.0,
                "width": m.get("width", 1920),
                "height": m.get("height", 1080),
                "has_audio": m.get("has_audio", False)
            })
        return segments

    remaining = target_duration_us
    for i, m in enumerate(media_info):
        is_last = (i == len(media_info) - 1)
        if is_last:
            alloc = remaining
        else:
            ratio = m["duration_us"] / total_avail
            alloc = int(target_duration_us * ratio)

        alloc = min(alloc, m["duration_us"])
        if alloc <= 0:
            continue

        skip = int(m["duration_us"] * 0.1)
        available_start = skip
        available_dur = m["duration_us"] - skip * 2
        if available_dur < alloc:
            available_start = 0
            available_dur = m["duration_us"]

        segments.append({
            "path": m["path"],
            "source_start_us": available_start,
            "source_duration_us": min(alloc, available_dur),
            "speed": 1.0,
            "width": m.get("width", 1920),
            "height": m.get("height", 1080),
            "has_audio": m.get("has_audio", False)
        })
        remaining -= alloc
        if remaining <= 0:
            break

    return segments


def us_to_srt_time(us: int) -> str:
    """将微秒转为 SRT 时间格式 HH:MM:SS,mmm"""
    total_ms = us // 1000
    h = total_ms // 3_600_000
    m = (total_ms % 3_600_000) // 60_000
    s = (total_ms % 60_000) // 1000
    ms = total_ms % 1000
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def print_banner(name, files, style, cut_mode, transitions, subtitle_style, tts_enabled):
    print(f"\n{'='*50}", file=sys.stderr)
    print(f"[剪映 AI 剪辑] 开始处理: {name}", file=sys.stderr)
    print(f"  素材数量: {len(files)}", file=sys.stderr)
    print(f"  风格: {style}, 剪辑模式: {cut_mode}", file=sys.stderr)
    print(f"  转场: {transitions}", file=sys.stderr)
    print(f"  字幕样式: {subtitle_style}", file=sys.stderr)
    print(f"  TTS配音: {'是' if tts_enabled else '否'}", file=sys.stderr)
    print(f"{'='*50}", file=sys.stderr)


def print_auto_inject_success(draft_dir: str, name: str):
    """打印自动注入成功的提示"""
    print(file=sys.stderr)
    print(f"{'*'*50}", file=sys.stderr)
    print(f"  ✅ 草稿已自动注入剪映！", file=sys.stderr)
    print(f"{'*'*50}", file=sys.stderr)
    print(file=sys.stderr)
    print(f"  打开（或重启）剪映 → 在「本地草稿」中找到「{name}」", file=sys.stderr)
    print(file=sys.stderr)
    print(f"  草稿路径：{draft_dir}", file=sys.stderr)
    print(f"{'*'*50}", file=sys.stderr)


def print_manual_import_guide(draft_dir: str, name: str):
    """打印手动导入剪映的指引"""
    print(file=sys.stderr)
    print(f"{'#'*50}", file=sys.stderr)
    print(f"  ⚠️ 自动注入失败，请手动导入剪映：", file=sys.stderr)
    print(f"{'#'*50}", file=sys.stderr)
    print(file=sys.stderr)
    print(f"  方法1（推荐）：", file=sys.stderr)
    print(f"    1. 打开剪映", file=sys.stderr)
    print(f"    2. 本地草稿 → 导入草稿", file=sys.stderr)
    print(f"    3. 选择目录：{draft_dir}", file=sys.stderr)
    print(file=sys.stderr)
    print(f"  方法2（自动识别）：", file=sys.stderr)
    print(f"    将整个文件夹复制到：", file=sys.stderr)
    print(f"    C:\\Users\\ASUS\\AppData\\Local\\JianyingPro\\User Data\\Projects\\com.lveditor.draft\\", file=sys.stderr)
    print(f"    然后重启剪映", file=sys.stderr)
    print(file=sys.stderr)
    print(f"  草稿目录：{draft_dir}", file=sys.stderr)
    print(f"{'#'*50}", file=sys.stderr)


def try_inject_inline(draft_output_dir: str, name: str) -> bool:
    """直接在当前进程中注入剪映草稿目录（不通过子进程），返回是否成功"""
    import shutil as _shutil

    # 查找剪映草稿根目录
    draft_base = None
    local_appdata = os.environ.get("LOCALAPPDATA", "")
    if local_appdata:
        p = os.path.join(local_appdata, "JianyingPro", "User Data", "Projects", "com.lveditor.draft")
        if os.path.exists(p):
            draft_base = p
    if not draft_base:
        home = os.path.expanduser("~")
        p = os.path.join(home, "AppData", "Local", "JianyingPro", "User Data", "Projects", "com.lveditor.draft")
        if os.path.exists(p):
            draft_base = p
    if not draft_base:
        print("[WARN] 找不到剪映草稿目录", file=sys.stderr)
        return False

    # 目标目录
    safe_name = name.replace("/", "_").replace("\\", "_").replace(":", "_")
    dest_dir = os.path.join(draft_base, safe_name)
    if os.path.exists(dest_dir):
        dest_dir = f"{dest_dir}_{int(time.time())}"

    try:
        os.makedirs(dest_dir, exist_ok=True)
    except PermissionError:
        print("[WARN] 权限不足，无法写入剪映目录", file=sys.stderr)
        return False
    except Exception as e:
        print(f"[WARN] 创建目录失败: {e}", file=sys.stderr)
        return False

    # 复制 draft_content.json
    src_dc = os.path.join(draft_output_dir, "draft_content.json")
    if not os.path.exists(src_dc):
        print("[WARN] 找不到 draft_content.json", file=sys.stderr)
        return False

    try:
        _shutil.copy2(src_dc, os.path.join(dest_dir, "draft_content.json"))
    except PermissionError:
        print("[WARN] 权限不足，无法写入草稿文件", file=sys.stderr)
        return False
    except Exception as e:
        print(f"[WARN] 复制草稿文件失败: {e}", file=sys.stderr)
        return False

    # 读取并更新内容
    dc_path = os.path.join(dest_dir, "draft_content.json")
    try:
        with open(dc_path, encoding="utf-8") as f:
            content = json.load(f)

        # 复制 TTS 音频到 textReading 子目录并更新路径
        tts_src = os.path.join(draft_output_dir, "tts_audio")
        if os.path.isdir(tts_src):
            tts_dst = os.path.join(dest_dir, "textReading")
            os.makedirs(tts_dst, exist_ok=True)
            for fname in os.listdir(tts_src):
                if fname.endswith(".mp3") or fname.endswith(".wav"):
                    _shutil.copy2(os.path.join(tts_src, fname), os.path.join(tts_dst, fname))

            # 更新音频路径
            for audio in content.get("materials", {}).get("audios", []):
                old_path = audio.get("path", "")
                if ("tts_" in old_path or "textReading" in old_path) and \
                   (old_path.endswith(".mp3") or old_path.endswith(".wav")):
                    audio["path"] = os.path.join(tts_dst, os.path.basename(old_path))

        content["name"] = name
        with open(dc_path, "w", encoding="utf-8") as f:
            json.dump(content, f, ensure_ascii=False, separators=(",", ":"))
    except Exception as e:
        print(f"[WARN] 更新草稿内容失败: {e}", file=sys.stderr)
        return False

    # 生成 draft_meta_info.json
    import uuid as _uuid
    now_ms = int(time.time() * 1000)
    meta = {
        "draft_cloud_capcut_purchase_info": "",
        "draft_cloud_last_action_download": False,
        "draft_cloud_materials": [],
        "draft_cloud_purchase_info": "",
        "draft_cloud_template_id": "",
        "draft_cloud_tutorial_info": "",
        "draft_cloud_videocut_purchase_info": "",
        "draft_cover": "",
        "draft_deeplink_url": "",
        "draft_enterprise_info": {
            "draft_enterprise_extra": "",
            "draft_enterprise_id": "",
            "draft_enterprise_name": "",
            "enterprise_material_objs": []
        },
        "draft_fold_path": "",
        "draft_id": str(_uuid.uuid4()).upper(),
        "draft_is_ai_shorts": False,
        "draft_is_article_video_draft": False,
        "draft_is_from_deeplink": False,
        "draft_is_invisible": False,
        "draft_materials_copied": False,
        "draft_name": name,
        "draft_new_version": "",
        "draft_removable_storage_device": "",
        "draft_root_path": dest_dir,
        "draft_segment_extra_info": None,
        "draft_timeline_materials_size": 0,
        "draft_timeline_materials_size_": 0,
        "tm_draft_cloud_completed": "",
        "tm_draft_cloud_modified": 0,
        "tm_draft_create": now_ms,
        "tm_draft_modified": now_ms,
        "tm_draft_removed": 0,
        "tm_duration": int(content.get("duration", 0) / 1000)
    }
    try:
        with open(os.path.join(dest_dir, "draft_meta_info.json"), "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[WARN] 写入 meta 文件失败: {e}", file=sys.stderr)
        return False

    # 更新 root_meta_info.json
    root_meta_path = os.path.join(draft_base, "root_meta_info.json")
    if os.path.exists(root_meta_path):
        try:
            with open(root_meta_path, encoding="utf-8") as f:
                root_meta = json.load(f)

            new_entry = {
                "draft_cloud_last_action_download": False,
                "draft_cloud_purchase_info": "",
                "draft_cloud_template_id": "",
                "draft_cloud_tutorial_info": "",
                "draft_cloud_videocut_purchase_info": "",
                "draft_cover": "",
                "draft_fold_path": dest_dir,
                "draft_id": meta["draft_id"],
                "draft_is_ai_shorts": False,
                "draft_is_invisible": False,
                "draft_json_file": os.path.join(dest_dir, "draft_content.json"),
                "draft_name": name,
                "draft_new_version": "109.0.0",
                "draft_root_path": draft_base,
                "draft_timeline_materials_size": 0,
                "draft_type": "",
                "tm_draft_cloud_completed": "",
                "tm_draft_cloud_modified": 0,
                "tm_draft_create": meta["tm_draft_create"],
                "tm_draft_modified": meta["tm_draft_modified"],
                "tm_draft_removed": 0,
                "tm_duration": meta["tm_duration"]
            }

            if isinstance(root_meta, list):
                existing = [i for i, m in enumerate(root_meta) if m.get("draft_name") == name]
                if existing:
                    for idx in existing:
                        root_meta[idx] = meta
                else:
                    root_meta.insert(0, meta)
            elif isinstance(root_meta, dict):
                all_drafts = root_meta.get("all_draft_store", [])
                existing = [i for i, m in enumerate(all_drafts) if m.get("draft_name") == name]
                if existing:
                    for idx in existing:
                        all_drafts[idx] = new_entry
                else:
                    all_drafts.insert(0, new_entry)
                root_meta["all_draft_store"] = all_drafts

            with open(root_meta_path, "w", encoding="utf-8") as f:
                json.dump(root_meta, f, ensure_ascii=False, indent=2)
            print("[OK] 已更新草稿列表索引", file=sys.stderr)
        except Exception as e:
            print(f"[WARN] 更新 root_meta_info.json 失败: {e}", file=sys.stderr)

    print(f"[OK] 草稿已注入: {dest_dir}", file=sys.stderr)
    return True


def main():
    parser = argparse.ArgumentParser(description="剪映 AI 剪辑一键入口（完整版）")
    # 基础参数
    parser.add_argument("--name", required=True, help="草稿名称")
    parser.add_argument("--files", nargs="+", required=True, help="视频素材文件路径")
    parser.add_argument("--output-dir", default=None,
                        help="草稿输出目录（默认 ./jianying_drafts/）")
    parser.add_argument("--bgm", default=None, help="BGM 音频路径")
    parser.add_argument("--bgm-volume", type=float, default=0.5, help="BGM 音量 (0.0~1.0)")
    parser.add_argument("--srt", default=None, help="字幕 SRT 文件路径")
    parser.add_argument("--duration", type=float, default=0, help="目标时长（秒），0=全部")
    parser.add_argument("--style", default="general",
                        choices=["vlog", "fast_cut", "documentary", "general"])
    parser.add_argument("--resolution", default="1920x1080", help="分辨率，如 1920x1080")
    parser.add_argument("--fps", type=float, default=30.0, help="帧率")
    parser.add_argument("--cut-mode", default="sequential",
                        choices=["sequential", "smart"])
    # 新增参数
    parser.add_argument("--tts", action="store_true", help="启用 TTS 配音（需配合 --srt）")
    parser.add_argument("--tts-voice", default="zh-CN-YunxiNeural", help="TTS 语音名称")
    parser.add_argument("--tts-rate", default="+0%", help="TTS 语速调节")
    parser.add_argument("--tts-volume", type=float, default=1.0, help="配音音量 (0.0~1.0)")
    parser.add_argument("--transitions", default="none",
                        choices=["dissolve", "flash_white", "slide_left", "blur", "push_in", "none"],
                        help="转场类型")
    parser.add_argument("--transition-duration", type=int, default=500000,
                        help="转场时长（微秒）")
    parser.add_argument("--subtitle-style", default="default",
                        choices=["default", "subtitle_with_bg", "yellow_accent", "title"],
                        help="字幕样式")
    parser.add_argument("--animations", default="none",
                        choices=["none", "fade_in"],
                        help="入场动画")
    parser.add_argument("--filter", default="none",
                        choices=["none", "warm", "cool", "vintage", "bw", "cinema"],
                        help="滤镜效果")
    parser.add_argument("--no-inject", action="store_true",
                        help="不自动注入剪映，只保存到本地目录")
    # AI 旁白模式
    parser.add_argument("--narration-json", default=None,
                        help="AI 生成的旁白 JSON（每段视频的旁白文案），格式见下方说明")
    parser.add_argument("--narration-file", default=None,
                        help="旁白 JSON 文件路径（同 --narration-json 但从文件读取）")
    # narration-json 格式:
    # [
    #   {"index": 0, "text": "阳光洒在海面上，波光粼粼"},
    #   {"index": 1, "text": "远处的灯塔在雾中若隐若现"},
    #   ...
    # ]
    # index 对应 --files 中的视频顺序
    args = parser.parse_args()

    # 解析 narration
    narration_list = None
    if args.narration_json:
        try:
            narration_list = json.loads(args.narration_json)
        except json.JSONDecodeError as e:
            print(f"[ERROR] --narration-json 格式错误: {e}", file=sys.stderr)
            sys.exit(1)
    elif args.narration_file:
        try:
            with open(args.narration_file, encoding="utf-8") as f:
                narration_list = json.load(f)
        except Exception as e:
            print(f"[ERROR] 读取旁白文件失败: {e}", file=sys.stderr)
            sys.exit(1)

    # AI 旁白模式自动启用 TTS + 字幕
    if narration_list:
        args.tts = True
        print("[INFO] AI 旁白模式：自动生成字幕和配音", file=sys.stderr)

    total_steps = 5 if (args.tts and args.srt) else 4
    current_step = 0

    print_banner(args.name, args.files, args.style, args.cut_mode,
                  args.transitions, args.subtitle_style, args.tts)

    # 解析分辨率
    try:
        w, h = args.resolution.lower().split("x")
        width, height = int(w), int(h)
    except Exception:
        width, height = 1920, 1080

    # =============================================
    # Step 1: 素材分析
    # =============================================
    current_step += 1
    print(f"\n[Step {current_step}/{total_steps}] 分析素材...", file=sys.stderr)
    analyze_cmd = [PYTHON, ANALYZE_SCRIPT, "--files"] + args.files
    raw_json = run(analyze_cmd, "素材分析")

    try:
        media_info = json.loads(raw_json)
    except json.JSONDecodeError:
        print(f"[ERROR] 素材分析输出格式错误: {raw_json[:200]}", file=sys.stderr)
        sys.exit(1)

    if not media_info:
        print("[ERROR] 没有有效素材", file=sys.stderr)
        sys.exit(1)

    print(f"[OK] 分析完成，{len(media_info)} 个素材", file=sys.stderr)
    for m in media_info:
        print(f"  - {m['filename']}: {m['duration_sec']}s {m['width']}x{m['height']}", file=sys.stderr)

    # =============================================
    # Step 2: 生成剪辑方案
    # =============================================
    current_step += 1
    print(f"\n[Step {current_step}/{total_steps}] 生成剪辑方案...", file=sys.stderr)
    target_duration_us = int(args.duration * 1_000_000) if args.duration > 0 else 0

    if args.cut_mode == "sequential":
        segments = []
        for m in media_info:
            segments.append({
                "path": m["path"],
                "source_start_us": 0,
                "source_duration_us": m["duration_us"],
                "speed": 1.0,
                "width": m.get("width", 1920),
                "height": m.get("height", 1080),
                "has_audio": m.get("has_audio", False)
            })
    else:
        segments = smart_cut(media_info, target_duration_us, args.style)

    total_dur = sum(s["source_duration_us"] / s.get("speed", 1.0) for s in segments)
    print(f"[OK] 规划完成，{len(segments)} 个片段，总时长 {total_dur/1_000_000:.1f}s", file=sys.stderr)

    # =============================================
    # Step 2.5 (AI 旁白模式): 自动生成 SRT
    # =============================================
    if narration_list and not args.srt:
        current_step += 1
        total_steps += 1
        print(f"\n[Step {current_step}/{total_steps}] AI 旁白：生成字幕时间轴...", file=sys.stderr)

        # 根据每个片段的时间范围，将旁白文案对齐到 SRT
        srt_content = ""
        timeline_cursor_us = 0

        for i, seg in enumerate(segments):
            seg_dur_us = int(seg["source_duration_us"] / seg.get("speed", 1.0))

            # 查找对应的旁白文案
            narration_text = ""
            for n in narration_list:
                if n.get("index") == i:
                    narration_text = n.get("text", "")
                    break
            if not narration_text and i < len(narration_list):
                narration_text = narration_list[i].get("text", "")

            if not narration_text:
                timeline_cursor_us += seg_dur_us
                continue

            # 计算 SRT 时间
            start_us = timeline_cursor_us
            end_us = timeline_cursor_us + seg_dur_us
            start_hhmmss = us_to_srt_time(start_us)
            end_hhmmss = us_to_srt_time(end_us)

            srt_content += f"{i+1}\n"
            srt_content += f"{start_hhmmss} --> {end_hhmmss}\n"
            srt_content += f"{narration_text}\n\n"

            timeline_cursor_us += seg_dur_us

        # 保存 SRT 文件
        srt_tmp_path = os.path.join(tempfile.gettempdir(), f"ai_narration_{int(time.time())}.srt")
        with open(srt_tmp_path, "w", encoding="utf-8") as f:
            f.write(srt_content)

        args.srt = srt_tmp_path
        print(f"[OK] AI 旁白 SRT 已生成: {srt_tmp_path}", file=sys.stderr)
        for i, n in enumerate(narration_list):
            text = n.get("text", "")[:40]
            print(f"  片段 {i}: {text}...", file=sys.stderr)

    # =============================================
    # Step 3 (可选): TTS 配音生成
    # =============================================
    tts_dir = None
    if args.tts and args.srt and os.path.exists(args.srt):
        current_step += 1
        print(f"\n[Step {current_step}/{total_steps}] 生成 TTS 配音（AI 旁白）...", file=sys.stderr)

        tts_dir = os.path.join(tempfile.gettempdir(), f"jianying_tts_{int(time.time())}")
        tts_cmd = [
            PYTHON, TTS_SCRIPT,
            "--srt", args.srt,
            "--output-dir", tts_dir,
            "--voice", args.tts_voice,
            "--rate", args.tts_rate,
        ]
        run(tts_cmd, "TTS配音生成")
        print(f"[OK] TTS 配音已生成到: {tts_dir}", file=sys.stderr)

    # =============================================
    # Step 4: 构建草稿
    # =============================================
    current_step += 1
    print(f"\n[Step {current_step}/{total_steps}] 构建剪映草稿...", file=sys.stderr)

    # 构建 BGM 信息
    bgm_info = None
    if args.bgm and os.path.exists(args.bgm):
        bgm_media = json.loads(run([PYTHON, ANALYZE_SCRIPT, "--files", args.bgm], "BGM分析"))
        bgm_dur = bgm_media[0]["duration_us"] if bgm_media else int(total_dur)
        bgm_info = {
            "path": str(Path(args.bgm).resolve()),
            "volume": args.bgm_volume,
            "duration_us": bgm_dur
        }
        print(f"[OK] BGM: {os.path.basename(args.bgm)}, {bgm_dur/1_000_000:.1f}s", file=sys.stderr)

    # 构建完整 plan
    plan = {
        "name": args.name,
        "resolution": [width, height],
        "fps": args.fps,
        "segments": segments,
        "bgm": bgm_info,
        "subtitle_srt": str(Path(args.srt).resolve()) if args.srt and os.path.exists(args.srt) else None,
        "subtitle_style": args.subtitle_style,
        "tts_dir": tts_dir,
        "tts_volume": args.tts_volume,
        "transitions": {
            "type": args.transitions,
            "duration_us": args.transition_duration,
        } if args.transitions != "none" else None,
        "animations": args.animations,
        "filter": args.filter,
    }

    # 确定输出目录
    if args.output_dir:
        output_base = os.path.abspath(args.output_dir)
    else:
        output_base = os.path.join(os.getcwd(), "jianying_drafts")
    draft_output_dir = os.path.join(output_base, args.name)
    # 去重
    counter = 1
    original_draft_dir = draft_output_dir
    while os.path.exists(draft_output_dir):
        draft_output_dir = f"{original_draft_dir}_{counter}"
        counter += 1

    os.makedirs(draft_output_dir, exist_ok=True)

    # 构建草稿
    with tempfile.TemporaryDirectory() as tmpdir:
        plan_path = os.path.join(tmpdir, "plan.json")
        build_dir = os.path.join(tmpdir, "draft")
        os.makedirs(build_dir, exist_ok=True)

        with open(plan_path, "w", encoding="utf-8") as f:
            json.dump(plan, f, ensure_ascii=False)

        run([PYTHON, BUILD_SCRIPT, "--plan", plan_path, "--output-dir", build_dir], "草稿构建")

        # 复制到输出目录
        import shutil
        src = os.path.join(build_dir, "draft_content.json")
        dst = os.path.join(draft_output_dir, "draft_content.json")
        shutil.copy2(src, dst)

        # 如果有 TTS 文件，也复制过去
        if tts_dir and os.path.exists(tts_dir):
            tts_dst = os.path.join(draft_output_dir, "tts_audio")
            if os.path.exists(tts_dst):
                shutil.rmtree(tts_dst)
            shutil.copytree(tts_dir, tts_dst)

    print(f"[OK] 草稿已保存到: {draft_output_dir}", file=sys.stderr)

    # =============================================
    # Step 5: 自动注入剪映
    # =============================================
    inject_success = False
    if not args.no_inject:
        current_step += 1
        print(f"\n[Step {current_step}/{total_steps}] 注入剪映草稿目录...", file=sys.stderr)
        inject_success = try_inject_inline(draft_output_dir, args.name)

    # =============================================
    # 输出结果
    # =============================================
    print(file=sys.stderr)
    print(f"{'='*50}", file=sys.stderr)
    print(f"  总时长: {total_dur/1_000_000:.1f} 秒", file=sys.stderr)
    if args.transitions != "none":
        print(f"  转场: {args.transitions} x{len(segments)-1}", file=sys.stderr)
    if args.srt:
        print(f"  字幕: {args.subtitle_style} 样式", file=sys.stderr)
    if args.tts:
        print(f"  配音: {args.tts_voice}", file=sys.stderr)
    if args.bgm:
        print(f"  BGM: {os.path.basename(args.bgm)}", file=sys.stderr)
    print(f"{'='*50}", file=sys.stderr)

    if inject_success:
        # 找到剪映目录中的实际路径
        jy_dir = os.path.join(
            os.environ.get("LOCALAPPDATA", r"C:\Users\ASUS\AppData\Local"),
            "JianyingPro", "User Data", "Projects", "com.lveditor.draft", args.name
        )
        print_auto_inject_success(jy_dir, args.name)
    else:
        print_manual_import_guide(draft_output_dir, args.name)

    # 输出最终路径（供 agent 读取）
    if inject_success:
        jy_dir = os.path.join(
            os.environ.get("LOCALAPPDATA", r"C:\Users\ASUS\AppData\Local"),
            "JianyingPro", "User Data", "Projects", "com.lveditor.draft", args.name
        )
        print(f"\nDRAFT_PATH:{jy_dir}")
        print(f"INJECTED:true")
    else:
        print(f"\nDRAFT_PATH:{draft_output_dir}")
        print(f"INJECTED:false")


if __name__ == "__main__":
    main()
