# Dog Blog AI Agent — GitHub Only

This repo generates **20 dog blog drafts per day** using GitHub Actions + Gemini API.

It does **not** publish to Shopify.
It only creates draft HTML files and a free GitHub Pages preview site.

## What it generates for each blog

- Blog Title
- Excerpt
- Search Engine Listing
  - Page Title
  - Meta Description
  - URL Handle
- SEO Keywords
- Full HTML blog in the Brutus & Barnaby style

## Folder structure

```text
data/
  topics.csv
  products.json
  generated_blogs.json
blogs/
  generated HTML blog files
scripts/
  generate_blogs.py
  build_index.py
.github/workflows/
  daily-blog-generator.yml
index.html
```

## Setup steps

### 1. Create a GitHub repo

Create a new GitHub repository, for example:

```text
dog-blog-agent
```

Make it public if you want free GitHub Pages preview hosting.

### 2. Upload these files

Upload all folders and files from this starter repo into your GitHub repository.

### 3. Get a Gemini API key

Go to Google AI Studio and create a Gemini API key.

### 4. Add the API key to GitHub Secrets

In your GitHub repo:

```text
Settings → Secrets and variables → Actions → New repository secret
```

Add:

```text
Name: GEMINI_API_KEY
Value: your Gemini API key
```

### 5. Enable GitHub Actions permissions

In your GitHub repo:

```text
Settings → Actions → General → Workflow permissions
```

Choose:

```text
Read and write permissions
```

Save.

### 6. Enable GitHub Pages

In your GitHub repo:

```text
Settings → Pages
```

Set:

```text
Source: Deploy from a branch
Branch: main
Folder: /root
```

Save.

### 7. Run the bot manually first

Go to:

```text
Actions → Daily Dog Blog Generator → Run workflow
```

The workflow will generate blogs and commit them back to your repo.

### 8. Daily schedule

By default, the workflow runs daily at around **9:00 AM Pakistan time**.

GitHub cron uses UTC. Pakistan is UTC+5, so this repo uses:

```yaml
cron: "0 4 * * *"
```

## Change how many blogs it creates

Open:

```text
.github/workflows/daily-blog-generator.yml
```

Change:

```yaml
BLOGS_PER_DAY: "20"
```

## Add more blog topics

Open:

```text
data/topics.csv
```

Add rows with status:

```text
pending
```

The bot only generates blogs from pending rows.

## Add or edit products

Open:

```text
data/products.json
```

Add product names, URLs, images, and best-for keywords.

## Important SEO note

This bot generates drafts. Review content before publishing anywhere. For dog health/safety content, avoid medical claims and keep vet disclaimers.
