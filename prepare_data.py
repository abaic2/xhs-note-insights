#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
准备 Streamlit Cloud 部署用的数据
=================================

把工程里的大文件压成「够展示、体积小、且已脱敏」的 JSON。
输出到 streamlit_app/data/，部署时只带上这个目录即可。

    python streamlit_app/prepare_data.py

做三件事：
  1. 全库聚合（dashboard_data.json）→ 原样搬过来
  2. 每篇 fixture 笔记 → 跑一遍 analyze_note，存成紧凑的 note_analysis.json
  3. **昵称脱敏**：公网 demo 不该原样展示他人昵称，统一打码
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "analysis"))

import analyze_note as AN  # noqa: E402

OUT = Path(__file__).resolve().parent / "data"
NOTES_OUT = OUT / "notes"
MAX_SAMPLE = 220


def mask(name: str) -> str:
    """昵称脱敏：保留前 2 个字，其余打码。

    公网 demo 里没必要原样展示他人的昵称 —— 保留可读性就够了。
    """
    n = (name or "").strip()
    if not n:
        return "匿名"
    if len(n) <= 2:
        return n[0] + "*"
    return n[:2] + "*" * min(4, len(n) - 2)


def mask_content(s: str) -> str:
    """@提及一并打码。"""
    return re.sub(r"@[\w\u4e00-\u9fff\-_]{1,20}", "@***", s or "")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    NOTES_OUT.mkdir(parents=True, exist_ok=True)

    # ---- 1. 全库聚合 ----
    src = ROOT / "data" / "processed" / "dashboard_data.json"
    if not src.exists():
        raise SystemExit(f"缺少 {src}，请先跑 analysis/pipeline.py")
    dash = json.loads(src.read_text(encoding="utf-8"))
    for c in dash.get("top_comments", []):
        c["nickname"] = mask(c.get("nickname", ""))
        c["content"] = mask_content(c.get("content", ""))
    for c in dash.get("sample", []):
        c["nickname"] = mask(c.get("nickname", ""))
        c["content"] = mask_content(c.get("content", ""))
    for p in dash.get("top_posts", []):
        p["nickname"] = mask(p.get("nickname", ""))
    for u in dash.get("users", []):
        u["nickname"] = mask(u.get("nickname", ""))
    (OUT / "dashboard_data.json").write_text(
        json.dumps(dash, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8")
    print(f"✓ dashboard_data.json  {(OUT / 'dashboard_data.json').stat().st_size/1024:.0f} KB")

    # ---- 2. 情感模型评估 ----
    ev = ROOT / "data" / "processed" / "eval_summary.json"
    if ev.exists():
        (OUT / "eval_summary.json").write_text(ev.read_text(encoding="utf-8"),
                                              encoding="utf-8")
        print("✓ eval_summary.json")

    # ---- 3. 每篇 fixture 笔记 ----
    notes_dir = ROOT / "data" / "notes"
    fixtures = sorted(d for d in notes_dir.glob("_fixture_*") if d.is_dir())
    index = []
    for d in fixtures:
        try:
            note, comments = AN.load_note(d)
            res = AN.analyze(note, comments)
        except SystemExit as exc:
            print(f"  跳过 {d.name}：{exc}")
            continue

        sample = res["sample"][:MAX_SAMPLE]
        for c in sample:
            c["nickname"] = mask(c.get("nickname", ""))
            c["content"] = mask_content(c.get("content", ""))
        top = res["top_comments"]
        for c in top:
            c["nickname"] = mask(c.get("nickname", ""))
            c["content"] = mask_content(c.get("content", ""))

        payload = {
            "note": {
                "note_id": note.get("note_id", ""),
                "title": note.get("title", ""),
                "desc": note.get("desc", ""),
                "type": note.get("type", "normal"),
                "author": mask((note.get("author") or {}).get("nickname", "")),
                "interact": note.get("interact") or {},
                "tags": note.get("tags") or [],
                "image_count": len(note.get("images") or []),
                "feature": note.get("feature", ""),
            },
            "stats": res["stats"],
            "sentiment": res["sentiment"],
            "kinds": res["kinds"],
            "avg_by_kind": res["avg_by_kind"],
            "geo": res["geo"],
            "words": res["words"][:60],
            "top_comments": top,
            "sample": sample,
            "sample_total": len(res["sample"]),
        }
        fp = NOTES_OUT / f"{d.name}.json"
        fp.write_text(json.dumps(payload, ensure_ascii=False,
                                 separators=(",", ":")), encoding="utf-8")
        index.append({
            "key": d.name,
            "title": note.get("title", "") or note.get("desc", "")[:30],
            "comments": res["stats"]["total"],
            "net": res["sentiment"]["net"],
            "ask_pct": next((k["pct"] for k in res["kinds"] if k["key"] == "ask"), 0),
            "discuss_pct": next((k["pct"] for k in res["kinds"] if k["key"] == "discuss"), 0),
        })
        print(f"✓ {fp.name}  {fp.stat().st_size/1024:.0f} KB "
              f"（{res['stats']['total']} 条评论）")

    (NOTES_OUT / "index.json").write_text(
        json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✓ notes/index.json（{len(index)} 篇）")

    total = sum(f.stat().st_size for f in OUT.rglob("*.json"))
    print(f"\n部署数据合计：{total/1024/1024:.2f} MB → {OUT}")


if __name__ == "__main__":
    main()
