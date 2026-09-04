# Render + Netlify deployment guide

**Status: this is the live reference deployment** (zero-cost demo).

| Service | URL |
|---|---|
| Frontend | https://cloudmlops.netlify.app |
| Backend API | https://cloudmlops.onrender.com |
| Health | https://cloudmlops.onrender.com/health |
| API docs | https://cloudmlops.onrender.com/docs |

This path is **separate from AWS**. It is documented here so teammates and reviewers know
what is actually running. For AWS (the target production path), see
[`deployment-aws.md`](deployment-aws.md). For an honest comparison of both, see
[`deployment-status.md`](deployment-status.md).

---

## Architecture

```
User browser
    │
    ▼
Netlify (static React build)
    │  HTTPS  VITE_API_BASE_URL
    ▼
Render Web Service (Docker — backend/Dockerfile)
    │  postgresql+psycopg://  (internal)
    ▼
Render PostgreSQL
```

---

## Render — backend Web Service

### Service settings

| Setting | Value |
|---|---|
| **Type** | Web Service |
| **Runtime** | Docker |
| **Root directory** | `backend` (or repo root with context `./backend`) |
| **Dockerfile** | `backend/Dockerfile` |
| **Port** | `8000` (uvicorn reads `PORT`; Render injects it) |
| **Health check** | `/health` |

### Recommended Docker build arguments (free tier)

| Build arg | Value | Why |
|---|---|---|
| `INSTALL_AI` | `false` | Skips torch (~200 MB+); free tier RAM cannot run FLAN-T5 reliably |
| `PREFETCH_MODEL` | `false` | No model to prefetch when AI deps are skipped |

> **AI note:** With `INSTALL_AI=false`, `AI_BACKEND=auto` resolves to **extractive**.
> FLAN-T5 is still implemented in the repo and runs locally via `docker compose` or on AWS
> when `INSTALL_AI=true`. The live `/health` endpoint reports which backend is active.

### Required environment variables

| Variable | Example / rule |
|---|---|
| `DATABASE_URL` | `postgresql+psycopg://USER:PASS@dpg-xxxxx-a/DATABASE` — **must** use `+psycopg`, not plain `postgresql://` |
| `JWT_SECRET_KEY` | Random string, **32+ characters** |
| `ADMIN_PASSWORD` | Strong password — **cannot** be `Admin123!` |
| `ENVIRONMENT` | `production` (set in Dockerfile by default) |
| `AI_BACKEND` | `extractive` (recommended on free tier) |
| `RUN_MIGRATIONS` | `true` |
| `AUTO_CREATE_SCHEMA` | `false` |
| `SEED_ADMIN` | `true` |
| `CORS_ORIGINS` | `https://cloudmlops.netlify.app` (add custom domain if used) |

**Internal vs external database URL**

Render provides both. Prefer the **Internal Database URL** for backend → Postgres on Render:

```
postgresql+psycopg://auto:PASSWORD@dpg-xxxxx-a/cloudmlops
```

External (for `psql` from your laptop):

```
postgresql+psycopg://auto:PASSWORD@dpg-xxxxx-a.oregon-postgres.render.com:5432/cloudmlops
```

---

## Netlify — frontend

### Build settings

| Setting | Value |
|---|---|
| **Base directory** | `frontend` |
| **Build command** | `npm run build` |
| **Publish directory** | `frontend/dist` |
| **Node version** | 22 |

### Required environment variable

| Variable | Value |
|---|---|
| `VITE_API_BASE_URL` | `https://cloudmlops.onrender.com` |

Rules:

- **No** trailing slash
- **No** `/health` suffix
- Must **redeploy** (clear cache) after changing — Vite bakes this in at build time

### SPA routing (optional)

If direct URLs like `/dashboard` return 404 on refresh, add `frontend/public/_redirects`:

```
/*    /index.html   200
```

---

## Team issues log (resolved)

These were encountered during the initial team deployment.

### 1. `Could not parse SQLAlchemy URL`

| | |
|---|---|
| **Error** | `sqlalchemy.exc.ArgumentError: Could not parse SQLAlchemy URL` during `alembic upgrade head` |
| **Cause** | Render’s copied URL uses `postgresql://`; this project requires `postgresql+psycopg://` |
| **Fix** | Edit `DATABASE_URL` on Render |

### 2. Container exits after migrations (`status 3`)

| | |
|---|---|
| **Error** | `ADMIN_PASSWORD is still the built-in default` |
| **Cause** | Production guard in `app/main.py` refuses insecure defaults |
| **Fix** | Set `ADMIN_PASSWORD` and `JWT_SECRET_KEY` (32+ chars) on Render |

### 3. Frontend: “Cannot reach the API”

| | |
|---|---|
| **Cause** | `VITE_API_BASE_URL` unset → browser calls Netlify’s own `/api/...` |
| **Fix** | Set env var to Render backend URL, **clear cache and redeploy** |

### 4. CORS blocks login

| | |
|---|---|
| **Console** | `No 'Access-Control-Allow-Origin' header` from `cloudmlops.netlify.app` |
| **Fix** | `CORS_ORIGINS=https://cloudmlops.netlify.app` on Render (exact origin, no trailing slash) |

### 5. “No open ports detected” on Render

| | |
|---|---|
| **Cause** | App crashed before uvicorn bound to `PORT` (usually issues 1–2 above) |
| **Fix** | Fix startup errors; not a separate port configuration bug |

---

## Verification checklist

- [ ] `GET https://cloudmlops.onrender.com/health` → `"status":"ok"`, `"database":"connected"`
- [ ] `/health` shows `"ai_backend":"extractive"` on free-tier Render (expected)
- [ ] Netlify login Network tab calls `cloudmlops.onrender.com/api/auth/login`
- [ ] No CORS errors in browser console
- [ ] Login: `admin@cloudmlops.app` + your `ADMIN_PASSWORD`

---

## Local vs Render differences

| Setting | Local (`docker compose`) | Render (live demo) |
|---|---|---|
| `VITE_API_BASE_URL` | Empty (nginx proxy) | Full Render API URL |
| `CORS_ORIGINS` | `localhost:5173` | Netlify URL |
| `INSTALL_AI` | `true` (default) | `false` (free tier) |
| `AI_BACKEND` live | Often `flan-t5` | `extractive` |
| `ADMIN_PASSWORD` | `Admin123!` allowed in dev | Must change |

---

## Security reminders

1. Rotate the database password if it was ever shared in chat or screenshots.
2. Never commit `.env` with production secrets.
3. Render free tier **spins down** after inactivity — first request may take 30–60 seconds.

---

## When to use this vs AWS

| Goal | Use |
|---|---|
| Free public URL for demo / portfolio | **Render + Netlify** (this guide) |
| Course requirement “initial AWS deployment” | **AWS** — [`deployment-aws.md`](deployment-aws.md) |
| FLAN-T5 on a public URL | **AWS App Runner** (2 vCPU / 4 GB) or local Docker — not Render free tier |
| Honest submission narrative | [`deployment-status.md`](deployment-status.md) |
