# 원자력 해외동향 브리핑

해외영업팀이 매일 아침 해외 원자력 시장 변화를 5분 안에 파악하기 위한 AI 에이전트입니다.

- **다루는 분야**: 대형원전 · SMR · 국가정책/정세 · 연료/공급망
- **기사마다**: 한글 요약, 원문 링크, 국가, 중요도(★1~3), **영업 시사점**
- **매일**: 오늘의 요약, 국가별 정세(확대/유지/신중/축소)

## 보는 법

- 휴대폰·태블릿: https://nuclear-business-development-team.github.io/nuclear-news-daily/
- 원문 보고서: `reports/` 폴더의 날짜별 Markdown
- 데이터: `data/` 폴더의 날짜별 JSON (사내 시스템 연동용)

## 관심 분야 바꾸기

코드를 몰라도 됩니다.
- 관심국가 추가/삭제 → `config/topics.yaml`의 `watch_countries`
- 출처 추가/제외 → `config/sources.yaml`

## 수동 실행

Claude Code에서 이 폴더를 열고:

```
오늘 원자력 뉴스 브리핑 만들어줘
```
