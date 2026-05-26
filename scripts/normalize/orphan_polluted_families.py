#!/usr/bin/env python3
"""forbes-2019 same-surname dedup 오염 가문 정리.

진단 (scripts/audit run):
  - `royal-tree:manual:zhang-juzheng-family`(明 정치가) ← 모든 Zhang씨 부호 흡수
  - `royal-tree:manual:sun-chuanfang-family`(1885-1935 軍閥) ← 모든 Sun씨
  - `royal-tree:manual:chen-daihe-family` ← 모든 Chen씨
  - `royal-tree:manual:jiang-family` ← 모든 Jiang씨
  - 그 외 surname slug 기반으로 합쳐진 가문들 — owner_name이 가족 멤버가 아니면
    orphan(family_id="") 처리.

매핑 정책:
  - allowlist에 명시된 owner만 family 유지
  - empty set이면 가문 전체 orphan (역사 인물 가문에 modern 동성씨 흡수)
  - 모든 source의 row를 검사 (forbes-2019 + bloomberg-2018-19 + forbes-2014-15)
  - OWNER_REMAP에 명시된 owner는 orphan 대신 정확한 family로 재할당

Idempotent — 같은 결과 반복.
"""
from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MASTER = ROOT / "data" / "master"
BIZ = MASTER / "businesses.jsonl"
BACKUP = MASTER / "businesses.pre_orphan_polluted.jsonl"

# Family id → allowed forbes-2019 owner_name set.
# Empty set = orphan all forbes-2019 rows for that family.
FAMILY_OWNER_ALLOWLIST: dict[str, set[str]] = {
    # ── 历史 인물 가문 — 동성씨 흡수 전체 orphan ──
    "royal-tree:manual:zhang-juzheng-family": set(),
    "royal-tree:manual:sun-chuanfang-family": set(),
    "royal-tree:manual:chen-daihe-family": set(),
    "royal-tree:manual:jiang-family": set(),

    # ── modern 가문 — founder만 유지 ──
    "royal-tree:manual:wang-chuanfu-family-byd": {
        "Wang Chuanfu", "Wang Chuan-Fu"},
    "royal-tree:manual:huang-zheng-colin-huang-family-pinduoduo": {
        "Huang Zheng", "Colin Huang"},
    "royal-tree:manual:zhou-hongyi-family-360-security": {"Zhou Hongyi"},
    "royal-tree:manual:xu-jiayin-hui-ka-yan-family-evergrande": {
        "Hui Ka Yan", "Xu Jiayin"},
    "royal-tree:manual:citrone-family-robert-citrone": {"Robert Citrone"},
    "royal-tree:manual:edward-debartolo-family-edward-debartolo-jr": {
        "Edward DeBartolo, Jr.", "Edward DeBartolo Jr."},
    "royal-tree:manual:lau-family-chinese-estates": {
        "Joseph Lau", "Thomas Lau"},
    "royal-tree:manual:mediatek-tsai-family": {
        "Ming-Kai Tsai", "Tsai Ming-Kai", "M.K. Tsai"},
    "royal-tree:manual:kwok-family-shk": {
        "Walter Kwok", "Thomas & Raymond Kwok", "Raymond Kwok",
        "Thomas Kwok", "Adam Kwok", "Edward Kwok", "Geoffrey Kwok",
        "Christopher Kwok"},
    "royal-tree:manual:persson-family-stefan-persson": {
        "Stefan Persson", "Karl-Johan Persson", "Tom Persson"},
    # ── Fraisse 가문에 Bernard Arnault 흡수 — 전체 orphan (Arnault는 별도 remap) ──
    "royal-tree:manual:fraisse-family-bernard-fraisse": {"Bernard Fraisse"},

    # ── QID 가문 — surname dedup 오염 ──
    "Q12908": {"George Soros"},                              # Soros, 다른 George 모두 orphan
    "Q855533": {"Lee Man Tat", "Lee Man-Tat", "Patrick Lee"},  # Lee Kum Kee, Shau Kee는 별개
    "Q683170": {"H. Fisk Johnson", "Imogene Powers Johnson",
                "S. Curtis Johnson"},                         # S.C. Johnson, Abigail은 Fidelity
    "Q29678773": {"Alexander Otto", "Frank Otto", "Maren Otto"},  # Otto Versand
    "Q16201355": {"J. Willard Marriott", "Marriott", "John Marriott",
                  "Richard Marriott", "J.W. Marriott Jr."},  # Marriott 가족만
}

# Owner name → 정확한 family_id. orphan 대신 재할당.
# (orphan 처리되는 owner 중 알려진 가족이 있는 경우)
OWNER_REMAP: dict[str, str] = {
    "Bernard Arnault": "royal-tree:manual:arnault-family",
    "Abigail Johnson": "royal-tree:manual:johnson-fidelity-family",  # 별도 가문 (없으면 orphan 유지)
    "Lee Shau Kee": "royal-tree:manual:lee-shau-kee-family",
    "Lee Shau-Kee": "royal-tree:manual:lee-shau-kee-family",
}


def main() -> None:
    if not BIZ.exists():
        raise SystemExit(f"missing {BIZ}")
    if not BACKUP.exists():
        shutil.copy(BIZ, BACKUP)
        print(f"backup → {BACKUP}")

    tmp = BIZ.with_suffix(".jsonl.tmp")
    n_orphaned = 0
    n_kept = 0
    n_unchanged = 0
    orphan_owners: dict[str, list[str]] = {}

    # Load existing family ids to validate remap targets
    fam_ids = set()
    with (MASTER / "families.jsonl").open() as f:
        for line in f:
            try:
                fam_ids.add(json.loads(line)["id"])
            except Exception:
                pass

    n_remapped = 0
    with BIZ.open() as src, tmp.open("w") as dst:
        for line in src:
            try:
                b = json.loads(line)
            except json.JSONDecodeError:
                dst.write(line)
                continue
            fid = b.get("family_id") or ""
            if fid not in FAMILY_OWNER_ALLOWLIST:
                n_unchanged += 1
                dst.write(json.dumps(b, ensure_ascii=False) + "\n")
                continue
            allowed = FAMILY_OWNER_ALLOWLIST[fid]
            raw = b.get("raw") or {}
            owner = (raw.get("owner_name") or "").strip()
            if owner in allowed:
                n_kept += 1
            else:
                # Try remap to a correct family if known
                remap_target = OWNER_REMAP.get(owner)
                if remap_target and remap_target in fam_ids:
                    raw["pollution_fix"] = (
                        f"remapped {fid} → {remap_target} (owner={owner})")
                    b["raw"] = raw
                    b["family_id"] = remap_target
                    n_remapped += 1
                else:
                    raw["pollution_fix"] = (
                        f"orphaned ({owner!r} not in allowlist for {fid})")
                    b["raw"] = raw
                    b["family_id"] = ""
                    n_orphaned += 1
                    orphan_owners.setdefault(fid, []).append(owner)
            dst.write(json.dumps(b, ensure_ascii=False) + "\n")
    os.replace(tmp, BIZ)

    print(f"\nrows kept (allowlisted owners):  {n_kept:,}")
    print(f"rows remapped to correct family: {n_remapped:,}")
    print(f"rows orphaned (surname dedup mismatch): {n_orphaned:,}")
    print(f"rows untouched (other families):  {n_unchanged:,}")
    print(f"\nfamilies cleaned: {len(orphan_owners)}")
    for fid, owners in orphan_owners.items():
        u = sorted(set(owners))
        print(f"  {fid}  → orphaned {len(owners)} rows ({len(u)} distinct: "
              f"{', '.join(u[:5])}{'…' if len(u)>5 else ''})")


if __name__ == "__main__":
    main()
