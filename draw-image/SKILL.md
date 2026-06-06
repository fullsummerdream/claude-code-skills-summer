---
name: draw-image
description: Generate images using the user's configured AI provider (volcengine ARK Doubao-Seedream, OpenAI gpt-image-1, Aliyun bailian qwen-image, or any custom OpenAI-compatible service). Use when the user says 画图 / 画一张图 / draw / generate an image / make a picture / 文生图 / 图生图. Invoke `python <skill-dir>/scripts/draw.py "<prompt>"` via Bash. The script auto-locates the skill directory, so you can call it from any working directory. To add a new provider, run `python <skill-dir>/scripts/auto_add_provider.py <pdf-path> --provider-name <name>` then have the agent complete the emitted YAML block.
license: MIT
---

# draw-image skill

This skill lets you (an AI agent) generate images by calling a single command
against the user's configured image-generation provider. The user has
already configured at least one provider in `<skill-dir>/config.yaml`.

## When to trigger

Use this skill whenever the user asks for visual content:
- 画图 / 画一张图 / 给我画一个 X / 文生图
- 图生图 / 把这张图改成 X / 用 Y 做参考
- draw / generate an image / make a picture / render X
- "Create a logo for Z" / "Show me a cat"
- "一组图标" / "four fruit icons" (sequential / group generation)

Do **NOT** use this skill if the user only wants to **describe** an existing
image (use the `vision` skill instead).

## First-time setup (the user does this once)

**Prerequisites:** Python 3.8+, an API key from at least one supported service
(volcengine ARK / OpenAI / Aliyun Bailian).

1. Install dependencies:
   ```bash
   pip install -r "<skill-dir>/requirements.txt"
   ```
2. Configure providers:
   - Copy `config.example.yaml` to `config.yaml` (if not already present).
   - Edit `config.yaml` — replace each `${...}` placeholder with a real API key,
     or set the matching environment variable.
3. Verify:
   ```bash
   python "<skill-dir>/scripts/draw.py" --validate-config
   ```
   Expected output ends with `OK: config is valid.`

> **For AI agents:** `<skill-dir>` means the directory containing this SKILL.md.
> If you're running inside Claude Code, locate the skill directory by looking for
> `SKILL.md` under the user's skills path (commonly
> `~/.claude/skills/draw-image/` on macOS/Linux or
> `%USERPROFILE%\.claude\skills\draw-image\` on Windows). Always use the
> absolute path in Bash commands — the script auto-detects its location from
> there.

## How to call

```bash
# Basic text-to-image
python "<skill-dir>/scripts/draw.py" "a cat in a window"

# Use a specific provider
python "<skill-dir>/scripts/draw.py" --provider openai "logo design"

# Use a specific size
python "<skill-dir>/scripts/draw.py" --size 2K "a cat"

# Group generation (volcengine only)
python "<skill-dir>/scripts/draw.py" --sequential --max-images 4 "four fruit icons"

# Reference image (volcengine / openai)
python "<skill-dir>/scripts/draw.py" --image "C:/path/to/cat.png" "make it orange"

# Multiple reference images
python "<skill-dir>/scripts/draw.py" --images "C:/path/to/a.png" "C:/path/to/b.png" "融合风格"

# Streaming output (requires: pip install aiohttp)
python "<skill-dir>/scripts/draw.py" --stream "four fruit icons"

# Validate config without drawing
python "<skill-dir>/scripts/draw.py" --validate-config
```

`<skill-dir>` is auto-detected by the script via `__file__` — you never
need to know its absolute path.

The script **does not require you to `cd` into the skill directory**. It
auto-locates its own location via `__file__`.

### All CLI flags

| Flag | Purpose | Supported by |
|---|---|---|
| `prompt` (positional) | Text description of the image | all providers |
| `--provider NAME` | Use a specific provider | all |
| `--size WxH` / `--size 2K` | Output dimensions or preset | all |
| `--image PATH/URL` | Single reference image | volcengine, openai, aliyun-bailian |
| `--images P1 P2 ...` | Multiple reference images | same as above |
| `--sequential` | Group / series of related images | volcengine only |
| `--max-images N` | Max images in a sequential group | volcengine only |
| `--no-watermark` | Disable watermark | volcengine only |
| `--stream` | Stream images as they generate | volcengine (requires `aiohttp`) |
| `--n N` | Number of images to generate | openai-compatible |
| `--response-format url\|b64_json` | How the API returns image data | all *¹ |
| `--output-format jpeg\|png` | Output file format | volcengine only |
| `--save-dir PATH` | Custom save directory | all |
| `--json` | Output structured JSON instead of plain paths | all |
| `--validate-config` | Check config.yaml without generating | all |

> *¹ `--response-format`: OpenAI-compatible providers return `url` (default)
> or `b64_json`. volcengine always returns a URL and downloads automatically;
> this flag is accepted but has no effect for volcengine.

### --json output format

When `--json` is used, the script prints a single JSON object to stdout.
All other output goes to stderr. Example:

```json
{
  "model": "doubao-seedream-5-0-260128",
  "created": 1718123456,
  "paths": ["~/Pictures/draw-image/20260605_201530_a1b2c3.jpg"],
  "usage": {
    "generated_images": 1,
    "output_tokens": 0,
    "total_tokens": 0,
    "web_search_calls": 0
  }
}
```

- `paths` — list of absolute paths to saved image files.
- `usage.generated_images` — number of images actually produced.
- `usage.web_search_calls` — non-zero only when the provider used web search.

## Reading the output

The script prints one image absolute path per line (or a single JSON object
if `--json` is used):

```
~/Pictures/draw-image/20260605_201530_a1b2c3.jpg
~/Pictures/draw-image/20260605_201530_d4e5f6.jpg
```

**Do NOT attempt to display or read the image binary.** The user can open it
manually, or you can pass the path to the `vision` skill for analysis.

If the script exits non-zero with an error, see the **Errors** section below.

## Adding a new provider

If the user wants to add a provider that isn't in `config.yaml`:

1. Have the user download the provider's API PDF documentation.
2. Run:
   ```bash
   python "<skill-dir>/scripts/auto_add_provider.py" "<path-to-pdf>" --provider-name <shortname>
   ```
3. The script emits a YAML block with TODO markers. Read the PDF yourself
   (or ask the user) to fill in the TODOs.
4. Append the completed block to `<skill-dir>/config.yaml`.
5. Run `python "<skill-dir>/scripts/draw.py" --validate-config` to confirm.

The script never silently overwrites `config.yaml`. Use `--apply --yes`
only when the user explicitly says "go ahead and write it".

## Configuration overview

The user edits one file: `<skill-dir>/config.yaml`. Three providers ship
enabled with placeholder config:

| Provider | Type | API Key env var |
|---|---|---|
| volcengine | volcengine (built-in) | `ARK_API_KEY` |
| openai | openai-compatible | `OPENAI_API_KEY` |
| aliyun-bailian | aliyun-bailian (built-in) | `ALIYUN_BAILIAN_API_KEY` |

`api_key: ${VAR_NAME}` means "use the value of the matching environment
variable" — keys never have to live in the file itself.

## Errors

All errors are subclasses of `GenerateError`. They print a friendly message
and exit with a non-zero code. Never panic; just relay the message to the
user and suggest the next step.

| Exception | HTTP | Likely cause | User action |
|---|---|---|---|
| `InvalidParameterError` | 400 | size / prompt / model_id wrong | Read the message; fix the call |
| `AuthenticationError` | 401/403 | bad/expired key, or model not authorized | Check the API key, ensure the model is enabled |
| `NotFoundError` | 404 | wrong model id or endpoint URL | Re-check `model:` and `base_url:` in config.yaml |
| `QuotaExceededError` | 402/403 | out of credits | Top up the account |
| `RateLimitError` | 429 | too many requests | Wait, or lower `--max-images` |
| `SensitiveContentError` | varies | prompt blocked by moderation | Rephrase the prompt |
| `InternalServerError` | 5xx | provider's bug | Retry; if persistent, file a ticket with the provider |

**API keys are never printed in error messages.** The skill masks them to
`first4***last4` (or `***` if too short) in any log output.

## Files you should know about

- `SKILL.md` (this file) — you are here
- `config.yaml` — the user edits this; you do not
- `config.example.yaml` — clean template, safe to commit
- `references/provider-schema.md` — full YAML schema for a provider
- `references/adding-a-provider.md` — long-form guide for adding providers
- `references/providers/<name>.md` — per-provider notes (volcengine, openai, aliyun-bailian, comfyui)
- `scripts/draw.py` — main CLI
- `scripts/validate_config.py` — pre-flight check
- `scripts/auto_add_provider.py` — PDF -> YAML bridge
- `lib/` — internal Python library (you should not need to import this directly)
