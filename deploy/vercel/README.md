# Vercel: Pixeltable Starter Kit (Frontend Only)

Deploy the React frontend on [Vercel](https://vercel.com) with the Pixeltable backend running on a separate platform (Fly.io, Render, Railway, K8s, etc.).

Vercel is serverless-only: it doesn't support long-running Docker containers or persistent storage, which Pixeltable's embedded Postgres requires. This config deploys **just the frontend** and proxies `/api` requests to your backend.

## Architecture

```
Users → Vercel (frontend, edge CDN)
           │
           └─ /api/* rewrites → Backend (Fly / Render / Railway / K8s)
                                   │
                                   └─ Pixeltable (embedded Postgres, embeddings, agent)
```

## Prerequisites

- [Vercel account](https://vercel.com/signup)
- Backend deployed elsewhere (see [`deploy/fly/`](../fly/), [`deploy/render/`](../render/), [`deploy/railway/`](../railway/), etc.)

## Quick Start

```bash
# Copy vercel.json to the frontend directory
cp deploy/vercel/vercel.json frontend/

# Deploy via Vercel CLI
cd frontend
npx vercel --yes

# Or: push to GitHub → import in Vercel dashboard
# Set root directory to "frontend" in project settings
```

### Set environment variable

In the Vercel dashboard → your project → **Settings** → **Environment Variables**:

```
BACKEND_URL=https://your-backend.fly.dev    # or .onrender.com, .up.railway.app, etc.
```

This tells Vercel where to proxy `/api/*` requests. The `vercel.json` rewrites use this variable.

## Configuration

The `vercel.json` is minimal:
- **Framework:** Vite (auto-detected)
- **Build:** `npm run build` → outputs to `dist`
- **Rewrites:** `/api/*` → `${BACKEND_URL}/api/*`

Note the `outputDirectory` is set to `dist` (Vite's default), not `../backend/static` (which is for monolith mode). Vercel serves from `dist` directly.

### CORS

Your backend needs to allow requests from your Vercel domain. Add the Vercel URL to `CORS_ORIGINS` on your backend:

```bash
# On your backend platform (Fly/Render/Railway):
CORS_ORIGINS=https://your-app.vercel.app
```

The backend's `config.py` already reads `CORS_ORIGINS` from the environment.

## When to Use This

| Deployment | Use when |
|---|---|
| **Monolith** (Docker Compose, Fly, Render, Railway, K8s) | Simple: one container serves everything |
| **Split** (Vercel frontend + separate backend) | You want Vercel's edge CDN, preview URLs, or your team already uses Vercel |

For most cases, deploying the monolith to a single platform is simpler. Use the split pattern when Vercel's DX features matter to your team.

## See Also

- [`deploy/fly/`](../fly/): Backend on Fly.io
- [`deploy/render/`](../render/): Backend on Render
- [`deploy/railway/`](../railway/): Backend on Railway
