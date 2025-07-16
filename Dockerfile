# Use a stable Python base
FROM python:3.10-slim

# Prevent Python from writing .pyc files & buffering
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Workdir
WORKDIR /app

# Install Node.js (for building React frontend)
RUN apt-get update && apt-get install -y curl && \
    curl -fsSL https://deb.nodesource.com/setup_18.x | bash - && \
    apt-get install -y nodejs && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Copy project
COPY . .

# Python deps
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Build frontend
WORKDIR /app/my-chatbot
RUN npm install && npm run build

# Back to root (Flask/Gunicorn)
WORKDIR /app

# Use shell form so $PORT expands; default 10000 if not set
CMD sh -c "gunicorn server:app -b 0.0.0.0:${PORT:-10000}"
