FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# src/ stays a directory now that the service is a small package, and
# migrations/ and scripts/ ship with it so `flask db upgrade` and the seed
# script can be run against the container.
COPY src/ ./src/
COPY migrations/ ./migrations/
COPY scripts/ ./scripts/

# Lets `app:app` and `flask --app src/app.py` resolve the modules in src/.
ENV PYTHONPATH=/app/src
ENV PYTHONUNBUFFERED=1
ENV FLASK_APP=src/app.py

EXPOSE 5001

# No --preload: the old code created tables and seeded demo rows at import time,
# which under --preload happened once in the pre-fork master. The schema is now
# applied by `flask db upgrade` before the service starts.
CMD ["gunicorn", "--bind", "0.0.0.0:5001", "--workers", "2", "app:app"]
