# USMSB SDK Backend Dockerfile
# Python FastAPI backend service

FROM public.ecr.aws/docker/library/python:3.14-slim-bookworm@sha256:86f975aca15cf04a40b399eebede9aea7c82eae084d1f1a0a6ef6bcaae871a30

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
RUN apt-get -o Acquire::Retries=5 -o Acquire::http::Timeout=30 update \
    && apt-get -o Acquire::Retries=5 -o Acquire::http::Timeout=30 install -y --no-install-recommends \
    curl \
    build-essential \
    gcc \
    libgmp-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Prepare the Python 3.14-only native dependency before application requirements.
COPY scripts/prepare_coincurve_py314_build.py /tmp/prepare_coincurve_py314_build.py
RUN --mount=type=cache,id=usmsb-pip-py314,target=/root/.cache/pip \
    pip install \
        cffi==2.0.0 \
        cmake==4.4.0 \
        hatchling==1.31.0 \
        scikit-build-core==1.0.3 \
        setuptools==83.0.0 \
    && python3.14 /tmp/prepare_coincurve_py314_build.py \
    && pip install --no-build-isolation coincurve==21.0.0
COPY requirements.txt .
RUN --mount=type=cache,id=usmsb-pip-py314,target=/root/.cache/pip \
    pip install -r requirements.txt

# Copy source code
COPY src/ ./src/
COPY pyproject.toml .
COPY README.md .

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
    CMD curl -f http://localhost:8000/api/health/live || exit 1

# Start the server
CMD ["python3.14", "-m", "usmsb_sdk.api.rest.main"]
