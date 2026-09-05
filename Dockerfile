FROM node:20-bookworm-slim AS web-builder

WORKDIR /build/web
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY web/ ./
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build

FROM node:20-bookworm-slim AS runtime

RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 python3-venv ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt ./
RUN python3 -m venv /opt/crossprofit-venv \
    && /opt/crossprofit-venv/bin/pip install --no-cache-dir -r requirements.txt

COPY . ./
COPY --from=web-builder /build/web/.next ./web/.next
COPY --from=web-builder /build/web/node_modules ./web/node_modules

RUN mkdir -p /data

ENV PATH="/opt/crossprofit-venv/bin:${PATH}" \
    PYTHONUNBUFFERED=1 \
    NEXT_TELEMETRY_DISABLED=1 \
    CROSSPROFIT_HOST=0.0.0.0 \
    CROSSPROFIT_WEB_MODE=production \
    CROSSPROFIT_INTERNAL_API_URL=http://127.0.0.1:8000 \
    CROSSPROFIT_DB_URL=sqlite:////data/crossprofit.db

EXPOSE 3000
VOLUME ["/data"]

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python3 -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:' + __import__('os').getenv('PORT', '3000') + '/api/health', timeout=4)" || exit 1

CMD ["python3", "run.py"]
