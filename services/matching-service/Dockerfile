# Use official Python 3.11 slim image
FROM python:3.11-slim

# Set working directory inside container
WORKDIR /app

# Copy dependencies first (better Docker cache behaviour)
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy rest of the service code
COPY . .

# Expose port 8004 (matching service port)
EXPOSE 8004

# Start the service
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8004"]