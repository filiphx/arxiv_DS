#!/usr/bin/env python3
"""
arXiv → Telegram bot
Busca artigos novos em Dynamical Systems (math.DS) e envia pro Telegram.
Usa submittedDate na query — equivalente à listagem diária do site.
"""

import os
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
import json
import time
from datetime import datetime, timezone, timedelta

# ── Configuração ────────────────────────────────────────────────────────────
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

CATEGORIES = ["math.DS"]
# Adicione mais se quiser: ["math.DS", "math.CA", "nlin.CD"]

# Janela de busca: artigos submetidos nos últimos N dias
# O arXiv agrupa sex+sab+dom e posta na segunda — use 4 para não perder nada
DAYS_BACK = 4

MAX_RESULTS = 50
# ────────────────────────────────────────────────────────────────────────────

NS = {
    "atom":  "http://www.w3.org/2005/Atom",
    "arxiv": "http://arxiv.org/schemas/atom",
}


def date_range_query() -> str:
    """
    Monta o filtro de data no formato que o arXiv entende:
    submittedDate:[YYYYMMDD0000 TO YYYYMMDD2359]
    """
    now   = datetime.now(timezone.utc)
    start = now - timedelta(days=DAYS_BACK)
    return (
        f"submittedDate:[{start.strftime('%Y%m%d')}0000"
        f" TO {now.strftime('%Y%m%d')}2359]"
    )


def fetch_arxiv(categories: list[str]) -> list[dict]:
    cat_query  = " OR ".join(f"cat:{c}" for c in categories)
    date_query = date_range_query()
    search_query = f"({cat_query}) AND {date_query}"

    params = urllib.parse.urlencode({
        "search_query": search_query,
        "sortBy":       "submittedDate",
        "sortOrder":    "descending",
        "max_results":  MAX_RESULTS,
    })
    url = f"https://export.arxiv.org/api/query?{params}"

    req = urllib.request.Request(url, headers={"User-Agent": "arxiv-telegram-bot/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = resp.read()

    root    = ET.fromstring(data)
    entries = root.findall("atom:entry", NS)
    articles = []

    for entry in entries:
        title   = (entry.findtext("atom:title",   "", NS) or "").strip().replace("\n", " ")
        summary = (entry.findtext("atom:summary", "", NS) or "").strip().replace("\n", " ")
        link    = (entry.findtext("atom:id",      "", NS) or "").strip()

        pub_str  = entry.findtext("atom:published", "", NS)
        pub_date = ""
        if pub_str:
            pub_date = datetime.fromisoformat(
                pub_str.replace("Z", "+00:00")
            ).strftime("%d/%m/%Y")

        authors = [
            a.findtext("atom:name", "", NS)
            for a in entry.findall("atom:author", NS)
        ]
        author_str = ", ".join(authors[:3])
        if len(authors) > 3:
            author_str += f" et al. ({len(authors)} autores)"

        cats = [c.get("term", "") for c in entry.findall("arxiv:primary_category", NS)]
        cats += [c.get("term", "") for c in entry.findall("atom:category", NS)]
        cats_str = ", ".join(dict.fromkeys(cats))

        articles.append({
            "title":      title,
            "authors":    author_str,
            "categories": cats_str,
            "pub_date":   pub_date,
            "summary":    summary[:300] + ("…" if len(summary) > 300 else ""),
            "link":       link,
        })

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

    print(f"Buscando artigos de {cats_label} (últimos {DAYS_BACK} dias)…")
    articles = fetch_arxiv(CATEGORIES)
    print(f"  → {len(articles)} artigo(s) encontrado(s).")

    if not articles:
        send_telegram(
            f"📭 <b>arXiv · {cats_label}</b> — {today_str}\n\n"
            "Nenhum artigo novo no período."
        )
        return

    header = (
        f"📄 <b>arXiv · {cats_label}</b> — {today_str}\n"
        f"{len(articles)} artigo(s) nos últimos {DAYS_BACK} dias\n"
        "━━━━━━━━━━━━━━━━━━━━"
    )
    send_telegram(header)

    for i, art in enumerate(articles, 1):
        msg = (
            f"<b>{i}. {art['title']}</b>\n"
            f"👤 {art['authors']}\n"
            f"🏷 {art['categories']}  •  📅 {art['pub_date']}\n\n"
            f"{art['summary']}\n\n"
            f"🔗 <a href=\"{art['link']}\">{art['link']}</a>"
        )
        send_telegram(msg)
        time.sleep(0.3)

    send_telegram(f"✅ Fim da lista ({len(articles)} artigo(s)).")


if __name__ == "__main__":
    main()
