#!/usr/bin/env python3
"""생성된 master 이미지를 원본 파일 하나하나의 정확한 픽셀 크기로 맞춰 업로드용으로 내보낸다.

usage: python3 -I scripts/fit_size.py [--langs en,ja,zh-Hant,zh-Hans] [--mode skip|pad|cover]

- 원본 폴더 구조를 그대로 따라 output/final/<lang>/<rel_path> 로 저장 (스토어에 그대로 올릴 수 있게)
- 비율 차이가 --tolerance 이내면 리사이즈만 한다
- 그보다 크면 기본(skip)은 건너뛰고 보고만 한다. pad=가장자리 색으로 여백, cover=가운데 잘라내기
- 알파 채널을 없앤다(Google Play는 24-bit PNG/JPEG만, 8MB 이하)
"""
import argparse
import csv
from pathlib import Path

from PIL import Image

PLAY_MAX_MB = 8


def job_id(screen, group):  # build_jobs.py와 같은 규칙
    return f"s{screen}_{group}"


def flatten(im):
    if im.mode in ("RGBA", "LA", "PA") or "transparency" in im.info:
        im = im.convert("RGBA")
        bg = Image.new("RGB", im.size, (255, 255, 255))
        bg.paste(im, mask=im.getchannel("A"))
        return bg
    return im.convert("RGB")


def edge_color(im):
    px = [im.getpixel(xy) for xy in ((0, 0), (im.width - 1, 0), (0, im.height - 1), (im.width - 1, im.height - 1))]
    return tuple(sum(c[i] for c in px) // len(px) for i in range(3))


def fit(im, w, h, mode):
    if mode == "pad":
        s = min(w / im.width, h / im.height)
        r = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
        canvas = Image.new("RGB", (w, h), edge_color(im))
        canvas.paste(r, ((w - r.width) // 2, (h - r.height) // 2))
        return canvas
    if mode == "cover":
        s = max(w / im.width, h / im.height)
        r = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
        x, y = (r.width - w) // 2, (r.height - h) // 2
        return r.crop((x, y, x + w, y + h))
    return im.resize((w, h), Image.LANCZOS)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--inventory", type=Path, default=Path("inventory.csv"))
    ap.add_argument("--workdir", type=Path, default=Path("output/work"))
    ap.add_argument("--out", type=Path, default=Path("output/final"))
    ap.add_argument("--langs", default="en,ja,zh-Hant,zh-Hans")
    ap.add_argument("--tolerance", type=float, default=0.03, help="허용 비율 차이 (0.03 = 3%%)")
    ap.add_argument("--mode", choices=["skip", "pad", "cover"], default="skip",
                    help="비율 차이가 허용치를 넘을 때 처리")
    args = ap.parse_args()

    with args.inventory.open(newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    done, problems = 0, []
    for lang in [l.strip() for l in args.langs.split(",") if l.strip()]:
        for r in rows:
            gen = args.workdir / lang / job_id(r["screen"], r["group"]) / "out.png"
            if not gen.exists():
                problems.append(f"{lang}/{r['rel_path']}: 생성본 없음 ({gen})")
                continue
            status = gen.parent / "status"
            if status.exists() and status.read_text().strip() != "OK":  # 검수 탈락(QA_FAIL)·실패분은 내보내지 않는다
                problems.append(f"{lang}/{r['rel_path']}: 상태 {status.read_text().strip()} — 재생성 후 다시 실행")
                continue
            w, h = int(r["width"]), int(r["height"])
            with Image.open(gen) as g:
                im = flatten(g)
            diff = abs(im.width / im.height - w / h) / (w / h)
            mode = "resize" if diff <= args.tolerance else args.mode
            if mode == "skip":
                problems.append(f"{lang}/{r['rel_path']}: 비율 차이 {diff:.1%} "
                                f"(생성 {im.width}x{im.height} vs 원본 {w}x{h}) — --mode pad|cover 로 처리하거나 재생성")
                continue
            dst = args.out / lang / r["rel_path"]
            dst.parent.mkdir(parents=True, exist_ok=True)
            res = fit(im, w, h, mode)
            if dst.suffix.lower() in (".jpg", ".jpeg"):
                res.save(dst, quality=95)
            else:
                res.save(dst.with_suffix(".png"), optimize=True)
                dst = dst.with_suffix(".png")
            mb = dst.stat().st_size / 1_048_576
            if mb > PLAY_MAX_MB:
                problems.append(f"{lang}/{r['rel_path']}: {mb:.1f}MB > {PLAY_MAX_MB}MB (Play 업로드 불가)")
            done += 1
            note = "" if mode == "resize" else f" [{mode}, 비율 차이 {diff:.1%}]"
            print(f"OK {lang}/{dst.relative_to(args.out / lang)} {w}x{h}{note}")

    print(f"\n{done}개 저장 → {args.out}")
    if problems:
        print(f"확인 필요 {len(problems)}건:")
        for p in problems:
            print("  - " + p)


if __name__ == "__main__":
    main()
