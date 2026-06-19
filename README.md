# jianying-video-editor

自动剪辑视频 Skill — 通过生成剪映草稿 JSON，实现零 GUI 全自动视频剪辑。

## 功能

- 视频素材自动拼接 + 转场特效
- 智能旁白文案生成 + TTS 配音
- 多种字幕样式（10 种预设）
- 多种转场特效（12 种预设）
- 13 种剪辑风格预设一键设定
- 20+ 种 TTS 音色选择
- 自动注入剪映草稿目录

## 快速开始

详见 [安装与使用文档.md](安装与使用文档.md)。

```bash
python scripts/jianying_edit.py \
  --name "我的第一个视频" \
  --files video1.mp4 video2.mp4 video3.mp4 \
  --narration-json '[{"index":0,"text":"开场白"}]' \
  --tts-voice zh-CN-YunxiNeural \
  --transitions dissolve \
  --subtitle-style default \
  --style general
```

打开剪映 → 本地草稿 → 即可查看和导出。

## 系统要求

- Windows 10/11
- 剪映专业版 5.9 及以下
- Python 3.8+
- 依赖：edge-tts, opencv-python-headless, mutagen, tabulate

## 剪映版本兼容性

| 版本 | 草稿生成 | 草稿读取 |
|------|---------|---------|
| 5.x | 完全兼容 | 完全兼容 |
| 6.x+ | 可能兼容 | 加密不可读 |

推荐使用剪映专业版 5.9 及以下。

## 文件结构

```
jianying-video-editor/
├── SKILL.md              ← Skill 描述文件
├── 安装与使用文档.md      ← 完整安装和使用说明
├── scripts/               ← 核心脚本
├── assets/                ← 配置文件（字幕样式/转场/音色）
└── references/            ← 剪映草稿结构文档
```

## License

MIT
