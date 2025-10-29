# Use official slim Python 3.11 image
FROM python:3.11-slim

# Set working directory inside container
WORKDIR /app

# Copy only what is needed
COPY backend/ /app/backend/
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

# Install system dependencies for some Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip
RUN pip install --no-cache-dir --upgrade pip

# Install CPU-only PyTorch and dependencies first to avoid huge builds
RUN pip install --no-cache-dir torch==2.9.0+cpu torchvision==0.24.0+cpu -f https://download.pytorch.org/whl/torch_stable.html

# Install the rest of the dependencies
COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Expose port (FastAPI default)
EXPOSE 8000

# Set entrypoint
ENTRYPOINT ["/app/start.sh"]
