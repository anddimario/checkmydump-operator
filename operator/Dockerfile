FROM python:3.13-alpine

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Create and set working directory
WORKDIR /app

# Add current directory code to working directory
COPY requirements.txt .

# Install python dependencies
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Create a user to run the application
RUN adduser -D -s /bin/bash app
USER app

CMD ["kopf", "run", "main.py"]
