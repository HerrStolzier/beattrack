# Beattrack

Sonically similar song finder — findet Songs die ähnlich klingen.

## Stack
- **Frontend**: Next.js 15 + TypeScript + TailwindCSS → Vercel
- **Backend**: Python FastAPI + Essentia → Railway (Dockerfile)
- **Database**: Supabase PostgreSQL + pgvector (eu-central-1)
- **Job Queue**: Procrastinate (Postgres-based, kein Redis)

## Monorepo-Struktur
- `apps/web/` — Next.js Frontend
- `apps/api/` — FastAPI Backend
- `supabase/migrations/` — SQL Migrations

## Deployment
- Railway: Root Directory `/apps/api`, Config `/apps/api/railway.toml`
- Vercel: Auto-deploy von `main`, `NEXT_PUBLIC_API_URL` zeigt auf Railway
- Supabase: Migrations via MCP oder `supabase db push`
- Deploy-Status prüfen: `/deploy-check` (Config in `.claude/deploy.json`)

## Entwicklung
- `cd apps/api && uvicorn app.main:app --reload` — Backend lokal
- `cd apps/web && npm run dev` — Frontend lokal
- Backend-Tests: `cd apps/api && pytest`
- Frontend-Tests: `cd apps/web && npm test`

## Konventionen
- Essentia läuft in isoliertem Subprocess (Crash-Schutz)
- Dual Embeddings: MusiCNN 200d (learned) + 44d handcrafted
- Normalisierung via Z-Score aus `config`-Tabelle
- URL-Identify: YouTube oEmbed, SoundCloud oEmbed, Spotify Web API
- Commit-Messages auf Englisch, UI-Texte auf Deutsch
