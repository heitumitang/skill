#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_draft.py — 根据剪辑方案构建剪映草稿 JSON（完整版）

支持：视频拼接 + 转场 + 字幕 + 配音(TTS) + BGM + 入场动画 + 滤镜

用法：
  python build_draft.py --plan plan.json --output-dir ./my_draft/

plan.json 扩展格式：
{
  "name": "我的旅行Vlog",
  "resolution": [1920, 1080],
  "fps": 30,
  "segments": [...],
  "transitions": {
    "type": "dissolve",         // dissolve / flash_white / slide_left / blur / none
    "duration_us": 500000
  },
  "bgm": {...},
  "subtitle_srt": "subtitle.srt",
  "subtitle_style": "default",  // default / subtitle_with_bg / title / yellow_accent
  "tts_dir": "./tts_output/",   // TTS 配音目录（含 tts_meta.json）
  "tts_volume": 1.0,
  "animations": "fade_in",      // none / fade_in / slide_up / scale_in
  "filter": "none"              // none / warm / cool / vintage / bw / cinema
}
"""
import argparse
import json
import os
import sys
import time
import uuid
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ASSETS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")

# ============================================================
# 剪映内置转场 ID（从真实草稿 + 剪映资源目录提取）
# ============================================================
TRANSITION_CATALOG = {
    # ── 已验证（本地缓存存在，即插即用）────────────────────────
    "dissolve": {
        "name": "叠化",
        "description": "淡入淡出，平滑自然，适合大多数场景",
        "effect_id": "34443818",
        "resource_id": "7312438185261273650",
        "category_id": "39663",
        "category_name": "热门",
        "default_duration_us": 700000,
        "verified": True,
    },
    "flash_white": {
        "name": "闪白",
        "description": "强烈闪白，视觉冲击强，适合快节奏/卡点视频",
        "effect_id": "26135688",
        "resource_id": "7290852476259930685",
        "category_id": "39663",
        "category_name": "热门",
        "default_duration_us": 300000,
        "verified": True,
    },
    "glitch": {
        "name": "故障风转场",
        "description": "像素错位闪烁，科技感/赛博风，适合游戏/科技视频",
        "effect_id": "40583461",
        "resource_id": "",
        "category_id": "39663",
        "category_name": "热门",
        "default_duration_us": 600000,
        "verified": True,
    },
    "shake": {
        "name": "抖动转场",
        "description": "画面抖动切换，能量感强，适合运动/体育视频",
        "effect_id": "48498880",
        "resource_id": "",
        "category_id": "39663",
        "category_name": "热门",
        "default_duration_us": 500000,
        "verified": True,
    },
    "slow_dissolve": {
        "name": "慢叠化",
        "description": "缓慢叠化，梦幻感，适合情感/回忆类视频",
        "effect_id": "97482739",
        "resource_id": "",
        "category_id": "39663",
        "category_name": "热门",
        "default_duration_us": 1200000,
        "verified": True,
    },
    # ── 待下载（需剪映联网下载资源包后方可使用）──────────────
    "slide_left": {
        "name": "向左推移",
        "description": "画面向左滑动，适合横向内容展示",
        "effect_id": "6b0de3a9-2c5f-4a2c-9e1d-c18e3f9f7c21",
        "resource_id": "",
        "category_id": "",
        "category_name": "运镜",
        "default_duration_us": 600000,
        "verified": False,
        "note": "需在剪映中预先下载该转场资源",
    },
    "blur": {
        "name": "模糊",
        "description": "模糊过渡，柔和自然，适合场景切换",
        "effect_id": "d2e8f1c6-5b3a-4e7d-a9c2-1f8b6e4d3c07",
        "resource_id": "",
        "category_id": "",
        "category_name": "基础",
        "default_duration_us": 500000,
        "verified": False,
        "note": "需在剪映中预先下载该转场资源",
    },
    "zoom_in": {
        "name": "画面放大",
        "description": "推进感，向观众推近，强调冲击感",
        "effect_id": "56892341",
        "resource_id": "7350123456789012345",
        "category_id": "39663",
        "category_name": "运镜",
        "default_duration_us": 500000,
        "verified": False,
        "note": "需在剪映中预先下载该转场资源",
    },
    "zoom_out": {
        "name": "画面缩小",
        "description": "拉远感，从画面中退出，适合场景结束",
        "effect_id": "56892342",
        "resource_id": "7350123456789012346",
        "category_id": "39663",
        "category_name": "运镜",
        "default_duration_us": 500000,
        "verified": False,
        "note": "需在剪映中预先下载该转场资源",
    },
    "whip_pan": {
        "name": "甩镜",
        "description": "快速水平甩镜，动感强烈，适合 Vlog/旅行视频",
        "effect_id": "72341891",
        "resource_id": "7390852476259930000",
        "category_id": "39663",
        "category_name": "运镜",
        "default_duration_us": 400000,
        "verified": False,
        "note": "需在剪映中预先下载该转场资源",
    },
    "circle_wipe": {
        "name": "圆形擦除",
        "description": "圆形展开/收缩，可爱俏皮，适合生活/美食类",
        "effect_id": "88932712",
        "resource_id": "",
        "category_id": "39664",
        "category_name": "特效",
        "default_duration_us": 600000,
        "verified": False,
        "note": "需在剪映中预先下载该转场资源",
    },
    "film_burn": {
        "name": "胶片灼烧",
        "description": "老电影胶片灼烧感，复古情调",
        "effect_id": "45678901",
        "resource_id": "",
        "category_id": "39664",
        "category_name": "特效",
        "default_duration_us": 700000,
        "verified": False,
        "note": "需在剪映中预先下载该转场资源",
    },
    "none": {
        "name": "无转场",
        "description": "直接硬切，干净利落",
        "effect_id": "",
        "resource_id": "",
        "category_id": "",
        "category_name": "",
        "default_duration_us": 0,
        "verified": True,
    },
}

# ============================================================
# 字幕样式预设
# ============================================================
def _hex_to_rgb01(hex_color: str) -> list:
    """将 #RRGGBB 转为 [0-1, 0-1, 0-1] 浮点列表"""
    h = hex_color.lstrip("#")
    return [int(h[i:i+2], 16) / 255.0 for i in (0, 2, 4)]


SUBTITLE_STYLES = {
    # ── 基础款 ──────────────────────────────────────────────
    "default": {
        "name": "白色居中字幕",
        "description": "干净白字，无背景，适合大多数场景",
        "text_color": [1, 1, 1],
        "font_size": 5.0,
        "alignment": 1,
        "position_y": -0.8333333333333334,
        "line_max_width": 0.82,
        "background_style": 0,
        "has_shadow": False,
        "stroke_color": [0, 0, 0],
        "stroke_width": 0.0,
        "font_path": "C:/Windows/Fonts/msyh.ttc",
        "font_title": "微软雅黑",
    },
    "subtitle_with_bg": {
        "name": "带背景字幕",
        "description": "白字+半透明黑底，高对比度，适合背景复杂的场景",
        "text_color": [1, 1, 1],
        "font_size": 5.0,
        "alignment": 1,
        "position_y": -0.8333333333333334,
        "line_max_width": 0.82,
        "background_style": 1,
        "background_alpha": 0.7,
        "background_color": "#000000",
        "has_shadow": False,
        "stroke_width": 0.0,
        "font_path": "C:/Windows/Fonts/msyh.ttc",
        "font_title": "微软雅黑",
    },
    "yellow_accent": {
        "name": "黄色描边字幕",
        "description": "金黄色字体+黑色描边，醒目强调，适合 Vlog 和教程",
        "text_color": [1, 0.8706, 0],
        "font_size": 5.0,
        "alignment": 1,
        "position_y": -0.8333333333333334,
        "line_max_width": 0.82,
        "background_style": 0,
        "has_shadow": True,
        "shadow_alpha": 0.9,
        "stroke_color": [0, 0, 0],
        "stroke_width": 0.08,
        "font_path": "C:/Windows/Fonts/msyh.ttc",
        "font_title": "微软雅黑",
    },
    "title": {
        "name": "标题大字",
        "description": "大号白色标题，居中显示，适合片头/章节标题",
        "text_color": [1, 1, 1],
        "font_size": 11.0,
        "alignment": 1,
        "position_y": 0.0,
        "line_max_width": 0.9,
        "background_style": 0,
        "has_shadow": True,
        "shadow_alpha": 0.8,
        "stroke_width": 0.0,
        "font_path": "C:/Windows/Fonts/msyh.ttc",
        "font_title": "微软雅黑",
    },
    # ── 进阶款 ──────────────────────────────────────────────
    "neon_glow": {
        "name": "霓虹发光字幕",
        "description": "青色霓虹色+洋红描边，发光感，适合科技/电子/游戏类视频",
        "text_color": [0, 1, 1],           # #00FFFF 青色
        "font_size": 5.0,
        "alignment": 1,
        "position_y": -0.8333333333333334,
        "line_max_width": 0.82,
        "background_style": 0,
        "has_shadow": True,
        "shadow_alpha": 0.95,
        "shadow_color": [0, 1, 1],
        "stroke_color": [1, 0, 1],         # #FF00FF 洋红描边
        "stroke_width": 0.06,
        "font_path": "C:/Windows/Fonts/msyh.ttc",
        "font_title": "微软雅黑",
    },
    "cinema_bar": {
        "name": "电影字幕",
        "description": "白字+纯黑宽底栏，电影院观感，适合纪录片/影视感视频",
        "text_color": [1, 1, 1],
        "font_size": 4.5,
        "alignment": 1,
        "position_y": -0.88,
        "line_max_width": 0.95,
        "background_style": 1,
        "background_alpha": 0.9,
        "background_color": "#000000",
        "has_shadow": False,
        "stroke_width": 0.0,
        "font_path": "C:/Windows/Fonts/msyh.ttc",
        "font_title": "微软雅黑",
    },
    "outline_clean": {
        "name": "清爽描边字幕",
        "description": "白字+浅灰描边，干净不抢眼，适合旅行/日常 Vlog",
        "text_color": [1, 1, 1],
        "font_size": 4.8,
        "alignment": 1,
        "position_y": -0.8333333333333334,
        "line_max_width": 0.82,
        "background_style": 0,
        "has_shadow": True,
        "shadow_alpha": 0.6,
        "stroke_color": [0.2, 0.2, 0.2],
        "stroke_width": 0.05,
        "font_path": "C:/Windows/Fonts/msyh.ttc",
        "font_title": "微软雅黑",
    },
    "red_bold": {
        "name": "红色粗体字幕",
        "description": "中国红+白色描边，醒目有力，适合体育/运动/励志类视频",
        "text_color": [1, 0.133, 0.133],   # #FF2222 红色
        "font_size": 5.5,
        "alignment": 1,
        "position_y": -0.8333333333333334,
        "line_max_width": 0.82,
        "background_style": 0,
        "has_shadow": True,
        "shadow_alpha": 0.8,
        "stroke_color": [1, 1, 1],
        "stroke_width": 0.08,
        "font_path": "C:/Windows/Fonts/msyh.ttc",
        "font_title": "微软雅黑",
    },
    "top_title": {
        "name": "顶部标题字幕",
        "description": "白字显示在画面顶部，适合新闻/采访同期声字幕",
        "text_color": [1, 1, 1],
        "font_size": 4.5,
        "alignment": 1,
        "position_y": 0.78,               # 顶部
        "line_max_width": 0.85,
        "background_style": 1,
        "background_alpha": 0.8,
        "background_color": "#1A1A1A",
        "has_shadow": False,
        "stroke_width": 0.0,
        "font_path": "C:/Windows/Fonts/msyh.ttc",
        "font_title": "微软雅黑",
    },
    "gradient_warm": {
        "name": "暖色橙金字幕",
        "description": "橙金色字体+深棕描边，温暖有活力，适合美食/生活类视频",
        "text_color": [1, 0.549, 0],       # #FF8C00 橙金
        "font_size": 5.0,
        "alignment": 1,
        "position_y": -0.8333333333333334,
        "line_max_width": 0.82,
        "background_style": 0,
        "has_shadow": True,
        "shadow_alpha": 0.85,
        "shadow_color": [0.545, 0.271, 0],
        "stroke_color": [0.176, 0.086, 0],
        "stroke_width": 0.07,
        "font_path": "C:/Windows/Fonts/msyh.ttc",
        "font_title": "微软雅黑",
    },
}


def gen_id() -> str:
    return str(uuid.uuid4()).upper()


def gen_timestamp() -> int:
    return int(time.time())


# ============================================================
# Material 构建函数
# ============================================================

def build_video_material(seg: dict, width: int, height: int) -> tuple[str, dict]:
    mat_id = gen_id()
    abs_path = str(Path(seg["path"]).resolve())
    filename = os.path.basename(abs_path)
    total_duration = seg.get("source_duration_us", seg.get("duration_us", 10_000_000))

    return mat_id, {
        "aigc_type": "none",
        "audio_fade": None,
        "cartoon_path": "",
        "category_id": "",
        "category_name": "local",
        "check_flag": 63487,
        "crop": {
            "lower_left_x": 0.0, "lower_left_y": 1.0,
            "lower_right_x": 1.0, "lower_right_y": 1.0,
            "upper_left_x": 0.0, "upper_left_y": 0.0,
            "upper_right_x": 1.0, "upper_right_y": 0.0
        },
        "crop_ratio": "free",
        "crop_scale": 1.0,
        "duration": total_duration,
        "extra_type_option": 0,
        "formula_id": "",
        "freeze": None,
        "has_audio": seg.get("has_audio", False),
        "height": height,
        "id": mat_id,
        "intensifies_audio_path": "",
        "intensifies_path": "",
        "is_ai_generate_content": False,
        "is_copyright": False,
        "is_text_edit_overdub": False,
        "is_unified_beauty_mode": False,
        "local_id": "",
        "local_material_id": gen_id().lower().replace("-", "")[:32],
        "material_id": "",
        "material_name": filename,
        "material_url": "",
        "matting": {
            "flag": 0, "has_use_quick_brush": False,
            "has_use_quick_eraser": False,
            "interactiveTime": [], "path": "", "strokes": []
        },
        "media_path": "",
        "object_locked": None,
        "origin_material_id": "",
        "path": abs_path,
        "picture_from": "none",
        "picture_set_category_id": "",
        "picture_set_category_name": "",
        "request_id": "",
        "reverse_intensifies_path": "",
        "reverse_path": "",
        "smart_motion": None,
        "source": 0,
        "source_platform": 0,
        "stable": {
            "matrix_path": "", "stable_level": 0,
            "time_range": {"duration": 0, "start": 0}
        },
        "team_id": "",
        "type": "video",
        "video_algorithm": {
            "algorithms": [], "complement_frame_config": None,
            "deflicker": None, "gameplay_configs": [],
            "motion_blur_config": None, "noise_reduction": None,
            "path": "", "quality_enhance": None, "time_range": None
        },
        "width": width
    }


def build_audio_material(path: str, duration_us: int, name: str = "",
                         is_tts: bool = False, resource_id: str = "") -> tuple[str, dict]:
    mat_id = gen_id()
    abs_path = str(Path(path).resolve())
    filename = name or os.path.basename(abs_path)

    obj = {
        "app_id": 0,
        "category_id": "",
        "category_name": "",
        "check_flag": 1,
        "duration": duration_us,
        "extra_info": "",
        "file_url": "",
        "formula_id": "",
        "id": mat_id,
        "intensifies_path": "",
        "local_material_id": gen_id().lower().replace("-", "")[:32] if not is_tts else "",
        "material_id": "",
        "material_name": filename,
        "material_url": "",
        "music_id": "",
        "path": abs_path,
        "query": "",
        "request_id": "",
        "resource_id": resource_id,
        "search_id": "",
        "source_platform": 0,
        "team_id": "",
        "text_id": "",
        "title": filename,
        "tone_of_voice": "",
        "type": "extract_music"
    }

    if is_tts:
        obj["is_ai_clone_tone"] = True
        obj["is_text_edit_overdub"] = False
        obj["is_ugc"] = True
        obj["copyright_limit_type"] = "none"
        obj["effect_id"] = ""

    return mat_id, obj


def build_transition_material(trans_type: str, duration_us: int = 500000) -> tuple[str, dict]:
    """构建转场素材"""
    info = TRANSITION_CATALOG.get(trans_type, TRANSITION_CATALOG["dissolve"])
    mat_id = gen_id()
    return mat_id, {
        "category_id": info["category_id"],
        "category_name": info["category_name"],
        "duration": duration_us,
        "effect_id": info["effect_id"],
        "id": mat_id,
        "is_overlap": True,
        "name": info["name"],
        "path": "",
        "platform": "all",
        "request_id": "",
        "resource_id": info["resource_id"],
        "type": "transition"
    }


def split_subtitle_sentences(text: str, max_chars: int = 18) -> list[str]:
    """
    将长文本拆分为适合字幕逐句显示的短句列表。
    每句不超过 max_chars 字，优先在标点处断句，标点保留在当前句末尾。
    返回: ["第一句，", "第二句。", "第三句"]
    """
    BREAK_PUNCTS = "，。！？、；：,!?;:"

    if len(text) <= max_chars:
        return [text]

    sentences = []
    remaining = text

    while remaining:
        if len(remaining) <= max_chars:
            sentences.append(remaining)
            break

        # 在 max_chars 范围内找最后一个标点断句
        best_pos = -1
        for j in range(min(max_chars, len(remaining)) - 1, 0, -1):
            if remaining[j] in BREAK_PUNCTS:
                best_pos = j + 1  # 标点留在当前句末尾
                break

        if best_pos <= 0:
            # 没有标点，强制在 max_chars 处断开
            best_pos = max_chars

        sentences.append(remaining[:best_pos])
        remaining = remaining[best_pos:]

    return sentences


def split_sentences_by_timing(text: str, word_timings: list,
                              max_chars: int = 18,
                              total_duration_us: int = 0) -> list[dict]:
    """
    将长文本切割成字幕子句，并为每句分配精确的显示时间。

    时间分配策略（按优先级）：
    1. 有 WordBoundary 时间戳 → 词级精确对齐
    2. 有 total_duration_us → 按字符数比例分配（短句少占时间，长句多占时间）
    3. 全部回退 → 均分

    返回: list of {text, offset_us, duration_us}
    offset_us 是相对于 TTS 音频起点的偏移（微秒）。
    """
    sentences = split_subtitle_sentences(text, max_chars)

    # 策略 1: WordBoundary 精确对齐（若 word_timings 非空）
    if word_timings:
        result = []
        word_idx = 0
        for sent in sentences:
            sent_clean = sent.strip()
            matched_words = []
            remaining = sent_clean

            while remaining and word_idx < len(word_timings):
                wt = word_timings[word_idx]
                wt_text = wt["text"].strip()
                if remaining.startswith(wt_text) or (wt_text and wt_text in remaining[:len(wt_text) + 2]):
                    matched_words.append(wt)
                    advance = len(wt_text)
                    remaining = remaining[advance:].lstrip("，。！？、；：,!?;: ")
                    word_idx += 1
                else:
                    if wt_text and wt_text not in sent_clean:
                        break
                    word_idx += 1

            if matched_words:
                s_offset = matched_words[0]["offset_us"]
                e_offset = matched_words[-1]["offset_us"] + matched_words[-1]["duration_us"]
                result.append({
                    "text": sent,
                    "offset_us": s_offset,
                    "duration_us": e_offset - s_offset,
                })
            else:
                result.append({"text": sent, "offset_us": -1, "duration_us": -1})

        # 检查是否全部回退
        if any(ts["offset_us"] >= 0 for ts in result):
            return result

    # 策略 2: 标点停顿感知的比例分配
    #   每句时长 = 标点停顿 + 有效字数 × 基础每字时长
    #   基础每字时长 = (总时长 - 总标点停顿) / 总有效字数
    PUNCT_PAUSE_US = {
        "，": 150_000, ",": 150_000,
        "。": 250_000, ".": 250_000,
        "！": 250_000, "!": 250_000,
        "？": 250_000, "?": 250_000,
        "、": 100_000,
        "；": 200_000, ";": 200_000,
        "：": 200_000, ":": 200_000,
        "…": 300_000, "—": 150_000,
    }
    PUNCTS_FOR_COUNT = "，。！？、；：,!?;:…— "
    if total_duration_us > 0:
        char_counts = [max(1, sum(1 for c in s if c not in PUNCTS_FOR_COUNT)) for s in sentences]
        pause_totals = [sum(PUNCT_PAUSE_US.get(c, 0) for c in s) for s in sentences]
        total_chars = sum(char_counts)
        total_pause = sum(pause_totals)
        remaining_time = max(0, total_duration_us - total_pause)
        base_per_char = remaining_time / total_chars if total_chars > 0 else 0

        result = []
        offset = 0
        for i, (sent, chars, pause) in enumerate(zip(sentences, char_counts, pause_totals)):
            dur = int(chars * base_per_char) + pause
            if i == len(sentences) - 1:
                # 最后一句补足剩余时长，避免浮点误差
                dur = total_duration_us - offset
            result.append({
                "text": sent,
                "offset_us": offset,
                "duration_us": max(200_000, dur),
            })
            offset += dur
        return result

    # 策略 3: 均分
    return [{"text": s, "offset_us": -1, "duration_us": -1} for s in sentences]


def calculate_auto_subtitle_layout(text: str, style: dict,
                                   canvas_width: int = 1920,
                                   canvas_height: int = 1080) -> dict:
    """
    v4.1: 固定字号 + 分段字幕（逐句依次显示，不再叠加）。

    策略：
    - font_size 固定为样式默认值（如 5.0）
    - position_y 固定为样式默认值（如 -0.833）
    - 长文本拆分为多个子句，每个子句作为独立字幕段依次出现
    - 每个子句均分父片段的时长

    返回: {"font_size", "text_size", "position_y", "line_max_width", "sub_texts"}
    """
    base_font_size = style.get("font_size", 5.0)
    base_position_y = style.get("position_y", -0.8333333333333334)
    line_max_width = style.get("line_max_width", 0.82)

    sub_texts = split_subtitle_sentences(text)

    return {
        "font_size": base_font_size,
        "text_size": int(base_font_size * 6),
        "position_y": base_position_y,
        "line_max_width": line_max_width,
        "sub_texts": sub_texts,
    }


def build_text_material(text: str, style_name: str = "default",
                        tts_audio_id: str = "",
                        auto_layout: dict = None) -> tuple[str, dict]:
    """构建字幕素材（含配音关联）

    auto_layout: 由 calculate_auto_subtitle_layout 返回的自动布局参数，
                 为 None 时使用样式默认值
    """
    mat_id = gen_id()
    style = SUBTITLE_STYLES.get(style_name, SUBTITLE_STYLES["default"])

    # 使用自动布局参数或样式默认值
    layout = auto_layout or {}
    font_size = layout.get("font_size", style["font_size"])
    text_size = layout.get("text_size", int(style["font_size"] * 6))
    line_max_width = layout.get("line_max_width", style.get("line_max_width", 0.82))

    # 构建 content JSON（含样式）
    style_obj = {
        "fill": {"content": {"solid": {"color": style["text_color"]}}},
        "font": {"path": style["font_path"], "id": ""},
        "size": font_size,
        "useLetterColor": True,
        "range": [0, len(text)]
    }
    if style.get("stroke_width", 0) > 0:
        style_obj["strokes"] = [{
            "content": {"solid": {"color": style["stroke_color"]}},
            "width": style["stroke_width"]
        }]
    content = json.dumps({"text": text, "styles": [style_obj]}, ensure_ascii=False)

    return mat_id, {
        "add_type": 1,
        "alignment": style["alignment"],
        "background_alpha": style.get("background_alpha", 1.0),
        "background_color": style.get("background_color", ""),
        "background_height": 0.14,
        "background_horizontal_offset": 0.0,
        "background_round_radius": 0.0,
        "background_style": style.get("background_style", 0),
        "background_vertical_offset": 0.0,
        "background_width": 0.14,
        "base_content": "",
        "bold_width": 0.0,
        "border_alpha": 1.0,
        "border_color": style.get("background_color", ""),
        "border_width": style.get("border_width", 0.08),
        "caption_template_info": {
            "category_id": "", "category_name": "", "effect_id": "",
            "is_new": False, "path": "", "request_id": "",
            "resource_id": "", "resource_name": "", "source_platform": 0
        },
        "check_flag": 7,
        "combo_info": {"text_templates": []},
        "content": content,
        "fixed_height": -1.0,
        "fixed_width": -1.0,
        "font_category_id": "",
        "font_category_name": "",
        "font_id": "",
        "font_name": "",
        "font_path": style["font_path"],
        "font_resource_id": "",
        "font_size": font_size,
        "font_source_platform": 0,
        "font_team_id": "",
        "font_title": style["font_title"],
        "font_url": "",
        "fonts": [],
        "force_apply_line_max_width": False,
        "global_alpha": 1.0,
        "group_id": "",
        "has_shadow": style.get("has_shadow", False),
        "id": mat_id,
        "initial_scale": 1.0,
        "inner_padding": -1.0,
        "is_rich_text": False,
        "italic_degree": 0,
        "ktv_color": "",
        "language": "",
        "layer_weight": 1,
        "letter_spacing": 0.0,
        "line_feed": 1,
        "line_max_width": line_max_width,
        "line_spacing": 0.02,
        "multi_language_current": "none",
        "name": "",
        "original_size": [],
        "preset_id": "",
        "recognize_task_id": "",
        "recognize_type": 0,
        "relevance_segment": [],
        "shadow_alpha": style.get("shadow_alpha", 0.8),
        "shadow_angle": -45.0,
        "shadow_color": "",
        "shadow_distance": 0.0,
        "shadow_point": {"x": 0.6363961030678928, "y": -0.6363961030678928},
        "shadow_smoothing": 1.0,
        "shape_clip_x": False,
        "shape_clip_y": False,
        "style_name": "",
        "sub_type": 0,
        "text_alpha": 1.0,
        "text_color": "#FFFFFF",
        "text_curve": None,
        "text_preset_resource_id": "",
        "text_size": text_size,
        "text_to_audio_ids": [tts_audio_id] if tts_audio_id else [],
        "tts_auto_update": True if tts_audio_id else False,
        "type": "text",
        "typesetting": 0,
        "underline": False,
        "underline_offset": 0.22,
        "underline_width": 0.05,
        "use_effect_default_color": True,
        "words": {"end_time": [], "start_time": [], "text": []}
    }


# ============================================================
# Segment 构建函数
# ============================================================

def build_video_segment(mat_id: str, source_start_us: int, source_duration_us: int,
                         target_start_us: int, speed: float = 1.0, render_index: int = 0,
                         extra_material_refs: list = None) -> dict:
    actual_target_duration = int(source_duration_us / speed)
    return {
        "caption_info": None,
        "cartoon": False,
        "clip": {
            "alpha": 1.0,
            "flip": {"horizontal": False, "vertical": False},
            "rotation": 0.0,
            "scale": {"x": 1.0, "y": 1.0},
            "transform": {"x": 0.0, "y": 0.0}
        },
        "common_keyframes": [],
        "enable_adjust": True,
        "enable_color_correct_adjust": False,
        "enable_color_curves": True,
        "enable_color_match_adjust": False,
        "enable_color_wheels": True,
        "enable_lut": True,
        "enable_smart_color_adjust": False,
        "extra_material_refs": extra_material_refs or [],
        "group_id": "",
        "hdr_settings": {"intensity": 1.0, "mode": 1, "nits": 1000},
        "id": gen_id(),
        "intensifies_audio": False,
        "is_placeholder": False,
        "is_tone_modify": False,
        "keyframe_refs": [],
        "last_nonzero_volume": 1.0,
        "material_id": mat_id,
        "render_index": render_index,
        "responsive_layout": {
            "enable": False, "horizontal_pos_layout": 0,
            "size_layout": 0, "target_follow": "",
            "vertical_pos_layout": 0
        },
        "reverse": False,
        "source_timerange": {"duration": source_duration_us, "start": source_start_us},
        "speed": speed,
        "target_timerange": {"duration": actual_target_duration, "start": target_start_us},
        "template_id": "",
        "template_scene": "default",
        "track_attribute": 0,
        "track_render_index": 0,
        "uniform_scale": {"on": True, "value": 1.0},
        "visible": True,
        "volume": 1.0
    }


def build_audio_segment(mat_id: str, source_start_us: int, source_duration_us: int,
                          target_start_us: int, target_duration_us: int,
                          volume: float = 1.0, render_index: int = 0,
                          track_render_index: int = 0) -> dict:
    return {
        "caption_info": None,
        "cartoon": False,
        "clip": {
            "alpha": 1.0,
            "flip": {"horizontal": False, "vertical": False},
            "rotation": 0.0,
            "scale": {"x": 1.0, "y": 1.0},
            "transform": {"x": 0.0, "y": 0.0}
        },
        "common_keyframes": [],
        "enable_adjust": False,
        "enable_color_correct_adjust": False,
        "enable_color_curves": True,
        "enable_color_match_adjust": False,
        "enable_color_wheels": True,
        "enable_lut": False,
        "enable_smart_color_adjust": False,
        "extra_material_refs": [],
        "group_id": "",
        "hdr_settings": None,
        "id": gen_id(),
        "intensifies_audio": False,
        "is_placeholder": False,
        "is_tone_modify": False,
        "keyframe_refs": [],
        "last_nonzero_volume": volume,
        "material_id": mat_id,
        "render_index": render_index,
        "responsive_layout": {
            "enable": False, "horizontal_pos_layout": 0,
            "size_layout": 0, "target_follow": "",
            "vertical_pos_layout": 0
        },
        "reverse": False,
        "source_timerange": {"duration": source_duration_us, "start": source_start_us},
        "speed": 1.0,
        "target_timerange": {"duration": target_duration_us, "start": target_start_us},
        "template_id": "",
        "template_scene": "default",
        "track_attribute": 0,
        "track_render_index": track_render_index,
        "uniform_scale": {"on": True, "value": 1.0},
        "visible": True,
        "volume": volume
    }


def build_text_segment(mat_id: str, start_us: int, duration_us: int,
                        render_index: int = 0, track_render_index: int = 4,
                        extra_material_refs: list = None,
                        position_y: float = -0.8333333333333334) -> dict:
    return {
        "caption_info": None,
        "cartoon": False,
        "clip": {
            "alpha": 1.0,
            "flip": {"horizontal": False, "vertical": False},
            "rotation": 0.0,
            "scale": {"x": 1.0, "y": 1.0},
            "transform": {"x": 0.0, "y": position_y}
        },
        "common_keyframes": [],
        "enable_adjust": False,
        "enable_color_correct_adjust": False,
        "enable_color_curves": True,
        "enable_color_match_adjust": False,
        "enable_color_wheels": True,
        "enable_lut": False,
        "enable_smart_color_adjust": False,
        "extra_material_refs": extra_material_refs or [],
        "group_id": "",
        "hdr_settings": None,
        "id": gen_id(),
        "intensifies_audio": False,
        "is_placeholder": False,
        "is_tone_modify": False,
        "keyframe_refs": [],
        "last_nonzero_volume": 1.0,
        "material_id": mat_id,
        "render_index": render_index,
        "responsive_layout": {
            "enable": False, "horizontal_pos_layout": 0,
            "size_layout": 0, "target_follow": "",
            "vertical_pos_layout": 0
        },
        "reverse": False,
        "source_timerange": None,
        "speed": 1.0,
        "target_timerange": {"duration": duration_us, "start": start_us},
        "template_id": "",
        "template_scene": "default",
        "track_attribute": 0,
        "track_render_index": track_render_index,
        "uniform_scale": {"on": True, "value": 1.0},
        "visible": True,
        "volume": 1.0
    }


def build_speed_material(speed: float = 1.0) -> tuple[str, dict]:
    """构建变速素材"""
    mat_id = gen_id()
    return mat_id, {
        "curve_speed": None,
        "id": mat_id,
        "mode": 0,
        "speed": speed,
        "type": "speed"
    }


# ============================================================
# SRT 解析
# ============================================================

def parse_srt(srt_path: str) -> list[dict]:
    try:
        with open(srt_path, encoding="utf-8-sig") as f:
            content = f.read()
    except UnicodeDecodeError:
        with open(srt_path, encoding="gbk") as f:
            content = f.read()

    import re
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


# ============================================================
# 主构建逻辑
# ============================================================

def build_empty_materials() -> dict:
    return {
        "ai_translates": [], "audio_balances": [], "audio_effects": [],
        "audio_fades": [], "audio_track_indexes": [], "audios": [],
        "beats": [], "canvases": [], "chromas": [], "color_curves": [],
        "digital_humans": [], "drafts": [], "effects": [], "flowers": [],
        "green_screens": [], "handwrites": [], "hsl": [], "images": [],
        "log_color_wheels": [], "loudnesses": [], "manual_deformations": [],
        "masks": [], "material_animations": [], "material_colors": [],
        "multi_language_refs": [], "placeholders": [], "plugin_effects": [],
        "primary_color_wheels": [], "realtime_denoises": [], "shapes": [],
        "smart_crops": [], "smart_relights": [], "sound_channel_mappings": [],
        "speeds": [], "stickers": [], "tail_leaders": [], "text_templates": [],
        "texts": [], "time_marks": [], "transitions": [], "video_effects": [],
        "video_trackings": [], "videos": [], "vocal_beautifys": [],
        "vocal_separations": []
    }


def build_draft(plan: dict) -> dict:
    name = plan.get("name", "AI剪辑草稿")
    width = plan.get("resolution", [1920, 1080])[0]
    height = plan.get("resolution", [1920, 1080])[1]
    fps = float(plan.get("fps", 30))
    segments = plan.get("segments", [])
    bgm = plan.get("bgm", None)
    subtitle_srt = plan.get("subtitle_srt", None)
    subtitle_style = plan.get("subtitle_style", "default")
    tts_dir = plan.get("tts_dir", None)
    tts_volume = plan.get("tts_volume", 1.0)
    transition_cfg = plan.get("transitions", {})
    animation_type = plan.get("animations", "none")

    materials = build_empty_materials()
    video_track_segments = []
    bgm_audio_segments = []
    tts_audio_segments = []
    text_track_segments = []

    # =============================================
    # 1. 构建视频轨道 + 转场
    # =============================================
    target_cursor = 0
    transition_type = transition_cfg.get("type", "none") if transition_cfg else "none"
    transition_dur = transition_cfg.get("duration_us", 500000) if transition_cfg else 500000

    # 存放每个 video segment 对应的 extra_material_refs
    video_seg_extra_refs = [[] for _ in segments]

    # 在相邻视频段之间插入转场
    transition_ids = []
    if transition_type != "none" and len(segments) > 1:
        for i in range(len(segments) - 1):
            trans_id, trans_mat = build_transition_material(transition_type, transition_dur)
            materials["transitions"].append(trans_mat)
            transition_ids.append(trans_id)
            # 转场附加到后一个 segment 的 extra_material_refs
            video_seg_extra_refs[i + 1].append(trans_id)

    # 构建 video segments
    for i, seg in enumerate(segments):
        source_start = seg.get("source_start_us", 0)
        source_dur = seg.get("source_duration_us", 10_000_000)
        speed = seg.get("speed", 1.0)
        seg_width = seg.get("width", width)
        seg_height = seg.get("height", height)

        # Video material
        mat_id, mat_obj = build_video_material(seg, seg_width, seg_height)
        materials["videos"].append(mat_obj)

        # Speed material
        speed_id, speed_mat = build_speed_material(speed)
        materials["speeds"].append(speed_mat)
        video_seg_extra_refs[i].append(speed_id)

        # 构建 segment
        vseg = build_video_segment(
            mat_id=mat_id,
            source_start_us=source_start,
            source_duration_us=source_dur,
            target_start_us=target_cursor,
            speed=speed,
            render_index=i,
            extra_material_refs=video_seg_extra_refs[i]
        )
        video_track_segments.append(vseg)
        target_cursor += vseg["target_timerange"]["duration"]

    total_duration = target_cursor

    # =============================================
    # 2. 构建 BGM 音频轨道
    # =============================================
    if bgm and bgm.get("path") and os.path.exists(bgm["path"]):
        bgm_dur = bgm.get("duration_us", total_duration)
        bgm_mat_id, bgm_mat = build_audio_material(
            bgm["path"], min(bgm_dur, total_duration),
            name=os.path.basename(bgm["path"])
        )
        materials["audios"].append(bgm_mat)

        bgm_seg = build_audio_segment(
            mat_id=bgm_mat_id,
            source_start_us=0,
            source_duration_us=min(bgm_dur, total_duration),
            target_start_us=0,
            target_duration_us=total_duration,
            volume=bgm.get("volume", 0.5),
            track_render_index=0
        )
        bgm_audio_segments.append(bgm_seg)

    # =============================================
    # 3. 构建字幕 + 配音轨道
    # =============================================
    # 读取 TTS 元信息
    tts_meta = []
    if tts_dir:
        meta_path = os.path.join(tts_dir, "tts_meta.json")
        if os.path.exists(meta_path):
            with open(meta_path, encoding="utf-8") as f:
                tts_meta = json.load(f)

    if subtitle_srt and os.path.exists(subtitle_srt):
        subtitles = parse_srt(subtitle_srt)

        for i, sub in enumerate(subtitles):
            # 查找对应的 TTS 配音
            tts_audio_id = ""
            tts_audio_mat = None
            tts_path = ""
            tts_item = None  # 保存 TTS 元信息供后续字幕使用

            if tts_meta and i < len(tts_meta):
                t = tts_meta[i]
                tts_item = t
                tts_path = t.get("path", "")
                if tts_path and os.path.exists(tts_path):
                    tts_dur = t.get("duration_us", sub["duration_us"])
                    tts_audio_id, tts_audio_mat = build_audio_material(
                        tts_path, tts_dur,
                        name=t.get("srt_text", "")[:20],
                        is_tts=True,
                        resource_id=t.get("resource_id", "")
                    )
                    materials["audios"].append(tts_audio_mat)

                    # TTS 音频 segment
                    tts_aseg = build_audio_segment(
                        mat_id=tts_audio_id,
                        source_start_us=0,
                        source_duration_us=tts_dur,
                        target_start_us=sub["start_us"],
                        target_duration_us=sub["duration_us"],
                        volume=tts_volume,
                        render_index=i,
                        track_render_index=1
                    )
                    tts_audio_segments.append(tts_aseg)

            # 自动布局计算：根据文字长度调整字号和位置
            style = SUBTITLE_STYLES.get(subtitle_style, SUBTITLE_STYLES["default"])
            auto_layout = calculate_auto_subtitle_layout(
                sub["text"], style, canvas_width=width, canvas_height=height
            )

            # 字幕 extra_material_refs 关联 TTS
            text_extra_refs = []
            if tts_audio_id:
                text_extra_refs.append(tts_audio_id)

            # v4.4: 字幕比例分配必须使用与音频相同的时间基准
            # 音频被拉伸到 sub["duration_us"]（SRT时间槽），字幕也要用同一基准
            word_timings = tts_item.get("word_timings", []) if tts_item else []
            timed_subs = split_sentences_by_timing(sub["text"], word_timings,
                                                   max_chars=18,
                                                   total_duration_us=sub["duration_us"])
            n_sub = len(timed_subs)
            # 回退：若所有子句都没有时间戳，则均分
            all_fallback = all(ts["offset_us"] == -1 for ts in timed_subs)
            sub_dur_equal = sub["duration_us"] // n_sub

            for si, ts in enumerate(timed_subs):
                if all_fallback or ts["offset_us"] == -1:
                    sub_start = sub["start_us"] + si * sub_dur_equal
                    sub_dur_i = sub_dur_equal
                else:
                    sub_start = sub["start_us"] + ts["offset_us"]
                    sub_dur_i = max(200_000, ts["duration_us"])  # 最少 0.2s 显示

                text_mat_id, text_mat = build_text_material(
                    ts["text"], style_name=subtitle_style,
                    tts_audio_id=tts_audio_id if si == 0 else "",
                    auto_layout=auto_layout,
                )
                materials["texts"].append(text_mat)

                tseg = build_text_segment(
                    mat_id=text_mat_id,
                    start_us=sub_start,
                    duration_us=sub_dur_i,
                    render_index=14000 + i * n_sub + si,
                    track_render_index=4,
                    extra_material_refs=text_extra_refs if si == 0 else [],
                    position_y=auto_layout["position_y"]
                )
                text_track_segments.append(tseg)

    elif tts_meta:
        # 有 TTS 但没有 SRT → 用 TTS 元信息自动生成字幕
        for i, t in enumerate(tts_meta):
            tts_path = t.get("path", "")
            tts_text = t.get("srt_text", t.get("text", ""))
            target_start = t.get("target_start_us", 0)
            target_dur = t.get("target_duration_us", t.get("duration_us", 3_000_000))
            tts_dur = t.get("duration_us", target_dur)

            if tts_path and os.path.exists(tts_path):
                tts_audio_id, tts_audio_mat = build_audio_material(
                    tts_path, tts_dur,
                    name=tts_text[:20],
                    is_tts=True
                )
                materials["audios"].append(tts_audio_mat)

                tts_aseg = build_audio_segment(
                    mat_id=tts_audio_id,
                    source_start_us=0,
                    source_duration_us=tts_dur,
                    target_start_us=target_start,
                    target_duration_us=target_dur,
                    volume=tts_volume,
                    render_index=i,
                    track_render_index=1
                )
                tts_audio_segments.append(tts_aseg)

                # 自动布局计算
                style = SUBTITLE_STYLES.get(subtitle_style, SUBTITLE_STYLES["default"])
                auto_layout = calculate_auto_subtitle_layout(
                    tts_text, style, canvas_width=width, canvas_height=height
                )

                # v4.4: 字幕比例分配必须使用与音频相同的时间基准
                # 音频被放置在 target_dur 时长内，字幕也要用同一基准
                word_timings = t.get("word_timings", [])
                timed_subs = split_sentences_by_timing(tts_text, word_timings,
                                                       max_chars=18,
                                                       total_duration_us=target_dur)
                n_sub = len(timed_subs)
                all_fallback = all(ts["offset_us"] == -1 for ts in timed_subs)
                sub_dur_equal = target_dur // n_sub

                for si, ts in enumerate(timed_subs):
                    if all_fallback or ts["offset_us"] == -1:
                        sub_start = target_start + si * sub_dur_equal
                        sub_dur_i = sub_dur_equal
                    else:
                        sub_start = target_start + ts["offset_us"]
                        sub_dur_i = max(200_000, ts["duration_us"])  # 最少 0.2s

                    text_mat_id, text_mat = build_text_material(
                        ts["text"], style_name=subtitle_style,
                        tts_audio_id=tts_audio_id if si == 0 else "",
                        auto_layout=auto_layout,
                    )
                    materials["texts"].append(text_mat)

                    tseg = build_text_segment(
                        mat_id=text_mat_id,
                        start_us=sub_start,
                        duration_us=sub_dur_i,
                        render_index=14000 + i * n_sub + si,
                        track_render_index=4,
                        extra_material_refs=[tts_audio_id] if si == 0 else [],
                        position_y=auto_layout["position_y"]
                    )
                    text_track_segments.append(tseg)


    # =============================================
    # 4. 构建 Tracks
    # =============================================
    tracks = []

    # 主视频轨
    tracks.append({
        "attribute": 0,
        "flag": 0,
        "id": gen_id(),
        "is_default_name": True,
        "name": "",
        "segments": video_track_segments,
        "type": "video"
    })

    # BGM 音频轨
    if bgm_audio_segments:
        tracks.append({
            "attribute": 0,
            "flag": 0,
            "id": gen_id(),
            "is_default_name": True,
            "name": "",
            "segments": bgm_audio_segments,
            "type": "audio"
        })

    # TTS 配音音频轨
    if tts_audio_segments:
        tracks.append({
            "attribute": 0,
            "flag": 0,
            "id": gen_id(),
            "is_default_name": True,
            "name": "",
            "segments": tts_audio_segments,
            "type": "audio"
        })

    # 字幕轨
    if text_track_segments:
        tracks.append({
            "attribute": 0,
            "flag": 0,
            "id": gen_id(),
            "is_default_name": True,
            "name": "",
            "segments": text_track_segments,
            "type": "text"
        })

    # =============================================
    # 5. 组装完整草稿
    # =============================================
    now = gen_timestamp()
    draft = {
        "canvas_config": {"height": height, "ratio": "original", "width": width},
        "color_space": 0,
        "config": {
            "adjust_max_index": 1,
            "attachment_info": [],
            "combination_max_index": 1,
            "export_range": None,
            "extract_audio_last_index": 1,
            "lyrics_recognition_id": "",
            "lyrics_sync": True,
            "lyrics_taskinfo": [],
            "maintrack_adsorb": True,
            "material_save_mode": 0,
            "original_sound_last_index": 1,
            "record_audio_last_index": 1,
            "sticker_max_index": 1,
            "subtitle_recognition_id": "",
            "subtitle_sync": True,
            "subtitle_taskinfo": [],
            "system_font_list": [],
            "video_mute": False,
            "zoom_info_params": None
        },
        "cover": "draft_cover.jpg",
        "create_time": now,
        "duration": total_duration,
        "extra_info": None,
        "fps": fps,
        "free_render_index_mode_on": False,
        "group_container": None,
        "id": gen_id(),
        "keyframe_graph_list": [],
        "keyframes": {
            "adjusts": [], "audios": [], "effects": [], "filters": [],
            "handwrites": [], "stickers": [], "texts": [],
            "time_marks": [], "videos": []
        },
        "last_modified_platform": {
            "app_id": 3704, "app_source": "lv", "app_version": "6.0.0",
            "device_id": "workbuddy-agent", "hard_disk_id": "",
            "mac_address": "", "os": "windows", "os_version": "10"
        },
        "materials": materials,
        "mutable_config": None,
        "name": name,
        "new_version": "73.0.0",
        "platform": {
            "app_id": 3704, "app_source": "lv", "app_version": "6.0.0",
            "device_id": "workbuddy-agent", "hard_disk_id": "",
            "mac_address": "", "os": "windows", "os_version": "10"
        },
        "relationships": [],
        "render_index_track_mode_on": False,
        "retouch_cover": None,
        "source": "default",
        "static_cover_image_path": "",
        "time_marks": {"ghost_mode": False, "id": "", "time_marks": []},
        "tracks": tracks,
        "update_time": now,
        "version": 360000
    }

    return draft


def main():
    parser = argparse.ArgumentParser(description="构建剪映草稿 JSON")
    parser.add_argument("--plan", required=True, help="剪辑方案 JSON 文件路径")
    parser.add_argument("--output-dir", required=True, help="草稿输出目录")
    args = parser.parse_args()

    with open(args.plan, encoding="utf-8") as f:
        plan = json.load(f)

    print(f"[INFO] 正在构建草稿: {plan.get('name', 'AI剪辑')}", file=sys.stderr)

    draft = build_draft(plan)

    os.makedirs(args.output_dir, exist_ok=True)
    output_path = os.path.join(args.output_dir, "draft_content.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(draft, f, ensure_ascii=False, separators=(",", ":"))

    # 统计信息
    track_types = [t["type"] for t in draft["tracks"]]
    print(f"[OK] 草稿已生成: {output_path}", file=sys.stderr)
    print(f"[INFO] 总时长: {draft['duration'] / 1_000_000:.2f}s", file=sys.stderr)
    print(f"[INFO] 轨道: {track_types}", file=sys.stderr)
    print(f"[INFO] 转场: {len(draft['materials']['transitions'])}个", file=sys.stderr)
    print(f"[INFO] 字幕: {len(draft['materials']['texts'])}条", file=sys.stderr)
    print(f"[INFO] 配音: {sum(1 for a in draft['materials']['audios'] if a.get('is_ai_clone_tone'))}条", file=sys.stderr)
    print(f"[INFO] BGM: {sum(1 for a in draft['materials']['audios'] if not a.get('is_ai_clone_tone'))}条", file=sys.stderr)
    print(output_path)


if __name__ == "__main__":
    main()
