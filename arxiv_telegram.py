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
import time
from datetime import datetime, timezone, timedelta

# ── Configuração ────────────────────────────────────────────────────────────
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

CATEGORIES = ["math.DS"]
DAYS_BACK = 7      # ampliado para 7 dias para garantir
MAX_RESULTS = 50
# ────────────────────────────────────────────────────────────────────────────

NS = {
    "atom":  "http://www.w3.org/2005/Atom",
    "arxiv": "http://arxiv.org/schemas/atom",
}


def fetch_arxiv(categories: list[str]) -> list[dict]:
    # Estratégia simples: busca por categoria ordenado por data, sem filtro de data na query
    # O filtro de data via submittedDate da API do arXiv é instável — evitamos
    cat_query = " OR ".join(f"cat:{c}" for c in categories)

    params = urllib.parse.urlencode({
        "search_query": cat_query,
        "sortBy":       "submittedDate",
        "sortOrder":    "descending",
        "max_results":  MAX_RESULTS,
    })
    url = f"https://export.arxiv.org/api/query?{params}"

    print(f"[DEBUG] URL: {url}")

    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (compatible; arxiv-bot/1.0)"}
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = resp.read()

    root    = ET.fromstring(data)
    entries = root.findall("atom:entry", NS)
    print(f"[DEBUG] Total de entradas retornadas pela API: {len(entries)}")

    now    = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=DAYS_BACK)
    articles = []

    for entry in entries:
        # Usa 'updated' — é quando o arXiv processou/publicou o artigo
        updated_str = entry.findtext("atom:updated", "", NS)
        pub_str     = entry.findtext("atom:published", "", NS)

        # Data de referência: updated (mais recente entre os dois)
        ref_str = updated_str or pub_str
        if not ref_str:
            continue

        ref_dt = datetime.fromisoformat(ref_str.replace("Z", "+00:00"))
        pub_dt = datetime.fromisoformat(pub_str.replace("Z", "+00:00")) if pub_str else ref_dt

        print(f"[DEBUG] published={pub_str[:10] if pub_str else '?'}  updated={updated_str[:10] if updated_str else '?'}")

        # Filtra por updated dentro da janela
        if ref_dt < cutoff:
            print(f"[DEBUG]   → fora da janela, pulando")
            continue

        title   = (entry.findtext("atom:title",   "", NS) or "").strip().replace("\n", " ")
        summary = (entry.findtext("atom:summary", "", NS) or "").strip().replace("\n", " ")
        link    = (entry.findtext("atom:id",      "", NS) or "").strip()

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
            "pub_date":   pub_dt.strftime("%d/%m/%Y"),
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
    print(f"→ {len(articles)} artigo(s) após filtro.")

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
