# Zweistufiger Build fuer den Betrieb auf infra-01.

FROM oven/bun:1 AS builder
WORKDIR /app

# Monorepo: Das Lockfile deckt alle Workspace-Pakete ab. Nur zwei package.json
# vorab zu kopieren laesst bun das Lockfile veraendern und --frozen-lockfile
# scheitern. Deshalb erst alles kopieren, dann installieren.
COPY . .
RUN bun install --frozen-lockfile

ARG NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL

WORKDIR /app/apps/web
RUN bun run build

FROM node:26-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
ENV PORT=3000
ENV HOSTNAME=0.0.0.0

RUN addgroup -g 1001 -S nodejs && adduser -S nextjs -u 1001

# Das Laufzeit-Image startet nur `node server.js`. npm, npx, corepack und yarn
# werden nie aufgerufen, schleppen aber ihre eigenen Abhaengigkeiten mit — zuletzt
# CVE-2026-59873 (node-tar). Was nicht im Image liegt, muss nicht gepatcht werden.
RUN rm -rf /usr/local/lib/node_modules/npm /usr/local/lib/node_modules/corepack \
           /usr/local/bin/npm /usr/local/bin/npx /usr/local/bin/corepack \
           /opt/yarn-v* /usr/local/bin/yarn /usr/local/bin/yarnpkg

# standalone kopiert public/ und .next/static NICHT mit.
# public/ ist derzeit leer, existiert aber (per .gitkeep) — sonst bricht der COPY ab.
COPY --from=builder /app/apps/web/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/apps/web/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/apps/web/.next/static ./apps/web/.next/static

USER nextjs
EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s \
  CMD node -e "fetch('http://127.0.0.1:3000/').then(r=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))"

CMD ["node", "apps/web/server.js"]
