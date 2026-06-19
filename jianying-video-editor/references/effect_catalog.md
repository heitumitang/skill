# 剪映内置特效 / 转场 ID 目录

> 注意：以下 ID 为剪映内置资源，使用时需确认剪映已下载对应资源包。
> 本地素材路径无需 effect_id，只有使用平台内置特效时才需要。

---

## 转场（Transitions）

转场写入 `materials.transitions[]`，并在 segment 的 `extra_material_refs` 中引用。

| 名称 | effect_id | resource_id | 说明 |
|------|-----------|--------------|------|
| 叠化（淡入淡出） | `34443818` | `7312438185261273650` | 最常用，适合大多数场景 |
| 闪白 | `26135688` | `7290852476259930685` | 强烈过渡 |
| 推移（向左） | `6b0de3a9-2c5f-4a2c-9e1d-c18e3f9f7c21` | — | 分镜过渡 |
| 模糊 | `d2e8f1c6-5b3a-4e7d-a9c2-1f8b6e4d3c07` | — | 场景切换 |
| 旋转 | `7f4c2b8e-1a5d-4c9e-b3f6-2e7d8a5c1b04` | — | 动感切换 |
| 拉镜 | `4a8e1c7d-9f2b-4a5c-b8e3-3d6c9f2a1b08` | — | 影视感 |

> **获取真实 ID 方法：**
> 在剪映中手动添加一个转场，保存后读取 `draft_content.json`，
> 找到 `materials.transitions[]` 数组中新增的条目，取其 `effect_id` 字段。

### 转场 material 结构

```json
{
  "id": "UPPERCASE-UUID",
  "type": "transition",
  "category_id": "39663",
  "category_name": "热门",
  "duration": 500000,
  "effect_id": "34443818",
  "is_overlap": true,
  "name": "叠化",
  "path": "C:/Users/ASUS/AppData/Local/JianyingPro/User Data/Cache/effect/34443818/...",
  "platform": "all",
  "request_id": "...",
  "resource_id": "7312438185261273650",
  "source_platform": 0
}
```

- `path`：本地缓存路径（内置特效）；空字符串 = 平台资源（需联网下载）
- `is_overlap`：true = 两段画面重叠转场
- `duration`：转场时长（μs），建议 300000~1000000

转场写在两个 segment 之间，`segment.extra_material_refs` 包含该转场 ID（附加到**后一个** segment）。

---

## 视频特效（Video Effects）

视频特效写入 `materials.video_effects[]`

| 名称 | 效果说明 |
|------|---------|
| 光晕 | 画面边缘发光 |
| 电影感色调 | 偏黄绿的胶片色 |
| 故障风 | 像素错位闪烁 |
| 黑白 | 去色处理 |

> 特效 ID 需要在剪映中实际使用后从 draft_content.json 提取

---

## 滤镜（Filters）

写入 `materials.effects[]`（type="filter"）

常用滤镜：
- 清晰（自然清晰）
- 复古（胶片色调）
- 日系（明亮清新）
- 电影（暗角+色偏）

---

## 字幕花字（Text Templates）

常用字幕样式写在 `materials.text_templates[]`，或通过 `texts[].caption_template_info` 引用。

---

## 贴纸（Stickers）

写入 `materials.stickers[]`，segment 写入 `tracks` 中 type 为 `"sticker"` 的轨道。

---

## TTS 语音列表（edge-tts）

| 语音 ID | 说明 |
|----------|------|
| `zh-CN-YunxiNeural` | 男声·阳光（默认） |
| `zh-CN-XiaoyiNeural` | 女声·活泼 |
| `zh-CN-YunjianNeural` | 男声·沉稳 |
| `zh-CN-YunyangNeural` | 男声·新闻播报 |
| `zh-CN-XiaochenNeural` | 女声·知性 |
| `zh-CN-XiaohanNeural` | 女声·甜美 |
| `zh-CN-XiaomengNeural` | 女声·可爱 |
| `zh-CN-XiaomoNeural` | 女声·御姐 |
| `zh-CN-XiaoruiNeural` | 女声·自然 |
| `zh-CN-XiaoshuangNeural` | 女声·儿童 |
| `zh-CN-XiaoxuanNeural` | 女声·知性2 |
| `zh-CN-XiaozhenNeural` | 女声·温柔2 |
| `zh-CN-YunfengNeural` | 男声·自然 |
| `zh-CN-YunhaoNeural` | 男声·阳光2 |
| `zh-CN-YunxiaNeural` | 男声·少年 |
| `zh-CN-YunzeNeural` | 男声·磁性 |

语速调节：`--tts-rate "+20%"`（快）`"--10%"`（慢）  
音调调节：`--tts-pitch "+50Hz"`（高）`"--50Hz"`（低）

---

## 注意

1. 平台内置素材（如剪映网络音乐库、网络特效）需要登录账号且联网才能使用
2. 本 skill 主要使用**本地素材**，避免依赖网络资源
3. 若需要使用平台素材，需在剪映中预先下载后，通过扫描 draft_content.json 获取对应 ID
