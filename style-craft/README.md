# style-craft — Writing Style Workshop for AI Agents

> **中文读者：完整中文教程见 [README_zh.md](README_zh.md)。**

A Claude Code / OpenClaw / Codex skill: three coordinated groups that form a closed
loop for writing style — **guide writing -> learn & distill -> audit & condense**.
Each group works standalone, but they are strongest when used together.

```
Group 2 distills a style profile --> Group 1 writes with that profile
                                            |
                                     output --> Group 3 audits it
                                            |
                              found patterns --> feed back to Group 2
                                            |
                              profile upgraded --> Group 1 gets sharper
```

---

## The Three Groups

| You want to... | Use | Entry |
|---|---|---|
| "Write X in style Y", "write an official/technical/essay piece", "draft a WeChat post" | **Group 1** Writing guidance | `references/group1-guide/` |
| "Learn/distill this style", "analyze the author's voice", "build my style profile" | **Group 2** Learning & distillation | `references/group2-learn/` |
| "Audit this text", "condense this", "remove the AI flavor", "this reads too AI" | **Group 3** Audit & condense | `references/group3-audit/` |

### Group 1 — Writing Style Guidance

Style packs loaded by **genre** and **scenario** (two orthogonal dimensions).
A "technical WeChat article" loads `genres/technical.md` + `scenarios/gongzhonghao.md`
(scenario wins on rule conflicts).

- **Genres** (`genres/`): gongwen (official), technical, essay, gongzhonghao (WeChat),
  academic, novel.
- **Scenarios** (`scenarios/`): email, speech, marketing, docs/README.
- **Shared framework**: `_dimensions.md` — a 1-10 Voice Dimensions scale that all
  genre packs are defined against, so Groups 2 and 3 can measure against the same axes.

### Group 2 — Learning & Distilling Style

Dual-track design; the two tracks are meant to work together:

- **A. Methodology** (`methodology.md`) — framework-level manual distillation:
  what dimensions a style has, how to read samples, how to derive rules. Good at
  deep style (rhythm, imagery density, emotional curve) and cold start.
- **B. Auto-distillation scripts** (`scripts/`) — scale-level automatic learning:
  - `observe.py` — records AI drafts vs. your final edits (zero dependencies).
  - `improve.py` — uses an LLM to diff them, extracts P0/P1/P2-graded rules, and
    writes them back into Group 1's genre packs.

Track B runs inside Track A's dimension framework; Track A's manual rules seed
Track B's cold start; high-confidence auto rules "graduate" back into the
methodology. A handles input (reading samples), B handles output (edit feedback) —
a closed loop.

### Group 3 — Auditing Style & Condensing

Forked from [xtao-sh/de-ai](https://github.com/xtao-sh/de-ai), extended with
positive-profile matching, quantitative audit, and a condensing module.

- `de-ai-tics-zh.md` — **forked verbatim from upstream**: pattern catalog
  (structure / sentence / vocabulary / first-person), fix tables, checklist, 24 cases.
- `audit-checklist.md` — audit workflow: three diagnostic tests (from de-ai) +
  style-conformance quantitative audit (new) + conciseness audit (new).
- `concise-rules.md` — condensing rules: cut redundancy, merge, remove filler,
  raise information density.

Improvements over upstream de-ai: positive style-profile matching (not just a
negative list), a condensing module, quantitative dimension scoring, broader genre
coverage, and feedback loops into Groups 1 and 2.

---

## Installation

Copy the whole directory into your agent's skills folder:

```bash
# Claude Code
cp -r style-craft ~/.claude/skills/style-craft

# OpenClaw
cp -r style-craft ~/.openclaw/skills/style-craft
```

On Windows, copy the folder to `%USERPROFILE%\.claude\skills\style-craft\`.

The skill triggers automatically from its `SKILL.md` frontmatter — no further
configuration. Group 2's `observe.py` is zero-dependency pure Python; `improve.py`
needs an LLM CLI (`claude` preferred, falls back to `llm`, or set `IMPROVE_LLM_CMD`).

---

## Quick Start

Once installed, just talk to your agent — one minimal example per group:

**Group 1 — guided writing:**

> You: 按技术体裁写一篇公众号文章，介绍 SQLite 的 WAL 模式
>
> *(loads `genres/technical.md` + `scenarios/gongzhonghao.md` and writes)*

**Group 2 — learning a style:**

> You: 提炼这段文字的文风，建立我的文风画像 *(paste a sample)*
>
> *(uses `methodology.md` to produce a dimension-scored style profile)*

Or, to accumulate rules automatically from your edits:

```bash
python references/group2-learn/scripts/observe.py   # log AI draft vs. your final
python references/group2-learn/scripts/improve.py   # extract rules, write back
```

**Group 3 — auditing & condensing:**

> You: 这段文字 AI 味太重了，帮我改 *(paste the text)*
>
> *(runs the de-ai pattern scan, returns a rewrite + a change-by-change table)*

> You: 把这段话精简到一半字数
>
> *(applies `concise-rules.md`)*

---

## Project Structure

```
style-craft/
├── SKILL.md                        # agent operations manual + routing table
├── README.md                       # this file (English)
├── README_zh.md                    # Chinese tutorial
├── NOTICE.md                       # fork attribution for upstream projects
├── LICENSE                         # MIT
└── references/
    ├── group1-guide/               # Group 1: writing guidance
    │   ├── _dimensions.md          #   Voice Dimensions 1-10 framework
    │   ├── genres/                 #   6 genre style packs
    │   └── scenarios/              #   4 scenario overlays
    ├── group2-learn/               # Group 2: learning & distillation
    │   ├── methodology.md          #   manual distillation framework
    │   └── scripts/
    │       ├── observe.py          #   record drafts (zero deps)
    │       └── improve.py          #   LLM diff -> graded rules
    └── group3-audit/               # Group 3: audit & condense
        ├── de-ai-tics-zh.md        #   de-AI pattern catalog (forked verbatim)
        ├── audit-checklist.md      #   audit workflow + quantitative audit
        └── concise-rules.md        #   condensing rules
```

---

## Acknowledgements

This skill forks / adapts content from the following upstream projects (both MIT),
with thanks — see [NOTICE.md](NOTICE.md) for the full breakdown:

- **[xtao-sh/de-ai](https://github.com/xtao-sh/de-ai)** — the de-AI pattern catalog
  (`de-ai-tics-zh.md`, kept verbatim) and the three diagnostic tests.
- **[jzOcb/writing-style-skill](https://github.com/jzOcb/writing-style-skill)** —
  the Voice Dimensions 1-10 framework and the observe/improve auto-learning
  mechanism (record drafts -> LLM diff -> P0/P1/P2 grading -> write-back).

The three-group closed-loop design, the genre x scenario orthogonal dispatch, and
the methodology/auto-distillation synergy in Group 2 are original to this repo.

---

## License

MIT. Upstream copyrights remain with their original authors; see NOTICE.md.
