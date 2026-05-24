#!/usr/bin/env python3
"""forbes-2019 source의 비뚤어진 owner→family 매핑 정정.

진단: 같은 surname을 공유하는 한국 chaebol(Lee/Kim/Chey/Cho/Shin/Chung 등)과
미국 Walton 가문의 자식들이 owner_name surname-prefix 일치만으로 잘못된
가문에 attach됨. 예: Lee Kun-Hee의 Samsung 사업이 royal-tree:manual:booyoung-lee-family에 매핑.

해결: 정확한 owner_name → family_id 매핑 dict를 manual로 작성.
  • match → 그 family로 재할당
  • no match → family_id="" (orphan; ranking에서 제외, 데이터는 보존)

Idempotent — 이미 수정된 row는 같은 결과.
"""
from __future__ import annotations

import json
import os
import shutil
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MASTER = ROOT / "data" / "master"
BIZ = MASTER / "businesses.jsonl"
BACKUP = MASTER / "businesses.pre_mapping_fix.jsonl"

# owner_name (Forbes 표기) → 올바른 family_id
OWNER_TO_FAMILY = {
    # ── Korea — Samsung & 이씨 분기 ──
    "Lee Kun-Hee": "Q333856",                                    # Samsung 회장
    "Jay Y. Lee": "Q333856",                                     # 이재용
    "Lee Boo-Jin": "Q333856",                                    # 이부진 (Hotel Shilla)
    "Lee Seo-Hyun": "Q333856",                                   # 이서현 (Samsung C&T)
    "Lee Myung-Hee": "royal-tree:manual:shinsegae-lee-family",   # 신세계 이명희
    "Hong Ra-Hee": "Q333856",
    # ── Korea — CJ 이재현 ──
    "Lee Jay-Hyun": "royal-tree:manual:cj-lee-family",
    "Lee Mi-Kyung": "royal-tree:manual:cj-lee-family",
    # ── Korea — NAVER 이해진 ──
    "Lee Hae-Jin": "royal-tree:manual:naver-lee-hae-jin-family",
    # ── Korea — Booyoung 이중근 (진짜 Booyoung) ──
    "Lee Joong-Keun": "royal-tree:manual:booyoung-lee-family",
    # ── Korea — NXC / NEXON (이정훈은 아니고 김정주 부인, 그러나 NXC 이정훈은 별도) ──
    "Lee Joon-ho": "royal-tree:manual:nxc-lee-jung-hoon-family",
    # ── Korea — 농심 신씨 / 미상 ──
    "Lee Hwa-Kyung": "",       # unclear
    "Lee Sang-Hyuk": "",       # unclear
    "Lee Ho-Jin": "",          # unclear
    # ── Korea — Hyundai Chung ──
    "Chung Mong-Koo": "Q484847",
    "Chung Eui-sun": "Q484847",
    "Chung Mong-joon": "Q484847",
    "Chung Yong-Jin": "royal-tree:manual:shinsegae-lee-family",   # Shinsegae VP
    # ── Korea — SK Chey ──
    "Chey Tae-Won": "royal-tree:manual:tae-won-family-chey-tae-won",
    "Chey Ki-Won": "royal-tree:manual:ki-won-family-chey-ki-won",
    # ── Korea — Lotte Shin ──
    "Shin Dong-Bin": "Q485145",
    "Shin Dong-Joo": "Q485145",
    # ── Korea — Hanjin Cho ──
    "Cho Yang-Ho": "royal-tree:manual:hanjin-cho-family",
    "Cho Won-Tae": "royal-tree:manual:hanjin-cho-family",
    # ── Korea — Hyosung Cho ──
    "Cho Hyun-Joon": "royal-tree:manual:hyosung-cho-family",
    "Cho Hyun-Sang": "royal-tree:manual:hyosung-cho-family",
    # ── Korea — LG Koo ──
    "Koo Kwang-Mo": "Q189867",
    "Koo Bon-Joon": "Q189867",
    "Koo Bon-Geol": "royal-tree:manual:lf-koo-family",
    # ── Korea — Doosan Park ──
    "Park Jeong-Won": "Q487497",
    "Park Yong-Maan": "Q487497",
    # ── Korea — Boryung Kim ──
    "Kim Jun-Ki": "royal-tree:manual:boryung-kim-family",
    # ── Korea — NEXON Kim Jung-Ju (김정주) ──
    "Kim Jung-Ju": "royal-tree:manual:nexon-kim-jung-ju-family",
    # ── Korea — Kakao Kim Beom-Su ──
    "Kim Beom-Su": "royal-tree:manual:kakao-kim-beom-su-family",
    # ── Korea — NCsoft Kim Taek-Jin ──
    "Kim Taek-Jin": "royal-tree:manual:ncsoft-kim-taek-jin-family",
    # ── Korea — MBK Michael Kim (외국 활동) ──
    "Michael Kim": "royal-tree:manual:mbk-michael-kim-family",
    "Kim Nam-Jung": "",  # unclear
    # ── Korea — Hanwha Kim ──
    "Kim Seung-Yeon": "Q487921",
    "Kim Dong-Kwan": "Q487921",
    # ── Korea — Amorepacific Suh ──
    "Suh Kyung-Bae": "royal-tree:manual:amorepacific-suh-family",
    # ── Korea — Kwon Hyuk-Bin (Smilegate) ──
    "Kwon Hyuk-Bin": "royal-tree:manual:hyuk-bin-family-kwon-hyuk-bin",
    # ── US — Walton 가족 ──
    "S. Robson Walton": "Q17343056",
    "Jim Walton": "Q17343056",
    "Alice Walton": "Q17343056",
    "Christy Walton": "Q17343056",
    "Ann Walton Kroenke": "Q17343056",
    "Nancy Walton Laurie": "Q17343056",
    "Lukas Walton": "Q17343056",
    # ── US — Koch ──
    "Charles Koch": "royal-tree:manual:koch-family-charles-koch",
    "Julia Koch": "royal-tree:manual:koch-family-charles-koch",
    "David Koch": "royal-tree:manual:koch-family-charles-koch",
    # ── US — Mars ──
    "Jacqueline Mars": "royal-tree:manual:mars-family-jacqueline-mars",
    "John Mars": "royal-tree:manual:mars-family-jacqueline-mars",
    "Forrest Mars": "royal-tree:manual:forrest-mars-family-forrest-mars-jr",
    # ── US — Pritzker (큰 가문) ──
    "Thomas Pritzker": "royal-tree:manual:pritzker-family",
    "Jay Robert Pritzker": "royal-tree:manual:pritzker-family",
    "Penny Pritzker": "royal-tree:manual:pritzker-family",
    # ── US — Cargill-MacMillan ──
    "Pauline Keinath": "royal-tree:manual:cargill-macmillan-family",
    "James Cargill": "royal-tree:manual:cargill-macmillan-family",
    # ── Brewer mismap (Jim Koch beer was mapped to Breyer) ──
    "Jim Koch": "royal-tree:manual:koch-jim-beer-family",  # Boston Beer 별도
    # ── 인도 Bhartia ──
    "Shyam & Hari Bhartia": "royal-tree:manual:bhartia-family-jubilant",
    "Hari Bhartia": "royal-tree:manual:bhartia-family-jubilant",
    "Shyam Bhartia": "royal-tree:manual:bhartia-family-jubilant",
    # ── 인도 Birla ──
    "Kumar Mangalam Birla": "royal-tree:manual:birla-aditya-family",
    # ── 인도 Adani ──
    "Gautam Adani": "royal-tree:manual:adani-family",
    # ── 사우디 Olayan ──
    "Lubna Olayan": "royal-tree:manual:olayan-family",
}


def main() -> None:
    if not BACKUP.exists():
        shutil.copy(BIZ, BACKUP)
        print(f"backup → {BACKUP}")

    tmp = BIZ.with_suffix(".jsonl.tmp")
    n_remapped = 0
    n_orphaned = 0
    n_unchanged = 0
    surname_first = Counter()  # how many forbes-2019 rows per surname token

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
            raw = b.get("raw") or {}
            owner = (raw.get("owner_name") or "").strip()
            cur_fam = b.get("family_id") or ""

            target = OWNER_TO_FAMILY.get(owner)
            if target is None:
                # owner not in our table → keep current mapping
                n_unchanged += 1
            elif target == "":
                # explicit orphan
                if cur_fam:
                    b["family_id"] = ""
                    b.setdefault("raw", {})["mapping_fix"] = f"orphaned (owner={owner}, no canonical family)"
                    n_orphaned += 1
                else:
                    n_unchanged += 1
            elif target != cur_fam:
                b.setdefault("raw", {})["mapping_fix"] = f"remapped {cur_fam} → {target} (owner={owner})"
                b["family_id"] = target
                n_remapped += 1
            else:
                n_unchanged += 1
            dst.write(json.dumps(b, ensure_ascii=False) + "\n")
    os.replace(tmp, BIZ)
    print(f"forbes-2019 remapped: {n_remapped:,}")
    print(f"forbes-2019 orphaned: {n_orphaned:,}")
    print(f"forbes-2019 unchanged: {n_unchanged:,}")


if __name__ == "__main__":
    main()
