# Use official PyTorch CPU image (prebuilt with Python 3.11)
FROM pytorch/pytorch:2.9.0-cpu

# Set working directory inside container
WORKDIR /app

# Copy backend code
COPY backend/ /app/backend/

# Copy start script
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

# Copy requirements from backend
COPY backend/requirements.txt /app/requirements.txt

# Upgrade pip and install remaining dependencies
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r /app/requirements.txt

# Expose FastAPI default port
EXPOSE 8000

# Set entrypoint to your start.sh
ENTRYPOINT ["/app/start.sh"]
