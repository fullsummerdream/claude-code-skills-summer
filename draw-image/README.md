# draw-image — AI Image Generation Skill for Claude Code

> **中文用户请阅读 [README_zh.md](README_zh.md)（简体中文完整教程）。**

A Claude Code skill that lets you (or your AI agent) generate images using
your own image-generation API account. One YAML file to configure. One CLI
command to draw. Zero code to write.

**Supported providers:**
[Volcengine ARK (Doubao-Seedream)](https://console.volcengine.com/ark) ·
[OpenAI (GPT-image-1 / DALL·E 3)](https://platform.openai.com) ·
[Aliyun Bailian (Qwen-image)](https://bailian.console.aliyun.com) ·
any OpenAI-compatible service (Replicate, Together, OpenRouter, …)

---

## Quick start (5 minutes)

```bash
# 1. Install Python dependencies
pip install -r requirements.txt

# 2. Run once — auto-creates config.yaml from the template
python scripts/draw.py --validate-config
# → Prints "Created config.yaml from template. Next steps: 1. Edit this file..."

# 3. Open config.yaml, replace ONE api_key line with your real key
#    (or set the matching environment variable — see Step 3 below)

# 4. Validate again
python scripts/draw.py --validate-config
# → "OK: config is valid."

# 5. Draw your first image
python scripts/draw.py "a cat sitting in a window"
# → ~/Pictures/draw-image/20260606_143021_a1b2c3.jpg
```

---

## Step 1 — Prerequisites

| What | How to check | Where to get it |
|---|---|---|
| **Python 3.8+** | `python --version` | [python.org](https://python.org) |
| **An API key** | — | Pick a provider below |

Pick at least one provider and get an API key:

| Provider | Get a key at | Cost model |
|---|---|---|
| Volcengine ARK | [console.volcengine.com → ARK → API Keys](https://console.volcengine.com/ark/region:ark+cn-beijing/openManagement?LLM) | Pay-per-image, ~¥0.10–0.50/image |
| OpenAI | [platform.openai.com → API keys](https://platform.openai.com/api-keys) | Pay-per-image, $0.02–0.08/image |
| Aliyun Bailian | [bailian.console.aliyun.com → API Keys](https://bailian.console.aliyun.com/) | Pay-per-image |

Don't have a key yet? You can still install and validate everything — the
validator will tell you exactly which keys are missing.

---

## Step 2 — Install dependencies

```bash
# From the draw-image/ directory
pip install -r requirements.txt
```

This installs **pyyaml** and **pydantic** (required, ~5 MB total).

| Package | Required? | What it's for |
|---|---|---|
| `pyyaml` | ✅ required | Reading config.yaml |
| `pydantic` | ✅ required | Validating configuration |
| `pypdf` | ⚪ optional | `auto_add_provider.py` (PDF → YAML) |
| `aiohttp` | ⚪ optional | `--stream` (real-time output) |

> **Windows users:** if `pip` isn't found, try `python -m pip install -r requirements.txt`.

---

## Step 3 — Get your API key(s)

### Pick a provider

You only need ONE working provider. The skill ships with three pre-configured.
Pick the one you have an account with.

<details>
<summary><b>Volcengine ARK (火山方舟)</b> — recommended for users in China</summary>

1. Go to [console.volcengine.com](https://console.volcengine.com/).
2. Open **ARK** (方舟) from the service menu.
3. Create an **inference endpoint** (推理接入点) for `Doubao-Seedream-5.0-lite`.
4. Go to **API Key Management** (API Key 管理) → create a key.
5. Copy the key (starts with `ark-`).

The default model `doubao-seedream-5-0-260128` in config.yaml is already
set up for this.
</details>

<details>
<summary><b>OpenAI</b></summary>

1. Go to [platform.openai.com/api-keys](https://platform.openai.com/api-keys).
2. Create a new secret key.
3. Copy the key (starts with `sk-`).
4. Make sure you have credits — image generation is billed separately from
   ChatGPT.
</details>

<details>
<summary><b>Aliyun Bailian (阿里云百炼)</b></summary>

1. Go to [bailian.console.aliyun.com](https://bailian.console.aliyun.com/).
2. Enable the **Qwen-image** (通义万相) model.
3. Create an API key in the console.
4. Copy the key.
</details>

### Fill in the key

Open `config.yaml` in any text editor. Find your provider's block. You have
two options:

**Option A — Environment variable (recommended, safer):**

Leave `api_key: ${ARK_API_KEY}` as-is, and set the variable in your shell:

```bash
# macOS / Linux (add to ~/.bashrc or ~/.zshrc)
export ARK_API_KEY="ark-your-key-here"

# Windows PowerShell
$env:ARK_API_KEY = "ark-your-key-here"

# Windows Command Prompt
set ARK_API_KEY=ark-your-key-here
```

**Option B — Direct (simpler, less safe):**

Replace the placeholder with your real key:

```yaml
volcengine:
  api_key: ark-your-real-key-here    # <-- paste your key
```

> ⚠️ `config.yaml` is in `.gitignore`. It will never be committed. But if you
> choose Option B, don't share the file with anyone.

Repeat for any other providers you want to enable (or leave them as-is —
the validator will warn you about unresolved keys).

---

## Step 4 — Validate

```bash
python scripts/draw.py --validate-config
```

If everything is set up correctly:

```
Loading .../config.yaml...
  default_provider: volcengine
  providers: 3
    - volcengine: type=volcengine, model=doubao-seedream-5-0-260128, api_key=ark-***xxxx
    ...

OK: config is valid.
```

If a key is missing or its env var isn't set, you'll see exactly which one:

```
config.yaml validation failed:
  - providers.volcengine: api_key placeholder(s) not resolved: ${ARK_API_KEY}.
    Set the matching environment variable(s) or edit config.yaml directly.
```

All keys in the output are masked (`ark-***cdef`). The full key is never printed.

---

## Step 5 — Generate your first image

```bash
python scripts/draw.py "a watercolor painting of a cat sitting by a window"
```

The script prints the path of the saved image:

```
/Users/you/Pictures/draw-image/20260606_143021_a1b2c3.jpg
```

Or on Windows:

```
C:\Users\you\Pictures\draw-image\20260606_143021_a1b2c3.jpg
```

**Images are saved to `~/Pictures/draw-image/` by default.** Override with
`--save-dir /path/to/folder`.

---

## Everyday use (with Claude Code)

Once configured, you never touch the command line again. Just talk to Claude
Code:

> **You:** 给我画一只坐在窗边的猫，水彩风格
>
> **Claude Code:** *(invokes draw-image skill)* → `~/Pictures/draw-image/xxx.jpg`
> Done! The image is at `~/Pictures/draw-image/xxx.jpg`.

The [SKILL.md](SKILL.md) frontmatter tells Claude Code when to trigger this
skill. No manual `cd`, no path wrangling — the script finds its own directory
via `__file__`.

To use a different provider, tell the agent: *"用 OpenAI 画个 logo"* — it will
add `--provider openai`.

---

## CLI reference

```
python scripts/draw.py "prompt" [flags]
```

| Flag | What it does | Works with |
|---|---|---|
| *`prompt`* | Text description (positional, required) | all |
| `--provider NAME` | Pick a provider | all |
| `--size WxH` or `--size 2K` | Output dimensions | all |
| `--image PATH/URL` | Single reference image | all |
| `--images A B C` | Multiple reference images | all |
| `--sequential` | Generate a related group | volcengine only |
| `--max-images N` | Max images in sequential group | volcengine only |
| `--no-watermark` | Disable watermark | volcengine only |
| `--stream` | Stream results in real time | volcengine (needs `aiohttp`) |
| `--n N` | Number of images | openai-compatible |
| `--response-format url\|b64_json` | API response format | all *¹ |
| `--output-format jpeg\|png` | File format on disk | volcengine only |
| `--save-dir PATH` | Custom save location | all |
| `--json` | Output machine-readable JSON | all |
| `--validate-config` | Check config, don't draw | all |

> *¹ `--response-format`: `url` downloads from a URL; `b64_json` decodes inline
> base64. Volcengine always returns URLs and downloads automatically — this flag
> has no effect for volcengine but won't cause an error.

### JSON output

Use `--json` when you need structured, machine-readable output:

```bash
python scripts/draw.py --json "a cat"
```

```json
{
  "model": "doubao-seedream-5-0-260128",
  "created": 1718123456,
  "paths": ["/home/you/Pictures/draw-image/20260606_143021_a1b2c3.jpg"],
  "usage": {
    "generated_images": 1,
    "output_tokens": 0,
    "total_tokens": 0,
    "web_search_calls": 0
  }
}
```

---

## Examples

```bash
# Text-to-image (any provider)
python scripts/draw.py "a cyberpunk city skyline at dusk"

# Change provider
python scripts/draw.py --provider openai "a minimalist logo of a fox"

# Change size
python scripts/draw.py --size 3K "epic mountain landscape"

# Image-to-image (use a reference)
python scripts/draw.py --image ~/cat.jpg "make it an oil painting"

# Multiple reference images (up to 14)
python scripts/draw.py --images ~/a.jpg ~/b.jpg ~/c.jpg "融合这三张图的风格"

# Sequential group generation (volcengine)
python scripts/draw.py --sequential --max-images 4 "four fruit icons"

# Stream results (volcengine, needs aiohttp)
python scripts/draw.py --stream "a series of fantasy landscapes"

# Output JSON for scripts
python scripts/draw.py --json "a cat" | jq .paths[0]

# Override save directory
python scripts/draw.py --save-dir ~/Desktop "a cat"

# PNG output (volcengine)
python scripts/draw.py --output-format png "a cat"

# No watermark (volcengine)
python scripts/draw.py --no-watermark "a cat"
```

---

## Adding more providers

### Method 1: YAML-only (easiest)

If the new provider's API looks like OpenAI's (`POST /v1/images/generations`),
just add a block to `config.yaml`:

```yaml
  my-new-provider:
    type: openai-compatible
    base_url: https://api.myprovider.com/v1
    api_key: ${MYPROV_API_KEY}
    model: their-model-id
    default_size: 1024x1024
```

If the provider uses different field names, map them:

```yaml
    request_fields:
      prompt: your_prompt_field
      size: dimensions
    image_field: image_urls       # if they use a different key for references
    multi_image: true             # if they always want image as a list
```

Run `python scripts/draw.py --validate-config` to check. Done — no Python
code required.

### Method 2: PDF → YAML (semi-automatic)

If you have the provider's API documentation as a PDF:

```bash
python scripts/auto_add_provider.py path/to/api-docs.pdf --provider-name myprov
```

The script prints a YAML block with all the fields it could extract, plus
`TODO_xxx` markers for things you need to fill in.

> ⚠️ **Scanned or multi-column PDFs will extract poorly** (most fields show as
> `TODO_xxx`). Prefer finding the API's online documentation or a plain-text
> reference and providing that directly to your AI agent.

To append the block directly to config.yaml:

```bash
python scripts/auto_add_provider.py path/to/api-docs.pdf --provider-name myprov --apply --yes
```

### Method 3: Custom Python provider (for exotic APIs)

If the provider uses websockets, message queues, or other non-HTTP patterns,
drop a Python file in `lib/providers/`. See the [provider schema](references/provider-schema.md)
and [adding-a-provider guide](references/adding-a-provider.md) for details.

---

## Where images are saved

| Platform | Default path |
|---|---|
| Windows | `C:\Users\<you>\Pictures\draw-image\` |
| macOS | `/Users/<you>/Pictures/draw-image/` |
| Linux | `/home/<you>/Pictures/draw-image/` |

Filenames: `YYYYMMDD_HHMMSS_01_xxxxxx.jpg` (timestamp + index + random suffix).

To change the save location, either:

- Set `save_dir` per-provider in `config.yaml`, or
- Use `--save-dir /custom/path` on the CLI.

---

## Security

- **Keys are never in chat history.** Use `api_key: ${ENV_VAR}` — the key lives
  in your shell, not in any file.
- **`config.yaml` is `.gitignore`'d.** Only `config.example.yaml` (with
  placeholders) is safe to commit.
- **Error messages mask keys.** Any API key that appears in an error is
  truncated to `first4***last4` (e.g. `ark-***cdef`).
- **Auto-copy warns you.** If `config.yaml` doesn't exist and the script
  creates it from the template, it prints a warning telling you to edit it
  before re-running.

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `python: command not found` | Python not installed or not in PATH | Install Python 3.8+ from [python.org](https://python.org) |
| `ModuleNotFoundError: No module named 'pydantic'` | Dependencies not installed | `pip install -r requirements.txt` |
| `config.yaml validation failed: api_key placeholder(s) not resolved` | Env var not set | `export ARK_API_KEY=...` or replace `${ARK_API_KEY}` in config.yaml |
| `Config not found` | config.yaml missing | Run `--validate-config` once (auto-creates from template) |
| `AuthenticationError` | Key invalid or expired | Regenerate the key at your provider's console |
| `NotFoundError` | Wrong model id or base URL | Double-check `model:` and `base_url:` in config.yaml |
| `InvalidParameterError: image size must be at least 3686400 pixels` | Size too small for volcengine | Use `--size 2K` or larger (≥ 3.7M pixels) |
| `SensitiveContentError` | Prompt blocked by moderation | Rephrase the prompt |
| `RateLimitError` | Too many requests | Wait a few seconds and retry |
| `QuotaExceededError` | Out of credits | Top up your account |
| `InternalServerError` | Provider-side bug | Retry; if persistent, contact the provider |
| `Streaming unavailable` (with `--stream`) | aiohttp not installed | `pip install aiohttp` |
| Images not appearing | Wrong save directory | Check `--save-dir` or `save_dir` in config.yaml |

---

## Project structure

```
draw-image/
├── SKILL.md                       # Agent instruction manual
├── README.md                      # This file — human tutorial
├── README_zh.md                   # Chinese version
├── config.yaml                    # Your provider config (gitignored)
├── config.example.yaml            # Clean template (safe to commit)
├── requirements.txt               # Python dependencies
├── .gitignore
├── references/
│   ├── provider-schema.md         # Full YAML field reference
│   ├── adding-a-provider.md       # Detailed provider integration guide
│   └── providers/                 # Per-provider notes
├── scripts/
│   ├── draw.py                    # Main CLI
│   ├── validate_config.py         # Pre-flight config check
│   └── auto_add_provider.py       # PDF → YAML bridge
├── lib/                           # Internal Python library
└── tests/
    └── test_self.py               # Self-test suite (15 tests, no network)
```

---

## License

MIT.
