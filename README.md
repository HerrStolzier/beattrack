# beattrack

[![CI](https://github.com/HerrStolzier/beattrack/actions/workflows/ci.yml/badge.svg)](https://github.com/HerrStolzier/beattrack/actions/workflows/ci.yml)
[![License: AGPL-3.0](https://img.shields.io/badge/License-AGPL--3.0-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![TypeScript](https://img.shields.io/badge/TypeScript-5-blue.svg)](https://www.typescriptlang.org/)

Find songs that sound alike — sonic similarity search powered by audio fingerprinting and vector embeddings.

## Stack

- **Frontend:** Next.js 15, React 19, TypeScript, Tailwind CSS
- **Backend:** FastAPI, Python 3.12, Essentia, Chromaprint/pyacoustid
- **Monorepo:** Bun workspaces

## Development

```bash
bun install
bun run dev        # Frontend (apps/web)
```

```bash
cd apps/api
uv sync --extra dev
uv run uvicorn app.main:app --reload
```

## Testing

```bash
bun run test       # Frontend unit tests
uv run pytest      # Backend tests
```

## License

AGPL-3.0 — see [LICENSE](./LICENSE)
