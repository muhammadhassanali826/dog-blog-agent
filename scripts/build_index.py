#!/usr/bin/env python3
"""
Colorful 3D dashboard builder for Dog Blog AI Agent.

What this UI does:
- Colorful animated/3D website design.
- Shows only one top stat: Total Blogs Generated.
- Keeps the blog generator form.
- Removes extra badges/status lines.
- Removes front-page Copy HTML / View HTML buttons.
- Keeps only Open Draft + Copy SEO on each blog card.
"""

from __future__ import annotations

import json
import os
from collections import defaultdict
from html import escape
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = ROOT / "data" / "generated_blogs.json"
OUT_FILE = ROOT / "index.html"

OWNER = os.getenv("GITHUB_REPOSITORY_OWNER", "muhammadhassanali826")
REPO = os.getenv("GITHUB_REPOSITORY", f"{OWNER}/dog-blog-agent").split("/", 1)[-1]
ACTIONS_URL = f"https://github.com/{OWNER}/{REPO}/actions/workflows/daily-blog-generator.yml"
TRIGGER_WORKER_URL = os.getenv("TRIGGER_WORKER_URL", "").strip()


def load_blogs() -> List[Dict[str, Any]]:
    if not DATA_FILE.exists():
        return []
    try:
        data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return [item for item in data if isinstance(item, dict)]
    except Exception:
        return []
    return []


def val(item: Dict[str, Any], *keys: str, default: str = "") -> str:
    for key in keys:
        if key in item and item[key] not in (None, ""):
            value = item[key]
            if isinstance(value, list):
                return ", ".join(str(v) for v in value)
            return str(value)
    return default


def blog_date(item: Dict[str, Any]) -> str:
    return val(item, "date", "generated_date", default="Latest")


def blog_path(item: Dict[str, Any]) -> str:
    path = val(item, "html_file", "file", "path", default="#")
    return path.replace("\\", "/")


def build_cards(blogs: List[Dict[str, Any]]) -> str:
    if not blogs:
        return """
        <section class="empty-state" id="drafts">
          <div class="orb small"></div>
          <h2>No blogs generated yet</h2>
          <p>Choose how many AI drafts you want and click <strong>Generate Blog Drafts</strong>.</p>
        </section>
        """

    groups: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for item in blogs:
        groups[blog_date(item)].append(item)

    sections: List[str] = []
    for date in sorted(groups.keys(), reverse=True):
        items = groups[date]
        cards: List[str] = []
        for idx, item in enumerate(items):
            title = val(item, "blog_title", "title", default="Untitled Blog")
            excerpt = val(item, "excerpt", "description", default="")
            page_title = val(item, "page_title", "seo_title", "search_engine_title", default=title)
            meta_description = val(item, "meta_description", "seo_description", default="")
            url_handle = val(item, "url_handle", "handle", default="")
            keywords = val(item, "seo_keywords", "keywords", default="")
            product_focus = val(item, "product_focus", "product", default="")
            category = val(item, "category", default="Blog Draft")
            path = blog_path(item)

            seo_payload = {
                "Blog Title": title,
                "Excerpt": excerpt,
                "Page Title": page_title,
                "Meta Description": meta_description,
                "URL Handle": url_handle,
                "SEO Keywords": keywords,
                "Product Focus": product_focus,
            }
            seo_json = escape(json.dumps(seo_payload, ensure_ascii=False), quote=True)

            cards.append(f"""
            <article class="draft-card tilt-card" style="--delay:{idx * 60}ms;">
              <div class="shine"></div>
              <div class="card-topline">{escape(category)} • {escape(date)}</div>
              <h3>{escape(title)}</h3>
              <p class="excerpt">{escape(excerpt)}</p>

              <div class="field-grid">
                <div class="field"><span>Page Title</span><p>{escape(page_title)}</p></div>
                <div class="field"><span>Meta Description</span><p>{escape(meta_description)}</p></div>
                <div class="field"><span>URL Handle</span><p>{escape(url_handle)}</p></div>
                <div class="field"><span>SEO Keywords</span><p>{escape(keywords)}</p></div>
              </div>

              <div class="card-actions">
                <a class="btn primary" href="{escape(path)}">Open Draft</a>
                <button class="btn secondary" type="button" onclick="copySeo(this)" data-seo="{seo_json}">Copy SEO</button>
              </div>
            </article>
            """)

        sections.append(f"""
        <section class="date-section" id="drafts">
          <div class="date-head">
            <h2>{escape(date)}</h2>
            <span>{len(items)} draft(s)</span>
          </div>
          <div class="draft-grid">{''.join(cards)}</div>
        </section>
        """)
    return "\n".join(sections)


def build_html(blogs: List[Dict[str, Any]]) -> str:
    total = len(blogs)
    cards_html = build_cards(blogs)
    blogs_json = json.dumps(blogs, ensure_ascii=False)
    trigger_url = json.dumps(TRIGGER_WORKER_URL)
    actions_url = json.dumps(ACTIONS_URL)

    # Keep this as a normal triple string and replace tokens to avoid f-string JS brace issues.
    html = r'''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Dog Blog AI Agent</title>
  <style>
    :root {
      --orange:#ff2a10;
      --orange2:#ff7a18;
      --pink:#ff3d8b;
      --purple:#6d5dfc;
      --cyan:#00d4ff;
      --green:#50f28f;
      --dark:#08080f;
      --cream:#fff7ef;
      --text:#191316;
      --muted:#675b60;
      --line:rgba(255,91,42,.22);
      --shadow:0 28px 70px rgba(45,18,5,.18);
      --radius:28px;
    }

    * { box-sizing:border-box; }
    html { scroll-behavior:smooth; }
    body {
      margin:0;
      font-family:system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
      background:
        radial-gradient(circle at 18% 12%, rgba(255,62,139,.24), transparent 26%),
        radial-gradient(circle at 88% 8%, rgba(0,212,255,.24), transparent 26%),
        radial-gradient(circle at 70% 68%, rgba(109,93,252,.22), transparent 30%),
        linear-gradient(135deg,#fff9f2 0%,#fff3ea 42%,#f3fbff 100%);
      color:var(--text);
      overflow-x:hidden;
    }

    body::before {
      content:"";
      position:fixed;
      inset:0;
      pointer-events:none;
      background-image:linear-gradient(rgba(255,255,255,.08) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,.08) 1px, transparent 1px);
      background-size:38px 38px;
      mask-image:linear-gradient(to bottom, rgba(0,0,0,.4), transparent 70%);
      z-index:0;
    }

    .page { position:relative; z-index:1; }

    .hero {
      position:relative;
      min-height:430px;
      padding:64px 6vw 76px;
      overflow:hidden;
      color:#fff;
      background:
        radial-gradient(circle at 18% 18%, rgba(255,42,16,.75), transparent 23%),
        radial-gradient(circle at 80% 20%, rgba(0,212,255,.45), transparent 27%),
        radial-gradient(circle at 58% 82%, rgba(109,93,252,.55), transparent 30%),
        linear-gradient(145deg,#05050a 0%,#11102a 45%,#230a09 100%);
      isolation:isolate;
    }

    .hero::after {
      content:"";
      position:absolute;
      inset:-40%;
      background:conic-gradient(from 90deg, transparent, rgba(255,255,255,.08), transparent, rgba(255,42,16,.12), transparent);
      animation:spin 18s linear infinite;
      z-index:-2;
    }

    .hero-inner { max-width:1180px; margin:0 auto; position:relative; }
    .eyebrow {
      display:inline-flex;
      align-items:center;
      gap:10px;
      color:#ffcf4a;
      font-size:12px;
      font-weight:950;
      letter-spacing:4px;
      text-transform:uppercase;
      text-shadow:0 0 18px rgba(255,207,74,.65);
    }

    .hero h1 {
      font-size:clamp(48px, 7vw, 94px);
      line-height:.94;
      max-width:980px;
      margin:22px 0 18px;
      letter-spacing:-4px;
      font-weight:1000;
      text-shadow:0 12px 0 rgba(0,0,0,.2), 0 32px 50px rgba(0,0,0,.45);
      transform:perspective(900px) rotateX(8deg);
    }

    .hero p {
      max-width:780px;
      font-size:18px;
      line-height:1.7;
      color:rgba(255,255,255,.84);
      margin:0 0 26px;
    }

    .stat-pill {
      display:inline-flex;
      align-items:center;
      gap:10px;
      padding:14px 20px;
      border-radius:999px;
      background:rgba(255,255,255,.12);
      border:1px solid rgba(255,255,255,.26);
      box-shadow:inset 0 1px 0 rgba(255,255,255,.18), 0 18px 45px rgba(0,0,0,.28);
      font-weight:1000;
      letter-spacing:.8px;
      text-transform:uppercase;
      backdrop-filter:blur(14px);
    }

    .stat-pill strong {
      color:#fff;
      font-size:18px;
      text-shadow:0 0 18px rgba(80,242,143,.55);
    }

    .hero-buttons { display:flex; flex-wrap:wrap; gap:14px; margin-top:28px; }

    .btn {
      border:0;
      cursor:pointer;
      display:inline-flex;
      align-items:center;
      justify-content:center;
      gap:8px;
      min-height:52px;
      padding:15px 24px;
      border-radius:999px;
      font-weight:1000;
      text-decoration:none;
      color:#fff;
      letter-spacing:-.2px;
      transition:transform .22s ease, box-shadow .22s ease, filter .22s ease;
      transform:translateZ(0);
      font-family:inherit;
      font-size:15px;
    }

    .btn:hover { transform:translateY(-4px) scale(1.02); filter:saturate(1.12); }
    .btn.primary {
      background:linear-gradient(135deg,var(--orange),var(--pink));
      box-shadow:0 18px 35px rgba(255,42,16,.34), inset 0 1px 0 rgba(255,255,255,.3);
    }
    .btn.secondary {
      color:#1d1007;
      background:linear-gradient(135deg,#fff,#fff2e5);
      border:1px solid rgba(255,91,42,.25);
      box-shadow:0 12px 25px rgba(54,18,7,.12), inset 0 1px 0 #fff;
    }
    .btn.dark {
      background:linear-gradient(135deg,#1a0e05,#392010);
      box-shadow:0 18px 38px rgba(0,0,0,.25), inset 0 1px 0 rgba(255,255,255,.12);
    }

    .float-shape {
      position:absolute;
      border-radius:34px;
      filter:blur(.1px);
      opacity:.92;
      transform-style:preserve-3d;
      animation:floaty 7s ease-in-out infinite;
      box-shadow:0 40px 80px rgba(0,0,0,.34), inset 0 2px 1px rgba(255,255,255,.35);
    }
    .shape-1 { width:150px;height:150px;right:9%;top:72px;background:linear-gradient(135deg,#ff2a10,#ffcf4a);transform:rotate(18deg); }
    .shape-2 { width:112px;height:112px;right:24%;bottom:70px;background:linear-gradient(135deg,#00d4ff,#6d5dfc);border-radius:50%;animation-delay:-2s; }
    .shape-3 { width:90px;height:90px;left:4%;bottom:42px;background:linear-gradient(135deg,#50f28f,#00d4ff);transform:rotate(-22deg);animation-delay:-4s; }

    .main { max-width:1280px; margin:-38px auto 80px; padding:0 5vw; position:relative; }

    .generator {
      position:relative;
      padding:30px;
      border:1px solid rgba(255,91,42,.24);
      border-radius:var(--radius);
      background:rgba(255,255,255,.74);
      backdrop-filter:blur(18px);
      box-shadow:var(--shadow), inset 0 1px 0 rgba(255,255,255,.9);
      overflow:hidden;
      transform:perspective(1100px) rotateX(1deg);
    }
    .generator::before {
      content:"";
      position:absolute;
      inset:0;
      background:linear-gradient(90deg, rgba(255,42,16,.08), transparent, rgba(0,212,255,.1));
      pointer-events:none;
    }
    .generator h2 { margin:0 0 8px; font-size:32px; letter-spacing:-1.2px; }
    .generator p { color:var(--muted); margin:0 0 24px; font-size:17px; line-height:1.6; }

    .form-row { display:grid; grid-template-columns:minmax(160px, 1fr) minmax(220px, 1fr) auto; gap:16px; align-items:end; position:relative; }
    label { display:block; color:#160d07; font-size:12px; font-weight:1000; text-transform:uppercase; letter-spacing:2px; margin-bottom:8px; }
    input, select {
      width:100%;
      height:58px;
      border-radius:18px;
      border:1px solid rgba(255,91,42,.28);
      background:rgba(255,247,239,.8);
      color:#1b1210;
      padding:0 16px;
      font:inherit;
      font-size:17px;
      outline:none;
      box-shadow:inset 0 1px 0 #fff;
    }
    input:focus, select:focus { border-color:var(--orange); box-shadow:0 0 0 4px rgba(255,42,16,.12); }

    .date-section { margin-top:48px; }
    .date-head { display:flex; align-items:end; justify-content:space-between; gap:18px; margin-bottom:20px; }
    .date-head h2 { font-size:34px; margin:0; letter-spacing:-1px; }
    .date-head span { color:var(--orange); font-weight:1000; letter-spacing:1px; text-transform:uppercase; }

    .draft-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(330px,1fr)); gap:22px; }
    .draft-card {
      position:relative;
      border-radius:26px;
      padding:24px;
      min-height:420px;
      border:1px solid rgba(255,91,42,.24);
      background:linear-gradient(145deg,rgba(255,255,255,.88),rgba(255,245,235,.86));
      box-shadow:0 24px 55px rgba(44,16,6,.13), inset 0 1px 0 rgba(255,255,255,.9);
      overflow:hidden;
      animation:rise .62s ease both;
      animation-delay:var(--delay);
      transform-style:preserve-3d;
    }
    .draft-card::before {
      content:"";
      position:absolute;
      width:220px;height:220px;
      right:-95px;top:-95px;
      border-radius:50%;
      background:radial-gradient(circle,var(--orange2),transparent 65%);
      opacity:.16;
    }
    .draft-card:hover { transform:translateY(-8px) rotateX(2deg) rotateY(-2deg); box-shadow:0 34px 75px rgba(44,16,6,.2); }
    .shine {
      position:absolute;
      inset:0;
      background:linear-gradient(115deg, transparent 0%, rgba(255,255,255,.5) 42%, transparent 58%);
      transform:translateX(-120%);
      transition:transform .7s ease;
      pointer-events:none;
    }
    .draft-card:hover .shine { transform:translateX(120%); }
    .card-topline { color:var(--orange); font-size:11px; font-weight:1000; letter-spacing:3px; text-transform:uppercase; margin-bottom:14px; }
    .draft-card h3 { font-size:28px; line-height:1.08; margin:0 0 10px; letter-spacing:-.8px; }
    .excerpt { color:#45373a; line-height:1.55; margin:0 0 20px; }
    .field-grid { display:grid; gap:10px; margin:18px 0 22px; }
    .field {
      border:1px solid rgba(255,91,42,.18);
      border-radius:16px;
      padding:12px;
      background:rgba(255,247,239,.76);
    }
    .field span { display:block; color:#1d1007; font-size:10px; font-weight:1000; letter-spacing:1.5px; text-transform:uppercase; margin-bottom:6px; }
    .field p { margin:0; color:#5c4d51; font-size:13px; line-height:1.45; }
    .card-actions { display:flex; flex-wrap:wrap; gap:10px; margin-top:auto; }

    .empty-state {
      margin-top:48px;
      min-height:300px;
      display:grid;
      place-items:center;
      text-align:center;
      border:1px dashed rgba(255,91,42,.35);
      border-radius:var(--radius);
      background:rgba(255,255,255,.58);
      box-shadow:var(--shadow);
      padding:40px;
      position:relative;
      overflow:hidden;
    }
    .empty-state h2 { font-size:36px; margin:0 0 10px; }
    .empty-state p { color:var(--muted); margin:0; }
    .orb.small { position:absolute;width:160px;height:160px;border-radius:50%;background:linear-gradient(135deg,var(--cyan),var(--purple));opacity:.25;filter:blur(2px);right:10%;top:20%;animation:floaty 8s ease-in-out infinite; }

    .toast {
      position:fixed;
      left:50%;bottom:24px;
      transform:translateX(-50%) translateY(30px);
      background:#100805;
      color:#fff;
      padding:14px 18px;
      border-radius:999px;
      box-shadow:0 18px 50px rgba(0,0,0,.28);
      font-weight:900;
      opacity:0;
      pointer-events:none;
      transition:.25s ease;
      z-index:20;
    }
    .toast.show { opacity:1; transform:translateX(-50%) translateY(0); }

    @keyframes spin { to { transform:rotate(360deg); } }
    @keyframes floaty { 0%,100% { transform:translate3d(0,0,0) rotate(0deg); } 50% { transform:translate3d(0,-22px,40px) rotate(8deg); } }
    @keyframes rise { from { opacity:0; transform:translateY(28px) scale(.98); } to { opacity:1; transform:translateY(0) scale(1); } }

    @media (max-width:900px) {
      .hero { padding:44px 22px 78px; }
      .hero h1 { letter-spacing:-2px; }
      .shape-1,.shape-2,.shape-3 { opacity:.28; }
      .main { padding:0 18px; }
      .form-row { grid-template-columns:1fr; }
      .btn { width:100%; }
      .date-head { align-items:flex-start; flex-direction:column; }
    }
  </style>
</head>
<body>
  <div class="page">
    <header class="hero">
      <div class="float-shape shape-1"></div>
      <div class="float-shape shape-2"></div>
      <div class="float-shape shape-3"></div>

      <div class="hero-inner">
        <div class="eyebrow">Brutus & Barnaby Blog AI Agent</div>
        <h1>AI Blog Draft Studio</h1>
        <p>Generate colorful, SEO-ready dog blog drafts, review each article, and copy the final HTML from inside the draft page.</p>

        <div class="stat-pill">Total Blogs Generated: <strong>__TOTAL__</strong></div>

        <div class="hero-buttons">
          <a class="btn primary" href="#generate">Generate Blogs</a>
          <a class="btn dark" href="#drafts">View Drafts</a>
        </div>
      </div>
    </header>

    <main class="main">
      <section class="generator" id="generate">
        <h2>Generate New Blogs</h2>
        <p>Choose how many new AI drafts to generate. Each new run clears the old dashboard drafts first, so the page only shows the latest batch.</p>

        <form class="form-row" onsubmit="startGeneration(event)">
          <div>
            <label for="blogsCount">How many blogs?</label>
            <input id="blogsCount" type="number" min="1" max="20" value="1" required>
          </div>
          <div>
            <label for="agentPin">PIN, optional</label>
            <input id="agentPin" type="password" placeholder="Only if Worker PIN is set">
          </div>
          <button class="btn primary" type="submit" id="generateBtn">Generate Blog Drafts</button>
        </form>
      </section>

      __CARDS__
    </main>
  </div>

  <div class="toast" id="toast">Copied</div>

  <script>
    const TRIGGER_WORKER_URL = __TRIGGER_URL__;
    const ACTIONS_URL = __ACTIONS_URL__;
    const BLOGS = __BLOGS_JSON__;

    function toast(message) {
      const el = document.getElementById('toast');
      el.textContent = message || 'Done';
      el.classList.add('show');
      setTimeout(() => el.classList.remove('show'), 1800);
    }

    async function startGeneration(event) {
      event.preventDefault();
      const btn = document.getElementById('generateBtn');
      const count = Math.min(Math.max(parseInt(document.getElementById('blogsCount').value || '1', 10), 1), 20);
      const pin = document.getElementById('agentPin').value || '';
      btn.disabled = true;
      const oldText = btn.textContent;
      btn.textContent = 'Starting...';

      try {
        if (!TRIGGER_WORKER_URL) {
          window.open(ACTIONS_URL, '_blank');
          return;
        }

        const response = await fetch(TRIGGER_WORKER_URL, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'x-agent-pin': pin
          },
          body: JSON.stringify({
            blogs_per_day: String(count),
            dry_run: 'false',
            clear_previous: 'true'
          })
        });

        if (!response.ok) {
          const text = await response.text();
          throw new Error(text || 'Could not start workflow');
        }

        toast('Blog generation started');
      } catch (error) {
        console.error(error);
        toast('Trigger failed. Opening GitHub Actions');
        window.open(ACTIONS_URL, '_blank');
      } finally {
        btn.disabled = false;
        btn.textContent = oldText;
      }
    }

    async function copySeo(button) {
      try {
        const data = JSON.parse(button.dataset.seo || '{}');
        const text = Object.entries(data)
          .map(([key, value]) => `${key}: ${value || ''}`)
          .join('\n');
        await navigator.clipboard.writeText(text);
        toast('SEO copied');
      } catch (error) {
        console.error(error);
        toast('Could not copy SEO');
      }
    }
  </script>
</body>
</html>
'''

    return (
        html.replace("__TOTAL__", escape(str(total)))
        .replace("__CARDS__", cards_html)
        .replace("__TRIGGER_URL__", trigger_url)
        .replace("__ACTIONS_URL__", actions_url)
        .replace("__BLOGS_JSON__", blogs_json)
    )


def main() -> None:
    blogs = load_blogs()
    OUT_FILE.write_text(build_html(blogs), encoding="utf-8")
    print(f"Built {OUT_FILE} with {len(blogs)} blog(s).")


if __name__ == "__main__":
    main()
