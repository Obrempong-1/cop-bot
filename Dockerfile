# -----------------------------
# Stage 1: Build Environment
# -----------------------------
FROM python:3.11-slim AS builder

# Prevents Python from writing pyc files
ENV PYTHONDONTWRITEBYTECODE 1
# Ensures output is sent straight to terminal
ENV PYTHONUNBUFFERED 1

WORKDIR /app

# Install system dependencies (for FAISS, fitz/PyMuPDF, etc.)
RUN apt-get update && apt-get install -y \
    build-essential \
    libgl1 \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY requirements.txt .

# Install dependencies
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# -----------------------------
# Stage 2: Production Image
# -----------------------------
FROM python:3.11-slim

WORKDIR /app

# Copy only necessary files from builder
COPY --from=builder /usr/local/lib/python3.11 /usr/local/lib/python3.11
COPY --from=builder /usr/local/bin /usr/local/bin
COPY backend ./backend
COPY documents ./documents
COPY .env .env
COPY requirements.txt .

# Expose FastAPI port
EXPOSE 8080

# Environment variable for Cloud Run
ENV PORT=8080

# Start command for FastAPI
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8080"]
