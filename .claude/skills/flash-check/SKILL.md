---
name: flash-check
description: 낮 시간 속보 점검. 공고 포털의 신규·마감임박 공고와 경쟁사 속보 계약만 가볍게 훑어 pipeline-watch 에 기록하고 속보 메일을 띄운다. 전체 브리핑(nuclear-news-daily)은 건드리지 않는다. 하루 2회(오후 1·6시) Sonnet 실행용.
---

# 파이프라인 속보 점검 (경량)

오전 8시 전체 브리핑과 별개로 **낮에 두 번** 도는 가벼운 점검이다. 목적은 딱 두 가지다.
1. 공고 포털의 **신규 공고**와 **마감 임박(D-7 이내)**
2. 경쟁사·파트너의 **속보성 계약**(MOU·LOI·contract award·FEED 수주 등)

**요약·번역·시사점을 길게 쓰지 않는다. 빠르고 싸게.** 검색 횟수를 아낀다. 새 건이 없으면 아무 파일도 쓰지 않는다(메일도 안 감).

## 0. 준비
- `pipeline-watch` 저장소가 클론돼 있어야 한다. 없으면 아무 것도 하지 말고 끝낸다.
- DATE = 오늘(Asia/Seoul). NOW = 현재 시각 `HH:MM`(KST).
- 읽기: `pipeline-watch/config/watchlist.yaml`, `config/tender_sources.yaml`, `tenders/seen.json`, `tenders/open.json`, `data/map-data.js`.
- **공개 저장소 `nuclear-news-daily` 의 어떤 파일도 쓰지 않는다.** data/·reports/·index.html 손대지 말 것.

## 1. 공고 (핵심)
- `tender_sources.yaml`의 포털 중 **우선순위 높은 곳만** 훑는다: TED, UK FTS, CanadaBuys, SAM.gov, Etimad, OSGE, Rolls-Royce SMR. (나머지는 전체 브리핑이 매일 훑으므로 생략)
- 각 포털에 `WebSearch`(allowed_domains=포털) + queries 로 신규 공고를 찾는다. 나온 공고는 WebFetch 로 마감일·발주처만 확인(막히면 "마감일 미확인").
- `tenders/seen.json` 과 대조해 **이미 본 공고는 제외**. `our_scope_keywords`(FEED 최우선)와 워치리스트로 관련성 판단.
- `tenders/open.json` 에서 오늘 기준 **D-7·D-3** 도달 건을 `[마감임박]`으로 뽑는다.

## 2. 속보 계약
- `topics.yaml`의 `industry_queries` 중 계약·협약 관련 2~3개만 오늘 날짜로 검색(예: "nuclear teaming agreement letter of intent {date}", "SMR developer MOU signed {date}", "FEED contract nuclear {date}").
- 워치리스트의 사업·파트너·경쟁 노형에 걸리는 **오늘·어제자 신규 계약**만. 오래된 건·이미 다룬 건 제외.

## 3. 기록 (새 건이 있을 때만)
새로 찾은 것이 **하나도 없으면 3~5단계를 건너뛰고 끝낸다.** (한 줄 보고: "속보 없음")

있으면 `pipeline-watch/alerts/flash/DATE-flash.md` 를 연다(없으면 만들고, 있으면 이어쓴다):

```markdown
# 파이프라인 속보 — YYYY-MM-DD

## HH:MM 점검
### [긴급|마감임박|주의|참고] <제목>
- 포털·출처: TED 155441-2026 / <URL>
- 발주처·주체: <기관·회사>
- 마감: 2026-10-12 (D-20)   ← 없으면 생략
- 한줄: 무엇이 새로운지 한 문장
- 관계: <워치리스트의 어느 대상>
```
- 이번 점검에서 새로 찾은 것만 이 시각 섹션에 넣는다. 이전 시각 섹션은 그대로 둔다.
- 요약은 한 줄. 길게 쓰지 않는다.

## 4. 목록·지도 갱신
- 새 공고를 `tenders/seen.json`(추가)과 `tenders/open.json`(마감 전이면 추가)에 반영.
- `data/map-data.js` 의 `tenders` 배열에 새 공고를, `alerts` 에 새 건 한 줄씩 추가하고 `updated` 를 오늘로. (형식은 기존 파일 그대로, `window.PIPELINE = {...};`. python3 로 문법 검증.)
- 사업명·파트너·단계를 공개 저장소로 내보내지 않는다.

## 5. 게시
```
cd pipeline-watch
git add alerts/flash tenders data
git commit -m "flash: DATE HH:MM (신규 N건)"
git push
```
- push 되면 속보 메일이 자동 발송된다. **새 건이 없으면 push 하지 않는다**(불필요한 메일 방지).
- 마지막 보고는 3줄 이내: 점검 시각, 신규 공고 N건·속보 M건, 가장 급한 건 한 줄.
