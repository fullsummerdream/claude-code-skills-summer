#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""improve.py — 第 2 组 B 轨：从 original/final diff 提炼写作规则，回写第 1 组文风包。

借鉴 jzOcb/writing-style-skill 的 improve.py，零依赖跨平台（Windows/macOS/Linux）。
数据流：observe.py JSONL 日志 → LLM 分析 diff → P0/P1/P2 提案 → 回写 genres/<content_type>.md。

observe.py 日志格式（每行一个 JSON 对象；分次对按 id 配对）：
    完整对：{"id": "abc", "ts": "...", "content_type": "technical", "original": "...", "final": "..."}
    分次对：{"id": "abc", "kind": "original"|"final", "text": "...", ...}

存储基目录（同 observe.py）：$SKILL_LOG_DIR > $STYLE_CRAFT_HOME > ~/.claude/style-craft
    > ~/.openclaw/style-craft > ~/.codex/style-craft > ~/.style-craft（兜底）。
    LLM CLI：$IMPROVE_LLM_CMD > claude -p > llm。

用法：extract [--days N]（默认7，0=全部）| auto --skill <path>（cron）| show | apply <id> | rollback
"""
import argparse
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

# 10 维度键名，与 group1-guide/_dimensions.md 一致（运行时会尝试从该文件动态解析）
DIMENSIONS: list[tuple[str, str]] = [
    ("formal_casual", "正式 ↔ 随意"), ("technical_accessible", "技术密集 ↔ 通俗易懂"),
    ("serious_playful", "严肃 ↔ 活泼"), ("concise_elaborate", "简洁 ↔ 详尽"),
    ("reserved_expressive", "克制 ↔ 外放"), ("abstract_concrete", "抽象 ↔ 具体"),
    ("declarative_narrative", "陈述 ↔ 叙事"), ("plain_imagery", "平实 ↔ 意象"),
    ("rhythm_flat", "节奏平 ↔ 节奏强"), ("impersonal_personal", "无人称 ↔ 人称密集"),
]
SECTION_SEARCH = {"基础规则": "### 基础规则", "禁止词": "### 禁止词", "句式偏好": "### 句式偏好"}
SECTION_CANONICAL = {"基础规则": "### 基础规则", "禁止词": "### 禁止词/禁止句式", "句式偏好": "### 句式偏好"}
CONFIDENCE_RANK = {"P0": 3, "P1": 2, "P2": 1}
PROPOSALS_NAME = "proposals.json"
LLM_TIMEOUT = 300
MAX_TEXT_CHARS = 4000
MAX_PAIRS_PER_CALL = 10

def storage_root() -> Path:
    """跨平台存储基目录（与 observe.py 共享同一逻辑）：$SKILL_LOG_DIR > $STYLE_CRAFT_HOME > ~/.claude/style-craft > ~/.openclaw/style-craft > ~/.codex/style-craft > 兜底。"""
    for var in ("SKILL_LOG_DIR", "STYLE_CRAFT_HOME"):
        env = os.environ.get(var, "").strip()
        if env:
            return Path(env).expanduser()
    for name in (".claude", ".openclaw", ".codex"):
        if (base := Path.home() / name).is_dir():
            return base / "style-craft"
    return Path.home() / ".style-craft"

def skill_root(override: Optional[str] = None) -> Path:
    """style-craft 技能根目录：--skill 覆盖，否则按脚本位置推断（scripts/ 上三级）。"""
    return Path(override).expanduser().resolve() if override else Path(__file__).resolve().parents[3]

def load_dimension_keys(root: Path) -> list[str]:
    """从 group1-guide/_dimensions.md 解析维度键名（保序去重）；失败回退内置 10 键。"""
    path = root / "references" / "group1-guide" / "_dimensions.md"
    text = path.read_text(encoding="utf-8") if path.is_file() else ""
    return list(dict.fromkeys(re.findall(r"`([a-z][a-z_]+)`", text))) or [k for k, _ in DIMENSIONS]

def _parse_ts(value: Any) -> Optional[datetime]:
    """宽松解析 ISO 时间戳（容忍 Z 后缀与时区）；失败返回 None。"""
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(str(value).strip().replace("Z", "+00:00"))
        return dt.astimezone().replace(tzinfo=None) if dt.tzinfo else dt
    except ValueError:
        return None

def load_pairs(log_path: Path, days: int) -> tuple[list[dict], int]:
    """读 JSONL 日志，返回 (已配对的 original/final 列表, 坏行数)。days<=0 不过滤时间。"""
    if not log_path.is_file():
        return [], 0
    cutoff = datetime.now() - timedelta(days=days) if days > 0 else None
    records, bad = [], 0
    for line in log_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            bad += 1
            continue
        ts = _parse_ts(rec.get("ts") or rec.get("timestamp"))
        if cutoff and ts and ts < cutoff:
            continue
        rec["_ts"] = ts.isoformat(timespec="seconds") if ts else ""
        records.append(rec)
    pairs, order = {}, []
    for rec in records:
        rid = str(rec.get("id") or rec.get("hash") or hashlib.sha1(
            json.dumps(rec, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()[:8])
        slot = pairs.setdefault(rid, {"id": rid, "content_type": "default",
                                      "original": "", "final": "", "ts": rec.get("_ts", "")})
        if rid not in order:
            order.append(rid)
        if rec.get("content_type"):
            slot["content_type"] = str(rec["content_type"])
        if rec.get("original") and rec.get("final"):
            slot["original"], slot["final"] = str(rec["original"]), str(rec["final"])
        elif (kind := str(rec.get("kind") or rec.get("role") or rec.get("type") or "").lower()) in ("original", "final"):
            slot[kind] = str(rec.get("text") or rec.get("content") or "")
    return [pairs[r] for r in order if pairs[r]["original"] and pairs[r]["final"]], bad

def detect_llm_cmd() -> Optional[list[str]]:
    """按优先级检测 LLM CLI：$IMPROVE_LLM_CMD > claude -p > llm。"""
    env = os.environ.get("IMPROVE_LLM_CMD", "").strip()
    if env:
        return shlex.split(env, posix=(os.name != "nt"))
    for name, args in (("claude", ["-p"]), ("llm", [])):
        if path := shutil.which(name):
            return [path, *args]
    return None

def call_llm(cmd: list[str], prompt: str) -> str:
    """prompt 经 stdin 传入，读 stdout；失败抛带友好信息的 RuntimeError。"""
    if os.name == "nt" and str(cmd[0]).lower().endswith((".cmd", ".bat")):
        cmd = ["cmd.exe", "/c", *cmd]  # Windows 上 .cmd/.bat 不能直接 CreateProcess
    try:
        proc = subprocess.run(cmd, input=prompt, capture_output=True, text=True,
                              encoding="utf-8", errors="replace", timeout=LLM_TIMEOUT)
    except FileNotFoundError as exc:
        raise RuntimeError(f"LLM CLI 不存在：{cmd[0]}（可用 IMPROVE_LLM_CMD 指定）") from exc
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"LLM CLI 超时（>{LLM_TIMEOUT}s）") from exc
    if proc.returncode != 0:
        tail = (proc.stderr or "").strip()[-300:]
        raise RuntimeError(f"LLM CLI 退出码 {proc.returncode}：{tail or '无 stderr 输出'}")
    return proc.stdout

def parse_rules_json(raw: str) -> list[dict]:
    """从 LLM 输出解析 JSON 数组（容忍解释文字与代码围栏）；失败抛 RuntimeError。"""
    text = raw.strip()
    for candidate in (text, text[text.find("["): text.rfind("]") + 1]):
        if not candidate:
            continue
        try:
            data = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(data, list):
            return [r for r in data if isinstance(r, dict)]
    raise RuntimeError("LLM 输出不是可解析的 JSON 数组")

def _clip(text: str, limit: int = MAX_TEXT_CHARS) -> str:
    """截断超长文本，避免 prompt 爆炸。"""
    text = text.strip()
    return text if len(text) <= limit else text[:limit] + f"\n……（截断，原文共 {len(text)} 字）"

def build_prompt(pairs: list[dict], content_type: str, dim_keys: list[str]) -> str:
    """构造提炼 prompt：10 维度键名 + original/final 对照 + 严格 JSON 输出约束。"""
    labels = dict(DIMENSIONS)
    dim_block = "\n".join(f"- {k}: {labels.get(k, '')}".rstrip() for k in dim_keys)
    samples = "\n\n".join(
        f"=== 样本 {i} ===\n--- AI 原稿 ---\n{_clip(p['original'])}\n--- 用户终稿 ---\n{_clip(p['final'])}"
        for i, p in enumerate(pairs, 1))
    return f"""你是一位中文写作风格分析专家。下面是 {len(pairs)} 对「AI 原稿 → 用户终稿」对照（内容类型：{content_type}）。
用户亲手把原稿改成终稿。你的任务：从改动中提炼可执行的写作规则。
【文风维度框架】每条规则必须归入以下 10 个维度键名之一（dimension 字段只准填键名）：
{dim_block}

【对照样本】
{samples}

【提炼要求】
1. 对比每对原稿/终稿，找出用户反复做出的同一类改动（删某类词、拆长句、加比喻、去感叹号等）。
2. 每条规则必须可执行、可用"是/否"检查（"每句不超过 30 字"可检查，"写得自然些"不可）。
3. confidence 分级：同一模式在 ≥3 对样本中出现 → P0；2 对 → P1；仅 1 对 → P2。
4. rule_type 三选一："基础规则"（正面必须做到）/ "禁止词"（绝不能出现的词或句式）/ "句式偏好"（偏好的句式骨架）。
5. evidence 引用最能说明该模式的 diff 片段（"原稿…… → 终稿……"，总长 ≤ 60 字）。
6. 只输出 JSON 数组本身：不要解释文字，不要 markdown 代码围栏。没有发现稳定模式就输出 []。
【输出格式】
[{{"dimension": "<维度键名>", "rule_type": "基础规则|禁止词|句式偏好", "rule": "<可执行规则>", "evidence": "<diff 片段>", "confidence": "P0|P1|P2"}}]"""

def normalize_rules(items: list[dict], dim_keys: list[str]) -> tuple[list[dict], int]:
    """校验字段、归一 rule_type/confidence、按 (dimension, rule) 去重合并。返回 (规则, 丢弃数)。"""
    merged: dict[tuple[str, str], dict] = {}
    dropped = 0
    for item in items:
        dim = str(item.get("dimension", "")).strip()
        rule = str(item.get("rule", "")).strip()
        if dim not in dim_keys or not rule:
            dropped += 1
            continue
        rtype = str(item.get("rule_type", "")).strip()
        rtype = "禁止词" if rtype.startswith("禁止") else ("句式偏好" if rtype.startswith("句式") else "基础规则")
        conf = c if (c := str(item.get("confidence", "P2")).strip().upper()) in CONFIDENCE_RANK else "P2"
        ev = str(item.get("evidence", "")).strip()
        key = (dim, rule)
        if key in merged:
            old = merged[key]
            if CONFIDENCE_RANK[conf] > CONFIDENCE_RANK[old["confidence"]]:
                old["confidence"] = conf
            if ev and not old["evidence"]:
                old["evidence"] = ev
        else:
            merged[key] = {"dimension": dim, "rule_type": rtype, "rule": rule,
                           "evidence": ev, "confidence": conf, "applied": False}
    return list(merged.values()), dropped

def load_store(path: Path) -> dict:
    """读提案库；文件损坏时备份为 .bad 并重建。"""
    if path.is_file():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict) and isinstance(data.get("proposals"), list):
                return data
        except json.JSONDecodeError:
            pass
        shutil.copy2(path, path.with_suffix(".bad"))
        print(f"警告：{path} 已损坏，备份为 .bad 后重建。", file=sys.stderr)
    return {"proposals": []}

def save_store(path: Path, store: dict) -> None:
    """写提案库（先写临时文件再替换，避免半截写入）。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(store, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)

def extract_proposals(days: int, root: Path, store: dict) -> list[dict]:
    """核心提炼：按 content_type 分组调 LLM，生成提案追加进 store，返回新提案列表。"""
    log_path = storage_root() / "observe.jsonl"
    if not log_path.is_file():
        print(f"未找到观察日志：{log_path}（先用 observe.py 记录原稿/终稿）。")
        return []
    pairs, bad = load_pairs(log_path, days)
    if bad:
        print(f"警告：跳过 {bad} 行无法解析的日志。", file=sys.stderr)
    done = {pid for p in store["proposals"] for pid in p.get("pair_ids", [])}
    fresh = [p for p in pairs if p["id"] not in done]
    if not fresh:
        print(f"没有新的已配对记录（日志：{log_path}）。")
        return []
    cmd = detect_llm_cmd()
    if not cmd:
        print("未检测到 LLM CLI。请设置 IMPROVE_LLM_CMD，或安装 claude / llm。", file=sys.stderr)
        return []
    dim_keys = load_dimension_keys(root)
    groups: dict[str, list[dict]] = {}
    for p in fresh:
        groups.setdefault(p["content_type"], []).append(p)
    created: list[dict] = []
    for ctype, group in sorted(groups.items()):
        items: list[dict] = []
        for i in range(0, len(group), MAX_PAIRS_PER_CALL):
            try:
                items.extend(parse_rules_json(call_llm(
                    cmd, build_prompt(group[i: i + MAX_PAIRS_PER_CALL], ctype, dim_keys))))
            except RuntimeError as exc:
                print(f"警告：{ctype} 第 {i // MAX_PAIRS_PER_CALL + 1} 批提炼失败：{exc}", file=sys.stderr)
        rules, dropped = normalize_rules(items, dim_keys)
        if dropped:
            print(f"警告：{ctype} 丢弃 {dropped} 条不合规规则（维度键名非法或规则为空）。", file=sys.stderr)
        if not rules:
            print(f"{ctype}：未提炼出有效规则。")
            continue
        seed = f"{ctype}|{sorted(p['id'] for p in group)}|{datetime.now().isoformat()}"
        pid = "p_" + hashlib.sha1(seed.encode("utf-8")).hexdigest()[:8]
        pack = root / "references" / "group1-guide" / "genres" / f"{ctype}.md"
        if not pack.is_file():
            avail = sorted(p.stem for p in pack.parent.glob("*.md")) if pack.parent.is_dir() else []
            print(f"警告：文风包不存在：{pack}（可用：{', '.join(avail) or '无'}）", file=sys.stderr)
        prop = {"id": pid, "created": datetime.now().isoformat(timespec="seconds"),
                "content_type": ctype, "status": "pending", "applied_at": "", "backup": "",
                "pack": str(pack), "pair_ids": [p["id"] for p in group], "rules": rules}
        store["proposals"].append(prop)
        created.append(prop)
    return created

def _format_rule(rule: dict) -> str:
    """单条规则的 markdown 行：维度标签 + 置信度 + 规则 + 证据（≤80 字）。"""
    ev = rule.get("evidence", "")
    suffix = f"（证据：{ev if len(ev) <= 80 else ev[:77] + '...'}）" if ev else ""
    return f"- 【{rule['dimension']} · {rule['confidence']}】{rule['rule']}{suffix}"

def insert_rules(pack: Path, rules: list[dict], proposal_id: str) -> int:
    """把规则按 rule_type 写入"写作规则"对应小节，小节内按维度归类排序。返回写入条数。"""
    lines = pack.read_text(encoding="utf-8").splitlines()
    idx = [i for i, ln in enumerate(lines) if ln.strip() == "## 写作规则"]
    if idx:
        sec_start = idx[0]
    else:
        lines += ["", "## 写作规则"]
        sec_start = len(lines) - 1
    sec_end = next((i for i in range(sec_start + 1, len(lines)) if lines[i].startswith("## ")), len(lines))
    by_type: dict[str, list[dict]] = {}
    for rule in rules:
        by_type.setdefault(rule["rule_type"], []).append(rule)
    edits: list[tuple[int, list[str]]] = []
    for rtype, group in by_type.items():
        block = [f"<!-- improve.py 提案 {proposal_id} -->"]
        block += [_format_rule(r) for r in sorted(group, key=lambda x: x["dimension"])]
        sub = next((i for i in range(sec_start + 1, sec_end)
                    if lines[i].strip().startswith(SECTION_SEARCH[rtype])), None)
        if sub is None:  # 小节不存在：在"写作规则"末尾新建
            edits.append((sec_end, ["", SECTION_CANONICAL[rtype], ""] + block))
            continue
        sub_end = next((i for i in range(sub + 1, sec_end)
                        if lines[i].startswith(("### ", "## "))), sec_end)
        pos = sub_end
        while pos > sub + 1 and not lines[pos - 1].strip():  # 跳过小节尾部空行
            pos -= 1
        edits.append((pos, [""] + block))
    for pos, block in sorted(edits, key=lambda e: e[0], reverse=True):  # 自底向上插入防移位
        lines[pos:pos] = block + [""]
    pack.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return len(rules)

def apply_proposal(prop: dict, only_p0: bool = False) -> int:
    """应用提案：备份目标文风包 → 写入规则 → 更新状态。返回写入条数。"""
    rules = [r for r in prop["rules"] if not r.get("applied") and (not only_p0 or r["confidence"] == "P0")]
    if not rules:
        return 0
    pack = Path(prop["pack"])
    if not pack.is_file():
        raise RuntimeError(f"目标文风包不存在：{pack}")
    backup = storage_root() / "backups" / f"{pack.stem}.{datetime.now():%Y%m%d_%H%M%S}.md"
    backup.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(pack, backup)
    inserted = insert_rules(pack, rules, prop["id"])
    for r in rules:
        r["applied"] = True
    prop.update(status="applied", applied_at=datetime.now().isoformat(timespec="seconds"), backup=str(backup))
    return inserted

def _print_proposal(prop: dict) -> None:
    """打印单个提案的摘要与规则明细。"""
    counts = {c: sum(1 for r in prop["rules"] if r["confidence"] == c) for c in ("P0", "P1", "P2")}
    applied_n = sum(1 for r in prop["rules"] if r.get("applied"))
    print(f"\n提案 {prop['id']}  [{prop['status']}]  {prop['created']}  content_type={prop['content_type']}")
    print(f"  规则 {len(prop['rules'])} 条（P0×{counts['P0']} P1×{counts['P1']} P2×{counts['P2']}，"
          f"已应用 {applied_n}）  来源样本 {len(prop['pair_ids'])} 对  目标：{prop['pack']}")
    for r in prop["rules"]:
        mark = "✓" if r.get("applied") else " "
        print(f"  [{mark}][{r['confidence']}]【{r['dimension']} / {r['rule_type']}】{r['rule']}")
        if r.get("evidence"):
            print(f"        证据：{r['evidence']}")

def cmd_extract(args: argparse.Namespace) -> int:
    """extract：读日志 → 配对 → LLM 提炼 → 存提案。"""
    store_path = storage_root() / PROPOSALS_NAME
    store = load_store(store_path)
    created = extract_proposals(args.days, skill_root(), store)
    if not created:
        return 1
    save_store(store_path, store)
    for prop in created:
        _print_proposal(prop)
    print("\n提示：show 查看提案，apply <proposal_id> 应用，auto 自动应用 P0。")
    return 0

def cmd_auto(args: argparse.Namespace) -> int:
    """auto：提炼 + 自动应用 P0 规则（cron 用）。"""
    root = skill_root(args.skill)
    if not (root / "references" / "group1-guide" / "genres").is_dir():
        print(f"--skill 路径不含 references/group1-guide/genres：{root}", file=sys.stderr)
        return 1
    store_path = storage_root() / PROPOSALS_NAME
    store = load_store(store_path)
    created = extract_proposals(args.days, root, store)
    total = 0
    for prop in created:
        try:
            total += apply_proposal(prop, only_p0=True)
        except RuntimeError as exc:
            print(f"警告：{prop['id']} 应用失败：{exc}", file=sys.stderr)
    save_store(store_path, store)
    print(f"auto 完成：新增提案 {len(created)} 个，自动应用 P0 规则 {total} 条。")
    return 0

def cmd_show() -> int:
    """show：列出所有提案。"""
    store = load_store(storage_root() / PROPOSALS_NAME)
    if not store["proposals"]:
        print("暂无提案。先运行 extract 提炼规则。")
        return 0
    for prop in store["proposals"]:
        _print_proposal(prop)
    return 0

def cmd_apply(args: argparse.Namespace) -> int:
    """apply <proposal_id>：应用指定提案（支持唯一前缀），自动备份。"""
    store_path = storage_root() / PROPOSALS_NAME
    store = load_store(store_path)
    matches = [p for p in store["proposals"] if p["id"].startswith(args.proposal_id)]
    if len(matches) != 1:
        print(f"提案 {args.proposal_id} {'不存在' if not matches else '不唯一'}，用 show 查看。", file=sys.stderr)
        return 1
    try:
        n = apply_proposal(matches[0])
    except RuntimeError as exc:
        print(f"应用失败：{exc}", file=sys.stderr)
        return 1
    if n == 0:
        print(f"提案 {matches[0]['id']} 没有待应用的规则。")
        return 0
    save_store(store_path, store)
    print(f"已应用提案 {matches[0]['id']}：写入 {n} 条规则 → {matches[0]['pack']}（备份：{matches[0]['backup']}）")
    return 0

def cmd_rollback() -> int:
    """rollback：回滚最近一次应用，从备份恢复目标文风包。"""
    store_path = storage_root() / PROPOSALS_NAME
    store = load_store(store_path)
    applied = [p for p in store["proposals"] if p.get("status") == "applied" and p.get("backup")]
    if not applied:
        print("没有可回滚的应用记录。")
        return 0
    prop = max(applied, key=lambda p: p.get("applied_at", ""))
    backup, pack = Path(prop["backup"]), Path(prop["pack"])
    if not backup.is_file():
        print(f"回滚失败：备份文件已丢失：{backup}", file=sys.stderr)
        return 1
    shutil.copy2(backup, pack)
    for r in prop["rules"]:
        r["applied"] = False
    prop["status"] = "rolledback"
    save_store(store_path, store)
    print(f"已回滚提案 {prop['id']}：{pack.name} 从备份恢复（{backup.name}）。")
    return 0

def main(argv: Optional[list[str]] = None) -> int:
    """CLI 入口。"""
    parser = argparse.ArgumentParser(prog="improve.py",
        description="从 original/final diff 提炼写作规则并回写第 1 组文风包（第 2 组 B 轨）。")
    sub = parser.add_subparsers(dest="command", required=True)
    p_ext = sub.add_parser("extract", help="提炼规则生成提案")
    p_ext.add_argument("--days", type=int, default=7, help="只处理最近 N 天日志，0 = 全部（默认 7）")
    p_auto = sub.add_parser("auto", help="提炼并自动应用 P0 规则（cron 用）")
    p_auto.add_argument("--skill", required=True, help="style-craft 技能目录路径")
    p_auto.add_argument("--days", type=int, default=7, help="同 extract --days")
    sub.add_parser("show", help="列出所有提案")
    p_app = sub.add_parser("apply", help="应用指定提案到目标文风包")
    p_app.add_argument("proposal_id", help="提案 id（支持唯一前缀）")
    sub.add_parser("rollback", help="回滚上次应用")
    args = parser.parse_args(argv)
    handlers = {"extract": cmd_extract, "auto": cmd_auto,
                "show": lambda a: cmd_show(), "apply": cmd_apply, "rollback": lambda a: cmd_rollback()}
    return handlers[args.command](args)

if __name__ == "__main__":
    sys.exit(main())
