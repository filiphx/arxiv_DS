#!/usr/bin/env python3
"""
arXiv → Telegram bot
Busca artigos novos em Dynamical Systems (math.DS) e envia pro Telegram.
"""

import os
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
import json
from datetime import datetime, timezone

# ── Configuração ────────────────────────────────────────────────────────────
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

# Categorias do arXiv — edite à vontade
CATEGORIES = ["math.DS"]          # Dynamical Systems
# Adicione mais se quiser, ex: ["math.DS", "math.CA", "nlin.CD"]

MAX_RESULTS = 30                   # máximo de artigos por execução
# ────────────────────────────────────────────────────────────────────────────

NS = {"atom": "http://www.w3.org/2005/Atom",
      "arxiv": "http://arxiv.org/schemas/atom"}


def fetch_arxiv(categories: list[str], max_results: int) -> list[dict]:
    """Busca artigos submetidos/cross-listados hoje no arXiv."""
    search_query = " OR ".join(f"cat:{c}" for c in categories)
    params = urllib.parse.urlencode({
        "search_query": search_query,
        "sortBy": "submittedDate",
        "sortOrder": "descending",
        "max_results": max_results,
    })
    url = f"https://export.arxiv.org/api/query?{params}"

    with urllib.request.urlopen(url, timeout=30) as resp:
        data = resp.read()

    root = ET.fromstring(data)
    entries = root.findall("atom:entry", NS)

    today = datetime.now(timezone.utc).date()
    articles = []

    for entry in entries:
        published_str = entry.findtext("atom:published", "", NS)
        if not published_str:
            continue
        pub_date = datetime.fromisoformat(published_str.replace("Z", "+00:00")).date()

        # Mantém apenas os de hoje (ou remove esse filtro se quiser todos)
        if pub_date != today:
            continue

        title = (entry.findtext("atom:title", "", NS) or "").strip().replace("\n", " ")
        summary = (entry.findtext("atom:summary", "", NS) or "").strip().replace("\n", " ")
        link = entry.findtext("atom:id", "", NS) or ""

        authors = [
            a.findtext("atom:name", "", NS)
            for a in entry.findall("atom:author", NS)
        ]
        author_str = ", ".join(authors[:3])
        if len(authors) > 3:
            author_str += f" et al. ({len(authors)} autores)"

        cats = [c.get("term", "") for c in entry.findall("arxiv:primary_category", NS)]
        cats += [c.get("term", "") for c in entry.findall("atom:category", NS)]
        cats_str = ", ".join(dict.fromkeys(cats))  # dedup preservando ordem

        articles.append({
            "title": title,
            "authors": author_str,
            "categories": cats_str,
            "summary": summary[:300] + ("…" if len(summary) > 300 else ""),
            "link": link,
        })

    return articles


def send_telegram(text: str) -> None:
    """Envia uma mensagem pro Telegram via Bot API."""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = json.dumps({
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }).encode()

    req = urllib.request.Request(url, data=payload,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        result = json.loads(resp.read())
        if not result.get("ok"):
            raise RuntimeError(f"Telegram error: {result}")


def main() -> None:
    today_str = datetime.now(timezone.utc).strftime("%d/%m/%Y")
    cats_label = " + ".join(CATEGORIES)

    print(f"Buscando artigos de {cats_label} em {today_str}…")
    articles = fetch_arxiv(CATEGORIES, MAX_RESULTS)
    print(f"  → {len(articles)} artigo(s) encontrado(s).")

    if not articles:
        send_telegram(
            f"📭 <b>arXiv · {cats_label}</b> — {today_str}\n\n"
            "Nenhum artigo novo hoje."
        )
        return

    # Cabeçalho
    header = (
        f"📄 <b>arXiv · {cats_label}</b> — {today_str}\n"
        f"{len(articles)} artigo(s) novo(s)\n"
        "━━━━━━━━━━━━━━━━━━━━"
    )
    send_telegram(header)

    # Um artigo por mensagem (evita limite de 4096 chars)
    for i, art in enumerate(articles, 1):
        msg = (
            f"<b>{i}. {art['title']}</b>\n"
            f"👤 {art['authors']}\n"
            f"🏷 {art['categories']}\n\n"
            f"{art['summary']}\n\n"
            f"🔗 <a href=\"{art['link']}\">{art['link']}</a>"
        )
        send_telegram(msg)

    send_telegram(f"✅ Fim da lista de hoje ({len(articles)} artigo(s)).")


if __name__ == "__main__":
    main()
