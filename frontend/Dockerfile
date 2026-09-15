FROM node:22.12.0-slim AS dependencies

WORKDIR /app

COPY package.json package-lock.json .npmrc* ./
RUN npm ci

FROM node:22.12.0-slim AS builder

WORKDIR /app

COPY --from=dependencies /app/node_modules ./node_modules
COPY . .

ARG NEXT_PUBLIC_API_BASE_URL
ENV NEXT_PUBLIC_API_BASE_URL=$NEXT_PUBLIC_API_BASE_URL
RUN npm run build

FROM node:22.12.0-slim AS runtime

WORKDIR /app

ENV NODE_ENV=production
ENV HOSTNAME=0.0.0.0
ENV PORT=3000

RUN groupadd --system nodejs \
    && useradd --system --gid nodejs nextjs

COPY package.json package-lock.json .npmrc* ./
RUN npm ci --omit=dev && npm cache clean --force

COPY --from=builder --chown=nextjs:nodejs /app/.next ./.next
COPY --from=builder --chown=nextjs:nodejs /app/next.config.mjs ./next.config.mjs

USER nextjs

CMD ["npm", "start"]
