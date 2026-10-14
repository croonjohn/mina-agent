#!/usr/bin/env python3
"""inventory.csv + strings.csv → 언어별 이미지 생성 작업 목록(jobs.jsonl).

usage: python3 -I scripts/build_jobs.py <원본폴더> [--langs en,ja,zh-Hant,zh-Hans] [-o jobs.jsonl]

master 이미지마다, 그 화면(screen)에 나오는 문자열을 strings.csv 순서대로 모아
"한국어 → 대상 언어" 교체 지시 프롬프트를 만든다. 번역이 빈 칸이면 멈춘다.
"""
import argparse
import csv
import json
from pathlib import Path

LANGS = {
    "en": "English (US)",
    "ja": "Japanese",
    "zh-Hant": "Traditional Chinese as used in Taiwan (Traditional characters only)",
    "zh-Hans": "Simplified Chinese as used in mainland China (Simplified characters only)",
}

PROMPT = """Edit ref.png, which is an app store screenshot for the mobile app DITTI. \
Produce the SAME image localized into {lang_name}.
Replace EVERY piece of Korean text - the marketing headline and description AND all text inside the app UI on the phone screen - with the exact strings listed below.
Keep everything else identical to ref.png: canvas size {w}x{h} ({orientation}), layout, positions, colors, background, illustrations, photos, icons, phone frame, status bar, and spacing. Match the original font weight, size hierarchy and alignment.
Do NOT redesign the UI, do NOT add, remove or move any element, do NOT draw a second screen or card on top, and do NOT leave any Korean (Hangul) characters anywhere.
If a translated line is longer than the Korean, reduce its font size slightly or wrap it inside the same area - never overflow or overlap other elements.
Text replacements, in reading order (Korean -> {lang_name}):
{pairs}"""


def job_id(screen, group):
    return f"s{screen}_{group}"


def read_csv(path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src", type=Path, help="원본 스크린샷 폴더 (inventory.py에 준 것과 같은 폴더)")
    ap.add_argument("--inventory", type=Path, default=Path("inventory.csv"))
    ap.add_argument("--strings", type=Path, default=Path("strings.csv"))
    ap.add_argument("--langs", default=",".join(LANGS))
    ap.add_argument("-o", "--out", type=Path, default=Path("jobs.jsonl"))
    args = ap.parse_args()

    langs = [l.strip() for l in args.langs.split(",") if l.strip()]
    unknown = [l for l in langs if l not in LANGS]
    if unknown:
        raise SystemExit(f"모르는 언어 코드: {unknown} (가능: {list(LANGS)})")

    strings = [s for s in read_csv(args.strings) if s.get("ko", "").strip()]
    masters = [r for r in read_csv(args.inventory) if r["master"] == "Y"]

    jobs, missing = [], []
    for m in masters:
        if not m["screen"]:
            raise SystemExit(f"screen 번호가 비었습니다: {m['rel_path']} — inventory.csv를 채우세요")
        rows = [s for s in strings
                if s["screens"].strip() == "*" or m["screen"] in [x.strip() for x in s["screens"].split(";")]]
        if not rows:
            raise SystemExit(f"화면 {m['screen']}에 해당하는 문자열이 strings.csv에 없습니다")
        for lang in langs:
            empty = [s["key"] for s in rows if not s.get(lang, "").strip()]
            if empty:
                msg = f"{lang} 화면{m['screen']}: {', '.join(empty)}"
                if msg not in missing:
                    missing.append(msg)
                continue
            pairs = "\n".join(f'{i}. "{s["ko"]}" -> "{s[lang]}"' for i, s in enumerate(rows, 1))
            jobs.append({
                "job_id": job_id(m["screen"], m["group"]),
                "lang": lang,
                "screen": m["screen"],
                "group": m["group"],
                "src": str((args.src / m["rel_path"]).resolve()),
                "width": int(m["width"]),
                "height": int(m["height"]),
                "prompt": PROMPT.format(lang_name=LANGS[lang], w=m["width"], h=m["height"],
                                        orientation=m["orientation"], pairs=pairs),
            })

    if missing:
        raise SystemExit("번역이 빈 칸입니다:\n  " + "\n  ".join(missing))
    with args.out.open("w", encoding="utf-8") as f:
        for j in jobs:
            f.write(json.dumps(j, ensure_ascii=False) + "\n")
    print(f"{len(jobs)}개 작업 ({len(masters)} master × {len(langs)} 언어) → {args.out}")


if __name__ == "__main__":
    main()
