"""일일 브리핑 JSON을 HTML 메일로 만들어 발송한다.

환경변수 (GitHub Secrets):
  SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS  — 발신 SMTP (Gmail: smtp.gmail.com / 465 / 주소 / 앱 비밀번호)
  MAIL_TO     — 받는 사람, 쉼표로 구분 (저장소가 공개라서 주소는 파일이 아닌 Secret에 둔다)
  MAIL_FROM   — 선택. 표시 발신자 (기본: SMTP_USER)
  PAGE_URL    — 선택. 웹 뷰어 주소
사용: python scripts/send_mail.py [YYYY-MM-DD]   (날짜 생략 시 data/index.json의 최신 날짜)
      --dry-run  발송하지 않고 out/mail-DATE.html 로 저장
"""
import html
import json
import os
import smtplib
import sys
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CAT = {"large": "대형원전", "smr": "SMR", "policy": "정책·정세", "fuel": "연료·공급망"}
CAT_COLOR = {"large": "#2c5a86", "smr": "#0d8474", "policy": "#946018", "fuel": "#6a4c9c"}
STANCE = {"expanding": ("확대", "#1f7a4d"), "steady": ("유지", "#65757c"),
          "cautious": ("신중", "#b0701a"), "retreating": ("축소", "#b23b3b")}
LANG = {"cs": "체코어", "pl": "폴란드어", "sk": "슬로바키아어", "sl": "슬로베니아어", "hu": "헝가리어",
        "ro": "루마니아어", "bg": "불가리아어", "nl": "네덜란드어", "sv": "스웨덴어", "fi": "핀란드어",
        "fr": "프랑스어", "de": "독일어", "tr": "튀르키예어", "ar": "아랍어", "ru": "러시아어",
        "vi": "베트남어", "id": "인도네시아어", "th": "태국어", "ja": "일본어", "zh": "중국어", "ko": "한국어"}
WD = "월화수목금토일"
e = html.escape


def load(date):
    if not date:
        date = json.loads((ROOT / "data/index.json").read_text(encoding="utf-8"))["days"][0]["date"]
    return json.loads((ROOT / f"data/{date}.json").read_text(encoding="utf-8"))


def kdate(d):
    import datetime
    y, m, dd = map(int, d.split("-"))
    return f"{y}년 {m}월 {dd}일 ({WD[datetime.date(y, m, dd).weekday()]})"


def build(d, page_url):
    arts = d["articles"]
    key = [a for a in arts if a["importance"] == 3]
    link = f"{page_url}?d={d['date']}" if page_url else ""

    def article(a):
        lang = a.get("language", "en")
        lang_tag = f' · 원문 {e(LANG.get(lang, lang))}' if lang != "en" else ""
        note = (f'<div style="margin-top:8px;padding:8px 12px;background:#f3f7f9;border-left:3px solid #0a6f96;'
                f'font-size:14px;color:#132026"><b style="color:#0a6f96;font-size:12px">영업 시사점</b><br>{e(a["sales_note"])}</div>'
                if a.get("sales_note") else "")
        return (f'<tr><td style="padding:14px 0;border-bottom:1px solid #e9edef">'
                f'<div style="font-size:12px;color:#65757c"><span style="color:#c98a12">{"★" * a["importance"]}</span> '
                f'{e(" · ".join(a["countries"]))}{lang_tag} · {e(a["source"])} · {e(a["published"])}</div>'
                f'<div style="margin-top:4px;font-size:16px;font-weight:bold;line-height:1.45">'
                f'<a href="{e(a["url"])}" style="color:#132026;text-decoration:none">{e(a["title_ko"])}</a></div>'
                f'<div style="font-size:12px;color:#8a979c;margin-top:2px">{e(a["title"])}</div>'
                f'<div style="margin-top:8px;font-size:14px;line-height:1.65;color:#34454d">{e(a["summary_ko"])}</div>'
                f'{note}</td></tr>')

    def sections(region_arts):
        out = ""
        for k in ["large", "smr", "policy", "fuel"]:
            items = sorted([a for a in region_arts if a["category"] == k], key=lambda a: a["published"], reverse=True)
            items.sort(key=lambda a: -a["importance"])
            if not items:
                continue
            out += (f'<h3 style="margin:24px 0 4px;font-size:16px;color:#132026;border-bottom:2px solid {CAT_COLOR[k]};padding-bottom:6px">'
                    f'{CAT[k]} <span style="font-size:13px;color:#65757c;font-weight:normal">{len(items)}건</span></h3>'
                    f'<table width="100%" cellpadding="0" cellspacing="0">{"".join(article(a) for a in items)}</table>')
        return out

    def summary(text):
        parts = text.split("영업 관점:")
        return (f'<p style="margin:0;font-size:14.5px;line-height:1.7;color:#34454d">{e(parts[0].strip())}</p>'
                + (f'<div style="margin-top:12px;background:#e3f0f6;padding:12px 14px;border-radius:6px;font-size:14.5px">'
                   f'<b style="color:#0a6f96">영업 관점</b> {e(parts[1].strip())}</div>' if len(parts) > 1 else ""))

    def keylist(items):
        if not items:
            return ""
        lis = "".join(
            f'<li style="margin:0 0 10px"><b>[{CAT[a["category"]]}]</b> '
            f'<a href="{e(a["url"])}" style="color:#0a6f96">{e(a["title_ko"])}</a>'
            f'<div style="color:#65757c;font-size:13px">{e(a.get("sales_note") or a["summary_ko"])}</div></li>' for a in items)
        return (f'<h3 style="margin:22px 0 8px;font-size:16px">핵심 기사 ★★★</h3>'
                f'<ul style="margin:0;padding-left:18px;font-size:14.5px;line-height:1.55">{lis}</ul>')

    def region_head(label, n):
        return (f'<h2 style="margin:34px 0 12px;font-size:19px;color:#ffffff;background:#10262f;padding:8px 14px;border-radius:6px">'
                f'{label} <span style="font-size:13px;color:#9fb6bf;font-weight:normal">{n}건</span></h2>')

    ov = [a for a in arts if a.get("region", "overseas") == "overseas"]
    dm = [a for a in arts if a.get("region") == "domestic"]

    pulse = "".join(
        f'<tr><td style="padding:8px 10px;border-bottom:1px solid #e9edef;font-weight:bold;white-space:nowrap;vertical-align:top">{e(p["name_ko"])}</td>'
        f'<td style="padding:8px 10px;border-bottom:1px solid #e9edef;white-space:nowrap;vertical-align:top;color:{STANCE.get(p["stance"], ("", "#65757c"))[1]};font-weight:bold">'
        f'● {STANCE.get(p["stance"], (p["stance"],))[0]}</td>'
        f'<td style="padding:8px 10px;border-bottom:1px solid #e9edef;color:#34454d;vertical-align:top">{e(p["signal"])}</td></tr>'
        for p in d["countries_pulse"])

    btn = (f'<p style="margin:24px 0 0;text-align:center"><a href="{e(link)}" style="display:inline-block;background:#0a6f96;color:#fff;'
           f'text-decoration:none;padding:10px 22px;border-radius:6px;font-weight:bold">웹에서 필터·검색하며 보기</a></p>') if link else ""

    return f"""<!doctype html><html><body style="margin:0;background:#eef1f3">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#eef1f3"><tr><td align="center" style="padding:20px 10px">
<table width="100%" cellpadding="0" cellspacing="0" style="max-width:680px;background:#ffffff;border-radius:10px;font-family:'Malgun Gothic','Apple SD Gothic Neo',sans-serif;color:#132026">
<tr><td style="background:#10262f;color:#e8f1f4;padding:18px 24px;border-radius:10px 10px 0 0">
<div style="font-size:11px;letter-spacing:2px;color:#7fc9e4">OVERSEAS NUCLEAR BRIEF</div>
<div style="font-size:21px;font-weight:bold;margin-top:4px">{kdate(d['date'])} 원자력 해외동향</div>
<div style="font-size:12px;color:#9fb6bf;margin-top:4px">수집 {e(d['period']['from'])} ~ {e(d['period']['to'])} · 해외 {len(ov)}건 · 국내 {len(dm)}건 · 핵심 {len(key)}건</div>
</td></tr>
<tr><td style="padding:4px 24px 28px">
{region_head("해외", len(ov))}
{summary(d["overview_ko"])}
{keylist([a for a in ov if a["importance"] == 3])}
<h3 style="margin:22px 0 8px;font-size:16px">국가별 정세</h3>
<table width="100%" cellpadding="0" cellspacing="0" style="font-size:13.5px;line-height:1.5">{pulse}</table>
{sections(ov)}
{region_head("국내", len(dm))}
{summary(d.get("domestic_overview_ko") or "국내 기사 없음.")}
{keylist([a for a in dm if a["importance"] == 3])}
{sections(dm)}
{btn}
<p style="margin:24px 0 0;padding-top:12px;border-top:1px solid #e9edef;font-size:12px;color:#132026;font-weight:bold">내부 참고용 자료입니다. 외부 공유를 금합니다.<br><span style="font-weight:normal;color:#65757c">Internal reference only. Not for external distribution.</span></p>
<p style="margin:10px 0 0;font-size:11.5px;color:#8a979c">AI 에이전트가 해외·국내 매체와 현지어 기사를 수집해 한국어로 요약했습니다. 요약과 시사점은 참고용이며 원문으로 확인하세요.</p>
</td></tr></table></td></tr></table></body></html>"""


def build_text(d, page_url):
    lines = [f"{kdate(d['date'])} 원자력 해외동향", "내부 참고용 자료입니다. 외부 공유를 금합니다. / Internal reference only.", "", "[해외] " + d["overview_ko"], "",
             "[국내] " + (d.get("domestic_overview_ko") or "국내 기사 없음."), ""]
    for a in d["articles"]:
        rg = "국내" if a.get("region") == "domestic" else "해외"
        lines += [f"[{rg}·{CAT[a['category']]}] {'★' * a['importance']} {a['title_ko']}", a["url"], ""]
    if page_url:
        lines.append(f"{page_url}?d={d['date']}")
    return "\n".join(lines)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    dry = "--dry-run" in sys.argv
    d = load(args[0] if args else None)
    page_url = os.environ.get("PAGE_URL", "").strip()
    body = build(d, page_url)
    top = next((a for a in d["articles"] if a["importance"] == 3), d["articles"][0] if d["articles"] else None)
    subject = f"[원자력 해외동향] {d['date']} — {top['title_ko'] if top else '브리핑'}"

    if dry:
        out = ROOT / "out"
        out.mkdir(exist_ok=True)
        (out / f"mail-{d['date']}.html").write_text(body, encoding="utf-8")
        print(f"saved out/mail-{d['date']}.html | {subject}")
        return

    to = [x.strip() for x in os.environ["MAIL_TO"].replace(";", ",").split(",") if x.strip()]
    user = os.environ["SMTP_USER"]
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = formataddr(("원자력 해외동향 브리핑", os.environ.get("MAIL_FROM") or user))
    msg["To"] = formataddr(("원자력 해외동향 브리핑", os.environ.get("MAIL_FROM") or user))
    msg.attach(MIMEText(build_text(d, page_url), "plain", "utf-8"))
    msg.attach(MIMEText(body, "html", "utf-8"))

    host = os.environ.get("SMTP_HOST") or "smtp.gmail.com"
    port = int(os.environ.get("SMTP_PORT") or "465")
    if port == 465:
        s = smtplib.SMTP_SSL(host, port, timeout=60)
    else:
        s = smtplib.SMTP(host, port, timeout=60)
        s.starttls()
    with s:
        s.login(user, os.environ["SMTP_PASS"])
        s.sendmail(user, to, msg.as_string())  # 받는 사람은 숨은참조처럼 전달 (서로 주소 노출 안 됨)
    print(f"sent to {len(to)} recipient(s) | {subject}")


if __name__ == "__main__":
    main()
