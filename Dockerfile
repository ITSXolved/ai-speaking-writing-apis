# syntax=docker/dockerfile:1
FROM --platform=linux/amd64 python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies for PyAudio, spaCy, NLTK, and other packages
RUN apt-get update && apt-get install -y \
    curl \
    gcc \
    g++ \
    make \
    libasound2-dev \
    libportaudio2 \
    libportaudiocpp0 \
    portaudio19-dev \
    python3-dev \
    pkg-config \
    libpq-dev \
    libmagic1 \
    libmagic-dev \
    build-essential \
    git \
    wget \
    unzip \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies with increased timeout
RUN pip install --no-cache-dir --default-timeout=100 --upgrade pip \
    && pip install --no-cache-dir --default-timeout=100 -r requirements.txt

# Download spaCy language models for text analysis
RUN python -m spacy download en_core_web_sm

# Download NLTK data for text processing
RUN python -c "import nltk; nltk.download('punkt'); nltk.download('stopwords'); nltk.download('averaged_perceptron_tagger'); nltk.download('wordnet')"

# Copy application code
COPY app/ ./app/

# Create necessary directories for logs, uploads, and temporary files
RUN mkdir -p /app/logs /app/uploads /app/temp /app/cache

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash appuser \
    && chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Set environment variables
ENV PYTHONPATH=/app
ENV HOST=0.0.0.0
ENV PYTHONUNBUFFERED=1
ENV NLTK_DATA=/home/appuser/nltk_data

# Create NLTK data directory for non-root user
RUN mkdir -p /home/appuser/nltk_data

# Expose ports
# Cloud Run will use PORT (8080 by default)
# Other ports for local development/testing
EXPOSE 8080 8765 8766

# Health check for container health monitoring
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8080}/health || exit 1

# Run uvicorn with correct module path
CMD ["sh", "-c", "python -m uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080} --workers 1"]

# # Set working directory
# WORKDIR /app

# # Install system dependencies for PyAudio and other packages
# RUN apt-get update && apt-get install -y \
#     curl \
#     gcc \
#     g++ \
#     make \
#     libasound2-dev \
#     libportaudio2 \
#     libportaudiocpp0 \
#     portaudio19-dev \
#     python3-dev \
#     pkg-config \
#     && rm -rf /var/lib/apt/lists/* \
#     && apt-get clean

# # Copy requirements first for better caching
# COPY requirements.txt .

# # Install Python dependencies with increased timeout
# RUN pip install --no-cache-dir --default-timeout=100 --upgrade pip \
#     && pip install --no-cache-dir --default-timeout=100 -r requirements.txt

# # Copy application code
# COPY app/ ./app/

# # Create non-root user for security
# RUN useradd --create-home --shell /bin/bash appuser \
#     && chown -R appuser:appuser /app

# # Switch to non-root user
# USER appuser

# # Set environment variables
# ENV PYTHONPATH=/app
# #ENV PORT=8000
# ENV HOST=0.0.0.0

# # Expose ports
# # Cloud Run will use PORT (8080 by default)
# # Other ports for local development/testing
# EXPOSE 8080 8765 8766

# # Health check for container health monitoring
# HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
#     CMD curl -f http://localhost:${PORT}/health || exit 1

# # Run uvicorn with correct module path
# CMD ["sh", "-c", "python -m uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]