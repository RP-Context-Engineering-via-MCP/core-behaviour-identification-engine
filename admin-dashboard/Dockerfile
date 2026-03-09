# ─────────────────────────────────────────────────────────────────────────────
# Stage 1: Builder — install dependencies and build Next.js app
# ─────────────────────────────────────────────────────────────────────────────
FROM node:20-alpine AS builder

WORKDIR /app

# Copy package files and install
COPY package*.json ./
RUN npm ci

# Copy source and build
COPY . .

# The CBIE API base URL is baked in at build time via NEXT_PUBLIC_ env vars.
# Pass --build-arg NEXT_PUBLIC_API_URL=http://cbie-engine:6009 when building.
ARG NEXT_PUBLIC_API_URL=http://localhost:6009
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL

RUN npm run build

# ─────────────────────────────────────────────────────────────────────────────
# Stage 2: Runtime — serve the built Next.js app
# ─────────────────────────────────────────────────────────────────────────────
FROM node:20-alpine AS runtime

WORKDIR /app

ENV NODE_ENV=production

# Copy only what's needed to run the app
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/package.json ./

RUN npm install --omit=dev --ignore-scripts

EXPOSE 3000

CMD ["node", "server.js"]
