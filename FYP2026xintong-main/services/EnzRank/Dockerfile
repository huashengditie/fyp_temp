FROM python:3.9-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    libxrender1 \
    libxext6 \
    libsm6 \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p tmp/input tmp/output

EXPOSE 8003

CMD ["python", "server.py"]