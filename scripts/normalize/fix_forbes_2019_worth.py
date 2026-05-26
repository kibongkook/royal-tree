#!/usr/bin/env python3
"""forbes-2019 source의 valuation_usd 정정.

진단: build_businesses.py가 raw CSV에서 `worth` 또는 `Net Worth` 컬럼을 valuation으로
사용했는데, fuzzy_pandas forbes-billionaires.csv의 실제 컬럼 구조는:
  - worthChange (잘못 사용됨; 일중 변동/스코어성 값으로 $250-422B 같이 비현실적)
  - realTimeWorth (정상 net worth, in USD millions — Forbes 2019 시점)

이 스크립트는 raw CSV를 다시 읽어 owner_name 단위로 realTimeWorth × 1e6 (USD raw)
값으로 valuation_usd을 강제 재할당한다. 단위 fix(`fix_valuation_units.py`)의
×1e9 보정이 forbes-2019 row에 추가 적용되지 않도록, 새 marker `worth_fix=v2-realtime`
도 함께 박는다 — fix_valuation_units 재실행 시에도 idempotent.

Idempotent — 두 번 돌려도 같은 결과.
"""
from __future__ import annotations

import csv
import json
import os
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MASTER = ROOT / "data" / "master"
BIZ = MASTER / "businesses.jsonl"
BACKUP = MASTER / "businesses.pre_forbes2019_worth_fix.jsonl"
RAW_CSV = ROOT / "data" / "raw" / "github" / "fuzzy_pandas" / "examples" / "data" / "forbes-billionaires.csv"


def load_owner_to_worth_usd() -> dict[str, float]:
    """owner name → real net worth (USD raw)."""
    out: dict[str, float] = {}
    if not RAW_CSV.exists():
        raise SystemExit(f"missing raw CSV: {RAW_CSV}")
    with RAW_CSV.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            name = (row.get("name") or "").strip()
            rt = (row.get("realTimeWorth") or "").strip()
            if not name or not rt:
                continue
            try:
                worth_m = float(rt)
            except ValueError:
                continue
            # realTimeWorth is in USD millions per Forbes API convention
            out[name] = worth_m * 1e6
    return out


def main() -> None:
    if not BIZ.exists():
        raise SystemExit(f"missing {BIZ}")
    if not BACKUP.exists():
        shutil.copy(BIZ, BACKUP)
        print(f"backup → {BACKUP}")

    owner_worth = load_owner_to_worth_usd()
    print(f"raw owners loaded: {len(owner_worth):,}")

    tmp = BIZ.with_suffix(".jsonl.tmp")
    n_total = 0
    n_fixed = 0
    n_zeroed = 0
    n_already = 0
    n_skip = 0
    with BIZ.open() as src, tmp.open("w") as dst:
        for line in src:
            try:
                b = json.loads(line)
            except json.JSONDecodeError:
                dst.write(line)
                continue
            srcs = b.get("sources") or []
            if "forbes-2019" not in srcs:
                dst.write(json.dumps(b, ensure_ascii=False) + "\n")
                continue
            n_total += 1
            raw = b.get("raw") or {}
            if raw.get("worth_fix") == "v2-realtime":
                n_already += 1
                dst.write(json.dumps(b, ensure_ascii=False) + "\n")
                continue
            owner = (raw.get("owner_name") or "").strip()
            new_val = owner_worth.get(owner)
            if new_val is None:
                # owner not present in raw CSV — zero out (was certainly noise)
                b["valuation_usd"] = 0
                raw["worth_fix"] = "v2-realtime"
                raw["worth_fix_note"] = "owner not found in raw CSV — zeroed"
                b["raw"] = raw
                n_zeroed += 1
            else:
                b["valuation_usd"] = float(new_val)
                raw["worth_fix"] = "v2-realtime"
                # remove the prior unit_fix marker so it does not look like a double-fix
                if "unit_fix" in raw:
                    raw["unit_fix_dropped"] = raw.pop("unit_fix")
                b["raw"] = raw
                n_fixed += 1
            dst.write(json.dumps(b, ensure_ascii=False) + "\n")
    os.replace(tmp, BIZ)
    print(f"\nforbes-2019 rows scanned: {n_total:,}")
    print(f"  fixed (re-set from realTimeWorth): {n_fixed:,}")
    print(f"  zeroed (owner not in raw CSV):     {n_zeroed:,}")
    print(f"  already-fixed (v2-realtime tag):   {n_already:,}")


if __name__ == "__main__":
    main()
