FROM python:3.8-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    libxrender1 \
    libxext6 \
    libsm6 \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p tmp/input tmp/output

EXPOSE 8002

CMD ["python", "server.py"]