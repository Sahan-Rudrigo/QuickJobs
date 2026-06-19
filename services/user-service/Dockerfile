# Use official Python 3.11 slim image
FROM python:3.11-slim

# Set working directory inside container
WORKDIR /app

# Copy requirements first (for Docker layer caching)
# If requirements.txt hasn't changed, Docker skips re-installing
COPY requirements.txt .

# Install all dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy all service files
COPY . .

# Expose the port this service runs on
EXPOSE 8001

# Command to start the service
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
