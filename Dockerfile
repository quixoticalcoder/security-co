FROM node:22-bookworm-slim AS dashboard
WORKDIR /build
RUN npm install -g pnpm@11.19.0
COPY dashboard/package.json dashboard/pnpm-lock.yaml dashboard/pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile
COPY dashboard/ ./
ENV NEXT_TELEMETRY_DISABLED=1 HOSTED_LITE=true
RUN pnpm build

FROM python:3.11-slim-bookworm
COPY --from=dashboard /usr/local/bin/node /usr/local/bin/node
WORKDIR /app
COPY backend/requirements-hosted.txt ./
RUN pip install --no-cache-dir -r requirements-hosted.txt
COPY backend/ ./backend/
COPY --from=dashboard /build/.next/standalone ./dashboard/
COPY --from=dashboard /build/.next/static ./dashboard/.next/static/
COPY --from=dashboard /build/public ./dashboard/public/
COPY deploy/start.py ./deploy/start.py
RUN useradd --create-home app && chown -R app:app /app
USER app
ENV HOSTED_LITE=true DEBUG=false NEXT_TELEMETRY_DISABLED=1 HOSTNAME=0.0.0.0 PORT=10000
CMD ["python", "deploy/start.py"]
