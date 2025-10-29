FROM python:3.11-slim

# Workdir
WORKDIR /app

# Env
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PORT=8080

# System deps (only if you really need gcc for building wheels)
RUN apt-get update && apt-get install -y --no-install-recommends gcc && \
    rm -rf /var/lib/apt/lists/*

# Install Python deps
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# App code
COPY app ./app

# (Optional) EXPOSE is ignored by Cloud Run, but harmless
EXPOSE 8080

# (Optional) Remove HEALTHCHECK — Cloud Run uses its own health checks.
# If you keep it, avoid adding extra deps; use Python stdlib:
# HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
#   CMD python -c "import http.client; c=http.client.HTTPConnection('localhost', 8080, timeout=5); c.request('GET','/health'); r=c.getresponse(); exit(0 if r.status<400 else 1)"

# ✅ Use shell form so ${PORT} expands; bind to 0.0.0.0
CMD sh -c "uvicorn app.main:app --host 0.0.0.0 --port \${PORT:-8080} --proxy-headers --forwarded-allow-ips '*'"