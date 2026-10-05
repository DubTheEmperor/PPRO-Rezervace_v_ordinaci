FROM python:3.12-slim

# Zakázání bufferování pro okamžité logy a zákaz tvorby .pyc
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Instalace systémových nástrojů potřebných pro překlad některých balíčků
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Instalace Python závislostí
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Zkopírování zdrojového kódu a konfigurace
COPY . .

# Oprávnění pro spouštěcí skript
RUN chmod +x entrypoint.sh

EXPOSE 8000

CMD ["./entrypoint.sh"]
