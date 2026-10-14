#!/usr/bin/env python3
"""jobs.jsonl의 작업을 Codex `$imagegen`(ChatGPT 구독 계정, API 키 X)으로 돌린다.

usage: python3 -I scripts/run_batch.py [jobs.jsonl] [--parallel 3] [--only ja] [--dry-run]

작업마다 output/work/<lang>/<job_id>/ 에 ref.png, out.png, codex.log, status 를 남긴다.
"GPT 이미지 생성 사용법" 문서의 필수 네 조각을 여기서 항상 붙인다:
  -m gpt-5.6-terra / stdin 닫기(< /dev/null) / "Save the result as out.png ..." / (mac) node@22 PATH
status=OK 이면서 out.png가 있으면 다시 돌리지 않는다(재실행 = 실패분만 재시도).
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from PIL import Image

SUFFIX = " Save the result as out.png in the current directory."
MAC_NODE22 = "/opt/homebrew/opt/node@22/bin"  # mac에서 기본 node@20이 깨져 있을 때의 우회로


def run_one(job, workdir, codex, model, use_stdin, timeout):
    d = workdir / job["lang"] / job["job_id"]
    d.mkdir(parents=True, exist_ok=True)
    status, out = d / "status", d / "out.png"
    if status.exists() and status.read_text().strip() == "OK" and out.exists():
        return job, "SKIP", 0.0

    with Image.open(job["src"]) as im:  # 레퍼런스는 항상 ref.png 이름으로 같은 폴더에
        im.convert("RGB").save(d / "ref.png")
    out.unlink(missing_ok=True)

    prompt = "$imagegen " + job["prompt"] + SUFFIX
    cmd = [codex, "exec", "-m", model, "--skip-git-repo-check",
           "--dangerously-bypass-approvals-and-sandbox"]
    env = dict(os.environ)
    if os.path.isdir(MAC_NODE22):
        env["PATH"] = MAC_NODE22 + os.pathsep + env.get("PATH", "")

    t0 = time.time()
    with (d / "codex.log").open("w", encoding="utf-8") as log:
        log.write(prompt + "\n\n" + "=" * 60 + "\n")
        log.flush()
        try:
            if use_stdin:  # Windows: codex.cmd가 여러 줄 인자를 깨뜨리므로 프롬프트를 stdin으로
                subprocess.run(cmd + ["-"], cwd=d, env=env, input=prompt, text=True,
                               encoding="utf-8", stdout=log, stderr=subprocess.STDOUT, timeout=timeout)
            else:
                subprocess.run(cmd + [prompt], cwd=d, env=env, stdin=subprocess.DEVNULL,
                               stdout=log, stderr=subprocess.STDOUT, timeout=timeout)
        except subprocess.TimeoutExpired:
            log.write(f"\n[run_batch] timeout {timeout}s\n")
    # 실패가 조용하므로 종료 코드가 아니라 out.png 존재로 판정한다
    ok = out.exists() and out.stat().st_size > 0
    status.write_text("OK" if ok else "FAIL")
    return job, "OK" if ok else "FAIL", time.time() - t0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("jobs", type=Path, nargs="?", default=Path("jobs.jsonl"))
    ap.add_argument("--workdir", type=Path, default=Path("output/work"))
    ap.add_argument("--model", default="gpt-5.6-terra")
    ap.add_argument("--parallel", type=int, default=3)
    ap.add_argument("--only", default="", help="쉼표 구분 필터: 언어 코드 또는 job_id (예: ja,s01_p2.17)")
    ap.add_argument("--limit", type=int, default=0, help="앞에서 N개만 (시험용)")
    ap.add_argument("--timeout", type=int, default=900, help="작업당 제한 시간(초)")
    ap.add_argument("--stdin-prompt", action="store_true", help="프롬프트를 stdin으로 전달 (Windows는 자동)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    jobs = [json.loads(l) for l in args.jobs.read_text(encoding="utf-8").splitlines() if l.strip()]
    if args.only:
        keys = {k.strip() for k in args.only.split(",")}
        jobs = [j for j in jobs if j["lang"] in keys or j["job_id"] in keys]
    if args.limit:
        jobs = jobs[:args.limit]
    if not jobs:
        raise SystemExit("돌릴 작업이 없습니다")

    codex = shutil.which("codex")
    use_stdin = args.stdin_prompt or os.name == "nt"
    if args.dry_run:
        for j in jobs:
            print(f"[{j['lang']}/{j['job_id']}] {j['src']}\n{j['prompt']}\n")
        print(f"{len(jobs)}개 작업 (dry-run, codex={codex}, model={args.model})")
        return
    if not codex:
        raise SystemExit("codex CLI가 없습니다: npm i -g @openai/codex")
    if subprocess.run([codex, "login", "status"], stdin=subprocess.DEVNULL,
                      capture_output=True).returncode != 0:
        raise SystemExit("codex 로그인이 안 되어 있습니다: codex login (원격이면 codex login --device-auth)")

    print(f"{len(jobs)}개 작업, 동시 {args.parallel}개, model={args.model}", flush=True)
    counts = {"OK": 0, "FAIL": 0, "SKIP": 0}
    with ThreadPoolExecutor(max_workers=args.parallel) as ex:
        futs = [ex.submit(run_one, j, args.workdir, codex, args.model, use_stdin, args.timeout) for j in jobs]
        for f in as_completed(futs):
            job, st, sec = f.result()
            counts[st] += 1
            print(f"{st:4} {job['lang']}/{job['job_id']} ({sec:.0f}s)", flush=True)
    print(f"완료: {counts}", flush=True)
    if counts["FAIL"]:
        print(f"실패 로그: {args.workdir}/<lang>/<job_id>/codex.log — 같은 명령을 다시 돌리면 실패분만 재시도", flush=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
