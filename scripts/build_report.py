#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""★★★ 기사를 회사 내부 보고 서식(.docx)으로 만든다.

내부 서식 규격(회의록 minute 스킬과 동일 계열):
  - 글꼴 바탕체, A4(여백 상하 1418 / 좌우 1134 dxa), 줄간격 1줄
  - 제목(20pt 굵게 밑줄 가운데) → 일자(우측) → 작성부서(우측)
  - 본문 3단 계층을 들여쓰기(w:ind hanging)로 구현
      h  = □ (Level 1, 굵게)      ind 580 / hanging 420
      -  = - (Level 2)            ind 600 / hanging 280
      d  = · (Level 3)            ind 760 / hanging 280
      note = ※ (11pt 참고)        ind 810 / hanging 330
      imp  = ⇒ (도출·시사점)      ind 900 / hanging 420
  - 종결 "- 以 上 -" 우측 정렬

입력: 에이전트가 기사별로 쓴 report.json (형식은 아래 build_document_xml 주석 참고).
사용:
  python3 scripts/build_report.py reports/docx/2026-09-22_2026-09-22-14.report.json
  python3 scripts/build_report.py reports/docx/*.report.json      # 여러 개
  python3 scripts/build_report.py --from-data data/2026-09-22.json # ★★★만 뼈대 생성
각 입력 옆에 같은 이름의 .docx 를 만든다.
"""
import glob
import json
import sys
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

FONT = "바탕체"

CONTENT_TYPES = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
    '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
    '<Default Extension="xml" ContentType="application/xml"/>'
    '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
    '<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>'
    '</Types>'
)
RELS = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
    '</Relationships>'
)
DOC_RELS = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
    '</Relationships>'
)
STYLES = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
    '<w:docDefaults><w:rPrDefault><w:rPr>'
    f'<w:rFonts w:ascii="{FONT}" w:eastAsia="{FONT}" w:hAnsi="{FONT}"/>'
    '<w:color w:val="000000"/><w:sz w:val="28"/><w:szCs w:val="28"/></w:rPr></w:rPrDefault>'
    '<w:pPrDefault><w:pPr><w:spacing w:after="320" w:line="240" w:lineRule="auto"/>'
    '<w:jc w:val="left"/></w:pPr></w:pPrDefault></w:docDefaults>'
    '<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/></w:style>'
    '</w:styles>'
)

# 계층별 (기호, ind left, hanging, sz, bold, note-size)
LEVELS = {
    "h":    ("□", 580, 420, 28, True),   # □
    "-":    ("-",      600, 280, 28, False),
    "d":    ("·", 760, 280, 28, False),  # ·
    "note": ("※", 810, 330, 22, False),  # ※ 11pt
    "imp":  ("⇒", 900, 420, 28, False),  # ⇒
}


def para(sym, left, hanging, sz, bold, text, after=320):
    b = "<w:b/>" if bold else ""
    rpr = f"<w:rPr>{b}<w:sz w:val=\"{sz}\"/><w:szCs w:val=\"{sz}\"/></w:rPr>"
    return (
        f'<w:p><w:pPr><w:ind w:left="{left}" w:hanging="{hanging}"/>'
        f'<w:spacing w:after="{after}"/></w:pPr>'
        f'<w:r>{rpr}<w:t xml:space="preserve">{escape(sym)}</w:t></w:r>'
        f'<w:r>{rpr}<w:tab/><w:t xml:space="preserve">{escape(text)}</w:t></w:r></w:p>'
    )


def build_document_xml(rep):
    """rep = {
        "title": "...(보고)",
        "date":  "'26. 9. 21(월)",     # 없으면 생략
        "dept":  "원전영업팀 (원자력 해외영업)",
        "body":  [ {"lv":"h|-|d|note|imp", "t":"..."}, ... ]
    }  lv 기본은 '-'.
    """
    out = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
           '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>']
    # 제목
    out.append(
        '<w:p><w:pPr><w:jc w:val="center"/><w:spacing w:before="120" w:after="200"/></w:pPr>'
        '<w:r><w:rPr><w:b/><w:u w:val="single"/><w:sz w:val="40"/><w:szCs w:val="40"/></w:rPr>'
        f'<w:t xml:space="preserve">{escape(rep["title"])}</w:t></w:r></w:p>')
    # 일자
    if rep.get("date"):
        out.append(
            '<w:p><w:pPr><w:jc w:val="right"/><w:spacing w:after="40"/></w:pPr>'
            '<w:r><w:rPr><w:sz w:val="26"/><w:szCs w:val="26"/></w:rPr>'
            f'<w:t xml:space="preserve">{escape(rep["date"])}</w:t></w:r></w:p>')
    # 작성 부서
    if rep.get("dept"):
        out.append(
            '<w:p><w:pPr><w:jc w:val="right"/><w:spacing w:after="360"/></w:pPr>'
            '<w:r><w:rPr><w:sz w:val="24"/><w:szCs w:val="24"/></w:rPr>'
            f'<w:t xml:space="preserve">{escape(rep["dept"])}</w:t></w:r></w:p>')
    # 본문
    items = rep.get("body", [])
    for i, it in enumerate(items):
        lv = it.get("lv", "-")
        sym, left, hanging, sz, bold = LEVELS.get(lv, LEVELS["-"])
        # 마지막 본문 단락은 뒤 간격을 넓혀 종결부와 분리
        after = 480 if i == len(items) - 1 else 320
        out.append(para(sym, left, hanging, sz, bold, it.get("t", ""), after))
    # 종결
    out.append(
        '<w:p><w:pPr><w:jc w:val="right"/><w:spacing w:after="0"/></w:pPr>'
        '<w:r><w:t xml:space="preserve">- 以 上 -</w:t></w:r></w:p>')
    out.append(
        '<w:sectPr><w:pgSz w:w="11906" w:h="16838"/>'
        '<w:pgMar w:top="1418" w:right="1134" w:bottom="1418" w:left="1134" '
        'w:header="851" w:footer="851" w:gutter="0"/></w:sectPr></w:body></w:document>')
    return "".join(out)


def write_docx(rep, out_path):
    doc = build_document_xml(rep)
    parts = {
        "[Content_Types].xml": CONTENT_TYPES,
        "_rels/.rels": RELS,
        "word/document.xml": doc,
        "word/styles.xml": STYLES,
        "word/_rels/document.xml.rels": DOC_RELS,
    }
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in parts.items():
            z.writestr(name, data)


def skeleton_from_article(a, date):
    """data/DATE.json 의 기사 하나로 report.json 뼈대를 만든다(사람/에이전트가 채움)."""
    return {
        "title": f'{a.get("title_ko", a.get("title", ""))}(보고)',
        "date": None,  # 예: "'26. 9. 21(월)" — 에이전트가 게재일로 채운다
        "dept": "원전영업팀 (원자력 해외영업)",
        "_article_id": a.get("id"),
        "_source": f'{a.get("source", "")} / {a.get("url", "")}',
        "_summary_ko": a.get("summary_ko", ""),
        "_sales_note": a.get("sales_note", ""),
        "body": [
            {"lv": "h", "t": "보고 배경"},
            {"lv": "-", "t": "(요약을 개조식으로 — 무엇을/누가/어디서/언제)"},
            {"lv": "h", "t": "주요 내용"},
            {"lv": "d", "t": "(수치·범위·대상·일정 등 세부를 · 항목으로 분해)"},
            {"lv": "note", "t": f'출처 : {a.get("source", "")} (게재일 병기) / 확정 시 수치 변동 가능'},
            {"lv": "h", "t": "시사점(당사 해외사업 관점)"},
            {"lv": "-", "t": a.get("sales_note", "(sales_note 기반 영업 시사점)")},
            {"lv": "imp", "t": "(후속 확인·추적 사항)"},
        ],
    }


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if "--from-data" in sys.argv:
        data_path = Path(args[0])
        data = json.loads(data_path.read_text(encoding="utf-8"))
        date = data["date"]
        outdir = Path("reports/docx")
        outdir.mkdir(parents=True, exist_ok=True)
        made = []
        for a in data["articles"]:
            if a.get("importance") == 3:
                rep = skeleton_from_article(a, date)
                p = outdir / f'{date}_{a["id"]}.report.json'
                p.write_text(json.dumps(rep, ensure_ascii=False, indent=2), encoding="utf-8")
                made.append(str(p))
        print("skeleton report.json created (본문을 채운 뒤 이 스크립트를 다시 실행):")
        print("\n".join(made) if made else "  (★★★ 기사 없음)")
        return

    paths = []
    for a in args:
        paths.extend(glob.glob(a))
    if not paths:
        sys.exit("입력할 report.json 을 지정하세요. (--from-data data/DATE.json 로 뼈대 생성 가능)")
    for p in paths:
        rep = json.loads(Path(p).read_text(encoding="utf-8"))
        out = str(Path(p).with_suffix("")).replace(".report", "") + ".docx"
        write_docx(rep, out)
        print(f"WROTE {out}")


if __name__ == "__main__":
    main()
