#!/usr/bin/env python3
"""
arXiv → Telegram bot
Usa o RSS diário do arXiv — exatamente os artigos da listagem do dia.
"""

import os
import urllib.request
import xml.etree.ElementTree as ET
import json
import re
import time
from datetime import datetime, timezone

# ── Configuração ────────────────────────────────────────────────────────────
TELEGRAM_TOKEN   = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

CATEGORIES = ["math.DS"]
# ────────────────────────────────────────────────────────────────────────────

DC_CREATOR = "{http://purl.org/dc/elements/1.1/}creator"


def fetch_rss(category: str) -> list[dict]:
    url = f"https://rss.arxiv.org/rss/{category}"
    print(f"[DEBUG] Fetching: {url}")

    req = urllib.request.Request(
        url, headers={"User-Agent": "Mozilla/5.0 (compatible; arxiv-bot/1.0)"}
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = resp.read()

    root    = ET.fromstring(data)
    channel = root.find("channel")
    items   = channel.findall("item")
    print(f"[DEBUG] Itens no RSS: {len(items)}")

    articles = []
    for item in items:
        title_raw = (item.findtext("title") or "").strip()
        link      = (item.findtext("link")  or "").strip()
        desc      = (item.findtext("description") or "").strip()
        authors   = (item.findtext(DC_CREATOR) or "").strip()

        # Descarta apenas replacements (revisões de artigos antigos)
        if title_raw.upper().startswith("REPLACED"):
            print(f"  [REPLACED] {title_raw[:80]}")
            continue

        # Limpa o título: remove prefixo "[math.DS]", "(cross-list from X.Y)", etc.
        title = re.sub(r"^\[.*?\]\s*", "", title_raw)          # remove [cat]
        title = re.sub(r"\(cross-list from .*?\)\s*", "", title)  # remove (cross-list...)
        title = title.strip()

        # Marca se é cross-list para exibir no Telegram
        is_cross = "cross-list" in title_raw.lower()

        # Abstract: remove tags HTML
        abstract = re.sub(r"<[^>]+>", " ", desc).strip()
        abstract = " ".join(abstract.split())
        if len(abstract) > 300:
            abstract = abstract[:300] + "…"

        articles.append({
            "title":    title,
            "authors":  authors,
            "link":     link.replace("http://", "https://"),
            "summary":  abstract,
            "cross":    is_cross,
        })

    print(f"[DEBUG] Artigos (novos + cross-lists): {len(articles)}")
    return articles


def send_telegram(text: str) -> None:
    url     = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = json.dumps({
        "chat_id":                  TELEGRAM_CHAT_ID,
        "text":                     text,
        "parse_mode":               "HTML",
        "disable_web_page_preview": True,
    }).encode()

    req = urllib.request.Request(
        url, data=payload,
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        result = json.loads(resp.read())
        if not result.get("ok"):
            raise RuntimeError(f"Telegram error: {result}")


def main() -> None:
    today_str  = datetime.now(timezone.utc).strftime("%d/%m/%Y")
    cats_label = " + ".join(CATEGORIES)

    all_articles = []
    seen_links   = set()

    for cat in CATEGORIES:
        for a in fetch_rss(cat):
            if a["link"] not in seen_links:
                seen_links.add(a["link"])
                all_articles.append(a)

    novos  = [a for a in all_articles if not a["cross"]]
    cross  = [a for a in all_articles if a["cross"]]

    print(f"→ {len(novos)} novo(s) + {len(cross)} cross-list(s) = {len(all_articles)} total")

    if not all_articles:
        send_telegram(
            f"📭 <b>arXiv · {cats_label}</b> — {today_str}\n\n"
            "Nenhum artigo novo hoje."
        )
        return

    header = (
        f"📄 <b>arXiv · {cats_label}</b> — {today_str}\n"
        f"{len(novos)} novo(s)  •  {len(cross)} cross-list(s)\n"
        "━━━━━━━━━━━━━━━━━━━━"
    )
    send_telegram(header)

    # Primeiro os novos, depois as cross-lists
    for i, art in enumerate(novos + cross, 1):
        tag = "🔀 <i>cross-list</i>\n" if art["cross"] else ""
        msg = (
            f"{tag}"
            f"<b>{i}. {art['title']}</b>\n"
            f"👤 {art['authors']}\n\n"
            f"{art['summary']}\n\n"
            f"🔗 <a href=\"{art['link']}\">{art['link']}</a>"
        )
        send_telegram(msg)
        time.sleep(0.3)

    send_telegram(f"✅ Fim da lista de hoje ({len(all_articles)} artigo(s)).")


if __name__ == "__main__":
    main()
