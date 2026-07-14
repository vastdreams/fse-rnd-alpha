# PATH: backend/Dockerfile
# FastAPI Backend Docker Image
#
# Build from the repository root so sealed investor contracts are baked in:
#   docker build -f backend/Dockerfile -t rd-alpha-backend:local .

FROM python:3.11-slim@sha256:e031123e3d85762b141ad1cbc56452ba69c6e722ebf2f042cc0dc86c47c0d8b3

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install the reviewed, transitive dependency lock rather than resolving
# mutable version ranges while a production image is built.
COPY backend/requirements.lock .
RUN pip install --no-cache-dir -r requirements.lock

# Application code, then sealed contracts used by rank/stance provenance.
COPY backend/ .
COPY contracts /app/contracts

# Create non-root user
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Run FastAPI with uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
