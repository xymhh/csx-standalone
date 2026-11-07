# ---- 前端构建 ----
FROM node:22-alpine AS web
WORKDIR /web
COPY web/package.json web/package-lock.json ./
RUN npm ci --include=dev
COPY web/ ./
RUN npm run build

# ---- 运行时 ----
FROM python:3.12-slim AS runtime
ENV PYTHONUNBUFFERED=1     PYTHONDONTWRITEBYTECODE=1     CSX_DATA_DIR=/data     CSX_WEB_DIST=/app/web/dist
WORKDIR /app
COPY backend/ ./
RUN pip install --no-cache-dir .
COPY --from=web /web/dist ./web/dist
VOLUME ["/data"]
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s   CMD python -c "import urllib.request;urllib.request.urlopen('http://127.0.0.1:8000/health')"
CMD ["uvicorn", "csx.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
