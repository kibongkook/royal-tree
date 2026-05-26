#!/usr/bin/env python3
"""advisors.jsonl → families.advisors join.

각 family에 자기를 client로 둔 advisor 요약 리스트 부착.
family_id 미존재 시 stderr에 warning 출력 (manual id 정확성 점검).

Idempotent — 매 실행마다 advisors 필드 완전 재계산.
"""
from __future__ import annotations

import json
import os
import shutil
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MASTER = ROOT / "data" / "master"
FAMILIES = MASTER / "families.jsonl"
ADVISORS = MASTER / "advisors.jsonl"
BACKUP = MASTER / "families.pre_advisors.jsonl"


def main() -> None:
    if not ADVISORS.exists():
        raise SystemExit(f"missing {ADVISORS}")
    if not BACKUP.exists():
        shutil.copy(FAMILIES, BACKUP)
        print(f"backup → {BACKUP}")

    # Load advisors and group by client family_id
    fam_to_advisors: dict[str, list[dict]] = defaultdict(list)
    referenced_fids: set[str] = set()
    n_adv = 0
    with ADVISORS.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            adv = json.loads(line)
            n_adv += 1
            for c in adv.get("clients", []):
                fid = c.get("family_id")
                if not fid:
                    continue
                referenced_fids.add(fid)
                fam_to_advisors[fid].append({
                    "id": adv["id"],
                    "name": adv["name"],
                    "role": adv["role"],
                    "firm": adv.get("firm"),
                    "country": adv.get("country"),
                    "relationship": c.get("type"),
                    "since": c.get("since"),
                    "until": c.get("until"),
                })

    # Load existing family ids
    fam_ids: set[str] = set()
    with FAMILIES.open() as f:
        for line in f:
            try:
                fam_ids.add(json.loads(line)["id"])
            except Exception:
                pass

    missing = referenced_fids - fam_ids
    if missing:
        print(f"\n⚠️  {len(missing)} family_id referenced by advisors but not in families.jsonl:", file=sys.stderr)
        for fid in sorted(missing):
            print(f"     • {fid}", file=sys.stderr)

    # Inject advisors array
    tmp = FAMILIES.with_suffix(".jsonl.tmp")
    n_fam = n_fam_with_adv = 0
    with FAMILIES.open() as src, tmp.open("w") as dst:
        for line in src:
            d = json.loads(line)
            n_fam += 1
            advs = fam_to_advisors.get(d["id"], [])
            if advs:
                d["advisors"] = advs
                n_fam_with_adv += 1
            elif "advisors" in d:
                # re-run: clear stale advisors
                del d["advisors"]
            dst.write(json.dumps(d, ensure_ascii=False) + "\n")
    os.replace(tmp, FAMILIES)

    print(f"\nadvisors loaded:                 {n_adv}")
    print(f"families scanned:                {n_fam:,}")
    print(f"families with ≥1 advisor:        {n_fam_with_adv}")
    print(f"family_ids referenced (valid):   {len(referenced_fids - missing)}")
    print(f"family_ids referenced (missing): {len(missing)}")


if __name__ == "__main__":
    main()
