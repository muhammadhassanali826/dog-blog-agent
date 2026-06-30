#!/usr/bin/env python3
"""
Premium neon dashboard builder for Dog Blog AI Agent.

UI goals:
- Fire/glow square at the top with BRUTUS & BARNABY text
- Big main headline: AI BLOG GENERATOR
- Only one top stat: Total Blogs Generated
- Animated side dog decorations
- RGB glowing borders for generated blog cards
- Cleaner, clearer fonts and stronger contrast
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
          <div class="empty-ring"></div>
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
            category = val(item, "category", default="Blog Draft")
            path = blog_path(item)

            seo_payload = {
                "Blog Title": title,
                "Excerpt": excerpt,
                "Page Title": page_title,
                "Meta Description": meta_description,
                "URL Handle": url_handle,
                "SEO Keywords": keywords,
            }
            seo_json = escape(json.dumps(seo_payload, ensure_ascii=False), quote=True)

            cards.append(f"""
            <article class="draft-card" style="--delay:{idx * 70}ms;">
              <div class="rgb-border"></div>
              <div class="card-inner">
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
              </div>
            </article>
            """)

        sections.append(f"""
        <section class="date-section" id="drafts">
          <div class="date-head">
            <h2>{escape(date)}</h2>
            <span>{len(items)} Draft(s)</span>
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

    html = r'''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>AI Blog Generator</title>
  <style>
    :root {
      --bg:#07070d;
      --panel:#11131b;
      --panel2:#171922;
      --soft:#1d202c;
      --text:#f5f7fb;
      --muted:#b9c0cf;
      --line:rgba(255,255,255,.08);
      --orange:#ff5b22;
      --orange2:#ff8a1e;
      --red:#ff2d55;
      --pink:#ff4fd8;
      --cyan:#32d8ff;
      --purple:#7269ff;
      --green:#53ff96;
      --shadow:0 20px 50px rgba(0,0,0,.35);
      --radius:26px;
    }

    * { box-sizing:border-box; }
    html { scroll-behavior:smooth; }
    body {
      margin:0;
      font-family:Inter,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
      background:
        radial-gradient(circle at 15% 20%, rgba(255,91,34,.18), transparent 26%),
        radial-gradient(circle at 85% 15%, rgba(50,216,255,.16), transparent 22%),
        radial-gradient(circle at 75% 80%, rgba(114,105,255,.16), transparent 25%),
        linear-gradient(180deg,#06070d 0%, #0d0f16 48%, #111521 100%);
      color:var(--text);
      overflow-x:hidden;
    }

    .page {
      position:relative;
      min-height:100vh;
      overflow:hidden;
    }

    .side-dog {
      position:fixed;
      top:50%;
      transform:translateY(-50%);
      width:130px;
      height:210px;
      z-index:0;
      pointer-events:none;
      opacity:.9;
    }

    .side-dog.left { left:18px; }
    .side-dog.right { right:18px; }

    .dog-core {
      position:absolute;
      inset:0;
      border-radius:36px;
      background:linear-gradient(180deg, rgba(255,255,255,.08), rgba(255,255,255,.02));
      border:1px solid rgba(255,255,255,.1);
      backdrop-filter:blur(10px);
      box-shadow:
        0 20px 50px rgba(0,0,0,.28),
        inset 0 1px 0 rgba(255,255,255,.12);
      animation:floatDog 6s ease-in-out infinite;
    }

    .dog-core::before {
      content:"🐶";
      position:absolute;
      inset:0;
      display:flex;
      align-items:center;
      justify-content:center;
      font-size:72px;
      filter:drop-shadow(0 8px 24px rgba(255,91,34,.35));
    }

    .dog-core::after {
      content:"";
      position:absolute;
      inset:-2px;
      border-radius:38px;
      background:linear-gradient(135deg,var(--orange),var(--pink),var(--cyan),var(--purple),var(--orange));
      background-size:300% 300%;
      z-index:-1;
      filter:blur(14px);
      opacity:.7;
      animation:rgbMove 5s linear infinite;
    }

    .dog-dot {
      position:absolute;
      width:18px;
      height:18px;
      border-radius:50%;
      background:linear-gradient(135deg,var(--cyan),var(--purple));
      box-shadow:0 0 20px rgba(50,216,255,.8);
      animation:floatDot 5s ease-in-out infinite;
    }
    .dog-dot.one { top:-10px; left:16px; }
    .dog-dot.two { bottom:12px; right:-6px; animation-delay:-2s; }
    .dog-dot.three { top:36px; right:-10px; width:12px; height:12px; animation-delay:-1s; }

    .hero {
      position:relative;
      z-index:1;
      padding:34px 6vw 70px;
      border-bottom:1px solid rgba(255,255,255,.06);
      background:
        radial-gradient(circle at 18% 12%, rgba(255,67,28,.3), transparent 24%),
        radial-gradient(circle at 82% 24%, rgba(50,216,255,.16), transparent 20%),
        linear-gradient(180deg, rgba(255,255,255,.02), transparent);
    }

    .hero-inner {
      max-width:1100px;
      margin:0 auto;
      text-align:center;
      position:relative;
      z-index:2;
    }

    .brand-cube {
      position:relative;
      width:110px;
      height:110px;
      margin:0 auto 26px;
      border-radius:28px;
      background:linear-gradient(145deg,#341005,#ff5b22 55%, #ffcc4d);
      display:flex;
      align-items:center;
      justify-content:center;
      text-align:center;
      padding:16px;
      font-size:11px;
      line-height:1.2;
      font-weight:1000;
      text-transform:uppercase;
      letter-spacing:1.8px;
      color:#fff;
      box-shadow:
        0 26px 60px rgba(255,91,34,.3),
        inset 0 1px 0 rgba(255,255,255,.3);
      transform:perspective(800px) rotateX(12deg) rotateY(-10deg);
      animation:floatCube 4s ease-in-out infinite;
    }

    .brand-cube::before {
      content:"";
      position:absolute;
      inset:-12px;
      border-radius:34px;
      background:
        radial-gradient(circle at 50% 100%, rgba(255,150,40,.95), transparent 52%),
        radial-gradient(circle at 35% 100%, rgba(255,70,30,.75), transparent 44%),
        radial-gradient(circle at 65% 100%, rgba(255,215,80,.75), transparent 44%);
      filter:blur(18px);
      z-index:-1;
      animation:firePulse 2.1s ease-in-out infinite;
    }

    .brand-cube::after {
      content:"";
      position:absolute;
      inset:-2px;
      border-radius:30px;
      border:1px solid rgba(255,255,255,.18);
      pointer-events:none;
    }

    .hero h1 {
      margin:0;
      font-size:clamp(46px, 7vw, 86px);
      line-height:.95;
      letter-spacing:-2.8px;
      font-weight:1000;
      color:#fff;
      text-shadow:0 12px 28px rgba(0,0,0,.38);
    }

    .stat-wrap {
      margin-top:24px;
      display:flex;
      justify-content:center;
    }

    .stat-pill {
      display:inline-flex;
      align-items:center;
      gap:10px;
      padding:14px 22px;
      border-radius:999px;
      background:rgba(255,255,255,.06);
      border:1px solid rgba(255,255,255,.12);
      box-shadow:
        0 12px 32px rgba(0,0,0,.25),
        inset 0 1px 0 rgba(255,255,255,.12);
      color:#fff;
      font-size:14px;
      font-weight:900;
      text-transform:uppercase;
      letter-spacing:1px;
    }

    .stat-pill strong {
      color:#fff;
      font-size:18px;
      text-shadow:0 0 18px rgba(255,91,34,.5);
    }

    .hero-buttons {
      display:flex;
      justify-content:center;
      gap:14px;
      flex-wrap:wrap;
      margin-top:22px;
    }

    .btn {
      border:0;
      outline:none;
      cursor:pointer;
      display:inline-flex;
      align-items:center;
      justify-content:center;
      min-height:52px;
      padding:14px 22px;
      border-radius:999px;
      text-decoration:none;
      font-weight:900;
      font-size:15px;
      font-family:inherit;
      transition:.2s ease;
      letter-spacing:-.2px;
    }

    .btn:hover {
      transform:translateY(-3px);
    }

    .btn.primary {
      color:#fff;
      background:linear-gradient(135deg,var(--orange),var(--red),var(--pink));
      box-shadow:0 14px 28px rgba(255,91,34,.28);
    }

    .btn.secondary {
      color:#fff;
      background:linear-gradient(135deg,#1c1e28,#2a2d39);
      border:1px solid rgba(255,255,255,.1);
      box-shadow:0 10px 24px rgba(0,0,0,.2);
    }

    .main {
      position:relative;
      z-index:1;
      max-width:1200px;
      margin:-28px auto 70px;
      padding:0 22px;
    }

    .generator {
      position:relative;
      overflow:hidden;
      border-radius:28px;
      padding:28px;
      background:linear-gradient(180deg, rgba(20,22,30,.92), rgba(14,16,24,.92));
      border:1px solid rgba(255,255,255,.08);
      box-shadow:var(--shadow);
      margin-bottom:42px;
    }

    .generator::before {
      content:"";
      position:absolute;
      inset:-1px;
      border-radius:28px;
      padding:1px;
      background:linear-gradient(135deg,var(--orange),var(--pink),var(--cyan),var(--purple),var(--orange));
      background-size:300% 300%;
      -webkit-mask:
        linear-gradient(#000 0 0) content-box,
        linear-gradient(#000 0 0);
      -webkit-mask-composite:xor;
      mask-composite:exclude;
      animation:rgbMove 7s linear infinite;
      pointer-events:none;
      opacity:.95;
    }

    .generator h2 {
      margin:0 0 8px;
      font-size:38px;
      letter-spacing:-1px;
      color:#fff;
    }

    .generator p {
      margin:0 0 22px;
      color:var(--muted);
      line-height:1.65;
      font-size:16px;
      max-width:860px;
    }

    .form-row {
      display:grid;
      grid-template-columns:1fr 1fr auto;
      gap:14px;
      align-items:end;
    }

    label {
      display:block;
      margin-bottom:8px;
      color:#fff;
      font-size:12px;
      font-weight:1000;
      text-transform:uppercase;
      letter-spacing:2px;
    }

    input {
      width:100%;
      height:56px;
      border-radius:18px;
      border:1px solid rgba(255,255,255,.12);
      background:#0f1118;
      color:#fff;
      padding:0 16px;
      font:inherit;
      font-size:16px;
      box-shadow:inset 0 1px 0 rgba(255,255,255,.05);
    }

    input:focus {
      outline:none;
      border-color:rgba(255,91,34,.7);
      box-shadow:0 0 0 3px rgba(255,91,34,.12);
    }

    .date-section {
      margin-top:18px;
    }

    .date-head {
      display:flex;
      align-items:end;
      justify-content:space-between;
      gap:12px;
      margin-bottom:20px;
    }

    .date-head h2 {
      margin:0;
      font-size:44px;
      letter-spacing:-1.4px;
      color:#fff;
    }

    .date-head span {
      color:#ff6940;
      font-weight:1000;
      text-transform:uppercase;
      letter-spacing:1px;
      font-size:14px;
    }

    .draft-grid {
      display:grid;
      grid-template-columns:1fr;
      gap:24px;
    }

    .draft-card {
      position:relative;
      border-radius:28px;
      padding:1px;
      background:linear-gradient(135deg,var(--orange),var(--pink),var(--cyan),var(--purple),var(--orange));
      background-size:300% 300%;
      box-shadow:0 16px 40px rgba(0,0,0,.25);
      animation:rgbMove 7s linear infinite, rise .45s ease both;
      animation-delay:var(--delay);
      overflow:hidden;
    }

    .rgb-border {
      display:none;
    }

    .card-inner {
      position:relative;
      border-radius:27px;
      padding:24px;
      background:linear-gradient(180deg,#12141c 0%, #151924 100%);
      min-height:100%;
    }

    .card-inner::before {
      content:"";
      position:absolute;
      inset:0;
      background:
        radial-gradient(circle at 100% 0%, rgba(255,91,34,.12), transparent 28%),
        radial-gradient(circle at 0% 100%, rgba(50,216,255,.08), transparent 22%);
      pointer-events:none;
    }

    .card-topline {
      position:relative;
      z-index:1;
      color:#ff6a3e;
      font-size:11px;
      font-weight:1000;
      letter-spacing:3px;
      text-transform:uppercase;
      margin-bottom:14px;
    }

    .draft-card h3 {
      position:relative;
      z-index:1;
      margin:0 0 12px;
      font-size:clamp(28px, 4vw, 46px);
      line-height:1.12;
      letter-spacing:-.8px;
      color:#fff;
    }

    .excerpt {
      position:relative;
      z-index:1;
      color:#d0d6e2;
      line-height:1.7;
      font-size:16px;
      margin:0 0 20px;
      max-width:1000px;
    }

    .field-grid {
      position:relative;
      z-index:1;
      display:grid;
      gap:12px;
      margin-top:18px;
      margin-bottom:22px;
    }

    .field {
      border:1px solid rgba(255,255,255,.09);
      border-radius:18px;
      padding:14px 14px 12px;
      background:rgba(255,255,255,.03);
    }

    .field span {
      display:block;
      color:#fff;
      font-size:11px;
      font-weight:1000;
      text-transform:uppercase;
      letter-spacing:2px;
      margin-bottom:7px;
    }

    .field p {
      margin:0;
      color:#d7dce6;
      font-size:15px;
      line-height:1.6;
      word-break:break-word;
    }

    .card-actions {
      position:relative;
      z-index:1;
      display:flex;
      flex-wrap:wrap;
      gap:12px;
      margin-top:8px;
    }

    .empty-state {
      position:relative;
      margin-top:34px;
      padding:56px 24px;
      text-align:center;
      border-radius:28px;
      background:linear-gradient(180deg,#12141c,#171b27);
      border:1px solid rgba(255,255,255,.08);
      box-shadow:var(--shadow);
      overflow:hidden;
    }

    .empty-ring {
      width:130px;
      height:130px;
      margin:0 auto 24px;
      border-radius:50%;
      border:2px solid rgba(255,255,255,.14);
      box-shadow:0 0 28px rgba(255,91,34,.22);
      position:relative;
    }

    .empty-ring::before {
      content:"🐾";
      position:absolute;
      inset:0;
      display:flex;
      align-items:center;
      justify-content:center;
      font-size:48px;
    }

    .empty-state h2 {
      margin:0 0 10px;
      font-size:34px;
      color:#fff;
    }

    .empty-state p {
      margin:0;
      color:#c7cfde;
      font-size:16px;
      line-height:1.6;
    }

    .toast {
      position:fixed;
      left:50%;
      bottom:24px;
      transform:translateX(-50%) translateY(24px);
      opacity:0;
      pointer-events:none;
      background:#12141c;
      color:#fff;
      border:1px solid rgba(255,255,255,.1);
      padding:14px 18px;
      border-radius:999px;
      box-shadow:0 16px 36px rgba(0,0,0,.28);
      font-weight:900;
      transition:.24s ease;
      z-index:30;
    }

    .toast.show {
      opacity:1;
      transform:translateX(-50%) translateY(0);
    }

    @keyframes rgbMove {
      0% { background-position:0% 50%; }
      50% { background-position:100% 50%; }
      100% { background-position:0% 50%; }
    }

    @keyframes firePulse {
      0%,100% { transform:scale(1); opacity:.9; }
      50% { transform:scale(1.08); opacity:1; }
    }

    @keyframes floatCube {
      0%,100% { transform:perspective(800px) rotateX(12deg) rotateY(-10deg) translateY(0); }
      50% { transform:perspective(800px) rotateX(12deg) rotateY(-10deg) translateY(-8px); }
    }

    @keyframes floatDog {
      0%,100% { transform:translateY(0) rotate(-2deg); }
      50% { transform:translateY(-12px) rotate(2deg); }
    }

    @keyframes floatDot {
      0%,100% { transform:translateY(0); }
      50% { transform:translateY(-10px); }
    }

    @keyframes rise {
      from { opacity:0; transform:translateY(18px); }
      to { opacity:1; transform:translateY(0); }
    }

    @media (max-width:1200px) {
      .side-dog { display:none; }
    }

    @media (max-width:900px) {
      .hero {
        padding:28px 18px 58px;
      }

      .main {
        padding:0 14px;
      }

      .form-row {
        grid-template-columns:1fr;
      }

      .btn {
        width:100%;
      }

      .date-head {
        flex-direction:column;
        align-items:flex-start;
      }

      .date-head h2 {
        font-size:34px;
      }

      .draft-card h3 {
        font-size:32px;
      }
    }
  </style>
</head>
<body>
  <div class="page">

    <div class="side-dog left">
      <div class="dog-core"></div>
      <div class="dog-dot one"></div>
      <div class="dog-dot two"></div>
      <div class="dog-dot three"></div>
    </div>

    <div class="side-dog right">
      <div class="dog-core"></div>
      <div class="dog-dot one"></div>
      <div class="dog-dot two"></div>
      <div class="dog-dot three"></div>
    </div>

    <header class="hero">
      <div class="hero-inner">
        <div class="brand-cube">Brutus<br>&amp;<br>Barnaby</div>
        <h1>AI BLOG GENERATOR</h1>

        <div class="stat-wrap">
          <div class="stat-pill">Total Blogs Generated: <strong>__TOTAL__</strong></div>
        </div>

        <div class="hero-buttons">
          <a class="btn primary" href="#generate">Generate Blogs</a>
          <a class="btn secondary" href="#drafts">View Drafts</a>
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
