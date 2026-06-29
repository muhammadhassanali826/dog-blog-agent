#!/usr/bin/env python3
"""Build a GitHub Pages homepage listing generated blog drafts."""

from __future__ import annotations

import html
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
GENERATED_JSON = ROOT / "data" / "generated_blogs.json"
INDEX_HTML = ROOT / "index.html"


def load_generated() -> List[Dict[str, Any]]:
    if not GENERATED_JSON.exists():
        return []
    try:
        return json.loads(GENERATED_JSON.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []


def esc(value: Any) -> str:
    return html.escape(str(value or ""))


def render_card(item: Dict[str, Any]) -> str:
    keywords = item.get("seo_keywords") or []
    if isinstance(keywords, list):
        keyword_text = ", ".join(str(k) for k in keywords[:10])
    else:
        keyword_text = str(keywords)

    return f"""
      <article class="blog-card">
        <div class="card-topline">{esc(item.get('category'))} · {esc(item.get('date'))}</div>
        <h2>{esc(item.get('blog_title'))}</h2>
        <p class="excerpt">{esc(item.get('excerpt'))}</p>
        <div class="meta-grid">
          <div><strong>Page Title</strong><span>{esc(item.get('page_title'))}</span></div>
          <div><strong>Meta Description</strong><span>{esc(item.get('meta_description'))}</span></div>
          <div><strong>URL Handle</strong><span>{esc(item.get('url_handle'))}</span></div>
          <div><strong>Product Focus</strong><span>{esc(item.get('product_focus'))}</span></div>
          <div class="full"><strong>SEO Keywords</strong><span>{esc(keyword_text)}</span></div>
        </div>
        <div class="actions">
          <a class="button" href="{esc(item.get('html_file'))}">Open Blog Draft</a>
          <button class="button secondary" onclick="copyText('{esc(item.get('html_file'))}')">Copy File Path</button>
        </div>
      </article>
    """


def render_index(items: List[Dict[str, Any]]) -> str:
    items = list(reversed(items))
    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for item in items:
        grouped[item.get("date", "Unknown Date")].append(item)

    if not items:
        content = """
        <section class="empty">
          <h2>No blogs generated yet</h2>
          <p>Run the GitHub Action manually or wait for the daily schedule.</p>
        </section>
        """
    else:
        sections = []
        for date, date_items in grouped.items():
            cards = "\n".join(render_card(item) for item in date_items)
            sections.append(f"""
            <section class="date-section">
              <h2 class="date-heading">{esc(date)} <span>{len(date_items)} draft(s)</span></h2>
              <div class="cards">{cards}</div>
            </section>
            """)
        content = "\n".join(sections)

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="robots" content="noindex, nofollow">
  <title>Dog Blog AI Agent Drafts</title>
  <style>
    :root {{
      --orange: #f02400;
      --black: #000000;
      --cream: #fffaf6;
      --soft: #fff4ee;
      --border: #f3d2c2;
      --text: #1a1208;
      --muted: #6b5d52;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
      background: var(--cream);
      color: var(--text);
    }}
    .hero {{
      background: var(--black);
      color: #fff;
      padding: 54px 6vw 46px;
    }}
    .eyebrow {{
      color: var(--orange);
      font-size: 11px;
      font-weight: 900;
      letter-spacing: 3px;
      text-transform: uppercase;
      margin-bottom: 12px;
    }}
    h1 {{
      font-size: clamp(32px, 5vw, 58px);
      line-height: 1;
      margin: 0 0 14px;
      letter-spacing: -1.8px;
    }}
    .hero p {{
      max-width: 760px;
      color: rgba(255,255,255,.8);
      font-size: 16px;
      line-height: 1.7;
      margin: 0;
    }}
    .stats {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-top: 24px;
    }}
    .stat {{
      border: 1px solid rgba(255,255,255,.16);
      background: rgba(255,255,255,.08);
      border-radius: 999px;
      padding: 8px 13px;
      font-size: 12px;
      font-weight: 800;
      text-transform: uppercase;
      letter-spacing: 1px;
    }}
    main {{ padding: 32px 6vw 70px; }}
    .date-heading {{
      margin: 30px 0 16px;
      font-size: 22px;
      display: flex;
      align-items: center;
      gap: 10px;
    }}
    .date-heading span {{
      color: var(--orange);
      font-size: 12px;
      font-weight: 900;
      text-transform: uppercase;
      letter-spacing: 1px;
    }}
    .cards {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
      gap: 18px;
    }}
    .blog-card {{
      background: #fff;
      border: 1px solid var(--border);
      border-radius: 18px;
      padding: 22px;
      box-shadow: 0 18px 40px rgba(0,0,0,.05);
    }}
    .card-topline {{
      color: var(--orange);
      font-size: 10px;
      font-weight: 900;
      letter-spacing: 2px;
      text-transform: uppercase;
      margin-bottom: 10px;
    }}
    .blog-card h2 {{
      font-size: 21px;
      line-height: 1.2;
      margin: 0 0 10px;
    }}
    .excerpt {{
      color: #3a2a1a;
      line-height: 1.65;
      font-size: 14px;
      margin: 0 0 16px;
    }}
    .meta-grid {{
      display: grid;
      grid-template-columns: 1fr;
      gap: 9px;
      margin: 15px 0 18px;
    }}
    .meta-grid div {{
      background: var(--soft);
      border: 1px solid #ffd7c4;
      border-radius: 10px;
      padding: 10px;
    }}
    .meta-grid strong {{
      display: block;
      color: var(--text);
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 1px;
      margin-bottom: 4px;
    }}
    .meta-grid span {{
      color: var(--muted);
      font-size: 13px;
      line-height: 1.45;
      overflow-wrap: anywhere;
    }}
    .actions {{ display: flex; gap: 10px; flex-wrap: wrap; }}
    .button {{
      display: inline-block;
      border: 0;
      background: var(--orange);
      color: #fff;
      font-weight: 900;
      font-size: 13px;
      text-decoration: none;
      border-radius: 999px;
      padding: 11px 16px;
      cursor: pointer;
    }}
    .button.secondary {{
      background: #1a1208;
    }}
    .empty {{
      background: #fff;
      border: 1px solid var(--border);
      border-radius: 18px;
      padding: 28px;
    }}
    @media (max-width: 640px) {{
      .hero {{ padding: 42px 22px 36px; }}
      main {{ padding: 24px 18px 50px; }}
      .cards {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <header class="hero">
    <div class="eyebrow">Brutus &amp; Barnaby Blog AI Agent</div>
    <h1>Generated Blog Drafts</h1>
    <p>This free GitHub preview site lists AI-generated draft blogs only. Review every blog before publishing it anywhere.</p>
    <div class="stats">
      <div class="stat">Total Drafts: {len(items)}</div>
      <div class="stat">GitHub Only</div>
      <div class="stat">No Shopify Publishing</div>
    </div>
  </header>
  <main>
    {content}
  </main>
  <script>
    function copyText(text) {{
      navigator.clipboard.writeText(text).then(function() {{
        alert('Copied: ' + text);
      }});
    }}
  </script>
</body>
</html>
"""


def main() -> int:
    items = load_generated()
    INDEX_HTML.write_text(render_index(items), encoding="utf-8")
    print(f"Built index.html with {len(items)} blog draft(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
