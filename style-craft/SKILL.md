---
name: style-craft
description: |
  文风工坊。三组协同的写作文风 skill：(1) 按体裁/场景调用文风指导来写作，
  (2) 学习提炼文风（方法论 + 自动提炼双轨），(3) 审核文风符合度与精简。
  当用户要求"用我的风格写 X""按 X 体裁写""模仿这段文风""提炼/学习某文风"
  "审核这段文风""精简这段文字""去 AI 味""改 AI 味""这段太 AI 了"时使用。
  兼容 Claude Code / OpenClaw / Codex。
license: MIT
---

# style-craft：文风工坊

三组协同：**指导写作 -> 学习提炼 -> 审核精简**，形成闭环。
每组可独立使用，但联合使用效果最佳。

---

## 三组路由

| 用户意图 | 用哪组 | 入口 |
|---|---|---|
| "用 X 风格写 Y""按公文/技术/散文写""写一段公众号" | **第 1 组** 写作指导 | [group1-guide/](references/group1-guide/) |
| "学习/提炼这段文风""分析作者风格""建立我的文风画像" | **第 2 组** 学习提炼 | [group2-learn/](references/group2-learn/) |
| "审核这段文风""精简这段""去 AI 味""这段太 AI 了""改 AI 味" | **第 3 组** 审核精简 | [group3-audit/](references/group3-audit/) |

**闭环协同（不是各自孤立）：**

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

## 第 1 组：写作文风指导

**用途：** AI 写作时调用对应体裁/场景的文风包，按画像写作。

**分组方式：体裁与场景两个正交维度，写作时按需匹配。**
一篇"技术公众号文章"同时加载 `genres/technical.md` + `scenarios/gongzhonghao.md`（规则冲突时场景优先）。

### 体裁（genres/）- 内容类型决定深层文风

| 体裁 | 文件 | 特征 |
|---|---|---|
| 公文 | `genres/gongwen.md` | 规范、庄重、程式化 |
| 技术/教程 | `genres/technical.md` | 准确、分层、可操作 |
| 散文/随笔 | `genres/essay.md` | 自由、有节奏、带意象 |
| 公众号/推文 | `genres/gongzhonghao.md` | 口语、短段、抓人 |
| 学术/论文 | `genres/academic.md` | 严谨、引用、克制 |
| 小说/叙事 | `genres/novel.md` | 场景、对话、节奏 |

### 场景（scenarios/）- 传播场合决定表层适配

| 场景 | 文件 |
|---|---|
| 邮件/职场沟通 | `scenarios/email.md` |
| 讲稿/演讲 | `scenarios/speech.md` |
| 营销/文案 | `scenarios/marketing.md` |
| 技术文档/README | `scenarios/docs.md` |

### 通用框架

- [group1-guide/_dimensions.md](references/group1-guide/_dimensions.md) -- Voice Dimensions 1-10 分量化框架（借鉴 jzOcb）。所有体裁文风包都基于这套维度定义，确保第 2/3 组可对照。

---

## 第 2 组：学习提炼文风

**用途：** 从样本中提炼文风画像，供第 1 组调用。

**双轨设计，必须协同：**

### A. 方法论指南（手动提炼，框架级）

- [group2-learn/methodology.md](references/group2-learn/methodology.md) -- 定义文风有哪些维度、如何读样本、如何提炼规则。是第 1 组的画像来源，也是 B 的提炼 prompt 框架。

**擅长：** 深层文风（节奏、意象密度、情绪曲线、价值观偏好、留白方式）；冷启动；教会用户"怎么读文"的元能力。

### B. 自动提炼脚本（自动学习，规模级）

- [group2-learn/scripts/observe.py](references/group2-learn/scripts/observe.py) -- 记录 AI 原稿与用户终稿（零依赖）。
- [group2-learn/scripts/improve.py](references/group2-learn/scripts/improve.py) -- 用 LLM diff 提取规则，P0/P1/P2 分级，回写第 1 组体裁文风包（借鉴 jzOcb）。

**擅长：** 表层文风（禁止词、句式、格式）；规模化积累；持续迭代。

### A 与 B 的协同关系（关键，不是各自孤立）

1. **B 在 A 的维度框架内执行** -- improve.py 的提取 prompt 使用 methodology.md 定义的维度分类，规则不碎片化。
2. **A 的手动提炼 = B 的冷启动种子** -- 新用户先用 A 读几篇样本得到种子规则，B 在此基础上自动补充。
3. **B 的新规则回填到 A** -- 高置信度自动规则"毕业"进 methodology.md，让 A 也跟着进化，不静止。
4. **A 管输入端（读样本），B 管输出端（改稿反馈）**，闭环。

---

## 第 3 组：审核文风与精简

**用途：** 审核文本是否符合目标文风画像，并做精简。
fork 自 [xtao-sh/de-ai](https://github.com/xtao-sh/de-ai)，扩展了正面画像对照、量化审计、精简专项。

### 入口

- [group3-audit/de-ai-tics-zh.md](references/group3-audit/de-ai-tics-zh.md) -- **fork 自上游，原文保留**。模式目录（结构层/句式层/词汇层/第一人称）、修复对照表、检查清单、24 案例。
- [group3-audit/audit-checklist.md](references/group3-audit/audit-checklist.md) -- 审核流程：三条诊断测试（fork 自 de-ai）+ 文风符合度量化审计（新增）+ 精简度审计（新增）。
- [group3-audit/concise-rules.md](references/group3-audit/concise-rules.md) -- 精简专项规则（删冗余/合并/去垫话/信息密度，新增）。

### 与 de-ai 的差异（改进点）

1. **加了正面画像** -- de-ai 只有负面清单，本组对照第 1 组文风画像做符合度审计。
2. **加了精简专项** -- de-ai 不做字数压缩，本组有 concise-rules.md。
3. **加了量化审计** -- 借鉴 jzOcb Voice Dimensions 做维度量化对照。
4. **扩展体裁** -- de-ai 主攻幻灯片/讲座/公众号，本组覆盖公文/技术/学术/散文/邮件等。
5. **桥接第 2 组** -- 审核发现的 AI 味模式反哺第 2 组提炼维度。

### de-ai 的核心可学习点（建议先读）

1. **三条诊断测试**（删除/换题/叠加）-- 覆盖未知模式，比清单强。
2. **分层扫描**（结构层 -> 句式层 -> 词汇层 -> 第一人称）-- 审核有路径。
3. **"压缩 ≠ 去除"** -- 看句式骨架不看字数。
4. **分体裁严格度** -- 幻灯片最严 / 报告宽松。
5. **案例驱动 + 维护机制** -- 发现新模式就追加，skill 会长大。
6. **输出格式** -- 改写稿 + 修改对照（改了哪几处/属哪类/为什么）。

---

## 平台兼容性

本 skill 兼容 Claude Code / OpenClaw / Codex：

- **SKILL.md 路径**：`<skill-dir>` 表示本 SKILL.md 所在目录。
  - Claude Code: `~/.claude/skills/style-craft/`
  - OpenClaw: `~/.openclaw/skills/style-craft/`
  - Codex: 按平台约定
- **第 2 组脚本**：observe.py 零依赖纯 Python，跨平台。
  improve.py 依赖 LLM CLI（优先 `claude`，回退 `llm`，可用 `IMPROVE_LLM_CMD` 环境变量自定义）。
- **路径检测**：脚本自动检测存储基目录（环境变量 > ~/.claude > ~/.openclaw > ~/.codex），不写死。

---

## 触发词速查

| 触发词 | 调用 |
|---|---|
| "用我的风格写""按 X 体裁写""写一段 X" | 第 1 组 |
| "模仿这段文风""像 X 一样写" | 第 1 组（先第 2 组提炼画像） |
| "提炼这段文风""学习作者风格""建立我的文风画像" | 第 2 组 A |
| "记录原稿/终稿""提取规则""自动学习我的修改" | 第 2 组 B |
| "审核这段""这段文风怎么样""像不像 X 写的" | 第 3 组 |
| "精简这段""这段太啰嗦""压缩字数" | 第 3 组 concise-rules |
| "去 AI 味""改 AI 味""这段太 AI 了""让中文更自然" | 第 3 组 de-ai-tics |
