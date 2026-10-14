# DITTI 스토어 스크린샷 다국어화

한국어 App Store / Google Play 스크린샷을 **영어·일본어·중국어 번체·중국어 간체**로 만든다.
이미지 생성은 ChatGPT 개인 구독 계정으로 로그인한 Codex CLI의 `$imagegen`을 쓴다 (API 키·별도 과금 없음).

```
원본 폴더 ──inventory.py──▶ inventory.csv   (사이즈·비율 그룹·화면 번호·스토어 규격 점검)
            (Claude가 읽음)─▶ strings.csv    (이미지 속 한국어 전부 + 4개 언어 번역)
          ──build_jobs.py─▶ jobs.jsonl      (master × 언어마다 프롬프트 한 개)
          ──run_batch.py──▶ output/work/<lang>/<job>/out.png   (Codex $imagegen)
          ──contact_sheet.py▶ output/review/                    (원본|en|ja|번체|간체 비교 검수)
          ──fit_size.py───▶ output/final/<lang>/<원본과 같은 경로>  (정확한 픽셀, 알파 제거)
```

같은 화면이라도 사이즈가 여러 개면, **비율이 같은 파일끼리는 가장 큰 것 한 장(master)만 생성**하고
나머지는 `fit_size.py`가 크기만 맞춘다. 생성 장수 = 화면 수 × 비율 그룹 수 × 4.

---

## 1. GPT 계정 연결 (Codex CLI, ChatGPT 로그인)

### 이 클라우드 세션 (Linux)

```bash
npm i -g @openai/codex          # 설치됨: codex-cli 0.162.1
codex login --device-auth       # URL + 코드가 뜬다 → 브라우저에서 개인 ChatGPT 계정으로 승인
codex login status              # "Logged in using ChatGPT" 이면 완료
```

- **네트워크 허용이 먼저 필요하다.** 기본 정책은 `auth.openai.com`, `chatgpt.com`을 막는다
  (`error sending request for url (https://auth.openai.com/api/accounts/deviceauth/usercode)`).
  환경 설정 → Network access에서 두 도메인을 Allowed domains에 추가.
  이미지 저장 단계에서 다른 호스트가 막히면 `codex.log`에 찍힌 호스트를 추가한다.
- device code 로그인이 거부되면 ChatGPT 설정 → 보안에서 Codex용 device code 로그인을 켠다.
- 로그인 정보(`~/.codex/auth.json`)는 **컨테이너 안에만** 있다. 세션 컨테이너가 바뀌면 다시 로그인.
  비밀번호와 같은 자격 증명이므로 저장소에 절대 커밋하지 않는다.

### 로컬 Windows (원본이 `D:\Downloads\...`에 있을 때 가장 간단)

```powershell
npm i -g @openai/codex
codex login                     # 브라우저가 열림 → 개인 ChatGPT 계정으로 로그인
pip install pillow
```
이후 명령은 아래와 같고 `python3 -I` 대신 `python -I`. Windows에서는 `run_batch.py`가 프롬프트를 자동으로 stdin으로 넘긴다.

### 원본 사용법 문서(mac)와 다른 점

| 문서의 필수 조각 | 여기서는 |
|---|---|
| `PATH=.../node@22/bin` | Linux는 기본 node가 22라 불필요. mac에서 `/opt/homebrew/opt/node@22/bin`이 있으면 `run_batch.py`가 자동으로 붙인다 |
| `-m gpt-5.6-terra` | `run_batch.py` 기본값. 400이 나면 `--model`로 교체 (문서 7절의 models_cache 확인) |
| `< /dev/null` | `run_batch.py`가 stdin을 닫고 실행 |
| `Save the result as out.png ...` | `run_batch.py`가 모든 프롬프트 끝에 붙인다 |
| 조용한 실패 | 종료 코드가 아니라 `out.png` 존재로 판정해 `status`에 OK/FAIL |

한 장 스모크 테스트:
```bash
mkdir -p /tmp/imgtest && cd /tmp/imgtest && rm -f out.png
codex exec -m gpt-5.6-terra --skip-git-repo-check --dangerously-bypass-approvals-and-sandbox \
  '$imagegen A single small red circle on white background, flat vector, minimal. Save the result as out.png in the current directory.' \
  < /dev/null
ls -la out.png
```

---

## 2. 원본 넣기

클라우드 세션은 로컬 `D:\` 드라이브에 접근할 수 없다.
`D:\Downloads\DITTI 스크린샷 사이즈별 대응` 폴더를 **zip으로 압축해 채팅에 첨부**하면
폴더 구조(사이즈별 하위 폴더)를 유지한 채 `input/`에 풀어 쓴다. 이미지 파일을 직접 여러 장 첨부해도 된다.

## 3. 순서

모든 명령은 이 폴더(`ditti-store-localization/`)에서 실행한다.

```bash
# 1) 목록·규격 점검 → inventory.csv (screen 칸이 비면 채운다)
python3 -I scripts/inventory.py input/

# 2) strings.csv 채우기 — Claude가 master 이미지를 하나씩 읽어 한국어 전부를 받아 적고 번역
#    규칙: translation_guide.md / 고유 용어: glossary.csv

# 3) 작업 목록
python3 -I scripts/build_jobs.py input/

# 4) 생성 — 먼저 한 장으로 품질·출력 비율 확인 후 전체
python3 -I scripts/run_batch.py --limit 1
python3 -I scripts/run_batch.py --parallel 3      # 다시 돌리면 실패분만 재시도

# 5) 검수 — 비교 이미지를 Claude가 읽어 strings.csv와 대조, 틀린 작업만 --only로 재생성
python3 -I scripts/contact_sheet.py

# 6) 최종 크기 맞추기 → output/final/<lang>/
python3 -I scripts/fit_size.py
```

## strings.csv 컬럼

| 컬럼 | 내용 |
|---|---|
| `key` | 고유 키. `s01.headline`, `s01.sub`, `ui.tab.home` 처럼 |
| `screens` | 이 문구가 나오는 화면 번호. `01` / `01;03` / `*`(전부) |
| `type` | `headline` · `sub` · `ui` · `badge` |
| `ko` | 이미지에 보이는 그대로 (줄바꿈 포함) |
| `en` `ja` `zh-Hant` `zh-Hans` | 번역. 하나라도 비면 `build_jobs.py`가 멈춘다 |
| `notes` | 길이 제약, 현지화 결정이 필요한 것(이름·통화) 등 |

UTF-8(BOM)로 저장되어 엑셀에서 그대로 열린다. 행 순서 = 프롬프트에 들어가는 읽기 순서.

## 스토어 규격 체크 (inventory.py가 자동 점검)

- **App Store**: 슬롯별로 정해진 픽셀만 허용 (`appstore_slot` 칸). `fit_size.py`가 원본과 같은 픽셀로 내보낸다.
- **Google Play**: 변 320~3840px, **긴 변 ≤ 짧은 변 × 2**, 알파 없는 24-bit PNG 또는 JPEG, 8MB 이하.
  iPhone 6.9"(1320×2868, 2.17:1) 같은 세로로 긴 이미지는 Play에 그대로 못 올린다 → `play_issues` 칸.

## 알려진 한계

- `$imagegen`은 원본 픽셀 크기를 그대로 내지 않을 수 있다. 비율 차이가 3%를 넘으면 `fit_size.py`가 멈추고 보고한다
  (`--mode pad` 여백 / `--mode cover` 잘라내기 중 선택, 또는 재생성).
- 작은 UI 글자는 틀리거나 뭉개질 수 있다 → 5단계 검수를 건너뛰지 않는다.
