FROM python:3.13-slim

# Install system dependencies
RUN apt-get update && \
apt-get install -y curl git wget && \
rm -rf /var/lib/apt/lists/*

# Install Heroku CLI
RUN wget https://cli-assets.heroku.com/install.sh | bash

# Set working directory
WORKDIR /action

# Copy requirements and script
COPY requirements.txt .
COPY deploy.py .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Set executable permissions
RUN chmod +x deploy.py

# Configure entrypoint
ENTRYPOINT ["python", "/action/deploy.py"]