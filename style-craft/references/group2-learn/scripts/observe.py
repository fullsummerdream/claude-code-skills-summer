#!/usr/bin/env python3
"""observe.py — 记录 AI 原稿与用户终稿（style-craft 第 2 组 B 轨）。

零依赖纯标准库，跨平台（Windows / macOS / Linux）。

用法：
    python observe.py record-original <file> --account <账号> --content-type <类型>
    python observe.py record-final <file> --match <hash>
    python observe.py list

日志为 JSONL，每行一条记录：
    {"type": "original"|"final", "hash": "...", "path": "...",
     "account": "...", "content_type": "...", "timestamp": "...",
     "content": "<文件全文>"}
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime
from pathlib import Path

LOG_FILENAME = "observe.jsonl"

def storage_root() -> Path:
    """跨平台存储基目录（与 improve.py 共享同一逻辑，保证日志能读到）。

    优先级：$SKILL_LOG_DIR > $STYLE_CRAFT_HOME > ~/.claude/style-craft
    > ~/.openclaw/style-craft > ~/.codex/style-craft > ~/.style-craft（兜底）。
    """
    for var in ("SKILL_LOG_DIR", "STYLE_CRAFT_HOME"):
        env = os.environ.get(var, "").strip()
        if env:
            return Path(env).expanduser()
    for name in (".claude", ".openclaw", ".codex"):
        if (base := Path.home() / name).is_dir():
            return base / "style-craft"
    return Path.home() / ".style-craft"


def get_log_path() -> Path:
    """返回 JSONL 日志文件路径（自动创建存储目录）。"""
    log_dir = storage_root()
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir / LOG_FILENAME


def fail(message: str) -> "NoReturn":  # type: ignore[name-defined]
    """打印友好错误并以非零码退出。"""
    print(f"错误：{message}", file=sys.stderr)
    sys.exit(1)


def read_file(file_arg: str) -> tuple[bytes, str, str]:
    """读取文件，返回 (原始字节, 文本内容, 规范化路径)。"""
    path = Path(file_arg).expanduser()
    if not path.is_file():
        fail(f"文件不存在或不是普通文件：{file_arg}")
    try:
        data = path.read_bytes()
    except OSError as exc:
        fail(f"无法读取文件 {file_arg}：{exc}")
    return data, data.decode("utf-8", errors="replace"), str(path.resolve())


def sha256_hex(data: bytes) -> str:
    """计算字节串的 SHA256 十六进制摘要。"""
    return hashlib.sha256(data).hexdigest()


def now_iso() -> str:
    """当前本地时间（带时区）的 ISO 格式字符串。"""
    return datetime.now().astimezone().isoformat(timespec="seconds")


def load_entries(log_path: Path) -> list[dict]:
    """读取 JSONL 日志；跳过损坏行并提示。日志不存在时返回空列表。"""
    entries: list[dict] = []
    if not log_path.is_file():
        return entries
    with log_path.open("r", encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                print(f"警告：跳过日志第 {lineno} 行（JSON 损坏）", file=sys.stderr)
    return entries


def append_entry(entry: dict) -> None:
    """追加一条记录到 JSONL 日志。"""
    log_path = get_log_path()
    with log_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")


def find_original(entries: list[dict], match: str) -> dict:
    """按 hash（支持唯一前缀）查找未配对的原稿记录。"""
    finals = {e.get("hash") for e in entries if e.get("type") == "final"}
    originals = [
        e for e in entries
        if e.get("type") == "original" and e.get("hash") not in finals
    ]
    hits = [e for e in originals if str(e.get("hash", "")).startswith(match)]
    if not hits:
        fail(
            f"未找到 hash 以 “{match}” 开头的未配对原稿。\n"
            "提示：用 `python observe.py list` 查看所有待配对原稿。"
        )
    if len(hits) > 1:
        listing = "\n".join(f"  {e['hash']}  {e.get('path', '?')}" for e in hits)
        fail(f"hash 前缀 “{match}” 匹配到多条原稿，请提供更长的前缀：\n{listing}")
    return hits[0]


def cmd_record_original(args: argparse.Namespace) -> None:
    """record-original：记录 AI 生成的第一版。"""
    data, content, path = read_file(args.file)
    entry = {
        "type": "original",
        "hash": sha256_hex(data),
        "path": path,
        "account": args.account,
        "content_type": args.content_type,
        "timestamp": now_iso(),
        "content": content,
    }
    append_entry(entry)
    print(f"已记录原稿（{len(content)} 字符）")
    print(f"  hash:         {entry['hash']}")
    print(f"  account:      {entry['account']}")
    print(f"  content_type: {entry['content_type']}")
    print(f"  日志:         {get_log_path()}")


def cmd_record_final(args: argparse.Namespace) -> None:
    """record-final：记录用户确认的终稿，通过 --match 关联原稿。"""
    data, content, path = read_file(args.file)
    original = find_original(load_entries(get_log_path()), args.match)
    entry = {
        "type": "final",
        "hash": original["hash"],  # 沿用原稿 hash 作为配对键
        "path": path,
        "account": original.get("account", ""),
        "content_type": original.get("content_type", ""),
        "timestamp": now_iso(),
        "content": content,
    }
    append_entry(entry)
    print(f"已记录终稿（{len(content)} 字符），关联原稿 {original['hash']}")
    print(f"  日志: {get_log_path()}")


def cmd_list(_args: argparse.Namespace) -> None:
    """list：列出所有未配对的原稿（有 original 无 final）。"""
    entries = load_entries(get_log_path())
    finals = {e.get("hash") for e in entries if e.get("type") == "final"}
    pending = [
        e for e in entries
        if e.get("type") == "original" and e.get("hash") not in finals
    ]
    if not pending:
        print("没有未配对的原稿。")
        return
    print(f"共 {len(pending)} 条未配对原稿：")
    for e in pending:
        print(f"  {e.get('hash', '?')}")
        print(f"    path:         {e.get('path', '?')}")
        print(f"    account:      {e.get('account', '?')}")
        print(f"    content_type: {e.get('content_type', '?')}")
        print(f"    timestamp:    {e.get('timestamp', '?')}")


def build_parser() -> argparse.ArgumentParser:
    """构建 argparse 解析器（含子命令与友好帮助）。"""
    parser = argparse.ArgumentParser(
        prog="observe.py",
        description="记录 AI 原稿与用户终稿，用于风格学习（JSONL 日志）。",
    )
    sub = parser.add_subparsers(dest="command", required=True, metavar="子命令")

    p_orig = sub.add_parser(
        "record-original", help="记录 AI 生成的第一版（原稿）"
    )
    p_orig.add_argument("file", help="原稿文件路径")
    p_orig.add_argument("--account", required=True, help="账号标识，如 weibo_main")
    p_orig.add_argument(
        "--content-type", required=True, help="内容类型，如 tweet / article"
    )
    p_orig.set_defaults(func=cmd_record_original)

    p_final = sub.add_parser(
        "record-final", help="记录用户确认的终稿（通过 hash 关联原稿）"
    )
    p_final.add_argument("file", help="终稿文件路径")
    p_final.add_argument(
        "--match", required=True, help="原稿 hash（可用唯一前缀）"
    )
    p_final.set_defaults(func=cmd_record_final)

    p_list = sub.add_parser("list", help="列出所有未配对的原稿")
    p_list.set_defaults(func=cmd_list)

    return parser


def main(argv: list[str] | None = None) -> None:
    """CLI 入口。"""
    args = build_parser().parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
