#!/usr/bin/env python3
"""검수용: master마다 [한국어 원본 | en | ja | zh-Hant | zh-Hans]를 한 줄로 붙인 비교 이미지를 만든다.

usage: python3 -I scripts/contact_sheet.py [--langs en,ja,zh-Hant,zh-Hans] [--height 1000]
→ output/review/<job_id>.jpg
"""
import argparse
import json
from pathlib import Path

from PIL import Image


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("jobs", type=Path, nargs="?", default=Path("jobs.jsonl"))
    ap.add_argument("--workdir", type=Path, default=Path("output/work"))
    ap.add_argument("--out", type=Path, default=Path("output/review"))
    ap.add_argument("--langs", default="en,ja,zh-Hant,zh-Hans")
    ap.add_argument("--height", type=int, default=1000)
    args = ap.parse_args()

    jobs = [json.loads(l) for l in args.jobs.read_text(encoding="utf-8").splitlines() if l.strip()]
    srcs = {j["job_id"]: j["src"] for j in jobs}
    langs = [l.strip() for l in args.langs.split(",") if l.strip()]
    args.out.mkdir(parents=True, exist_ok=True)

    for jid, src in srcs.items():
        paths = [Path(src)] + [args.workdir / l / jid / "out.png" for l in langs]
        tiles = []
        for p in paths:
            if p.exists():
                with Image.open(p) as im:
                    im = im.convert("RGB")
                    tiles.append(im.resize((round(im.width * args.height / im.height), args.height)))
            else:
                tiles.append(Image.new("RGB", (args.height // 2, args.height), (220, 220, 220)))
        gap = 20
        sheet = Image.new("RGB", (sum(t.width for t in tiles) + gap * (len(tiles) - 1), args.height), (255, 255, 255))
        x = 0
        for t in tiles:
            sheet.paste(t, (x, 0))
            x += t.width + gap
        dst = args.out / f"{jid}.jpg"
        sheet.save(dst, quality=88)
        print(f"{dst}  (ko | {' | '.join(langs)})")


if __name__ == "__main__":
    main()
