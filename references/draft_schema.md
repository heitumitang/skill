# 剪映草稿 Schema 说明（基于 JianyingPro 6.x / 7.x，2026年6月实测）

## 单位约定

- **时间**：微秒（μs），1秒 = 1,000,000 μs
- **坐标/缩放**：归一化浮点数（0.0 ~ 1.0）
- **颜色**：`#RRGGBB` 十六进制或 `{red, green, blue, alpha}` 对象（0.0 ~ 1.0）

---

## 顶层字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `canvas_config` | object | 画布宽高，`{"width": 1920, "height": 1080, "ratio": "original"}` |
| `fps` | float | 帧率，通常 30.0 |
| `duration` | int | 总时长（μs），等于所有视频片段 target_timerange 之和 |
| `tracks` | array | 所有轨道 |
| `materials` | object | 所有素材定义（videos/audios/texts/transitions 等） |
| `id` | string | 草稿 UUID（大写） |
| `create_time` | int | Unix 时间戳（秒） |
| `version` | int | 草稿版本号，写 360000 |
| `new_version` | string | 写 "73.0.0" |

---

## tracks 结构

每个 track 对象：

```json
{
  "id": "UPPERCASE-UUID",
  "type": "video" | "audio" | "text",
  "attribute": 0,
  "flag": 0,
  "is_default_name": true,
  "name": "",
  "segments": [ ...segment 对象... ]
}
```

### track type 枚举
- `"video"` — 主视频/画中画轨
- `"audio"` — BGM/配音/提取音频轨
- `"text"` — 字幕/文字轨

---

## segment 结构（video track）

```json
{
  "id": "UPPERCASE-UUID",
  "material_id": "对应 materials.videos[].id",
  "source_timerange": {
    "start": 0,
    "duration": 5000000
  },
  "target_timerange": {
    "start": 0,
    "duration": 5000000
  },
  "speed": 1.0,
  "volume": 1.0,
  "visible": true,
  "reverse": false,
  "clip": {
    "alpha": 1.0,
    "rotation": 0.0,
    "scale": {"x": 1.0, "y": 1.0},
    "transform": {"x": 0.0, "y": 0.0},
    "flip": {"horizontal": false, "vertical": false}
  },
  "render_index": 0,
  "track_render_index": 0,
  "extra_material_refs": [],
  "keyframe_refs": [],
  "common_keyframes": []
}
```

**关键字段说明：**
- `source_timerange.start`：从原视频哪个时间点开始截取（μs）
- `source_timerange.duration`：截取多长（μs）
- `target_timerange.start`：放到时间轴的哪个位置（μs）
- `target_timerange.duration`：在时间轴上占多长（= source_duration / speed）
- `speed`：速度倍数，2.0 = 2倍速，0.5 = 慢动作

---

## materials.videos[] 结构

```json
{
  "id": "UPPERCASE-UUID",
  "type": "video",
  "path": "C:/absolute/path/to/video.mp4",
  "material_name": "video.mp4",
  "width": 1920,
  "height": 1080,
  "duration": 10000000,
  "has_audio": false,
  "category_name": "local",
  "source": 0,
  "crop": {
    "lower_left_x": 0.0, "lower_left_y": 1.0,
    "lower_right_x": 1.0, "lower_right_y": 1.0,
    "upper_left_x": 0.0, "upper_left_y": 0.0,
    "upper_right_x": 1.0, "upper_right_y": 0.0
  }
}
```

---

## materials.audios[] 结构

```json
{
  "id": "UPPERCASE-UUID",
  "type": "extract_music",
  "path": "C:/absolute/path/to/bgm.mp3",
  "material_name": "bgm.mp3",
  "duration": 180000000,
  "category_name": "local",
  "source_platform": 0
}
```

---

## materials.texts[] 结构

核心字段：
- `id`：大写 UUID
- `type`：`"text"`
- `content`：JSON 字符串，包含 `{"text": "字幕内容", "styles": [...]}`
- `text_color`：`"#FFFFFF"`
- `font_size`：8.0（相对单位，剪映内部）
- `alignment`：0=左对齐，1=居中，2=右对齐
- `line_max_width`：文字最大宽度比例（0.0~1.0）

字幕 segment 中：
- `clip.transform.y = -0.85`：位于画面下方

---

## ID 格式

所有 id 字段统一使用大写 UUID：
```python
import uuid
def gen_id():
    return str(uuid.uuid4()).upper()
```

---

## 草稿目录文件列表

| 文件 | 必须 | 说明 |
|------|------|------|
| `draft_content.json` | 是 | 主要编辑数据 |
| `draft_meta_info.json` | 是 | 草稿元数据（名称、素材列表、时长等） |
| `draft_cover.jpg` | 否 | 封面图，没有则显示占位图 |
| `draft_biz_config.json` | 否 | 业务配置 |
| `draft_settings/` | 否 | 草稿设置目录 |

---

## 适配版本

- 剪映 PC 版：5.9 ~ 7.x（2025-2026）
- 草稿文件 version 字段：360000
- new_version：73.0.0
- 如版本不兼容，剪映会提示"草稿版本较旧"但通常仍可打开

---

## materials.transitions[]（转场素材）

转场写在相邻两个 video segment 之间，由后一个 segment 的 `extra_material_refs` 引用。

```json
{
  "id": "UPPERCASE-UUID",
  "type": "transition",
  "name": "叠化",
  "category_id": "39663",
  "category_name": "热门",
  "duration": 500000,
  "effect_id": "34443818",
  "resource_id": "7312438185261273650",
  "is_overlap": true,
  "path": "C:/Users/ASUS/AppData/Local/JianyingPro/User Data/Cache/effect/34443818/...",
  "platform": "all",
  "request_id": "20260604..."
}
```

关键字段：
- `effect_id`：剪映内置特效 ID（空字符串 = 本地特效）
- `path`：本地缓存路径（内置特效需提前在剪映中下载）
- `duration`：转场时长（μs），通常 300000~1000000
- `is_overlap`：true = 两段画面重叠转场

### segment 如何引用转场

在 video track 的 segment 中（通常是后一段）：

```json
{
  "extra_material_refs": [
    "SPEED_MATERIAL_ID",
    "TRANSITION_MATERIAL_ID"   // ← 转场在这里
  ]
}
```

第一个 segment 不需要转场引用。

---

## materials.texts[]（字幕素材 — 含配音关联）

字幕（含配音关联）的 material 结构：

```json
{
  "id": "UPPERCASE-UUID",
  "add_type": 1,
  "content": "{\"text\":\"字幕文本...\",\"styles\":[...]}",
  "font_path": "C:/Windows/Fonts/msyh.ttc",
  "font_title": "微软雅黑",
  "font_size": 5.0,
  "text_size": 30,
  "alignment": 1,
  "background_style": 0,
  "background_color": "#000000",
  "border_width": 0.08,
  "has_shadow": false,
  "text_to_audio_ids": ["AUDIO_MATERIAL_ID"],
  "tts_auto_update": true,
  "type": "text"
}
```

关键字段：
- `add_type`：0 = 手动添加，1 = 自动识别字幕（含配音）
- `content`：JSON 字符串，内含 `text`（纯文本）和 `styles`（样式数组）
- `text_to_audio_ids`：关联 TTS 配音的 audio material ID
- `font_path`：字体文件路径（建议使用系统字体）
- `text_size`：字号（与 `font_size` 不同，此为渲染字号）

### content 字段格式

```json
{
  "text": "字幕文本内容",
  "styles": [
    {
      "fill": {"content": {"solid": {"color": [1, 1, 1]}}},
      "font": {"path": "C:/Windows/Fonts/msyh.ttc", "id": ""},
      "size": 5,
      "useLetterColor": true,
      "range": [0, 7]
    }
  ]
}
```

---

## materials.audios[]（音频素材 — 含 TTS 配音）

TTS 生成的配音音频 material：

```json
{
  "id": "UPPERCASE-UUID",
  "path": "C:/Users/ASUS/.../textReading/XXX_000.wav",
  "duration": 3966666,
  "name": "字幕文本前20字...",
  "is_ai_clone_tone": true,
  "is_ugc": true,
  "is_text_edit_overdub": false,
  "type": "extract_music"
}
```

关键字段：
- `is_ai_clone_tone`：true = TTS 配音
- `path`：配音音频文件路径（WAV 或 MP3）
- `duration`：音频时长（μs）
- `is_text_edit_overdub`：false = 非即兴配音

---

## materials.speeds[]（变速素材）

每个 video segment 对应一个 speed material（即使 speed=1.0）：

```json
{
  "id": "UPPERCASE-UUID",
  "speed": 1.0,
  "mode": 0,
  "curve_speed": null,
  "type": "speed"
}
```

关联的 segment 在 `extra_material_refs` 中引用此 ID。

---

## 完整 plan.json 格式（build_draft.py 输入）

```json
{
  "name": "草稿名称",
  "resolution": [1920, 1080],
  "fps": 30,
  "segments": [
    {
      "path": "C:/videos/clip1.mp4",
      "source_start_us": 0,
      "source_duration_us": 5000000,
      "speed": 1.0,
      "width": 1920,
      "height": 1080,
      "has_audio": true
    }
  ],
  "bgm": {
    "path": "C:/music/bgm.mp3",
    "volume": 0.5,
    "duration_us": 180000000
  },
  "subtitle_srt": "C:/subs/subtitle.srt",
  "subtitle_style": "default",
  "tts_dir": "C:/tts_output/",
  "tts_volume": 1.0,
  "transitions": {
    "type": "dissolve",
    "duration_us": 500000
  },
  "animations": "none",
  "filter": "none"
}
```
