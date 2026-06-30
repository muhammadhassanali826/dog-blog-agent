#!/usr/bin/env python3
"""Build a GitHub Pages dashboard for generated dog blog drafts.

Includes:
- Generator form on the website
- Optional Cloudflare Worker trigger
- SEO cards
- HTML viewer/copy modal for each blog
"""

from __future__ import annotations

import html
import json
import os
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
GENERATED_JSON = ROOT / "data" / "generated_blogs.json"
INDEX_HTML = ROOT / "index.html"

# Put your Cloudflare Worker URL here OR set GitHub Actions env TRIGGER_WORKER_URL.
# Example: https://dog-blog-trigger.yourname.workers.dev
TRIGGER_WORKER_URL = os.getenv("TRIGGER_WORKER_URL", "").strip()

# This is used when the direct website trigger is not connected yet.
GITHUB_ACTIONS_URL = os.getenv(
    "GITHUB_ACTIONS_URL",
    "https://github.com/muhammadhassanali826/dog-blog-agent/actions/workflows/daily-blog-generator.yml",
).strip()


def load_generated() -> List[Dict[str, Any]]:
    if not GENERATED_JSON.exists():
        return []
    try:
        return json.loads(GENERATED_JSON.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []


def esc(value: Any) -> str:
    return html.escape(str(value or ""), quote=True)


def js_str(value: Any) -> str:
    return json.dumps(str(value or ""))


def render_card(item: Dict[str, Any]) -> str:
    keywords = item.get("seo_keywords") or []
    if isinstance(keywords, list):
        keyword_text = ", ".join(str(k) for k in keywords[:14])
    else:
        keyword_text = str(keywords)

    seo_payload = {
        "blog_title": item.get("blog_title", ""),
        "excerpt": item.get("excerpt", ""),
        "page_title": item.get("page_title", ""),
        "meta_description": item.get("meta_description", ""),
        "url_handle": item.get("url_handle", ""),
        "seo_keywords": keyword_text,
        "html_file": item.get("html_file", ""),
    }

    html_file = item.get("html_file", "")
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
          <a class="button" href="{esc(html_file)}" target="_blank" rel="noopener">Open Draft</a>
          <button class="button secondary" type="button" onclick="openHtmlModal({js_str(html_file)}, {js_str(item.get('blog_title'))})">View HTML</button>
          <button class="button ghost" type="button" onclick='copySeoDetails({json.dumps(seo_payload, ensure_ascii=False)})'>Copy SEO</button>
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
          <p>Use the generator form above or run the GitHub Action manually.</p>
        </section>
        """
    else:
        sections = []
        for date, date_items in grouped.items():
            cards = "\n".join(render_card(item) for item in date_items)
            sections.append(f"""
            <section class="date-section" id="drafts">
              <h2 class="date-heading">{esc(date)} <span>{len(date_items)} draft(s)</span></h2>
              <div class="cards">{cards}</div>
            </section>
            """)
        content = "\n".join(sections)

    worker_connected = "true" if TRIGGER_WORKER_URL else "false"

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
    .eyebrow {{ color: var(--orange); font-size: 11px; font-weight: 900; letter-spacing: 3px; text-transform: uppercase; margin-bottom: 12px; }}
    h1 {{ font-size: clamp(32px, 5vw, 58px); line-height: 1; margin: 0 0 14px; letter-spacing: -1.8px; }}
    .hero p {{ max-width: 800px; color: rgba(255,255,255,.8); font-size: 16px; line-height: 1.7; margin: 0; }}
    .stats {{ display: flex; flex-wrap: wrap; gap: 10px; margin-top: 24px; }}
    .stat {{ border: 1px solid rgba(255,255,255,.16); background: rgba(255,255,255,.08); border-radius: 999px; padding: 8px 13px; font-size: 12px; font-weight: 800; text-transform: uppercase; letter-spacing: 1px; }}
    .hero-actions {{ display:flex; gap:12px; flex-wrap:wrap; margin-top:24px; }}
    main {{ padding: 32px 6vw 70px; }}
    .generator-panel {{
      background:#fff;
      border:1px solid var(--border);
      border-radius:22px;
      padding:22px;
      box-shadow:0 18px 50px rgba(0,0,0,.06);
      margin-bottom:28px;
    }}
    .generator-panel h2 {{ margin:0 0 8px; font-size:24px; }}
    .generator-panel p {{ margin:0 0 18px; color:var(--muted); line-height:1.6; }}
    .generator-grid {{ display:grid; grid-template-columns: repeat(auto-fit,minmax(210px,1fr)); gap:14px; align-items:end; }}
    label {{ font-size:12px; font-weight:900; letter-spacing:1px; text-transform:uppercase; display:block; margin-bottom:7px; }}
    input, select {{ width:100%; border:1px solid #ffd7c4; background:#fff8f3; border-radius:12px; padding:13px 12px; font:inherit; }}
    .hint {{ margin-top:12px; padding:12px 14px; border-radius:12px; background:#fff4ee; border:1px solid #ffd7c4; color:#5c3628; font-size:14px; line-height:1.55; }}
    .date-heading {{ margin: 30px 0 16px; font-size: 22px; display: flex; align-items: center; gap: 10px; }}
    .date-heading span {{ color: var(--orange); font-size: 12px; font-weight: 900; text-transform: uppercase; letter-spacing: 1px; }}
    .cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 18px; }}
    .blog-card {{ background: #fff; border: 1px solid var(--border); border-radius: 18px; padding: 22px; box-shadow: 0 18px 40px rgba(0,0,0,.05); }}
    .card-topline {{ color: var(--orange); font-size: 10px; font-weight: 900; letter-spacing: 2px; text-transform: uppercase; margin-bottom: 10px; }}
    .blog-card h2 {{ font-size: 21px; line-height: 1.2; margin: 0 0 10px; }}
    .excerpt {{ color: #3a2a1a; line-height: 1.65; font-size: 14px; margin: 0 0 16px; }}
    .meta-grid {{ display: grid; grid-template-columns: 1fr; gap: 9px; margin: 15px 0 18px; }}
    .meta-grid div {{ background: var(--soft); border: 1px solid #ffd7c4; border-radius: 10px; padding: 10px; }}
    .meta-grid strong {{ display: block; color: var(--text); font-size: 11px; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 4px; }}
    .meta-grid span {{ color: var(--muted); font-size: 13px; line-height: 1.45; overflow-wrap: anywhere; }}
    .actions {{ display: flex; gap: 10px; flex-wrap: wrap; }}
    .button {{ display: inline-block; border: 0; background: var(--orange); color: #fff; font-weight: 900; font-size: 13px; text-decoration: none; border-radius: 999px; padding: 12px 17px; cursor: pointer; text-align:center; }}
    .button.secondary {{ background: #1a1208; }}
    .button.ghost {{ background:#fff; color:#1a1208; border:1px solid #d8c6b8; }}
    .empty {{ background: #fff; border: 1px solid var(--border); border-radius: 18px; padding: 28px; }}
    .modal-backdrop {{ position:fixed; inset:0; background:rgba(0,0,0,.74); display:none; z-index:9999; padding:24px; }}
    .modal-backdrop.active {{ display:block; }}
    .modal {{ background:#fffaf6; border:1px solid #ffd7c4; border-radius:20px; max-width:1100px; height:calc(100vh - 48px); margin:0 auto; display:flex; flex-direction:column; overflow:hidden; }}
    .modal-head {{ padding:16px 18px; display:flex; justify-content:space-between; gap:12px; align-items:center; border-bottom:1px solid #f3d2c2; }}
    .modal-head h3 {{ margin:0; font-size:18px; }}
    .modal-actions {{ display:flex; gap:8px; flex-wrap:wrap; }}
    #htmlCode {{ width:100%; flex:1; border:0; padding:18px; font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; font-size:13px; line-height:1.5; background:#111; color:#fff; resize:none; outline:none; }}
    @media (max-width: 640px) {{ .hero {{ padding: 42px 22px 36px; }} main {{ padding: 24px 18px 50px; }} .cards {{ grid-template-columns: 1fr; }} .modal-backdrop {{ padding:8px; }} .modal {{ height:calc(100vh - 16px); }} }}
  </style>
</head>
<body>
  <header class="hero">
    <div class="eyebrow">Brutus &amp; Barnaby Blog AI Agent</div>
    <h1>Generated Blog Drafts</h1>
    <p>Generate draft blogs from this dashboard, review SEO details, open each draft, and copy the full blog HTML. GitHub-only. No Shopify auto-publishing.</p>
    <div class="stats">
      <div class="stat">Total Drafts: {len(items)}</div>
      <div class="stat">GitHub Only</div>
      <div class="stat">No Shopify Publishing</div>
      <div class="stat">Website Trigger: {'Connected' if TRIGGER_WORKER_URL else 'Manual/Not Connected'}</div>
    </div>
    <div class="hero-actions">
      <a class="button" href="#generate">Generate Blogs</a>
      <a class="button secondary" href="#drafts">View Drafts</a>
    </div>
  </header>
  <main>
    <section class="generator-panel" id="generate">
      <h2>Generate New Blogs</h2>
      <p>Choose how many drafts to generate and whether to use AI. “Test only” creates sample blogs without Gemini credits. “Use AI” uses your Gemini key stored in GitHub Secrets.</p>
      <form id="generateForm" class="generator-grid">
        <div>
          <label for="blogCount">How many blogs?</label>
          <input id="blogCount" name="blogs_per_day" type="number" min="1" max="20" value="20">
        </div>
        <div>
          <label for="aiMode">Generation mode</label>
          <select id="aiMode" name="dry_run">
            <option value="false">Use AI / Gemini</option>
            <option value="true">Test only / no AI</option>
          </select>
        </div>
        <div>
          <label for="agentPin">PIN, optional</label>
          <input id="agentPin" name="pin" type="password" placeholder="Only if Worker PIN is set">
        </div>
        <div>
          <button class="button" type="submit">Generate Blog Drafts</button>
        </div>
      </form>
      <div class="hint" id="triggerStatus">If the button is not connected yet, it will open GitHub Actions where you can click Run workflow manually.</div>
    </section>

    {content}
  </main>

  <div class="modal-backdrop" id="htmlModal" aria-hidden="true">
    <div class="modal">
      <div class="modal-head">
        <h3 id="modalTitle">Blog HTML</h3>
        <div class="modal-actions">
          <button class="button" type="button" onclick="copyHtmlCode()">Copy HTML</button>
          <button class="button ghost" type="button" onclick="closeHtmlModal()">Close</button>
        </div>
      </div>
      <textarea id="htmlCode" spellcheck="false"></textarea>
    </div>
  </div>

  <script>
    const WORKER_URL = {json.dumps(TRIGGER_WORKER_URL)};
    const WORKER_CONNECTED = {worker_connected};
    const ACTIONS_URL = {json.dumps(GITHUB_ACTIONS_URL)};

    const form = document.getElementById('generateForm');
    const triggerStatus = document.getElementById('triggerStatus');

    form.addEventListener('submit', async function(event) {{
      event.preventDefault();
      const blogsPerDay = document.getElementById('blogCount').value || '20';
      const dryRun = document.getElementById('aiMode').value;
      const pin = document.getElementById('agentPin').value || '';

      if (!WORKER_CONNECTED || !WORKER_URL) {{
        triggerStatus.innerHTML = 'Direct website trigger is not connected yet. Opening GitHub Actions. Choose <strong>blogs_per_day=' + blogsPerDay + '</strong> and <strong>dry_run=' + dryRun + '</strong> there.';
        window.open(ACTIONS_URL, '_blank', 'noopener');
        return;
      }}

      triggerStatus.textContent = 'Starting workflow...';
      try {{
        const res = await fetch(WORKER_URL, {{
          method: 'POST',
          headers: {{ 'Content-Type': 'application/json', 'x-agent-pin': pin }},
          body: JSON.stringify({{ blogs_per_day: blogsPerDay, dry_run: dryRun }})
        }});
        const data = await res.json().catch(() => ({{}}));
        if (!res.ok) throw new Error(data.error || 'Trigger failed');
        triggerStatus.innerHTML = 'Workflow started. Wait 5–10 minutes, then refresh this page. <a href="' + ACTIONS_URL + '" target="_blank" rel="noopener">Open GitHub Actions</a>';
      }} catch (error) {{
        triggerStatus.textContent = 'Could not trigger workflow: ' + error.message;
      }}
    }});

    async function openHtmlModal(path, title) {{
      const modal = document.getElementById('htmlModal');
      const code = document.getElementById('htmlCode');
      const modalTitle = document.getElementById('modalTitle');
      modalTitle.textContent = 'HTML: ' + title;
      code.value = 'Loading HTML from ' + path + '...';
      modal.classList.add('active');
      modal.setAttribute('aria-hidden', 'false');

      try {{
        const response = await fetch(path + '?v=' + Date.now());
        const text = await response.text();
        const doc = new DOMParser().parseFromString(text, 'text/html');
        const raw = doc.querySelector('#rawHtmlCode');
        code.value = raw ? raw.value : text;
      }} catch (error) {{
        code.value = 'Could not load HTML: ' + error.message;
      }}
    }}

    function closeHtmlModal() {{
      const modal = document.getElementById('htmlModal');
      modal.classList.remove('active');
      modal.setAttribute('aria-hidden', 'true');
    }}

    async function copyHtmlCode() {{
      const code = document.getElementById('htmlCode');
      await navigator.clipboard.writeText(code.value);
      alert('Blog HTML copied.');
    }}

    async function copySeoDetails(item) {{
      const text = `Blog Title:\n${{item.blog_title}}\n\nExcerpt:\n${{item.excerpt}}\n\nSearch Engine Listing Page Title:\n${{item.page_title}}\n\nMeta Description:\n${{item.meta_description}}\n\nURL Handle:\n${{item.url_handle}}\n\nSEO Keywords:\n${{item.seo_keywords}}\n\nHTML File:\n${{item.html_file}}`;
      await navigator.clipboard.writeText(text);
      alert('SEO details copied.');
    }}
  </script>
</body>
</html>
"""


def main() -> int:
    items = load_generated()
    INDEX_HTML.write_text(render_index(items), encoding="utf-8")
    print(f"Built {INDEX_HTML} with {len(items)} generated blog(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
