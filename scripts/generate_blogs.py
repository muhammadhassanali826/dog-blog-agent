#!/usr/bin/env python3
"""
AI-driven dog blog generator for the GitHub-only Dog Blog AI Agent.

New behavior:
- Does NOT depend on data/topics.csv.
- Uses Gemini to create fresh SEO topics automatically.
- Uses Gemini again to write the full blog HTML for each topic.
- Keeps data/products.json for product recommendations.
- Stores topic history in data/topic_history.json to reduce duplicate topics.
- Clears old dashboard drafts only after at least one new draft is generated successfully when CLEAR_PREVIOUS=true.
- No Shopify publishing.
"""

from __future__ import annotations

import datetime as dt
import html
import json
import os
import re
import sys
import time
import shutil
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
BLOGS_DIR = ROOT / "blogs"
PRODUCTS_JSON = DATA_DIR / "products.json"
GENERATED_JSON = DATA_DIR / "generated_blogs.json"
TOPIC_HISTORY_JSON = DATA_DIR / "topic_history.json"
TOPIC_RULES_JSON = DATA_DIR / "topic_rules.json"

BLOGS_PER_DAY = int(os.getenv("BLOGS_PER_DAY", "20"))
BLOGS_PER_DAY = min(max(BLOGS_PER_DAY, 1), 20)
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
SLEEP_SECONDS = float(os.getenv("SLEEP_SECONDS_BETWEEN_CALLS", "20"))
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "6"))
DRY_RUN = os.getenv("DRY_RUN", "false").lower() == "true"
CLEAR_PREVIOUS = os.getenv("CLEAR_PREVIOUS", "true").lower() == "true"

BRAND_NAME = "Brutus & Barnaby"
BRAND_SITE = "https://brutusandbarnaby.com"
ORANGE = "#f02400"

DEFAULT_PRODUCTS = [
    {
        "name": "Training Treats",
        "best_for": ["training", "puppies", "recall", "reward", "begging", "manners"],
        "url": "https://brutusandbarnaby.com/collections/training-treats",
        "image": "https://brutusandbarnaby.com/cdn/shop/files/Sweet-potato-chicken-flavour-training-treats-for-dogs.jpg?v=1780585838",
        "cta": "Shop Training Treats",
        "benefits": ["Easy to portion", "Great for repeated rewards", "Useful for calm behavior", "Helpful for puppy training"],
    },
    {
        "name": "Bully Sticks",
        "best_for": ["chewing", "boredom", "rawhide alternative", "power chewers", "puppy chews", "dental chews"],
        "url": "https://brutusandbarnaby.com/products/natural-bully-sticks",
        "image": "https://cdn.shopify.com/s/files/1/2502/9690/files/61b7eT8ehkL._AC_9407a40e-351d-44c4-b5ea-4d5f9b4e36b2.jpg?v=1704211819",
        "cta": "Shop Bully Sticks",
        "benefits": ["Rawhide-free chew option", "Great for supervised chew time", "Helps keep dogs busy", "Made for dogs who love to gnaw"],
    },
    {
        "name": "Cow Ears",
        "best_for": ["chewing", "lighter chews", "rawhide alternative", "boredom", "dental chewing"],
        "url": "https://brutusandbarnaby.com/products/cow-ears-for-dogs",
        "image": "https://cdn.shopify.com/s/files/1/2502/9690/files/Cow-ears-for-dogs-by-Brutus-Barnaby.jpg?v=1780582538",
        "cta": "Shop Cow Ears",
        "benefits": ["Natural chew option", "Good for supervised downtime", "Rawhide-free", "Helps redirect chewing"],
    },
    {
        "name": "Sweet Potato Treats",
        "best_for": ["sweet potato", "lighter treats", "sensitive stomach", "snacking", "low fat"],
        "url": "https://brutusandbarnaby.com/collections/sweet-potato-dog-treats",
        "image": "https://brutusandbarnaby.com/cdn/shop/files/Sweet-potato-fries-dog-treats-by-Brutus-Barnaby.jpg?v=1780583148",
        "cta": "Shop Sweet Potato Treats",
        "benefits": ["Simple snack option", "Easy to portion", "Great for treat routines", "Useful for lighter treat days"],
    },
    {
        "name": "Beef Lung Bites",
        "best_for": ["high value", "training", "picky eaters", "recall", "single ingredient"],
        "url": "https://brutusandbarnaby.com/products/beef-lung-bites",
        "image": "https://brutusandbarnaby.com/cdn/shop/files/Beef-lung-bites-dog-treats.jpg?v=1780585048",
        "cta": "Shop Beef Lung Bites",
        "benefits": ["High-value reward", "Easy to break smaller", "Great for focus", "Simple beef treat"],
    },
]

TRUSTED_EXTERNAL_LINKS = [
    {"label": "VCA Hospitals: Dog treats and moderation", "url": "https://vcahospitals.com/know-your-pet/dog-treats"},
    {"label": "AKC: How many treats can a dog have?", "url": "https://www.akc.org/expert-advice/nutrition/how-many-treats-can-dog-have/"},
    {"label": "ASPCA: Common dog behavior issues", "url": "https://www.aspca.org/pet-care/dog-care/common-dog-behavior-issues"},
    {"label": "PetMD: Dog nutrition basics", "url": "https://www.petmd.com/dog/nutrition"},
]

INTERNAL_LINKS = [
    {"label": "Shop all natural dog treats", "url": "https://brutusandbarnaby.com/collections/all"},
    {"label": "Dog treat rotation guide", "url": "https://brutusandbarnaby.com/blogs/dog-tips/dog-treat-rotation-guide"},
    {"label": "Long-lasting dog chews for power chewers", "url": "https://brutusandbarnaby.com/blogs/dog-tips/long-lasting-dog-chews-for-power-chewers"},
]

DEFAULT_TOPIC_RULES = {
    "brand": "Brutus & Barnaby",
    "goal": "Generate fresh SEO blog topics automatically for a dog treats and chews brand.",
    "daily_categories": [
        "dog chewing safety",
        "puppy treats and chews",
        "senior dog treats",
        "dog boredom and enrichment",
        "rawhide alternatives",
        "dog treat nutrition",
        "training treats",
        "dental chews",
        "sensitive stomach treats",
        "power chewer guides",
        "can dogs eat topics",
        "dog treat routines",
    ],
    "avoid_topics_about": [
        "medical diagnosis",
        "guaranteed health cures",
        "unsafe feeding advice",
        "recommending treats as treatment for disease",
        "making claims that chews cure dental disease",
    ],
}


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def slugify(text: str, max_length: int = 80) -> str:
    text = text.lower().strip()
    text = re.sub(r"&", " and ", text)
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = re.sub(r"-+", "-", text).strip("-")
    return text[:max_length].strip("-") or "dog-blog"


def clean_json_text(text: str) -> str:
    """Extract JSON from a Gemini response even if it includes markdown fences."""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)

    starts = [pos for pos in (text.find("{"), text.find("[")) if pos != -1]
    if not starts:
        return text
    first = min(starts)

    last_obj = text.rfind("}")
    last_arr = text.rfind("]")
    last = max(last_obj, last_arr)
    if last != -1 and last > first:
        return text[first : last + 1]
    return text


def call_gemini_json(prompt: str, max_output_tokens: int = 16000, temperature: float = 0.75) -> Any:
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is missing. Add it in GitHub Secrets.")

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": temperature,
            "topP": 0.95,
            "maxOutputTokens": max_output_tokens,
            "responseMimeType": "application/json",
        },
    }
    body = json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json", "x-goog-api-key": GEMINI_API_KEY}

    for attempt in range(1, MAX_RETRIES + 1):
        req = urllib.request.Request(url, data=body, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=220) as resp:
                raw = resp.read().decode("utf-8")
            data = json.loads(raw)
            text = data["candidates"][0]["content"]["parts"][0]["text"]
            return json.loads(clean_json_text(text))
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8", errors="ignore")
            print(f"Gemini HTTP error attempt {attempt}/{MAX_RETRIES}: {e.code} {error_body[:700]}")
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


def normalize_product_name(name: str, products: List[Dict[str, Any]]) -> str:
    if not products:
        return name.strip() or "Natural Dog Treats"
    names = [str(p.get("name", "")).strip() for p in products if p.get("name")]
    if not names:
        return name.strip() or "Natural Dog Treats"
    lowered = (name or "").strip().lower()
    for existing in names:
        if lowered == existing.lower():
            return existing
    for existing in names:
        if existing.lower() in lowered or lowered in existing.lower():
            return existing
    return names[0]


def fake_topics(count: int, products: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    seeds = [
        ("Are Bully Sticks Safe for Puppies? Safety Guide & Tips", "bully sticks for puppies", "Bully Sticks", "puppy chews"),
        ("Best Dog Chews for Bored Dogs: Natural Enrichment Ideas", "dog chews for boredom", "Cow Ears", "enrichment"),
        ("Can Dogs Eat Sweet Potatoes? Treat Safety & Benefits Guide", "can dogs eat sweet potatoes", "Sweet Potato Treats", "dog nutrition"),
        ("How Many Treats Can a Dog Have Per Day? Simple Portion Guide", "dog treats per day", "Training Treats", "dog treats"),
        ("Best Natural Dog Treats for Picky Eaters", "dog treats for picky eaters", "Beef Lung Bites", "dog treats"),
        ("Bully Sticks vs Rawhide: Which Chew Is Better for Dogs?", "bully sticks vs rawhide", "Bully Sticks", "rawhide alternatives"),
    ]
    topics: List[Dict[str, str]] = []
    for i in range(count):
        topic, keyword, product, category = seeds[i % len(seeds)]
        if i >= len(seeds):
            topic = f"{topic} #{i + 1}"
        topics.append({"topic": topic, "main_keyword": keyword, "product_focus": normalize_product_name(product, products), "category": category})
    return topics


def generate_topics_with_ai(count: int, products: List[Dict[str, Any]], history: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    product_names = [p.get("name", "") for p in products if p.get("name")]
    recent_titles = []
    for item in reversed(history[-120:]):
        title = item.get("blog_title") or item.get("topic") or item.get("title")
        if title:
            recent_titles.append(str(title))
    recent_titles = recent_titles[-80:]
    rules = load_json(TOPIC_RULES_JSON, DEFAULT_TOPIC_RULES)

    prompt = f"""
You are an SEO topic strategist for {BRAND_NAME}, a dog treats and chews brand.

Create {count} fresh blog topic ideas for daily SEO blog drafts.

Brand website: {BRAND_SITE}
Available product focus options: {json.dumps(product_names, ensure_ascii=False)}
Topic rules: {json.dumps(rules, ensure_ascii=False, indent=2)}
Avoid repeating or closely duplicating these recent topics: {json.dumps(recent_titles, ensure_ascii=False, indent=2)}

Return valid JSON only. No markdown. No explanation.

Schema:
[
  {{
    "topic": "",
    "main_keyword": "",
    "product_focus": "one exact product name from available product focus options",
    "category": ""
  }}
]

Topic rules:
- Make every topic unique and SEO-searchable.
- Use topics dog owners actually search for.
- Mix informational, comparison, safety, routine, puppy, senior, boredom, dental, and product-intent topics.
- Avoid medical diagnosis and cure claims.
- Do not create seasonal topics unless broadly evergreen.
- Make product_focus relevant to the topic.
- main_keyword should be a real search phrase, not a sentence.
- category should be short, like "dog chews", "puppy treats", "dog nutrition", "enrichment", "training".
""".strip()

    raw = call_gemini_json(prompt, max_output_tokens=5000, temperature=0.85)
    if isinstance(raw, dict):
        raw_topics = raw.get("topics") or raw.get("data") or []
    else:
        raw_topics = raw
    if not isinstance(raw_topics, list):
        raise ValueError("AI topic response was not a JSON array.")

    topics: List[Dict[str, str]] = []
    seen_slugs = set()
    for item in raw_topics:
        if not isinstance(item, dict):
            continue
        topic = str(item.get("topic", "")).strip()
        keyword = str(item.get("main_keyword", "")).strip()
        category = str(item.get("category", "dog treats")).strip()
        product_focus = normalize_product_name(str(item.get("product_focus", "")).strip(), products)
        if not topic or not keyword:
            continue
        key = slugify(topic, 100)
        if key in seen_slugs:
            continue
        seen_slugs.add(key)
        topics.append({"topic": topic, "main_keyword": keyword, "product_focus": product_focus, "category": category})
        if len(topics) >= count:
            break

    if len(topics) < count:
        for fallback in fake_topics(count - len(topics), products):
            fallback["topic"] = f"{fallback['topic']} Fresh Guide"
            topics.append(fallback)

    return topics[:count]


def pick_relevant_products(topic: Dict[str, str], products: List[Dict[str, Any]], limit: int = 4) -> List[Dict[str, Any]]:
    if not products:
        products = DEFAULT_PRODUCTS
    searchable = " ".join([topic.get("topic", ""), topic.get("main_keyword", ""), topic.get("product_focus", ""), topic.get("category", "")]).lower()
    scored = []
    for product in products:
        score = 0
        name = str(product.get("name", "")).lower()
        if name and name in searchable:
            score += 8
        if topic.get("product_focus", "").lower() == name:
            score += 14
        for phrase in product.get("best_for", []):
            if str(phrase).lower() in searchable:
                score += 3
        scored.append((score, product))
    scored.sort(key=lambda item: item[0], reverse=True)
    selected = [product for score, product in scored if score > 0][:limit]
    if len(selected) < limit:
        for _, product in scored:
            if product not in selected:
                selected.append(product)
            if len(selected) >= limit:
                break
    return selected[:limit]


def build_blog_prompt(topic: Dict[str, str], products: List[Dict[str, Any]]) -> str:
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
{json.dumps(products, ensure_ascii=False, indent=2)}

Use 1-2 internal links from this list:
{json.dumps(INTERNAL_LINKS, ensure_ascii=False, indent=2)}

Use 2-3 external trusted links from this list only:
{json.dumps(TRUSTED_EXTERNAL_LINKS, ensure_ascii=False, indent=2)}

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
- blog_title: natural, high-click SEO title. Keep it close to the topic.
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
- Use safe wording: “may help,” “can support,” “can be part of a routine,” and “ask your veterinarian.”
- Mention vet guidance for sudden symptoms, allergies, choking, digestion, weight loss, vomiting, diarrhea, increased thirst, or medical concerns.
- Do not say Brutus & Barnaby products cure or treat medical conditions.
- Do not keyword stuff.
- Do not make all blogs sound the same.
- Keep paragraphs short and mobile-friendly.
- Make the article genuinely useful, not thin content.
- Aim for roughly 1200-1800 words in the HTML.
""".strip()


def fake_blog(topic: Dict[str, str], products: List[Dict[str, Any]]) -> Dict[str, Any]:
    title = topic.get("topic", "Dog Blog Draft").strip()
    slug = slugify(title)
    product = products[0] if products else DEFAULT_PRODUCTS[0]
    product_card = f"""
      <div style=\"border:1px solid #f3d2c2;border-radius:14px;padding:1.4em;margin:2em 0;background:#fff8f3;display:flex;gap:1.4em;align-items:center;flex-wrap:wrap;\">
        <div style=\"flex:0 0 180px;max-width:260px;\"><img src=\"{html.escape(str(product.get('image','')))}\" alt=\"{html.escape(str(product.get('name','Dog treats')))}\" style=\"width:100%;border-radius:12px;display:block;\"></div>
        <div style=\"flex:1;min-width:240px;\"><div style=\"font-size:10px;font-weight:800;letter-spacing:1.6px;text-transform:uppercase;color:#f02400;margin-bottom:8px;\">Recommended Pick</div><h3 style=\"color:#1a1208;margin:0 0 .5em;font-size:18px;line-height:1.25;\">{html.escape(str(product.get('name','Natural Dog Treats')))}</h3><p style=\"margin-top:0;line-height:1.7;color:#3a2a1a;font-size:15px;\">A useful product match for this blog topic.</p><a href=\"{html.escape(str(product.get('url','#')))}\" style=\"display:inline-block;background:#f02400;color:#ffffff;font-weight:800;text-decoration:none;padding:.85em 1.25em;border-radius:999px;font-size:13px;\">{html.escape(str(product.get('cta','Shop Now')))}</a></div>
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
        "search_engine_listing": {"page_title": page_title, "meta_description": meta_description, "url_handle": url_handle},
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
    keywords = ", ".join(str(k) for k in blog.get("seo_keywords", []))
    keywords_escaped = html.escape(keywords)
    body = blog.get("html", "")
    raw_body = html.escape(body)

    template = r'''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="robots" content="noindex, nofollow">
  <title>__TITLE__</title>
  <meta name="description" content="__DESC__">
  <style>
    body { margin: 0; background: #fffaf6; color: #1a1208; }
    .agent-preview-bar { font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background:#fff; border-bottom:1px solid #ead7cc; padding:18px 24px; }
    .agent-preview-bar a { color:#f02400; font-weight:800; }
    .agent-meta { display:grid; grid-template-columns: repeat(auto-fit,minmax(220px,1fr)); gap:12px; margin-top:12px; }
    .agent-meta div { background:#fff8f3; border:1px solid #f3d2c2; border-radius:10px; padding:12px; font-size:13px; line-height:1.55; }
    .agent-copy { border:0; background:#f02400; color:#fff; font-weight:800; border-radius:999px; padding:10px 16px; cursor:pointer; }
    .agent-html-panel { margin-top:14px; background:#111; border-radius:12px; overflow:hidden; border:1px solid #2c2c2c; }
    .agent-html-head { display:flex; justify-content:space-between; gap:10px; align-items:center; padding:12px 14px; color:#fff; font-family:system-ui,-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif; border-bottom:1px solid #333; flex-wrap:wrap; }
    .agent-html-head strong { color:#fff; }
    #rawHtmlCode { width:100%; min-height:280px; border:0; outline:none; resize:vertical; padding:16px; background:#111; color:#fff; font-family:ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,monospace; font-size:13px; line-height:1.5; }
    @media (max-width: 640px) {
      .agent-preview-bar { padding:14px; }
      div[style*="padding:48px 44px"] { padding:34px 22px !important; }
      div[style*="padding:28px 44px"] { padding:24px 22px !important; }
      div[style*="padding:36px 44px"] { padding:30px 22px !important; }
      div[style*="padding:22px 44px"] { padding:20px 22px !important; }
    }
  </style>
</head>
<body>
  <div class="agent-preview-bar">
    <div style="display:flex;justify-content:space-between;gap:12px;align-items:center;flex-wrap:wrap;">
      <div>
        <strong>Draft Preview:</strong> __BLOG_TITLE__<br>
        <span style="color:#6b5d52;font-size:13px;">Generated: __GENERATED_DATE__</span>
      </div>
      <div><a href="../index.html">← Back to all drafts</a></div>
    </div>
    <div class="agent-meta">
      <div><strong>Blog Title</strong><br>__BLOG_TITLE__</div>
      <div><strong>Excerpt</strong><br>__EXCERPT__</div>
      <div><strong>Page Title</strong><br>__TITLE__</div>
      <div><strong>Meta Description</strong><br>__DESC__</div>
      <div><strong>URL Handle</strong><br>__HANDLE__</div>
      <div><strong>SEO Keywords</strong><br>__KEYWORDS__</div>
    </div>
    <div class="agent-html-panel" id="html-copy">
      <div class="agent-html-head">
        <strong>Full Blog HTML</strong>
        <button class="agent-copy" type="button" onclick="selectRawHtml()">Select All</button>
        <button class="agent-copy" type="button" onclick="copyRawHtml()">Copy HTML</button>
      </div>
      <textarea id="rawHtmlCode" spellcheck="false">__RAW_BODY__</textarea>
    </div>
  </div>

__BODY__
<script>
  function selectRawHtml() {
    const el = document.getElementById('rawHtmlCode');
    el.focus();
    el.select();
  }
  async function copyRawHtml() {
    const el = document.getElementById('rawHtmlCode');
    selectRawHtml();
    try {
      if (navigator.clipboard && window.isSecureContext) {
        await navigator.clipboard.writeText(el.value);
      } else {
        document.execCommand('copy');
      }
      alert('Blog HTML copied.');
    } catch (error) {
      alert('Copy failed. Select the HTML box manually and press Ctrl+C. Error: ' + error.message);
    }
  }
</script>
</body>
</html>
'''
    return (
        template.replace("__TITLE__", title)
        .replace("__DESC__", desc)
        .replace("__BLOG_TITLE__", blog_title)
        .replace("__EXCERPT__", excerpt)
        .replace("__HANDLE__", handle)
        .replace("__KEYWORDS__", keywords_escaped)
        .replace("__RAW_BODY__", raw_body)
        .replace("__BODY__", body)
        .replace("__GENERATED_DATE__", html.escape(generated_date))
    )


def clear_previous_drafts() -> None:
    save_json(GENERATED_JSON, [])
    if BLOGS_DIR.exists():
        for path in BLOGS_DIR.glob("*.html"):
            try:
                path.unlink()
                print(f"Deleted old draft: {path}")
            except OSError as exc:
                print(f"Could not delete old draft {path}: {exc}", file=sys.stderr)


def main() -> int:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    BLOGS_DIR.mkdir(parents=True, exist_ok=True)

    products = load_json(PRODUCTS_JSON, DEFAULT_PRODUCTS)
    if not isinstance(products, list) or not products:
        products = DEFAULT_PRODUCTS

    history = load_json(TOPIC_HISTORY_JSON, [])
    if not isinstance(history, list):
        history = []

    existing_generated = load_json(GENERATED_JSON, [])
    if not isinstance(existing_generated, list):
        existing_generated = []

    # IMPORTANT:
    # Do not delete old dashboard drafts before Gemini succeeds.
    # Gemini can return 503 / high-demand errors, and we do not want those errors
    # to wipe the currently visible website drafts.
    if CLEAR_PREVIOUS:
        print("CLEAR_PREVIOUS=true. Old drafts will be kept until at least one new draft is generated successfully.")
        generated: List[Dict[str, Any]] = []
        output_dir = ROOT / "_new_blog_batch_tmp"
        if output_dir.exists():
            shutil.rmtree(output_dir, ignore_errors=True)
        output_dir.mkdir(parents=True, exist_ok=True)
    else:
        generated = existing_generated
        output_dir = BLOGS_DIR

    today = dt.date.today().isoformat()

    print(f"Creating {BLOGS_PER_DAY} fresh topic(s) with AI. DRY_RUN={DRY_RUN}")
    try:
        if DRY_RUN:
            topics = fake_topics(BLOGS_PER_DAY, products)
        else:
            topics = generate_topics_with_ai(BLOGS_PER_DAY, products, history)
    except Exception as exc:
        print(f"Topic generation failed: {exc}", file=sys.stderr)
        print("No old drafts were deleted. Website will keep the previous successful batch.")
        if CLEAR_PREVIOUS:
            shutil.rmtree(output_dir, ignore_errors=True)
        return 0

    print("Topics selected for this run:")
    for i, topic in enumerate(topics, 1):
        print(f"  {i}. {topic.get('topic')} | {topic.get('main_keyword')} | {topic.get('product_focus')}")

    generated_count = 0
    for index, topic in enumerate(topics, start=1):
        print(f"\n[{index}/{len(topics)}] Writing blog: {topic.get('topic')}")
        relevant_products = pick_relevant_products(topic, products, limit=4)
        try:
            if DRY_RUN:
                raw_blog = fake_blog(topic, relevant_products)
            else:
                raw_blog = call_gemini_json(build_blog_prompt(topic, relevant_products), max_output_tokens=16000, temperature=0.78)

            blog = validate_blog(raw_blog, topic)
            handle = blog["search_engine_listing"]["url_handle"]
            filename = f"{today}-{handle}.html"
            blog_path = output_dir / filename
            suffix = 2
            while blog_path.exists():
                filename = f"{today}-{handle}-{suffix}.html"
                blog_path = output_dir / filename
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
            history.append(
                {
                    "date": today,
                    "topic": topic.get("topic", ""),
                    "main_keyword": topic.get("main_keyword", ""),
                    "product_focus": topic.get("product_focus", ""),
                    "category": topic.get("category", ""),
                    "blog_title": blog["blog_title"],
                    "url_handle": blog["search_engine_listing"]["url_handle"],
                }
            )
            generated_count += 1
            print(f"Saved new draft temporarily: {blog_path}")

            if not DRY_RUN and index < len(topics):
                time.sleep(SLEEP_SECONDS)
        except Exception as e:
            print(f"Failed blog '{topic.get('topic')}': {e}", file=sys.stderr)

    if generated_count > 0:
        if CLEAR_PREVIOUS:
            print("New batch generated successfully. Now clearing old dashboard drafts and publishing the new batch.")
            clear_previous_drafts()
            for path in sorted(output_dir.glob("*.html")):
                target = BLOGS_DIR / path.name
                shutil.move(str(path), str(target))
                print(f"Published new draft: {target}")
            shutil.rmtree(output_dir, ignore_errors=True)
        save_json(GENERATED_JSON, generated)
        save_json(TOPIC_HISTORY_JSON, history[-500:])
        print(f"\nDone. Generated {generated_count} blog(s). Topics are now AI-generated directly, no topics.csv needed.")
        return 0

    print("\nNo new blogs were generated. Old dashboard drafts were kept unchanged.")
    if CLEAR_PREVIOUS:
        shutil.rmtree(output_dir, ignore_errors=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
