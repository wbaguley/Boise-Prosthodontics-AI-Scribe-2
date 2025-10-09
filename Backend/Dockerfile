FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy ALL Python files including new modules
COPY *.py ./

# Create necessary directories
RUN mkdir -p /app/models \
    /app/logs \
    /tmp/audio \
    /app/soap_templates \
    /app/voice_profiles \
    /app/data

# Copy initialization scripts
COPY init_database.py ./
COPY init_data_structure.py ./

ENV PYTHONUNBUFFERED=1
ENV OLLAMA_HOST=http://ollama:11434

EXPOSE 3051

# Run data structure and database initialization, then start the server
CMD python init_data_structure.py && python init_database.py && uvicorn main:app --host 0.0.0.0 --port 3051 --reload