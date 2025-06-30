# Use official Python image
FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Create app directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    npm \
    && rm -rf /var/lib/apt/lists/*

# Copy all files into container
COPY . /app/

# Install Python dependencies
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Build React frontend
WORKDIR /app/my-chatbot
RUN npm install
RUN npm run build

# Return to Flask directory
WORKDIR /app

# Expose port (Render uses PORT env var)
ENV PORT=10000

# Start the app
CMD ["gunicorn", "server:app", "-b", "0.0.0.0:$PORT"]
