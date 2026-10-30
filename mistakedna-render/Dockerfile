# Build only: Node and frontend development dependencies are absent from the runtime image.
FROM node:22-bookworm-slim AS frontend
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim-bookworm AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
WORKDIR /app
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt && useradd --create-home --uid 10001 appuser
COPY backend/ backend/
COPY scripts/start.sh scripts/start.sh
COPY --from=frontend /web/dist/ frontend/dist/
RUN mkdir -p /app/data && chown -R appuser:appuser /app && chmod +x scripts/start.sh
USER appuser
EXPOSE 10000
CMD ["sh", "scripts/start.sh"]
