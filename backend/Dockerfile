# === STAGE 1: Builder ===
FROM python:3.11-slim AS builder

# Ambil binary uv resmi dari image Astral secara instan
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Mengoptimalkan cache Docker layer
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

# Pindahkan file pengunci dependency terlebih dahulu
COPY pyproject.toml uv.lock ./

# Install dependency produksi tanpa mengotori environment dengan grup dev
# --frozen menjamin uv tidak akan mencoba memperbarui lockfile saat build
RUN uv sync --frozen --no-dev --no-editable

# === STAGE 2: Runtime ===
FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Jaga library OS yang dibutuhkan tetap ada
RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq5 curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m -r appuser

# Salin virtual environment (.venv) yang sudah matang dari stage builder
COPY --from=builder /app/.venv /app/.venv

# Salin kode aplikasi kamu
COPY --chown=appuser:appuser . .

# Siapkan folder untuk model cache dan uploads dengan permission yang benar
RUN mkdir -p /app/uploads /app/model_cache \
    && chown -R appuser:appuser /app

# Daftarkan path virtual environment ke PATH sistem agar binary uvicorn langsung terbaca
ENV PATH="/app/.venv/bin:$PATH"
ENV HF_HOME=/app/model_cache

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health/live || exit 1

# Panggil langsung uvicorn dari virtual environment yang sudah diaktifkan di PATH
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
