FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Configure APT for robust network handling over official mirrors
RUN echo 'Acquire::Retries "5";' > /etc/apt/apt.conf.d/80retries && \
    echo 'Acquire::http::Timeout "30";' >> /etc/apt/apt.conf.d/80retries && \
    echo 'Acquire::ForceIPv4 "true";' >> /etc/apt/apt.conf.d/80retries && \
    rm -rf /var/lib/apt/lists/* && \
    apt-get update -o Acquire::CompressionTypes::Order::="gz" && \
    apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend ./backend
RUN mkdir -p static/palm_images

EXPOSE 8000
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]