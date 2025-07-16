# ----------------------------
# Base image
# ----------------------------
FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# ----------------------------
# System deps incl. Node.js
# ----------------------------
RUN apt-get update && apt-get install -y curl git build-essential && \
    curl -fsSL https://deb.nodesource.com/setup_18.x | bash - && \
    apt-get install -y nodejs && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# ----------------------------
# Python deps (layer-cached)
# ----------------------------
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# ----------------------------
# Frontend deps (layer-cached)
# ----------------------------
COPY my-chatbot/package*.json my-chatbot/
WORKDIR /app/my-chatbot
RUN npm ci || npm install

# ----------------------------
# Copy rest of source & build frontend
# ----------------------------
COPY . /app
WORKDIR /app/my-chatbot
RUN npm run build

# ----------------------------
# Final runtime
# ----------------------------
WORKDIR /app
EXPOSE 10000
# Shell form so $PORT expands; fallback 10000
CMD ["python", "server.py"]
