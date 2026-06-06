# Claude Code Skills

Personal collection of Claude Code skills. Each subdirectory is an
independent skill — copy it to `~/.claude/skills/` to install.

## Skills

| Skill | Description | Docs |
|---|---|---|
| [draw-image](draw-image/) | AI image generation via volcengine / OpenAI / Aliyun Bailian / any OpenAI-compatible API | [English](draw-image/README.md) · [中文](draw-image/README_zh.md) |

## Install a skill

```bash
# Clone this repo
git clone https://github.com/fullsummerdream/claude-code-skills-summer.git

# Copy the skill you want to Claude Code's skills directory
# macOS / Linux
cp -r claude-code-skills-summer/draw-image ~/.claude/skills/

# Windows PowerShell
Copy-Item -Recurse claude-code-skills-summer/draw-image "$env:USERPROFILE\.claude\skills\"

# Then follow the skill's README for setup instructions
```

## License

MIT — see [LICENSE](LICENSE) for details.
