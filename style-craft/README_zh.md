# style-craft — 文风工坊 Skill

> **English readers: see [README.md](README.md) for the English version.**

一个 Claude Code / OpenClaw / Codex 技能插件：三组协同的文风工坊——
**指导写作 -> 学习提炼 -> 审核精简**，形成闭环。
每组可独立使用，但联合使用效果最佳。

```
第 2 组提炼出文风画像 → 第 1 组用画像指导写作
                              ↓
                       产出文本 → 第 3 组审核
                              ↓
                   发现问题模式 → 反哺第 2 组维度
                              ↓
                      画像升级 → 第 1 组更准
```

---

## 三组功能一览

| 你想做什么 | 用哪组 | 入口 |
|---|---|---|
| "用 X 风格写 Y""按公文/技术/散文写""写一段公众号" | **第 1 组** 写作指导 | `references/group1-guide/` |
| "学习/提炼这段文风""分析作者风格""建立我的文风画像" | **第 2 组** 学习提炼 | `references/group2-learn/` |
| "审核这段文风""精简这段""去 AI 味""这段太 AI 了" | **第 3 组** 审核精简 | `references/group3-audit/` |

### 第 1 组：写作文风指导

按**体裁**与**场景**两个正交维度加载文风包。
一篇"技术公众号文章"同时加载 `genres/technical.md` + `scenarios/gongzhonghao.md`
（规则冲突时场景优先）。

- **体裁**（`genres/`）：公文、技术/教程、散文/随笔、公众号/推文、学术/论文、小说/叙事。
- **场景**（`scenarios/`）：邮件/职场沟通、讲稿/演讲、营销/文案、技术文档/README。
- **通用框架**：`_dimensions.md`——Voice Dimensions 1-10 分量化框架，
  所有体裁文风包都基于这套维度定义，确保第 2/3 组可对照度量。

### 第 2 组：学习提炼文风

双轨设计，两轨必须协同：

- **A. 方法论指南**（`methodology.md`）——框架级手动提炼：文风有哪些维度、
  如何读样本、如何提炼规则。擅长深层文风（节奏、意象密度、情绪曲线）与冷启动。
- **B. 自动提炼脚本**（`scripts/`）——规模级自动学习：
  - `observe.py`——记录 AI 原稿与你的终稿（零依赖纯 Python）。
  - `improve.py`——用 LLM diff 提取规则，P0/P1/P2 分级，回写第 1 组体裁文风包。

B 在 A 的维度框架内执行；A 的手动提炼是 B 的冷启动种子；高置信度自动规则
"毕业"回 methodology.md。A 管输入端（读样本），B 管输出端（改稿反馈）——闭环。

### 第 3 组：审核文风与精简

fork 自 [xtao-sh/de-ai](https://github.com/xtao-sh/de-ai)，扩展了正面画像对照、
量化审计、精简专项。

- `de-ai-tics-zh.md`——**fork 自上游，原文保留**：模式目录（结构层/句式层/
  词汇层/第一人称）、修复对照表、检查清单、24 案例。
- `audit-checklist.md`——审核流程：三条诊断测试（fork 自 de-ai）+
  文风符合度量化审计（新增）+ 精简度审计（新增）。
- `concise-rules.md`——精简专项：删冗余、合并、去垫话、提信息密度。

相对上游 de-ai 的改进：加了正面画像对照（不再只有负面清单）、精简专项、
维度量化审计、更广的体裁覆盖，以及与第 1/2 组的反哺联动。

---

## 安装

把整个目录复制到你的 agent 的 skills 目录：

```bash
# Claude Code
cp -r style-craft ~/.claude/skills/style-craft

# OpenClaw
cp -r style-craft ~/.openclaw/skills/style-craft
```

Windows 上把文件夹复制到 `%USERPROFILE%\.claude\skills\style-craft\`。

skill 会根据 `SKILL.md` 的 frontmatter 自动触发，无需额外配置。
第 2 组的 `observe.py` 是零依赖纯 Python；`improve.py` 需要 LLM CLI
（优先 `claude`，回退 `llm`，也可用 `IMPROVE_LLM_CMD` 环境变量自定义）。

---

## 快速开始

装好后直接跟 agent 说话即可——每组一个最小用例：

**第 1 组——指导写作：**

> 你：按技术体裁写一篇公众号文章，介绍 SQLite 的 WAL 模式
>
> *（自动加载 `genres/technical.md` + `scenarios/gongzhonghao.md` 写作）*

**第 2 组——提炼文风：**

> 你：提炼这段文字的文风，建立我的文风画像 *（粘贴一段样本）*
>
> *（按 `methodology.md` 产出带维度评分的文风画像）*

或者从你的改稿中自动积累规则：

```bash
python references/group2-learn/scripts/observe.py   # 记录 AI 原稿与你的终稿
python references/group2-learn/scripts/improve.py   # 提取规则并回写文风包
```

**第 3 组——审核精简：**

> 你：这段文字 AI 味太重了，帮我改 *（粘贴文本）*
>
> *（跑 de-ai 模式扫描，返回改写稿 + 逐处修改对照表）*

> 你：把这段话精简到一半字数
>
> *（应用 `concise-rules.md`）*

---

## 目录结构

```
style-craft/
├── SKILL.md                        # agent 操作手册 + 三组路由表
├── README.md                       # 英文说明
├── README_zh.md                    # 中文说明（本文件）
├── NOTICE.md                       # 上游 fork 标注
├── LICENSE                         # MIT
└── references/
    ├── group1-guide/               # 第 1 组：写作指导
    │   ├── _dimensions.md          #   Voice Dimensions 1-10 量化框架
    │   ├── genres/                 #   6 个体裁文风包
    │   └── scenarios/              #   4 个场景适配包
    ├── group2-learn/               # 第 2 组：学习提炼
    │   ├── methodology.md          #   手动提炼方法论框架
    │   └── scripts/
    │       ├── observe.py          #   记录原稿/终稿（零依赖）
    │       └── improve.py          #   LLM diff -> 分级规则
    └── group3-audit/               # 第 3 组：审核精简
        ├── de-ai-tics-zh.md        #   去 AI 味模式目录（fork 原文保留）
        ├── audit-checklist.md      #   审核流程 + 量化审计
        └── concise-rules.md        #   精简专项规则
```

---

## 致谢上游

本 skill fork / 改编自以下上游项目（均为 MIT 许可），谨致谢意——
完整明细见 [NOTICE.md](NOTICE.md)：

- **[xtao-sh/de-ai](https://github.com/xtao-sh/de-ai)**——去 AI 味模式目录
  （`de-ai-tics-zh.md`，原文保留）与三条诊断测试（删除/换题/叠加）。
- **[jzOcb/writing-style-skill](https://github.com/jzOcb/writing-style-skill)**——
  Voice Dimensions 1-10 量化框架，以及 observe/improve 自动学习机制
  （记录原稿终稿 -> LLM diff -> P0/P1/P2 分级 -> 回写）。

三组协同闭环设计、体裁 x 场景正交调度、第 2 组方法论与自动提炼的协同关系，
为本仓库原创。

---

## 许可证

MIT。上游内容的原始版权归原作者所有，详见 NOTICE.md。
