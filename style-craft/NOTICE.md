# NOTICE

本 skill (`style-craft`) 部分内容 fork / 改编自以下上游项目，遵循其 MIT 许可。
原始版权归原作者所有；本仓库的修改与新增内容以 MIT 许可发布。

## 1. xtao-sh/de-ai

- 上游: https://github.com/xtao-sh/de-ai
- 许可: MIT
- Fork 范围:
  - `references/group3-audit/de-ai-tics-zh.md` —— 整份文件 fork 自上游
    `references/de-ai-tics-zh.md`（884 行，含模式目录、修复对照表、
    检查清单、案例存档），**原文保留不加工**。
  - 三条诊断测试（删除 / 换题 / 叠加）改编自上游 `SKILL.md`，写入
    `references/group3-audit/audit-checklist.md`。
- 本仓库在 fork 之外新增的内容（不属于上游）:
  - `references/group3-audit/audit-checklist.md` 中除诊断测试外的
    文风符合度量化审计、精简度审计部分。
  - `references/group3-audit/concise-rules.md`（精简专项规则）。
  - 与第 1 组 / 第 2 组的联动设计。

## 2. jzOcb/writing-style-skill

- 上游: https://github.com/jzOcb/writing-style-skill
- 许可: MIT
- 借鉴范围（非整份 fork，为思想与机制移植）:
  - Voice Dimensions 1-10 分量化框架，改编进
    `references/group1-guide/_dimensions.md`。
  - observe/improve 自动学习机制（记录原稿与终稿 -> LLM diff 提取规则
    -> P0/P1/P2 分级 -> 回写 SKILL.md），移植进
    `references/group2-learn/scripts/observe.py` 与
    `improve.py`。
- 本仓库的修改: 路径检测调整为跨平台（Claude Code / OpenClaw / Codex
  兼容），维度分类与第 2 组方法论对齐，规则回写目标改为第 1 组的
  体裁文风包而非单一 SKILL.md。

## 3. 其他参考（未直接 fork，仅借鉴结构）

- `lout33/writing-style-skill` - 单文件风格画像 + 上下文自动检测结构。
- `software-ai-life/Writing-Style-Skill` - 体裁风格包组织方式。

## 4. 原创部分

本 skill 的三组协同设计（指导 -> 学习 -> 审核闭环）、体裁与场景
正交分组调度、第 2 组方法论与自动提炼的协同关系，为原创。
