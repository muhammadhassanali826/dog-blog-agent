/**
 * Cloudflare Worker: safely trigger GitHub Actions from your GitHub Pages dashboard.
 *
 * Required Worker secrets/variables:
 * - GITHUB_TOKEN: fine-grained GitHub token with Actions: Read/Write + Contents: Read/Write for this repo
 * - GITHUB_OWNER: muhammadhassanali826
 * - GITHUB_REPO: dog-blog-agent
 * - WORKFLOW_FILE: daily-blog-generator.yml
 * - GITHUB_BRANCH: main
 * Optional:
 * - AGENT_PIN: any private PIN you want the dashboard to require
 */

const CORS_HEADERS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'POST, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type, x-agent-pin',
};

function jsonResponse(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: {
      ...CORS_HEADERS,
      'Content-Type': 'application/json',
    },
  });
}

export default {
  async fetch(request, env) {
    if (request.method === 'OPTIONS') {
      return new Response(null, { status: 204, headers: CORS_HEADERS });
    }

    if (request.method !== 'POST') {
      return jsonResponse({ error: 'Use POST only.' }, 405);
    }

    if (env.AGENT_PIN) {
      const submittedPin = request.headers.get('x-agent-pin') || '';
      if (submittedPin !== env.AGENT_PIN) {
        return jsonResponse({ error: 'Invalid PIN.' }, 401);
      }
    }

    let body;
    try {
      body = await request.json();
    } catch (_) {
      return jsonResponse({ error: 'Invalid JSON body.' }, 400);
    }

    const blogsPerDay = String(Math.min(Math.max(parseInt(body.blogs_per_day || '20', 10), 1), 20));
    const dryRun = String(body.dry_run) === 'true' ? 'true' : 'false';

    const owner = env.GITHUB_OWNER;
    const repo = env.GITHUB_REPO;
    const workflowFile = env.WORKFLOW_FILE || 'daily-blog-generator.yml';
    const branch = env.GITHUB_BRANCH || 'main';
    const token = env.GITHUB_TOKEN;

    if (!owner || !repo || !token) {
      return jsonResponse({ error: 'Worker is missing GITHUB_OWNER, GITHUB_REPO, or GITHUB_TOKEN.' }, 500);
    }

    const url = `https://api.github.com/repos/${owner}/${repo}/actions/workflows/${workflowFile}/dispatches`;

    const githubResponse = await fetch(url, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Accept': 'application/vnd.github+json',
        'X-GitHub-Api-Version': '2022-11-28',
        'User-Agent': 'dog-blog-agent-dashboard',
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        ref: branch,
        inputs: {
          blogs_per_day: blogsPerDay,
          dry_run: dryRun,
        },
      }),
    });

    if (!githubResponse.ok) {
      const errorText = await githubResponse.text();
      return jsonResponse({ error: 'GitHub workflow dispatch failed.', details: errorText }, githubResponse.status);
    }

    return jsonResponse({
      ok: true,
      message: 'Workflow started.',
      blogs_per_day: blogsPerDay,
      dry_run: dryRun,
    });
  },
};
