# Backend Dockerfile - Python FastAPI with PaddleOCR
#
# Pin to Debian Bookworm for stability; floating `python:3.11-slim` can move to
# newer Debian releases (e.g. trixie) and break apt in some networks.
FROM python:3.11-slim-bookworm

# Set working directory
WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies for PaddleOCR, PDF processing, and healthcheck
RUN set -eux; \
    # Some environments block plain HTTP to debian mirrors; force HTTPS where possible.
    if [ -f /etc/apt/sources.list ]; then sed -i 's|http://|https://|g' /etc/apt/sources.list; fi; \
    if [ -f /etc/apt/sources.list.d/debian.sources ]; then sed -i 's|http://|https://|g' /etc/apt/sources.list.d/debian.sources; fi; \
    apt-get -o Acquire::Retries=3 update; \
    apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxrender1 \
    libxext6 \
    libgomp1 \
    curl \
    ; \
    rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN python -m pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create uploads directory
RUN mkdir -p uploads

# Expose port
EXPOSE 8000

# Run with hot reload for development
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
