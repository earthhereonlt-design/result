FROM mcr.microsoft.com/playwright/python:v1.42.0-jammy

# Set working directory
WORKDIR /app

# Install system dependencies (minimal extra for bot)
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers (already in image, but ensuring chromium is ready)
RUN playwright install chromium

# Copy application code
COPY app.py .

# Expose port for ping
EXPOSE 3000

# Run the application
CMD ["python3", "app.py"]
