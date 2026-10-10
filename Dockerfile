# CampusPulse container image
FROM python:3.12-slim

# Do not write .pyc files; print logs immediately.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000 \
    DATABASE_PATH=/data/campuspulse.db

WORKDIR /app

# Install dependencies first so Docker can cache this layer.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code (see .dockerignore for what is left out).
COPY . .

# Run as a normal user, not root. /data holds the SQLite file.
RUN useradd --create-home appuser \
    && mkdir -p /data \
    && chown -R appuser:appuser /app /data
USER appuser

EXPOSE 8000

# One worker with several threads keeps the SQLite file and the signed
# session cookie simple. ${PORT} is set by Render at runtime.
CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:${PORT} --workers 1 --threads 4 'app:create_app()'"]
