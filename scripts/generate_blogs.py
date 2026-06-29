#!/usr/bin/env python3
"""
Generate 20 dog blog drafts per day with Gemini API.

This script:
- Reads pending topics from data/topics.csv
- Reads product card data from data/products.json
- Calls Gemini once per topic
- Saves each generated blog as blogs/YYYY-MM-DD-url-handle.html
- Updates data/generated_blogs.json
- Marks used topics as generated in topics.csv

No Shopify publishing is included.
"""

from __future__ import annotations

import csv
import datetime as dt
import html
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
BLOGS_DIR = ROOT / "blogs"
TOPICS_CSV = DATA_DIR / "topics.csv"
PRODUCTS_JSON = DATA_DIR / "products.json"
GENERATED_JSON = DATA_DIR / "generated_blogs.json"

BLOGS_PER_DAY = int(os.getenv("BLOGS_PER_DAY", "20"))
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
SLEEP_SECONDS = float(os.getenv("SLEEP_SECONDS_BETWEEN_CALLS", "6"))
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
DRY_RUN = os.getenv("DRY_RUN", "false").lower() == "true"

BRAND_NAME = "Brutus & Barnaby"
BRAND_SITE = "https://brutusandbarnaby.com"
ORANGE = "#f02400"

TRUSTED_EXTERNAL_LINKS = [
    {
        "label": "VCA Hospitals: Dog treats and moderation",
        "url": "https://vcahospitals.com/know-your-pet/dog-treats",
    },
    {
        "label": "AKC: How many treats can a dog have?",
        "url": "https://www.akc.org/expert-advice/nutrition/how-many-treats-can-dog-have/",
    },
    {
        "label": "ASPCA: Common dog behavior issues",
        "url": "https://www.aspca.org/pet-care/dog-care/common-dog-behavior-issues",
    },
    {
        "label": "PetMD: Dog nutrition basics",
        "url": "https://www.petmd.com/dog/nutrition",
    },
]

INTERNAL_LINKS = [
    {
        "label": "Shop all natural dog treats",
        "url": "https://brutusandbarnaby.com/collections/all",
    },
    {
        "label": "Dog treat rotation guide",
        "url": "https://brutusandbarnaby.com/blogs/dog-tips/dog-treat-rotation-guide",
    },
    {
        "label": "Long-lasting dog chews for power chewers",
        "url": "https://brutusandbarnaby.com/blogs/dog-tips/long-lasting-dog-chews-for-power-chewers",
    },
]


def load_csv(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"Missing file: {path}")
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: List[Dict[str, str]]) -> None:
    if not rows:
        return
    fieldnames = list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return default


def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def slugify(text: str, max_length: int = 80) -> str:
    text = text.lower().strip()
    text = re.sub(r"&", " and ", text)
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = re.sub(r"-+", "-", text).strip("-")
    return text[:max_length].strip("-") or "dog-blog"


def clean_json_text(text: str) -> str:
    """Extract JSON from model response even if it accidentally includes fences."""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    first = text.find("{")
    last = text.rfind("}")
    if first != -1 and last != -1 and last > first:
        return text[first : last + 1]
    return text


def pick_relevant_products(topic: Dict[str, str], products: List[Dict[str, Any]], limit: int = 4) -> List[Dict[str, Any]]:
    searchable = " ".join(
        [
            topic.get("topic", ""),
            topic.get("main_keyword", ""),
            topic.get("product_focus", ""),
            topic.get("category", ""),
        ]
    ).lower()

    scored = []
    for product in products:
        score = 0
        name = product.get("name", "").lower()
        if name and name in searchable:
            score += 8
        for phrase in product.get("best_for", []):
            if str(phrase).lower() in searchable:
                score += 3
        if topic.get("product_focus", "").lower() == name:
            score += 12
        scored.append((score, product))

    scored.sort(key=lambda item: item[0], reverse=True)
    selected = [product for score, product in scored if score > 0][:limit]

    # Always include some fallback products so the blog can create product cards.
    if len(selected) < limit:
        for _, product in scored:
            if product not in selected:
                selected.append(product)
            if len(selected) >= limit:
                break
    return selected[:limit]


def build_prompt(topic: Dict[str, str], products: List[Dict[str, Any]]) -> str:
    product_json = json.dumps(products, ensure_ascii=False, indent=2)
    internal_json = json.dumps(INTERNAL_LINKS, ensure_ascii=False, indent=2)
    external_json = json.dumps(TRUSTED_EXTERNAL_LINKS, ensure_ascii=False, indent=2)

    return f"""
You are the Brutus & Barnaby SEO blog generator.

Create one complete SEO-optimized dog blog draft.

Topic: {topic.get('topic', '').strip()}
Main keyword: {topic.get('main_keyword', '').strip()}
Product focus: {topic.get('product_focus', '').strip()}
Category: {topic.get('category', '').strip()}
Brand: {BRAND_NAME}
Brand website: {BRAND_SITE}
Accent color: {ORANGE}

Use these products for product recommendation cards:
{product_json}

Use 1-2 internal links from this list:
{internal_json}

Use 2-3 external trusted links from this list only:
{external_json}

REQUIRED OUTPUT:
Return valid JSON only. No markdown. No explanation.

JSON schema:
{{
  "blog_title": "",
  "excerpt": "",
  "search_engine_listing": {{
    "page_title": "",
    "meta_description": "",
    "url_handle": ""
  }},
  "seo_keywords": [""],
  "html": ""
}}

FIELD RULES:
- blog_title: natural, high-click SEO title. Do not exceed 75 characters unless needed.
- excerpt: 1-2 sentence blog excerpt, conversion-aware but educational.
- page_title: SEO page title, ideally 50-65 characters.
- meta_description: SEO meta description, ideally 140-160 characters.
- url_handle: lowercase hyphenated slug only, no domain, no slash.
- seo_keywords: 8-15 SEO keywords, including main keyword, long-tail variations, product intent terms, and buyer-intent terms.
- html: Full inline HTML body content only. Do not include <!DOCTYPE>, <html>, <head>, or <body> tags.

HTML STYLE REQUIREMENTS:
Match the Brutus & Barnaby reference blog style:
- One outer wrapper div using system-ui font.
- Black hero section with white H1.
- Orange accent color #f02400.
- Hero should include a small uppercase category label.
- Hero should include 2-3 keyword tag pills.
- Include italic intro callout with orange left border.
- Include a “Quick answer” box near the top.
- Use clean H2/H3 headings.
- Include cards/grids where useful.
- Include at least one helpful table where useful.
- Include a product recommendation section with 2-4 product cards.
- Product cards must include image, short copy, bullets, and orange CTA button.
- Include a Helpful Reading & Trusted Sources section.
- Include 1-2 internal Brutus & Barnaby links.
- Include 2-3 external trusted links from the supplied list only.
- Include FAQ section with 4-6 questions.
- Include black final CTA section.
- Include educational disclaimer at the bottom.

CONTENT RULES:
- Write for dog owners/pet parents.
- Tone: helpful, warm, educational, conversion-focused.
- Avoid medical claims.
- Use safe wording: “may help,” “can support,” “can be part of a routine,” “ask your veterinarian.”
- Mention vet guidance for sudden symptoms, allergies, choking, digestion, weight loss, vomiting, diarrhea, increased thirst, or medical concerns.
- Do not say Brutus & Barnaby products cure or treat medical conditions.
- Do not keyword stuff.
- Do not make all blogs sound the same.
- Keep paragraphs short and mobile-friendly.
- Make the article genuinely useful, not thin content.
- Aim for roughly 1200-1800 words in the HTML.
""".strip()


def call_gemini(prompt: str) -> Dict[str, Any]:
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is missing. Add it in GitHub Secrets.")

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": prompt}],
            }
        ],
        "generationConfig": {
            "temperature": 0.78,
            "topP": 0.95,
            "maxOutputTokens": 16000,
            "responseMimeType": "application/json",
        },
    }

    body = json.dumps(payload).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": GEMINI_API_KEY,
    }

    for attempt in range(1, MAX_RETRIES + 1):
        req = urllib.request.Request(url, data=body, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=180) as resp:
                raw = resp.read().decode("utf-8")
            data = json.loads(raw)
            text = data["candidates"][0]["content"]["parts"][0]["text"]
            return json.loads(clean_json_text(text))
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8", errors="ignore")
            print(f"Gemini HTTP error attempt {attempt}/{MAX_RETRIES}: {e.code} {error_body[:500]}")
            if e.code in (429, 500, 502, 503, 504) and attempt < MAX_RETRIES:
                time.sleep(30 * attempt)
                continue
            raise
        except Exception as e:
            print(f"Gemini error attempt {attempt}/{MAX_RETRIES}: {e}")
            if attempt < MAX_RETRIES:
                time.sleep(15 * attempt)
                continue
            raise

    raise RuntimeError("Gemini request failed after retries.")


def fake_blog(topic: Dict[str, str], products: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Used only when DRY_RUN=true for testing the workflow without API calls."""
    title = topic.get("topic", "Dog Blog Draft").strip()
    slug = slugify(title)
    product = products[0]
    product_card = f"""
      <div style=\"border:1px solid #f3d2c2;border-radius:14px;padding:1.4em;margin:2em 0;background:#fff8f3;display:flex;gap:1.4em;align-items:center;flex-wrap:wrap;\">
        <div style=\"flex:0 0 180px;max-width:260px;\"><img src=\"{html.escape(product.get('image',''))}\" alt=\"{html.escape(product.get('name','Dog treats'))}\" style=\"width:100%;border-radius:12px;display:block;\"></div>
        <div style=\"flex:1;min-width:240px;\"><div style=\"font-size:10px;font-weight:800;letter-spacing:1.6px;text-transform:uppercase;color:#f02400;margin-bottom:8px;\">Recommended Pick</div><h3 style=\"color:#1a1208;margin:0 0 .5em;font-size:18px;line-height:1.25;\">{html.escape(product.get('name','Natural Dog Treats'))}</h3><p style=\"margin-top:0;line-height:1.7;color:#3a2a1a;font-size:15px;\">A useful product match for this blog topic.</p><a href=\"{html.escape(product.get('url','#'))}\" style=\"display:inline-block;background:#f02400;color:#ffffff;font-weight:800;text-decoration:none;padding:.85em 1.25em;border-radius:999px;font-size:13px;\">{html.escape(product.get('cta','Shop Now'))}</a></div>
      </div>
    """
    body = f"""
<div style=\"font-family:system-ui,-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;max-width:100%;overflow:hidden;\">
  <div style=\"background:#000000;color:#ffffff;padding:48px 44px 40px;border-radius:0;\">
    <div style=\"font-size:10px;font-weight:800;letter-spacing:3px;text-transform:uppercase;color:#f02400;margin-bottom:14px;\">DOG TREAT GUIDE</div>
    <h1 style=\"font-size:34px;font-weight:800;line-height:1.18;margin:0 0 14px;color:#ffffff;\">{html.escape(title)}</h1>
    <p style=\"font-size:15px;opacity:.84;line-height:1.65;max-width:760px;margin:0 0 20px;color:#ffffff;\">This is a dry-run draft preview. Turn DRY_RUN off and add GEMINI_API_KEY to generate full AI blogs.</p>
  </div>
  <div style=\"padding:28px 44px;border-bottom:1px solid #f0ece6;\">
    <p style=\"font-size:15px;line-height:1.8;color:#2a2a2a;font-style:italic;padding-left:16px;border-left:3px solid #f02400;margin:0 0 22px;\">This draft follows the required Brutus & Barnaby blog structure.</p>
    <div style=\"background:#fff4ee;border:1px solid #ffd7c4;border-left:4px solid #f02400;border-radius:10px;padding:14px 16px;margin:18px 0 24px;\"><p style=\"margin:0;font-size:15px;line-height:1.7;color:#3a2a1a;\"><strong style=\"color:#1a1208;\">Quick answer:</strong> This is a test blog generated without using API credits.</p></div>
    <h2 style=\"font-size:24px;font-weight:800;color:#1a1208;margin:24px 0 10px;line-height:1.25;\">Helpful Guide</h2>
    <p style=\"font-size:15px;line-height:1.8;color:#444;margin:0 0 16px;\">Replace this with Gemini output when your API key is ready.</p>
    {product_card}
  </div>
  <div style=\"background:#000000;color:#ffffff;padding:36px 44px;text-align:center;\"><h2 style=\"font-size:30px;font-weight:800;color:#ffffff;margin:0 0 12px;line-height:1.18;\">Build a Better Treat Routine</h2><a href=\"https://brutusandbarnaby.com/collections/all\" style=\"display:inline-block;background:#f02400;color:white;font-weight:800;font-size:13px;letter-spacing:.6px;text-transform:uppercase;text-decoration:none;padding:14px 24px;border-radius:999px;\">Shop Natural Dog Treats</a></div>
  <div style=\"padding:22px 44px;background:#fffaf6;\"><p style=\"font-size:13px;line-height:1.7;color:#6b5d52;margin:0;\"><strong>Educational disclaimer:</strong> This article is for general education only and is not veterinary advice.</p></div>
</div>
"""
    return {
        "blog_title": title,
        "excerpt": f"A helpful dog guide about {title.lower()}.",
        "search_engine_listing": {
            "page_title": title[:65],
            "meta_description": f"Learn about {title.lower()} and how to build a smarter dog treat routine.",
            "url_handle": slug,
        },
        "seo_keywords": [topic.get("main_keyword", "dog treats"), "dog treats", "natural dog chews"],
        "html": body,
    }


def validate_blog(data: Dict[str, Any], fallback_topic: Dict[str, str]) -> Dict[str, Any]:
    title = str(data.get("blog_title") or fallback_topic.get("topic") or "Dog Blog Draft").strip()
    excerpt = str(data.get("excerpt") or "A helpful dog treat and chew guide for pet parents.").strip()
    listing = data.get("search_engine_listing") or {}
    page_title = str(listing.get("page_title") or title).strip()
    meta_description = str(listing.get("meta_description") or excerpt).strip()
    url_handle = slugify(str(listing.get("url_handle") or title))
    keywords = data.get("seo_keywords") or [fallback_topic.get("main_keyword", "dog treats")]
    if isinstance(keywords, str):
        keywords = [k.strip() for k in keywords.split(",") if k.strip()]
    html_body = str(data.get("html") or "").strip()
    if not html_body:
        raise ValueError("Generated blog missing html field.")

    return {
        "blog_title": title,
        "excerpt": excerpt,
        "search_engine_listing": {
            "page_title": page_title,
            "meta_description": meta_description,
            "url_handle": url_handle,
        },
        "seo_keywords": keywords,
        "html": html_body,
    }


def render_blog_page(blog: Dict[str, Any], generated_date: str) -> str:
    listing = blog["search_engine_listing"]
    title = html.escape(listing.get("page_title") or blog.get("blog_title") or "Dog Blog Draft")
    desc = html.escape(listing.get("meta_description") or blog.get("excerpt") or "")
    blog_title = html.escape(blog.get("blog_title", "Dog Blog Draft"))
    excerpt = html.escape(blog.get("excerpt", ""))
    handle = html.escape(listing.get("url_handle", ""))
    keywords = ", ".join(blog.get("seo_keywords", []))
    keywords_escaped = html.escape(keywords)
    body = blog.get("html", "")

    return f"""<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\">
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
  <meta name=\"robots\" content=\"noindex, nofollow\">
  <title>{title}</title>
  <meta name=\"description\" content=\"{desc}\">
  <style>
    body {{ margin: 0; background: #fffaf6; color: #1a1208; }}
    .agent-preview-bar {{ font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background:#fff; border-bottom:1px solid #ead7cc; padding:18px 24px; }}
    .agent-preview-bar a {{ color:#f02400; font-weight:800; }}
    .agent-meta {{ display:grid; grid-template-columns: repeat(auto-fit,minmax(220px,1fr)); gap:12px; margin-top:12px; }}
    .agent-meta div {{ background:#fff8f3; border:1px solid #f3d2c2; border-radius:10px; padding:12px; font-size:13px; line-height:1.55; }}
    .agent-copy {{ border:0; background:#f02400; color:#fff; font-weight:800; border-radius:999px; padding:10px 16px; cursor:pointer; }}
    @media (max-width: 640px) {{
      .agent-preview-bar {{ padding:14px; }}
      div[style*=\"padding:48px 44px\"] {{ padding:34px 22px !important; }}
      div[style*=\"padding:28px 44px\"] {{ padding:24px 22px !important; }}
      div[style*=\"padding:36px 44px\"] {{ padding:30px 22px !important; }}
      div[style*=\"padding:22px 44px\"] {{ padding:20px 22px !important; }}
    }}
  </style>
</head>
<body>
  <div class=\"agent-preview-bar\">
    <div style=\"display:flex;justify-content:space-between;gap:12px;align-items:center;flex-wrap:wrap;\">
      <div>
        <strong>Draft Preview:</strong> {blog_title}<br>
        <span style=\"color:#6b5d52;font-size:13px;\">Generated: {html.escape(generated_date)}</span>
      </div>
      <div>
        <a href=\"../index.html\">← Back to all drafts</a>
      </div>
    </div>
    <div class=\"agent-meta\">
      <div><strong>Blog Title</strong><br>{blog_title}</div>
      <div><strong>Excerpt</strong><br>{excerpt}</div>
      <div><strong>Page Title</strong><br>{title}</div>
      <div><strong>Meta Description</strong><br>{desc}</div>
      <div><strong>URL Handle</strong><br>{handle}</div>
      <div><strong>SEO Keywords</strong><br>{keywords_escaped}</div>
    </div>
  </div>

{body}
</body>
</html>
"""


def main() -> int:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    BLOGS_DIR.mkdir(parents=True, exist_ok=True)

    topics = load_csv(TOPICS_CSV)
    products = load_json(PRODUCTS_JSON, [])
    generated = load_json(GENERATED_JSON, [])

    pending = [row for row in topics if row.get("status", "").strip().lower() == "pending"]
    selected = pending[:BLOGS_PER_DAY]

    if not selected:
        print("No pending topics found. Nothing to generate.")
        return 0

    today = dt.date.today().isoformat()
    print(f"Generating {len(selected)} blog(s) for {today} using model {GEMINI_MODEL}.")

    generated_count = 0
    for index, topic in enumerate(selected, start=1):
        print(f"\n[{index}/{len(selected)}] Topic: {topic.get('topic')}")
        relevant_products = pick_relevant_products(topic, products, limit=4)
        try:
            if DRY_RUN:
                raw_blog = fake_blog(topic, relevant_products)
            else:
                prompt = build_prompt(topic, relevant_products)
                raw_blog = call_gemini(prompt)

            blog = validate_blog(raw_blog, topic)
            handle = blog["search_engine_listing"]["url_handle"]
            filename = f"{today}-{handle}.html"
            blog_path = BLOGS_DIR / filename

            # Avoid overwriting if the model repeats a handle.
            suffix = 2
            while blog_path.exists():
                filename = f"{today}-{handle}-{suffix}.html"
                blog_path = BLOGS_DIR / filename
                suffix += 1

            blog_path.write_text(render_blog_page(blog, today), encoding="utf-8")

            generated.append(
                {
                    "date": today,
                    "status": "generated",
                    "topic": topic.get("topic", ""),
                    "main_keyword": topic.get("main_keyword", ""),
                    "product_focus": topic.get("product_focus", ""),
                    "category": topic.get("category", ""),
                    "blog_title": blog["blog_title"],
                    "excerpt": blog["excerpt"],
                    "page_title": blog["search_engine_listing"]["page_title"],
                    "meta_description": blog["search_engine_listing"]["meta_description"],
                    "url_handle": blog["search_engine_listing"]["url_handle"],
                    "seo_keywords": blog["seo_keywords"],
                    "html_file": f"blogs/{filename}",
                }
            )

            topic["status"] = "generated"
            generated_count += 1
            print(f"Saved: blogs/{filename}")

            if not DRY_RUN and index < len(selected):
                time.sleep(SLEEP_SECONDS)

        except Exception as e:
            print(f"Failed topic '{topic.get('topic')}': {e}", file=sys.stderr)
            topic["status"] = "error"

    save_json(GENERATED_JSON, generated)
    write_csv(TOPICS_CSV, topics)
    print(f"\nDone. Generated {generated_count} blog(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
