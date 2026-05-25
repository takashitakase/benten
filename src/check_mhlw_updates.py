#!/usr/bin/env python3
"""
厚生労働省の令和8年度診療報酬改定ページを監視し、
疑義解釈・通知の新着情報をチェックするスクリプト。

新着があった場合は終了コード 2 を返す（GitHub Actions のメール送信ステップ用）。

環境変数（メール通知用、省略時は通知しない）:
  NOTIFY_SMTP_SERVER   - SMTPサーバー（例: smtp.gmail.com）
  NOTIFY_SMTP_PORT     - SMTPポート（例: 587）
  NOTIFY_EMAIL_FROM    - 送信元メールアドレス
  NOTIFY_EMAIL_PASSWORD- 送信元メールパスワード（Gmailはアプリパスワード）
  NOTIFY_EMAIL_TO      - 送信先メールアドレス

Source: https://www.mhlw.go.jp/stf/newpage_67729.html
"""

import hashlib
import json
import os
import re
import smtplib
import sys
import urllib.request
from datetime import datetime, timezone, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

MHLW_R8_URL = "https://www.mhlw.go.jp/stf/newpage_67729.html"
STATE_FILE = Path(__file__).parent.parent / "data" / "processed" / "mhlw_watch_state.json"
REPORT_FILE = Path(__file__).parent.parent / "data" / "processed" / "weekly_report.md"
ISSUE_BODY_FILE = Path(__file__).parent.parent / "data" / "processed" / "issue_body.md"

JST = timezone(timedelta(hours=9))

KEYWORDS_OF_INTEREST = [
    "疑義解釈",
    "施設基準",
    "通知",
    "告示",
    "訂正",
    "事務連絡",
    "Q&A",
    "チェックリスト",
]

# 終了コード
EXIT_NO_UPDATE = 0
EXIT_ERROR = 1
EXIT_HAS_UPDATE = 2


def fetch_page(url: str) -> str:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (compatible; benten-monitor/1.0; "
            "+https://github.com/takashitakase/benten)"
        )
    }
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as resp:
        charset = resp.headers.get_content_charset() or "utf-8"
        return resp.read().decode(charset)


def page_hash(content: str) -> str:
    return hashlib.sha256(content.encode()).hexdigest()


def extract_links(html: str, base_url: str = "https://www.mhlw.go.jp") -> list[dict]:
    """PDFおよび関連リンクを抽出する。"""
    pattern = re.compile(
        r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',
        re.IGNORECASE | re.DOTALL,
    )
    links = []
    for m in pattern.finditer(html):
        href = m.group(1).strip()
        text = re.sub(r"<[^>]+>", "", m.group(2)).strip()
        if not text:
            continue
        if href.startswith("/"):
            href = base_url + href
        if any(kw in text for kw in KEYWORDS_OF_INTEREST) or href.endswith(".pdf"):
            links.append({"href": href, "text": text})
    return links


def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {"last_hash": None, "known_links": [], "last_checked": None}


def save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def write_report(new_links: list[dict], all_links: list[dict], checked_at: str) -> None:
    REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# 令和8年度診療報酬改定 週次更新レポート",
        "",
        f"**確認日時:** {checked_at}（JST）",
        f"**監視URL:** {MHLW_R8_URL}",
        "",
    ]
    if new_links:
        lines += ["## 新着情報", ""]
        for lnk in new_links:
            lines.append(f"- [{lnk['text']}]({lnk['href']})")
        lines.append("")
    else:
        lines += ["## 今週の新着情報", "", "更新はありませんでした。", ""]

    lines += ["## 現在確認されている主な資料", ""]
    for lnk in all_links[:40]:
        lines.append(f"- [{lnk['text']}]({lnk['href']})")

    REPORT_FILE.write_text("\n".join(lines), encoding="utf-8")
    print(f"レポートを保存しました: {REPORT_FILE}")


def write_issue_body(new_links: list[dict], checked_at: str) -> None:
    """GitHub Issue 作成用の本文ファイルを書き出す。"""
    lines = [
        f"確認日時: **{checked_at}（JST）**",
        "",
        "以下の新しい情報が厚生労働省の改定ページに追加されました。",
        "",
    ]
    for lnk in new_links:
        lines.append(f"- [{lnk['text']}]({lnk['href']})")
    lines += [
        "",
        "---",
        f"監視URL: {MHLW_R8_URL}",
    ]
    ISSUE_BODY_FILE.parent.mkdir(parents=True, exist_ok=True)
    ISSUE_BODY_FILE.write_text("\n".join(lines), encoding="utf-8")


def build_email_html(new_links: list[dict], checked_at: str) -> str:
    items_html = "\n".join(
        f'<li><a href="{lnk["href"]}">{lnk["text"]}</a></li>'
        for lnk in new_links
    )
    return f"""<!DOCTYPE html>
<html lang="ja">
<head><meta charset="UTF-8"></head>
<body style="font-family: sans-serif; line-height: 1.7;">
<h2 style="color: #1a5276;">【benten】令和8年度診療報酬改定 新着情報</h2>
<p>確認日時: <strong>{checked_at}（JST）</strong></p>
<p>以下の新しい情報が厚生労働省の改定ページに追加されました。</p>
<ul>
{items_html}
</ul>
<hr>
<p style="font-size: 0.85em; color: #666;">
  監視URL: <a href="{MHLW_R8_URL}">{MHLW_R8_URL}</a><br>
  このメールは自動送信されています。
</p>
</body>
</html>"""


def send_email(new_links: list[dict], checked_at: str) -> None:
    smtp_server = os.environ.get("NOTIFY_SMTP_SERVER", "")
    smtp_port = int(os.environ.get("NOTIFY_SMTP_PORT", "587"))
    email_from = os.environ.get("NOTIFY_EMAIL_FROM", "")
    email_password = os.environ.get("NOTIFY_EMAIL_PASSWORD", "")
    email_to = os.environ.get("NOTIFY_EMAIL_TO", "")

    if not all([smtp_server, email_from, email_password, email_to]):
        print("メール設定が不完全なため、通知をスキップします。（NOTIFY_* 環境変数を確認してください）")
        return

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"【診療報酬改定】新着情報 {len(new_links)}件 ({checked_at})"
    msg["From"] = email_from
    msg["To"] = email_to

    text_body = f"令和8年度診療報酬改定に新着情報が{len(new_links)}件あります。\n\n"
    for lnk in new_links:
        text_body += f"・{lnk['text']}\n  {lnk['href']}\n"
    text_body += f"\n監視URL: {MHLW_R8_URL}"

    msg.attach(MIMEText(text_body, "plain", "utf-8"))
    msg.attach(MIMEText(build_email_html(new_links, checked_at), "html", "utf-8"))

    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.ehlo()
        server.starttls()
        server.login(email_from, email_password)
        server.sendmail(email_from, email_to, msg.as_string())

    print(f"メール通知を送信しました → {email_to}")


def main() -> int:
    now_jst = datetime.now(JST).strftime("%Y-%m-%d %H:%M")
    print(f"[{now_jst} JST] 厚生労働省ページを確認中: {MHLW_R8_URL}")

    try:
        html = fetch_page(MHLW_R8_URL)
    except Exception as exc:
        print(f"ERROR: ページ取得に失敗しました: {exc}", file=sys.stderr)
        return EXIT_ERROR

    current_hash = page_hash(html)
    current_links = extract_links(html)

    state = load_state()
    known_hrefs = {lnk["href"] for lnk in state.get("known_links", [])}
    new_links = [lnk for lnk in current_links if lnk["href"] not in known_hrefs]

    if state["last_hash"] == current_hash:
        print("ページに変更はありませんでした。")
    else:
        print(f"ページが更新されています（前回ハッシュ: {state['last_hash'][:8] if state['last_hash'] else 'なし'}）")
        if new_links:
            print(f"新着リンク {len(new_links)} 件:")
            for lnk in new_links:
                print(f"  - {lnk['text']}\n    {lnk['href']}")

    write_report(new_links, current_links, now_jst)

    if new_links:
        write_issue_body(new_links, now_jst)
        try:
            send_email(new_links, now_jst)
        except Exception as exc:
            print(f"WARNING: メール送信に失敗しました: {exc}", file=sys.stderr)

    state["last_hash"] = current_hash
    state["known_links"] = current_links
    state["last_checked"] = now_jst
    save_state(state)

    return EXIT_HAS_UPDATE if new_links else EXIT_NO_UPDATE


if __name__ == "__main__":
    sys.exit(main())
