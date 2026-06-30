# Dog Blog Agent UI Upgrade

This upgrade adds:

1. A Generate Blogs form on the GitHub Pages dashboard.
2. Inputs for how many blogs to generate, 1-20.
3. A mode selector: Use AI / Gemini or Test only / no AI.
4. A View HTML button on each blog card.
5. A Copy HTML button on the dashboard and on each draft page.
6. Optional direct generation from the webpage using a free Cloudflare Worker.

## Upload these files to GitHub

Upload/replace these files in your repo:

```text
scripts/build_index.py
scripts/generate_blogs.py
.github/workflows/daily-blog-generator.yml
```

Keep this file for the optional direct website trigger:

```text
workers/cloudflare-worker.js
```

## Fast version: button opens GitHub Actions

After uploading the Python files and workflow:

1. Go to Actions → Daily Dog Blog Generator → Run workflow.
2. Run with `blogs_per_day = 2`, `dry_run = true` for test.
3. Then run with `blogs_per_day = 20`, `dry_run = false`.
4. Open your website.

The dashboard will show a Generate Blogs form. If the Cloudflare Worker is not connected yet, the button will open GitHub Actions for you.

## Full version: direct Generate button from website

To make the website button actually start the GitHub workflow, use the Cloudflare Worker.

### 1. Create GitHub fine-grained token

Create a fine-grained personal access token for this repo.

Give it access to this repository only:

```text
muhammadhassanali826/dog-blog-agent
```

Permissions needed:

```text
Actions: Read and write
Contents: Read and write
Metadata: Read-only
```

### 2. Create Cloudflare Worker

1. Go to Cloudflare Dashboard.
2. Workers & Pages → Create → Worker.
3. Paste the code from:

```text
workers/cloudflare-worker.js
```

4. Deploy it.

### 3. Add Worker variables/secrets

In the Worker settings, add:

```text
GITHUB_TOKEN = your GitHub fine-grained token  (secret)
GITHUB_OWNER = muhammadhassanali826
GITHUB_REPO = dog-blog-agent
WORKFLOW_FILE = daily-blog-generator.yml
GITHUB_BRANCH = main
AGENT_PIN = choose-a-private-pin  (optional but recommended)
```

### 4. Add Worker URL to GitHub repo variable

Copy the Worker URL, for example:

```text
https://dog-blog-trigger.yourname.workers.dev
```

Then in GitHub repo:

```text
Settings → Secrets and variables → Actions → Variables → New repository variable
```

Add:

```text
Name: TRIGGER_WORKER_URL
Value: your Cloudflare Worker URL
```

### 5. Run workflow once

Run the workflow one more time so `index.html` is rebuilt with the Worker URL.

Then the website Generate Blogs button will trigger the workflow directly.

## How to see the HTML

On the website:

1. Each blog card has `View HTML`.
2. Click it to open the full HTML modal.
3. Click `Copy HTML`.

On the blog preview page:

1. Open a blog draft.
2. The top section now includes `Full Blog HTML`.
3. Click `Copy HTML`.

## Notes

- GitHub Pages is static, so it cannot safely store API keys or GitHub tokens inside the website.
- The Cloudflare Worker keeps the GitHub token private and triggers the workflow for the website.
- The website still does not publish to Shopify. It only generates and shows drafts.
