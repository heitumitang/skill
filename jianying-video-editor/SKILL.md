---
name: jianying-video-editor
description: >
  AI 自动剪辑视频 Skill，使用剪映（JianyingPro）完成视频剪辑。
  通过直接生成剪映草稿 JSON 文件（draft_content.json），实现零 GUI 操作的全自动视频剪辑。
  适配所有 agent：接收自然语言剪辑指令，分析素材，AI 看画面写旁白，生成草稿，注入剪映。
version: "4.7"
agent_created: true
---

# jianying-video-editor — AI 自动剪辑视频 Skill（v4.7）

## 触发条件

当用户提出以下类型需求时，加载本 Skill：

- "帮我剪一个视频" / "用剪映剪辑"
- "自动剪辑 / 拼接这些视频"
- "生成一个 xx 风格的视频"
- "把这些视频素材做成一个完整视频"
- "帮我做视频，加字幕/BGM/转场/配音"
- "帮我做视频，要配上跟画面相关的旁白"
- 任何包含视频素材路径 + 剪辑意图的请求

---

## 功能一览

| 功能 | 状态 | 说明 |
|------|------|------|
| 视频拼接 | ✅ | 多段素材顺序/智能拼接 |
| 转场效果 | ✅ | **12 种转场**，含已验证/待下载两类，详见下方表格 |
| 字幕（SRT） | ✅ | 支持 SRT 导入，**10 种字幕样式**，自动适配字号和位置 |
| TTS 配音 | ✅ | edge-tts，**20+ 种语音**，含普通话/粤语/方言 |
| BGM 配乐 | ✅ | 支持本地音频，可调音量 |
| 剪辑风格 | ✅ | **13 种风格预设**（vlog/纪录片/科技/美食等），自动匹配转场/字幕/音色 |
| **AI 旁白** | ✅ | **提取关键帧 → AI 看图写旁白 → 自动生成字幕+配音** |
| **字幕自适应** | ✅ | 逐句依次显示，每句 18 字以内，标点停顿权重分配时长 |

---

## v4.0 改动说明

**问题**：v3.1 根据文字长度自动缩小字号，导致字幕大小不一致，视觉效果差。

**解决方案**（v4.0）：
1. **固定字号**：所有字幕统一使用样式默认字号（如 `yellow_accent` 为 5.0），不再缩放
2. **智能换行**：`wrap_text()` 优先在标点符号处断行，否则按字符数（18字/行）硬断，确保文本在 `line_max_width` 范围内
3. **Y轴自适应**：根据换行后的行数，自动上移字幕位置（`position_y`），多行字幕不会超出画面底部
4. **禁用剪映自动换行**：`line_feed=0`，完全由 `wrap_text()` 控制换行位置

**效果**：所有字幕字号统一、位置统一，超长文本自动分成多行，画面整洁。

---

## v4.1 改动说明

**问题**：v4.0 的多行字幕在同一时间段内叠加显示（如3行文本同时出现在画面中），用户反馈"几句叠在一起太影响观感"。

**解决方案**（v4.1）：
1. **分段依次显示**：`split_subtitle_sentences()` 将长文本按标点拆分为短句（每句 ≤18 字）
2. **均分时长**：每个短句作为独立的字幕段，均分父视频片段的时长，依次出现
3. **恢复 `line_feed=1`**：单句短文本不超过 `line_max_width`，剪映自动换行作为兜底
4. **固定字号/Y**：所有字幕统一 `font_size=5.0`，`position_y=-0.833`，不随行数变化

**效果**：字幕一句一句出现，不叠加，观感清爽。

---

## v4.3 改动说明

**问题**：v4.1 均分时长导致字幕与 TTS 音频不同步（短句占用时间过长，长句时间不足）。

**根本原因**：edge-tts 在当前网络环境下不返回 `WordBoundary` 事件，无法获取词级时间戳。

**解决方案**（v4.3）：
1. **字符比例分配**：`split_sentences_by_timing()` 按每句的有效字数（去标点）比例分配时长
   - 例如：总时长 13.25s，两句各 15 字 + 一句 6 字 → 5.52s + 5.52s + 2.21s
2. **保留 WordBoundary 支持**：若未来网络环境支持，自动切换为词级精确同步
3. **最小显示时间**：每句字幕至少显示 0.2s，防止极短句闪烁

**效果**：字幕时长与说话时长基本匹配，短句快速切换，长句停留更久，与语音节奏一致。

---

## v4.4 改动说明

**问题**：v4.3 字幕仍与 TTS 音频不同步。

**根本原因**：时间基准不一致——TTS 音频被拉伸到 SRT 时间槽（`sub["duration_us"]`），但字幕子句的时间分配用的是 TTS 实际时长（`tts_actual_dur`），导致字幕偏移量与拉伸后的音频不对应。

**解决方案**（v4.4）：
1. **统一时间基准**：字幕比例分配使用与音频相同的时间基准（SRT 时间槽或 target_dur），而非 TTS 实际时长
2. **标点停顿感知**：比例分配加入标点停顿权重（逗号 150ms、句号/感叹号 250ms、顿号 100ms 等），更贴近真实语音节奏
3. **精确音频时长**：TTS 生成后用 `mutagen` 读取 MP3 精确时长，替代粗略的文件大小估算（从 32kbps 改为更精确的 mutagen 解析）

**效果**：字幕偏移量与音频播放时间在同一时间线上，消除基准不一致导致的偏移；标点停顿让短句切换更自然。

---

## v4.7 改动说明

**问题**：字幕超出画面边界（尤其宽屏/超长文本时）。

**根本原因**：`force_apply_line_max_width` 设置为 `False`，导致剪映不强制执行 `line_max_width` 约束，文本按实际像素宽度渲染，超出可视区域后既不换行也不裁切。

**修复内容**：
1. **`force_apply_line_max_width: False → True`**：强制剪映在 `line_max_width` 范围内换行，确保文本不超出画面
2. **`inner_padding: -1.0 → 0.0`**：修复负数内边距可能导致文本渲染偏移
3. **`text_size` 从 `font_size*6` 调大为 `max(48, font_size*10)`**：增大文本渲染缓冲区，避免文字超出 clip 边界

**效果**：所有字幕严格约束在 `line_max_width`（默认 82% 画幅）范围内，超长文本自动换行，不再超出画面。

---

## v4.6 改动说明

**需求**：丰富剪辑风格、字幕样式、转场特效、配音音色，供使用者选择。

**新增内容**：

1. **字幕样式从 4 种扩展到 10 种**（`assets/subtitle_styles.json`）：
   - 新增：`neon_glow`（霓虹发光）、`cinema_bar`（电影字幕）、`outline_clean`（清爽描边）、`red_bold`（红色粗体）、`top_title`（顶部标题）、`gradient_warm`（暖色橙金）
   - 每种样式新增 `description` 和适用场景说明

2. **转场从 5 种扩展到 12 种**（`build_draft.py` + `assets/transition_presets.json`）：
   - 新增已验证（本地缓存存在）：`glitch`（故障风）、`shake`（抖动）、`slow_dissolve`（慢叠化）、`none`（无转场）
   - 新增待下载：`zoom_in`（画面放大）、`whip_pan`（甩镜）、`circle_wipe`（圆形擦除）、`film_burn`（胶片灼烧）
   - 每种转场标注 `verified` 字段，区分"即插即用"和"需下载"

3. **剪辑风格从 4 种扩展到 13 种**（`assets/transition_presets.json`）：
   - 新增：`cinematic`、`travel`、`short_video`、`emotional`、`product`、`sports`、`tech`、`food`、`news`
   - 每种风格关联推荐的转场、字幕样式、TTS 音色、语速、BGM 音量

4. **TTS 音色整理为结构化配置文件**（`assets/tts_voices.json`）：
   - 按分类整理：普通话男声（7）、普通话女声（9）、方言（2）、粤语（2）、台湾腔（2）
   - 新增 `best_for`、`style`、`rate_range` 字段，便于按内容类型选择
   - 新增 `quick_pick` 快捷查询表和 `style_to_voice` 风格→推荐音色映射

---

## v4.5 改动说明

**问题**：注入剪映后草稿不可见，用户反馈"打开剪映后无法看到草稿"。

**根本原因**：`root_meta_info.json` 中的草稿条目缺少关键字段，尤其是 `draft_json_file`（剪映靠它定位 `draft_content.json`），还有 `draft_is_invisible`、`draft_new_version`、`draft_type` 等。

**解决方案**（v4.5）：
1. **补全 root_meta_info.json 条目格式**：参照剪映真实格式，补全 `draft_json_file`、`draft_is_invisible`、`draft_is_ai_shorts`、`draft_new_version`、`draft_type`、`draft_timeline_materials_size` 等关键字段
2. **jianying venv 安装 mutagen**：v4.4 新增的 mutagen 依赖未安装到 jianying venv，已补装
3. **修复缩进错误**：`inject_draft.py` 中 `elif isinstance(root_meta, dict)` 分支缩进错误，已修复

**效果**：注入的草稿可被剪映正确识别，重启剪映即可在「本地草稿」中看到。

---

## 环境依赖

在执行任何步骤前，检查：

1. **Python**: 使用 `C:\Users\ASUS\.workbuddy\binaries\python\envs\jianying\Scripts\python.exe`
2. **ffprobe**: 运行 `ffprobe -version`，若不存在则 cv2 回退
3. **edge-tts**: TTS 功能需要 `pip install edge-tts`（已包含在 venv 中）
4. **opencv**: 关键帧提取需要 `opencv-python-headless`（已包含在 venv 中）
5. **剪映已安装**: 至少需要创建过一个草稿（用于获取草稿目录路径）

依赖检查命令：
```bash
"C:/Users/ASUS/.workbuddy/binaries/python/envs/jianying/Scripts/python.exe" \
  "C:/Users/ASUS/.workbuddy/skills/jianying-video-editor/scripts/check_env.py"
```

---

## ⭐ AI 旁白工作流（推荐）

这是 v4.0 的核心升级。当用户希望字幕/配音跟视频内容相关时，**必须使用此工作流**：

### 总体流程

```
视频素材 → 提取关键帧 → AI 看图写旁白 → 自动生成SRT → TTS配音 → 构建草稿 → 注入剪映
```

### Step 1 — 提取关键帧

```bash
"C:/Users/ASUS/.workbuddy/binaries/python/envs/jianying/Scripts/python.exe" \
  "C:/Users/ASUS/.workbuddy/skills/jianying-video-editor/scripts/extract_frames.py" \
  --files <视频路径列表> \
  --output-dir ./keyframes \
  --frames-per-clip 3
```

输出：JSON 数组，每个视频包含提取的帧图片路径和元信息。

### Step 2 — AI 分析画面，生成旁白文案

**这一步由 agent 完成**，不是脚本：

1. 读取上一步输出的帧图片（使用 Read 工具读取图片文件）
2. 用 AI 视觉能力分析每段视频的内容
3. 为每段视频写一句旁白文案（要跟画面内容相关，可以是描述、感慨、叙事等）
4. 生成 narration JSON 数组：

```json
[
  {"index": 0, "text": "阳光洒在海面上，波光粼粼"},
  {"index": 1, "text": "远处的灯塔在雾中若隐若现"},
  {"index": 2, "text": "海鸥掠过浪尖，留下一道弧线"}
]
```

**旁白文案要求**：
- 每段 1-2 句话，15-40 字为宜
- 要描述画面实际内容，不要泛泛而谈
- 文案风格根据用户指定的 `--style` 调整（vlog 活泼、documentary 沉稳等）
- 可以有叙事性、抒情性，但必须跟画面对应

### Step 3 — 一键生成（含自动旁白）

将 narration JSON 传给主脚本：

```bash
"C:/Users/ASUS/.workbuddy/binaries/python/envs/jianying/Scripts/python.exe" \
  "C:/Users/ASUS/.workbuddy/skills/jianying-video-editor/scripts/jianying_edit.py" \
  --name "我的视频" \
  --files video1.mp4 video2.mp4 \
  --narration-json '[{"index":0,"text":"阳光洒在海面上"},{"index":1,"text":"远处的灯塔"}]' \
  --tts-voice zh-CN-YunxiNeural \
  --transitions dissolve \
  --subtitle-style yellow_accent
```

或者保存到文件：

```bash
--narration-file narration.json
```

脚本会自动：
1. 根据每段视频时长，将旁白文案对齐到 SRT 时间轴
2. 调用 edge-tts 为每段旁白生成配音
3. 构建完整草稿（视频+字幕+配音+转场）
4. 注入剪映草稿目录

---

## 手动 SRT 模式

如果用户已有 SRT 字幕文件，可以跳过 AI 旁白：

```bash
"C:/Users/ASUS/.workbuddy/binaries/python/envs/jianying/Scripts/python.exe" \
  "C:/Users/ASUS/.workbuddy/skills/jianying-video-editor/scripts/jianying_edit.py" \
  --name "我的视频" \
  --files video1.mp4 video2.mp4 \
  --srt subtitle.srt \
  --tts \
  --tts-voice zh-CN-YunxiNeural \
  --transitions dissolve \
  --subtitle-style yellow_accent
```

---

## 完整参数说明

| 参数 | 必填 | 说明 |
|------|------|------|
| `--name` | ✅ | 草稿名称 |
| `--files` | ✅ | 视频素材路径（多个） |
| `--narration-json` | ❌ | AI 旁白 JSON 字符串（自动启用 TTS+字幕） |
| `--narration-file` | ❌ | AI 旁白 JSON 文件路径（同上） |
| `--bgm` | ❌ | BGM 音频文件路径 |
| `--bgm-volume` | ❌ | BGM 音量 0.0~1.0，默认 0.5 |
| `--srt` | ❌ | 字幕 SRT 文件路径（与 narration 二选一） |
| `--tts` | ❌ | 启用 TTS 配音（配合 `--srt`；`--narration-json` 自动启用） |
| `--tts-voice` | ❌ | TTS 语音（见下方语音表），默认 `zh-CN-YunxiNeural` |
| `--tts-rate` | ❌ | TTS 语速，如 `"+20%"` `"-10%"` |
| `--tts-volume` | ❌ | TTS 配音音量，默认 1.0 |
| `--transitions` | ❌ | 转场类型（见下方转场表），默认 `none` |
| `--transition-duration` | ❌ | 转场时长（微秒），不填则用各转场默认值 |
| `--subtitle-style` | ❌ | 字幕样式（见下方样式表），默认 `default` |
| `--style` | ❌ | 风格预设（见下方风格表），自动匹配转场/字幕/音色 |
| `--duration` | ❌ | 目标时长（秒），0=使用全部素材 |
| `--resolution` | ❌ | 输出分辨率，默认 `1920x1080` |
| `--fps` | ❌ | 帧率，默认 30 |
| `--cut-mode` | ❌ | 剪辑模式：`sequential`（顺序）/ `smart`（智能） |
| `--no-inject` | ❌ | 不自动注入剪映，只保存到本地目录 |

---

## 字幕样式说明（10 种）

| 样式 ID | 名称 | 说明 | 适合场景 |
|---------|------|------|----------|
| `default` | 白色居中字幕 | 干净白字，无背景 | 大多数场景 |
| `subtitle_with_bg` | 带背景字幕 | 白字+半透明黑底，高对比度 | 背景复杂的场景 |
| `yellow_accent` | 黄色描边字幕 | 金黄色+黑色描边，醒目 | Vlog、教程 |
| `title` | 标题大字 | 大号白色标题，居中显示 | 片头、章节标题 |
| `neon_glow` | 霓虹发光字幕 | 青色+洋红描边，发光感 | 科技、电子、游戏 |
| `cinema_bar` | 电影字幕 | 白字+纯黑宽底栏，电影感 | 纪录片、影视感 |
| `outline_clean` | 清爽描边字幕 | 白字+浅灰描边，干净不抢眼 | 旅行、日常 Vlog |
| `red_bold` | 红色粗体字幕 | 中国红+白色描边，醒目有力 | 体育、运动、励志 |
| `top_title` | 顶部标题字幕 | 白字显示在画面顶部 | 新闻、采访同期声 |
| `gradient_warm` | 暖色橙金字幕 | 橙金色+深棕描边，温暖活力 | 美食、生活 |

自定义样式：编辑 `assets/subtitle_styles.json`。

---

## 转场类型说明（12 种）

### ✅ 已验证（本地缓存存在，即插即用）

| 类型 ID | 名称 | 时长 | 说明 |
|---------|------|------|------|
| `dissolve` | 叠化 | 700ms | 淡入淡出，平滑自然，最通用 |
| `flash_white` | 闪白 | 300ms | 强烈闪白，视觉冲击，快节奏首选 |
| `glitch` | 故障风 | 600ms | 像素错位闪烁，科技感/赛博风 |
| `shake` | 抖动 | 500ms | 画面抖动切换，能量感强 |
| `slow_dissolve` | 慢叠化 | 1200ms | 缓慢叠化，梦幻感，情感类 |
| `none` | 无转场 | 0ms | 直接硬切，干净利落 |

### ⚠️ 待下载（需在剪映中预先下载对应资源包）

| 类型 ID | 名称 | 说明 |
|---------|------|------|
| `slide_left` | 向左推移 | 画面向左滑动 |
| `blur` | 模糊 | 模糊过渡，柔和自然 |
| `zoom_in` | 画面放大 | 推进感，适合强调重点 |
| `whip_pan` | 甩镜 | 快速水平甩镜，动感强烈 |
| `circle_wipe` | 圆形擦除 | 圆形展开，可爱俏皮 |
| `film_burn` | 胶片灼烧 | 老电影灼烧感，复古情调 |

---

## 剪辑风格预设（13 种）

风格预设会自动匹配推荐的转场、字幕样式、TTS 音色：

| 风格 ID | 名称 | 转场 | 字幕 | 推荐音色 | 适合内容 |
|---------|------|------|------|----------|----------|
| `general` | 通用默认 | 叠化 | 白色居中 | 云希（男） | 各类视频 |
| `vlog` | 生活 Vlog | 叠化 | 清爽描边 | 晓伊（女） | 旅行、日常 |
| `fast_cut` | 快节奏卡点 | 闪白 | 黄色描边 | 云希（男） | 卡点、混剪 |
| `documentary` | 纪录片 | 慢叠化 | 电影字幕 | 云健（男） | 专题、深度 |
| `cinematic` | 影视感 | 慢叠化 | 电影字幕 | 云泽（男） | 短片、MV |
| `travel` | 旅行探索 | 叠化 | 清爽描边 | 云皓（男） | 户外、风景 |
| `short_video` | 短视频爆款 | 故障风 | 黄色描边 | 晓伊（女） | 抖音、快手 |
| `emotional` | 情感治愈 | 慢叠化 | 暖色橙金 | 晓辰（女） | 情感、治愈 |
| `product` | 产品展示 | 叠化 | 带背景 | 云扬（男） | 评测、商业 |
| `sports` | 运动热血 | 抖动 | 红色粗体 | 云枫（男） | 体育、健身 |
| `tech` | 科技数码 | 故障风 | 霓虹发光 | 云健（男） | 科技、游戏 |
| `food` | 美食生活 | 叠化 | 暖色橙金 | 晓梦（女） | 美食、探店 |
| `news` | 新闻播报 | 无转场 | 顶部标题 | 云扬（男） | 新闻、资讯 |

---

## TTS 配音语音（20+ 种）

### 普通话·男声

| 语音 ID | 名称 | 风格 | 最适合 |
|---------|------|------|--------|
| `zh-CN-YunxiNeural` | 云希 | 阳光活力（**默认**） | Vlog、通用 |
| `zh-CN-YunjianNeural` | 云健 | 沉稳磁性 | 纪录片、科技 |
| `zh-CN-YunyangNeural` | 云扬 | 新闻播报 | 新闻、产品介绍 |
| `zh-CN-YunzeNeural` | 云泽 | 磁性深沉 | 电影感、叙事 |
| `zh-CN-YunfengNeural` | 云枫 | 自然亲切 | 生活、美食 |
| `zh-CN-YunhaoNeural` | 云皓 | 阳光清晰 | 旅行、户外 |
| `zh-CN-YunxiaNeural` | 云夏 | 少年清亮 | 青春、短视频 |

### 普通话·女声

| 语音 ID | 名称 | 风格 | 最适合 |
|---------|------|------|--------|
| `zh-CN-XiaoyiNeural` | 晓伊 | 活泼可爱 | Vlog、短视频 |
| `zh-CN-XiaochenNeural` | 晓辰 | 知性温柔 | 情感、纪录片 |
| `zh-CN-XiaomengNeural` | 晓梦 | 软萌可爱 | 美食、萌宠 |
| `zh-CN-XiaomoNeural` | 晓墨 | 成熟御姐 | 影视、产品 |
| `zh-CN-XiaoruiNeural` | 晓睿 | 自然亲切 | 通用 |
| `zh-CN-XiaoshuangNeural` | 晓双 | 儿童活泼 | 亲子、儿童 |
| `zh-CN-XiaoxuanNeural` | 晓萱 | 知性成熟 | 商务、新闻 |
| `zh-CN-XiaohanNeural` | 晓涵 | 甜美温柔 | 情感、生活 |
| `zh-CN-XiaozhenNeural` | 晓甄 | 温柔细腻 | 情感、电影感 |

### 方言 & 其他

| 语音 ID | 名称 | 语言/方言 |
|---------|------|-----------|
| `zh-CN-liaoning-XiaobeiNeural` | 晓北 | 东北方言 |
| `zh-CN-shaanxi-XiaoniNeural` | 晓妮 | 陕西方言 |
| `zh-HK-HiuMaanNeural` | 晓曼 | 粤语·女声 |
| `zh-HK-WanLungNeural` | 云龙 | 粤语·男声 |
| `zh-TW-HsiaoChenNeural` | 晓臻 | 台湾腔·女声 |
| `zh-TW-YunJheNeural` | 云哲 | 台湾腔·男声 |

语速调节：`--tts-rate "+20%"`（快）`"-10%"`（慢）  
音调调节：`--tts-pitch "+50Hz"`（高）`"-50Hz"`（低）

---

## 注入剪映

脚本自动尝试注入剪映草稿目录。如果自动注入失败（沙箱限制），agent 需用 `inject_draft.py` 手动注入：

```bash
# ⚠️ 必须使用 inject_draft.py，不要直接 cp！
# 直接 cp 会导致缺少 draft_meta_info.json 和 root_meta_info.json 索引，剪映无法识别草稿
"C:/Users/ASUS/.workbuddy/binaries/python/envs/jianying/Scripts/python.exe" \
  "C:/Users/ASUS/.workbuddy/skills/jianying-video-editor/scripts/inject_draft.py" \
  --draft-dir ./jianying_drafts/<name> \
  --name "<草稿名称>"
```

注入成功后，**重启剪映**即可在「本地草稿」中看到项目。

---

## 注意事项

1. **TTS 需要联网**：`edge-tts` 调用微软在线 API，需保持网络连接
2. **素材路径**：建议使用绝对路径，避免相对路径解析错误
3. **AI 旁白质量**：旁白质量取决于 AI 看图的准确度，建议每段视频提取 3+ 帧
4. **旁白节奏**：旁白文案不宜过长，每段 15-40 字为宜，否则 TTS 可能超出视频时长

---

## 文件结构

```
jianying-video-editor/
├── SKILL.md              ← 本文件
├── scripts/
│   ├── jianying_edit.py    ← 一键入口（推荐使用）
│   ├── analyze_media.py   ← 素材分析（ffprobe + cv2 回退）
│   ├── extract_frames.py  ← 关键帧提取（AI 旁白用）
│   ├── build_draft.py     ← 构建 draft_content.json
│   ├── inject_draft.py    ← 写入剪映目录
│   ├── tts_generate.py    ← TTS 配音生成
│   └── check_env.py       ← 环境检查
├── references/
│   ├── draft_schema.md     ← 草稿 JSON 结构文档
│   └── effect_catalog.md  ← 转场/特效 ID 目录
└── assets/
    ├── transition_presets.json  ← 转场预设
    └── subtitle_styles.json    ← 字幕样式预设
```

---

## 故障排查

| 问题 | 解决方案 |
|------|------|
| `ffprobe 未找到` | 安装 ffmpeg 或使用 cv2 回退 |
| `cv2 无法分析` | 运行 `pip install opencv-python-headless` |
| TTS 生成失败 | 检查网络连接；尝试更换语音 ID |
| 草稿导入后无素材 | 检查素材路径是否为绝对路径 |
| 转场不显示 | 确保剪映已下载对应转场资源 |
| 旁白与画面不匹配 | 增加提取帧数（`--frames-per-clip 5`），或手动调整 narration JSON |
| **剪映看不到草稿** | **必须用 `inject_draft.py` 注入，不要直接 cp！检查 `root_meta_info.json` 中是否有 `draft_json_file` 字段** |
| **草稿打开报错** | 检查视频素材路径是否存在、TTS 音频是否在 `textReading` 目录下 |
