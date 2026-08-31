# =============================================================================
# CloudMLOps presentation tier
# Multi-stage: Node builds the static bundle, nginx serves it.
#
# Point the bundle at a different API host at build time:
#   docker build --build-arg VITE_API_BASE_URL=https://api.example.com ./frontend
# Leaving it empty keeps requests same-origin and lets nginx proxy them.
# =============================================================================
FROM node:22-alpine AS build

WORKDIR /app

COPY package*.json ./
RUN npm ci || npm install

COPY . .

ARG VITE_API_BASE_URL=""
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
RUN npm run build

# -----------------------------------------------------------------------------
FROM nginx:1.27-alpine AS runtime

RUN apk add --no-cache curl

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=4s --start-period=10s --retries=3 \
    CMD curl -fsS http://localhost/ >/dev/null || exit 1

CMD ["nginx", "-g", "daemon off;"]
