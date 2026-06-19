#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
inject_draft.py — 将生成的草稿目录写入剪映草稿路径

用法：
  python inject_draft.py --draft-dir ./my_draft_output/ --name "我的旅行Vlog"

说明：
  将 draft-dir 目录中的 draft_content.json 等文件，复制到剪映草稿目录下，
  同时创建 draft_meta_info.json，让剪映能在"本地草稿"中识别该项目。
  支持自动处理 TTS 音频文件（复制到 textReading 子目录并更新路径）。
  完成后需要【重启剪映】或在剪映中刷新草稿列表才能看到。
"""
import argparse
import json
import os
import shutil
import sys
import time
import uuid
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def _find_draft_base_dir() -> str:
    """自动查找剪映草稿根目录"""
    # 优先级1：环境变量
    local_appdata = os.environ.get("LOCALAPPDATA", "")
    if local_appdata and os.path.exists(local_appdata):
        p = os.path.join(local_appdata, "JianyingPro", "User Data", "Projects", "com.lveditor.draft")
        if os.path.exists(p):
            return p

    # 优先级2：常见安装路径（Windows）
    candidates = []
    try:
        home = os.path.expanduser("~")
        candidates.append(os.path.join(home, "AppData", "Local", "JianyingPro", "User Data", "Projects", "com.lveditor.draft"))
        candidates.append(os.path.join(home, "AppData", "Roaming", "JianyingPro", "User Data", "Projects", "com.lveditor.draft"))
    except Exception:
        pass

    for c in candidates:
        if os.path.exists(c):
            return c

    # 都找不到，返回默认候选
    return candidates[0] if candidates else r"C:\Users\ASUS\AppData\Local\JianyingPro\User Data\Projects\com.lveditor.draft"


DRAFT_BASE_DIR = _find_draft_base_dir()


def gen_id() -> str:
    return str(uuid.uuid4()).upper()


def gen_timestamp() -> int:
    return int(time.time())


def build_meta_info(name: str, draft_dir: str, content: dict) -> dict:
    """根据 draft_content.json 构建 draft_meta_info.json"""
    duration = content.get("duration", 0)
    now = gen_timestamp()
    now_ms = now * 1000

    # 收集所有视频素材
    materials = []
    videos = content.get("materials", {}).get("videos", [])
    for v in videos:
        materials.append({
            "type": 0,
            "value": [{
                "create_time": now,
                "duration": v.get("duration", 0),
                "extra_info": v.get("material_name", ""),
                "file_Path": v.get("path", ""),
                "height": v.get("height", 1080),
                "id": gen_id().lower().replace("-", "")[:36],
                "import_time": now,
                "import_time_ms": now_ms,
                "item_source": 1,
                "md5": "",
                "metetype": "video",
                "roughcut_time_range": {"duration": v.get("duration", 0), "start": 0},
                "sub_time_range": {"duration": -1, "start": -1},
                "type": 0,
                "width": v.get("width", 1920)
            }]
        })

    audios = content.get("materials", {}).get("audios", [])
    if audios:
        audio_items = []
        for a in audios:
            audio_items.append({
                "create_time": 0,
                "duration": a.get("duration", 0),
                "extra_info": "",
                "file_Path": a.get("path", ""),
                "height": 0,
                "id": gen_id().lower().replace("-", "")[:36],
                "import_time": now,
                "import_time_ms": -1,
                "item_source": 1,
                "md5": "",
                "metetype": "none",
                "roughcut_time_range": {"duration": -1, "start": -1},
                "sub_time_range": {"duration": -1, "start": -1},
                "type": 8,
                "width": 0
            })
        materials.append({"type": 8, "value": audio_items})

    return {
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
        "draft_id": gen_id(),
        "draft_is_ai_shorts": False,
        "draft_is_article_video_draft": False,
        "draft_is_from_deeplink": False,
        "draft_is_invisible": False,
        "draft_materials_copied": False,
        "draft_name": name,
        "draft_new_version": "",
        "draft_removable_storage_device": "",
        "draft_root_path": draft_dir,
        "draft_segment_extra_info": None,
        "draft_timeline_materials_size": 0,
        "draft_timeline_materials_size_": 0,
        "tm_draft_cloud_completed": "",
        "tm_draft_cloud_modified": 0,
        "tm_draft_create": now_ms,
        "tm_draft_modified": now_ms,
        "tm_draft_removed": 0,
        "tm_duration": int(duration / 1000)
    }


def inject_draft(src_dir: str, name: str) -> str:
    """将草稿写入剪映草稿目录，返回最终草稿路径。失败时抛出异常。"""
    if not os.path.isdir(DRAFT_BASE_DIR):
        raise FileNotFoundError(f"剪映草稿目录不存在: {DRAFT_BASE_DIR}")

    # 目标目录
    safe_name = name.replace("/", "_").replace("\\", "_").replace(":", "_")
    dest_dir = os.path.join(DRAFT_BASE_DIR, safe_name)

    # 如果目录已存在，加时间戳避免覆盖
    if os.path.exists(dest_dir):
        ts = int(time.time())
        dest_dir = f"{dest_dir}_{ts}"
        safe_name = os.path.basename(dest_dir)
        print(f"[WARN] 草稿目录已存在，改用: {dest_dir}", file=sys.stderr)

    os.makedirs(dest_dir, exist_ok=True)

    # 复制 draft_content.json
    src_content = os.path.join(src_dir, "draft_content.json")
    if not os.path.exists(src_content):
        raise FileNotFoundError(f"找不到 draft_content.json: {src_content}")

    shutil.copy2(src_content, os.path.join(dest_dir, "draft_content.json"))

    # 读取内容
    dc_path = os.path.join(dest_dir, "draft_content.json")
    with open(dc_path, encoding="utf-8") as f:
        content = json.load(f)

    # 复制 TTS 音频到 textReading 子目录并更新路径
    tts_src = os.path.join(src_dir, "tts_audio")
    if os.path.isdir(tts_src):
        tts_dst = os.path.join(dest_dir, "textReading")
        os.makedirs(tts_dst, exist_ok=True)
        for fname in os.listdir(tts_src):
            if fname.endswith(".mp3") or fname.endswith(".wav"):
                shutil.copy2(os.path.join(tts_src, fname), os.path.join(tts_dst, fname))

        # 更新 draft_content.json 中的音频路径
        for audio in content.get("materials", {}).get("audios", []):
            old_path = audio.get("path", "")
            if ("tts_" in old_path or "textReading" in old_path) and \
               (old_path.endswith(".mp3") or old_path.endswith(".wav")):
                fname = os.path.basename(old_path)
                audio["path"] = os.path.join(tts_dst, fname)

    # 更新名称
    content["name"] = name
    with open(dc_path, "w", encoding="utf-8") as f:
        json.dump(content, f, ensure_ascii=False, separators=(",", ":"))

    # 生成 draft_meta_info.json
    meta = build_meta_info(name, dest_dir, content)
    with open(os.path.join(dest_dir, "draft_meta_info.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    # 更新 root_meta_info.json
    root_meta_path = os.path.join(DRAFT_BASE_DIR, "root_meta_info.json")
    if os.path.exists(root_meta_path):
        try:
            with open(root_meta_path, encoding="utf-8") as f:
                root_meta = json.load(f)

            # root_meta_info.json 可能是列表或 dict
            if isinstance(root_meta, list):
                # 检查是否已存在同名草稿
                existing = [i for i, m in enumerate(root_meta) if m.get("draft_name") == name]
                if existing:
                    for idx in existing:
                        root_meta[idx] = meta
                else:
                    root_meta.insert(0, meta)  # 插入最前面
            elif isinstance(root_meta, dict):
                all_drafts = root_meta.get("all_draft_store", [])
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
                "draft_root_path": DRAFT_BASE_DIR,
                "draft_timeline_materials_size": 0,
                "draft_type": "",
                "tm_draft_cloud_completed": "",
                "tm_draft_cloud_modified": 0,
                "tm_draft_create": meta["tm_draft_create"],
                "tm_draft_modified": meta["tm_draft_modified"],
                "tm_draft_removed": 0,
                "tm_duration": meta["tm_duration"]
            }
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
            print(f"[WARN] 更新 root_meta_info.json 失败（不影响使用）: {e}", file=sys.stderr)

    return dest_dir


def main():
    parser = argparse.ArgumentParser(description="将草稿写入剪映草稿目录")
    parser.add_argument("--draft-dir", required=True, help="包含 draft_content.json 的目录")
    parser.add_argument("--name", required=True, help="草稿项目名称")
    args = parser.parse_args()

    src_dir = str(Path(args.draft_dir).resolve())
    print(f"[INFO] 正在写入草稿: {args.name}", file=sys.stderr)

    try:
        dest = inject_draft(src_dir, args.name)
        print(f"\n[成功] 草稿已写入: {dest}")
        print(f"\n接下来：")
        print(f"  1. 打开（或重启）剪映")
        print(f"  2. 在「本地草稿」中找到「{args.name}」")
        print(f"  3. 打开后点击「导出」完成视频渲染")
    except PermissionError as e:
        print(f"\n[ERROR] 权限不足，无法写入剪映目录: {e}", file=sys.stderr)
        print(f"  请手动将 {src_dir} 复制到剪映草稿目录", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] 注入失败: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
