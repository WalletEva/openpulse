# OpenPulse Dockerfile
# Multi-stage build for optimized image size

FROM python:3.12-slim AS base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    OPENPULSE_DATA_DIR=/data

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd --create-home --shell /bin/bash openpulse

# Set working directory
WORKDIR /app

# Install Python dependencies
FROM base AS dependencies
COPY pyproject.toml .
COPY src/ src/
RUN pip install --no-cache-dir .

# Final runtime image
FROM base AS runtime

COPY --from=dependencies /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=dependencies /usr/local/bin/openpulse /usr/local/bin/openpulse
COPY --from=dependencies /app/src /app/src

# Create data directory
RUN mkdir -p /data && chown openpulse:openpulse /data

USER openpulse

# Expose API port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

# Default command: start API server
CMD ["openpulse", "serve", "--host", "0.0.0.0", "--port", "8000"]
