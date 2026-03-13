# USMSB SDK Backend Dockerfile
# Python FastAPI backend service

FROM python:3.12-slim

# Use Chinese mirror for faster download
RUN pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

# Configure Chinese apt mirror for better connectivity
RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources 2>/dev/null || \
    sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list 2>/dev/null || true

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    gcc \
    libgmp-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ ./src/
COPY pyproject.toml .
COPY README.md .
COPY run_server.py .

# Install the package
RUN pip install -e .

# Create non-root user for security
RUN useradd -m -u 1000 usmsb && chown -R usmsb:usmsb /app
RUN mkdir -p /app/logs && chown -R usmsb:usmsb /app/logs
USER usmsb

# Expose ports
# 8000: REST API
# 8080: P2P node (optional)
EXPOSE 8000 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Start the server
CMD ["python", "run_server.py"]
