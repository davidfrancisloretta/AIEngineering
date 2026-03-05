FROM python:3.11-slim

WORKDIR /app

# Install system dependencies including Node.js and unzip (required by Reflex)
RUN apt-get update && apt-get install -y \
    curl \
    git \
    nodejs \
    npm \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY . .

# Make run script executable
RUN chmod +x run_reflex.py

# Expose port
EXPOSE 3000

# Health check - Start period is longer for Reflex startup
HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=3 \
    CMD curl -f http://localhost:3000 || exit 1

# Run app via Python initialization script
CMD ["python", "run_reflex.py"]
