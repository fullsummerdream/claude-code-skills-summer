# Claude Code Skills

个人 Claude Code 技能合集。每个子目录是一个独立的 skill，
复制到 `~/.claude/skills/` 即可安装使用。

## 技能列表

| 技能 | 简介 | 文档 |
|---|---|---|
| [draw-image](draw-image/) | AI 图片生成，支持火山方舟 / OpenAI / 阿里云百炼 / 任意 OpenAI 兼容接口 | [English](draw-image/README.md) · [中文](draw-image/README_zh.md) |

## 安装方式

```bash
# 克隆仓库
git clone https://github.com/fullsummerdream/claude-code-skills-summer.git

# 把需要的 skill 复制到 Claude Code 的 skills 目录
# macOS / Linux
cp -r claude-code-skills-summer/draw-image ~/.claude/skills/

# Windows PowerShell
Copy-Item -Recurse claude-code-skills-summer/draw-image "$env:USERPROFILE\.claude\skills\"

# 然后按照对应 skill 的 README 完成配置
```

## 许可证

MIT — 详见 [LICENSE](LICENSE)。
