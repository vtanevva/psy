# Use a stable Python image
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install Node.js for the frontend build
RUN apt-get update && apt-get install -y curl && \
    curl -fsSL https://deb.nodesource.com/setup_18.x | bash - && \
    apt-get install -y nodejs && \
    apt-get clean

# Copy all files
COPY . .

# Install Python dependencies
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Build the React frontend
WORKDIR /app/my-chatbot
RUN npm install && npm run build

# Return to root app dir and run server
WORKDIR /app
CMD ["sh", "-c", "gunicorn server:app -b 0.0.0.0:${PORT:-10000}"]
