#!/usr/bin/env python3
"""
厚生労働省の令和8年度診療報酬改定ページを監視し、
疑義解釈・通知の新着情報をチェックするスクリプト。

Source: https://www.mhlw.go.jp/stf/newpage_67729.html
"""

import hashlib
import json
import re
import sys
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

MHLW_R8_URL = "https://www.mhlw.go.jp/stf/newpage_67729.html"
STATE_FILE = Path(__file__).parent.parent / "data" / "processed" / "mhlw_watch_state.json"
REPORT_FILE = Path(__file__).parent.parent / "data" / "processed" / "weekly_report.md"

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
        lines += [
            "## 🆕 今週の新着情報",
            "",
        ]
        for lnk in new_links:
            lines.append(f"- [{lnk['text']}]({lnk['href']})")
        lines.append("")
    else:
        lines += ["## 今週の新着情報", "", "更新はありませんでした。", ""]

    lines += [
        "## 現在確認されている主な資料",
        "",
    ]
    for lnk in all_links[:40]:
        lines.append(f"- [{lnk['text']}]({lnk['href']})")

    REPORT_FILE.write_text("\n".join(lines), encoding="utf-8")
    print(f"レポートを保存しました: {REPORT_FILE}")


def main() -> int:
    now_jst = datetime.now(JST).strftime("%Y-%m-%d %H:%M")
    print(f"[{now_jst} JST] 厚生労働省ページを確認中: {MHLW_R8_URL}")

    try:
        html = fetch_page(MHLW_R8_URL)
    except Exception as exc:
        print(f"ERROR: ページ取得に失敗しました: {exc}", file=sys.stderr)
        return 1

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
                print(f"  - {lnk['text']}")
                print(f"    {lnk['href']}")

    write_report(new_links, current_links, now_jst)

    state["last_hash"] = current_hash
    state["known_links"] = current_links
    state["last_checked"] = now_jst
    save_state(state)

    return 0


if __name__ == "__main__":
    sys.exit(main())
