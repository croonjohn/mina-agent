#!/usr/bin/env python3
"""원본 스크린샷 폴더를 스캔해 사이즈·비율·스토어 규격 적합성을 inventory.csv로 정리한다.

usage: python3 -I scripts/inventory.py <원본폴더> [-o inventory.csv]

- group  : 화면 비율(세로/가로)이 같은 파일끼리 묶은 그룹. 같은 그룹은 한 장만 생성해 크기만 맞춘다.
- screen : 파일명 앞 숫자로 추정한 화면 번호(01, 02 ...). 틀리면 CSV에서 직접 고친다.
- master : (screen, group)마다 가장 큰 파일 하나에 Y. 이미지 생성은 master만 한다.
"""
import argparse
import csv
import re
from pathlib import Path

from PIL import Image

EXTS = {".png", ".jpg", ".jpeg", ".webp"}

# App Store Connect 허용 픽셀(세로 기준). 가로 이미지는 뒤집어서 매칭한다.
# 참고용 — 최신 규격은 App Store Connect 도움말 "Screenshot specifications"에서 확인.
APP_STORE = {
    (1320, 2868): "iPhone 6.9", (1290, 2796): "iPhone 6.9",
    (1284, 2778): "iPhone 6.5", (1242, 2688): "iPhone 6.5",
    (1206, 2622): "iPhone 6.3", (1179, 2556): "iPhone 6.3",
    (1170, 2532): "iPhone 6.1", (1125, 2436): "iPhone 6.1", (1080, 2340): "iPhone 6.1",
    (1242, 2208): "iPhone 5.5",
    (2064, 2752): "iPad 13", (2048, 2732): "iPad 13",
    (1668, 2420): "iPad 11", (1668, 2388): "iPad 11", (1640, 2360): "iPad 11", (1488, 2266): "iPad 11",
}

RATIO_TOL = 0.02  # 비율 차이 2% 이내면 같은 그룹


def play_issues(w, h, has_alpha, size_mb):
    """Google Play 스크린샷 규칙: 변 320~3840px, 긴 변 <= 짧은 변 x2, 알파 없음, 8MB 이하."""
    issues = []
    if min(w, h) < 320 or max(w, h) > 3840:
        issues.append("변 길이 320~3840px 벗어남")
    if max(w, h) > 2 * min(w, h):
        issues.append(f"비율 {max(w, h) / min(w, h):.2f}:1 > 2:1")
    if has_alpha:
        issues.append("알파 채널 있음")
    if size_mb > 8:
        issues.append(f"{size_mb:.1f}MB > 8MB")
    return issues


def guess_screen(stem):
    m = re.search(r"\d+", stem)
    return f"{int(m.group()):02d}" if m else ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src", type=Path)
    ap.add_argument("-o", "--out", type=Path, default=Path("inventory.csv"))
    args = ap.parse_args()

    rows = []
    for p in sorted(args.src.rglob("*")):
        if p.suffix.lower() not in EXTS or not p.is_file():
            continue
        with Image.open(p) as im:
            w, h = im.size
            has_alpha = im.mode in ("RGBA", "LA", "PA") or "transparency" in im.info
        size_mb = p.stat().st_size / 1_048_576
        rows.append({
            "rel_path": p.relative_to(args.src).as_posix(),
            "width": w, "height": h,
            "orientation": "portrait" if h >= w else "landscape",
            "ratio": round(max(w, h) / min(w, h), 4),
            "appstore_slot": APP_STORE.get((min(w, h), max(w, h)), ""),
            "play_issues": "; ".join(play_issues(w, h, has_alpha, size_mb)),
            "has_alpha": "Y" if has_alpha else "",
            "size_mb": round(size_mb, 2),
            "screen": guess_screen(p.stem),
        })
    if not rows:
        raise SystemExit(f"이미지가 없습니다: {args.src}")

    # 비율 그룹: 방향 + 비율이 RATIO_TOL 이내인 것끼리
    groups = []  # [(orientation, 대표비율, label)]
    for r in sorted(rows, key=lambda r: (r["orientation"], r["ratio"])):
        for o, base, label in groups:
            if o == r["orientation"] and abs(r["ratio"] - base) / base <= RATIO_TOL:
                r["group"] = label
                break
        else:
            label = f"{r['orientation'][0]}{r['ratio']:.2f}"
            groups.append((r["orientation"], r["ratio"], label))
            r["group"] = label

    # (screen, group)마다 가장 큰 파일이 master
    best = {}
    for r in rows:
        k = (r["screen"], r["group"])
        if k not in best or r["width"] * r["height"] > best[k]["width"] * best[k]["height"]:
            best[k] = r
    for r in rows:
        r["master"] = "Y" if best[(r["screen"], r["group"])] is r else ""

    cols = ["rel_path", "screen", "group", "master", "width", "height", "orientation", "ratio",
            "appstore_slot", "play_issues", "has_alpha", "size_mb"]
    with args.out.open("w", newline="", encoding="utf-8-sig") as f:
        wr = csv.DictWriter(f, fieldnames=cols)
        wr.writeheader()
        wr.writerows(rows)

    print(f"{len(rows)}개 파일 → {args.out}")
    for _, base, label in groups:
        members = [r for r in rows if r["group"] == label]
        sizes = sorted({f"{r['width']}x{r['height']}" for r in members})
        print(f"  [{label}] {len(members)}개  사이즈 {', '.join(sizes)}")
    no_screen = [r["rel_path"] for r in rows if not r["screen"]]
    if no_screen:
        print(f"  ! 화면 번호를 못 찾은 파일 {len(no_screen)}개 — inventory.csv의 screen 칸을 채우세요")
    masters = sum(1 for r in rows if r["master"])
    print(f"  생성 대상(master) {masters}장 × 언어 수")


if __name__ == "__main__":
    main()
