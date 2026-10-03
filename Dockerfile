# Build Python dependencies separately so compiler/header packages do not
# ship in the production runtime image.
FROM python:3.14-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/
RUN python -m pip install --upgrade pip setuptools wheel \
    && python -m pip install --no-cache-dir --prefix=/install -r requirements.txt


FROM python:3.14-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Runtime-only system packages. curl is used by container health checks.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq5 curl \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system smartgarden \
    && useradd --system --gid smartgarden --home-dir /app --shell /usr/sbin/nologin smartgarden

COPY --from=builder /install /usr/local
COPY . /app/

RUN mkdir -p /app/staticfiles /app/media \
    && chown -R smartgarden:smartgarden /app \
    && chmod +x /app/entrypoint.sh

USER smartgarden

EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["gunicorn", "smartgarden.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]
