FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && useradd --create-home appuser
COPY app ./app
COPY db ./db
RUN mkdir temporales && chown appuser:appuser temporales
USER appuser
EXPOSE 8000
# Servidor de desarrollo: Fase 2.1 local, sin debug ni recarga.
CMD ["sh", "-c", "python -m flask --app app:create_app actualizar-esquema && python -m flask --app app:create_app inicializar-admin && exec python -m flask --app app:create_app run --host=0.0.0.0 --port=8000 --no-debugger --no-reload"]
