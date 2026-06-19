# Skill 合集

本仓库存放各类 Skill，每个 Skill 占独立子目录，互不干扰。

## 目录结构

```
skill/
├── jianying-video-editor/   ← 自动剪辑视频 Skill
├── <其他-skill>/            ← 后续新增的 Skill
├── README.md                ← 本文件（仓库总览）
└── .gitignore
```

## 已收录 Skill

| Skill | 说明 | 详情 |
|-------|------|------|
| [jianying-video-editor](jianying-video-editor/) | 通过生成剪映草稿 JSON，实现零 GUI 全自动视频剪辑 | [安装与使用文档](jianying-video-editor/安装与使用文档.md) |

## 新增 Skill

每个 Skill 放在独立子目录下，结构如下：

```
<skill-name>/
├── SKILL.md          ← Skill 描述文件
├── README.md         ← 该 Skill 的简介（可选）
├── scripts/          ← 脚本（如有）
├── assets/           ← 配置/资源（如有）
└── ...
```

只需新建子目录并提交即可，不会与其他 Skill 冲突。

## License

各 Skill 遵循各自目录内的 License 说明，未注明者默认 MIT。
