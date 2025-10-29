# Use slim Python image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies needed for some Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip
RUN pip install --no-cache-dir --upgrade pip

# Copy only requirements first (layer caching)
COPY backend/requirements.txt /app/requirements.txt

# Install CPU-only PyTorch and torchvision first to leverage layer caching
RUN pip install --no-cache-dir torch==2.9.0 torchvision==0.24.0

# Install other Python dependencies
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy backend code
COPY backend/ /app/backend/

# Copy start script and make executable
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

# Expose FastAPI port
EXPOSE 8000

# Start app
ENTRYPOINT ["/app/start.sh"]
