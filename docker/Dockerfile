FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

# ⚠️ Пути от корня проекта (build context), не от docker/
COPY requirements.txt .
RUN pip install -r requirements.txt

# Копируем весь контекст (там уже отфильтровано .dockerignore)
COPY . .

# entrypoint лежит в docker/ — путь тоже от корня
RUN chmod +x docker/entrypoint.sh

RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

ENTRYPOINT ["docker/entrypoint.sh"]