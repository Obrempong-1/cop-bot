# Use official Python 3.11 slim image
FROM python:3.11-slim

# Set working directory inside container
WORKDIR /app

# Copy backend code
COPY backend/ /app/backend/

# Copy start script
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

# Copy requirements from backend
COPY backend/requirements.txt /app/requirements.txt

# Upgrade pip and install dependencies
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r /app/requirements.txt

# Expose port (if using FastAPI default)
EXPOSE 8000

# Set entrypoint to your start.sh
ENTRYPOINT ["/app/start.sh"]
