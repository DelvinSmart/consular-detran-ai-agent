# Imagen de producción. Sirve para Render, Railway, Fly.io, Google Cloud Run,
# etc. Las credenciales NO se copian a la imagen: se configuran como
# variables de entorno en el panel de la plataforma.
FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Usuario sin privilegios; necesita escribir en data/index para el auto-ingest.
RUN useradd --create-home appuser && chown -R appuser /app/data
USER appuser

# La mayoría de plataformas inyectan PORT; 8000 es el valor local.
ENV PORT=8000
EXPOSE 8000

CMD ["sh", "-c", "uvicorn server:app --host 0.0.0.0 --port ${PORT} --proxy-headers --forwarded-allow-ips='*'"]
