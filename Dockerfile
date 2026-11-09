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

# 反盾浏览器：构建期下载二进制（免 key 的稳定版），运行期才能直接拉起
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 libatspi2.0-0 \
        libcups2 libdrm2 libdbus-1-3 libexpat1 libuuid1 \
        libx11-6 libxcomposite1 libxext6 libxi6 libxrender1 libxshmfence1 \
        libxkbcommon0 libxdamage1 libxfixes3 libxrandr2 libgbm1 \
        libasound2 libpango-1.0-0 libcairo2 fonts-noto-cjk \
    && rm -rf /var/lib/apt/lists/* \
    && python -m cloakbrowser install

COPY --from=web /web/dist ./web/dist
VOLUME ["/data"]
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s   CMD python -c "import urllib.request;urllib.request.urlopen('http://127.0.0.1:8000/health')"
CMD ["uvicorn", "csx.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
