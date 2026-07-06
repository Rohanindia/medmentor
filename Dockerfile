# Use an official lightweight Python runtime as a parent image
FROM python:3.12-slim

# Set the working directory in the container
WORKDIR /app

# Install system dependencies if any library needs compiling
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file first to leverage Docker build cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire project code into the container
COPY . .

# Expose the port FastAPI runs on
EXPOSE 8000

# Set environment variable defaults
ENV PORT=8000

# Command to run the application using uvicorn
CMD ["sh", "-c", "uvicorn bridge:app --host 0.0.0.0 --port ${PORT}"]
