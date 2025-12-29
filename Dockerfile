# Official lightweight Python image
FROM python:3.11-slim

# Environment
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# System deps (libpq for Postgres if used) and build tools for some packages
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libpq-dev gcc curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps
COPY requirements.txt /app/
RUN pip install --upgrade pip setuptools wheel \
    && pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . /app/

# Ensure static directory exists for collectstatic
RUN mkdir -p /app/staticfiles

# Add entrypoint and make executable
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Expose port
EXPOSE 8000

# Run migrations, collectstatic, then start Gunicorn
# NOTE: set appropriate env vars (SECRET_KEY, DEBUG=False, ALLOWED_HOSTS, DB settings) at runtime
ENTRYPOINT ["/entrypoint.sh"]
CMD ["gunicorn", "smartgarden.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]
