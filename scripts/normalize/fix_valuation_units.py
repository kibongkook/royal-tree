#!/usr/bin/env python3
"""data/master/businesses.jsonl의 valuation_usd 단위 정정.

진단 결과: 일부 행이 net-worth-in-USD-billions 단위로 raw 저장됨
(Forbes/Bloomberg net worth → manual extraction에서 단위 손실).

규칙:
  • 0 < valuation_usd < 10_000     → ×1e9 (= USD billions → USD)
  • 10_000 ≤ valuation_usd < 1e6   → ×1e6 (= USD millions → USD) — 극히 적음
  • 1e6 이상                       → 이미 정상

10,000 미만은 단일 가문 자산이 $10조 이상일 수 없으므로 안전한 컷.
거꾸로 정상 행은 모두 $1M+ 단위이므로 1e6 위에서는 절대 건드리지 않음.

Idempotent — pre-fix backup을 만들고 다시 돌려도 같은 결과.
"""
from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MASTER = ROOT / "data" / "master"
BIZ = MASTER / "businesses.jsonl"
BACKUP = MASTER / "businesses.pre_unit_fix.jsonl"


def main() -> None:
    if not BACKUP.exists():
        shutil.copy(BIZ, BACKUP)
        print(f"backup → {BACKUP}")

    tmp = BIZ.with_suffix(".jsonl.tmp")
    n_fixed_b = 0
    n_fixed_m = 0
    n_total = 0
    with BIZ.open() as src, tmp.open("w") as dst:
        for line in src:
            try:
                b = json.loads(line)
            except json.JSONDecodeError:
                dst.write(line)
                continue
            n_total += 1
            v = b.get("valuation_usd")
            if isinstance(v, (int, float)) and v > 0:
                if v < 10_000:
                    b["valuation_usd"] = float(v) * 1e9
                    b.setdefault("raw", {})["unit_fix"] = "×1e9 (USD billions)"
                    n_fixed_b += 1
                elif v < 1e6:
                    b["valuation_usd"] = float(v) * 1e6
                    b.setdefault("raw", {})["unit_fix"] = "×1e6 (USD millions)"
                    n_fixed_m += 1
            dst.write(json.dumps(b, ensure_ascii=False) + "\n")
    os.replace(tmp, BIZ)
    print(f"businesses scanned: {n_total:,}")
    print(f"fixed USD-billions units (×1e9): {n_fixed_b:,}")
    print(f"fixed USD-millions units (×1e6): {n_fixed_m:,}")


if __name__ == "__main__":
    main()
