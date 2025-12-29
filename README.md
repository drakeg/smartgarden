# CI status: replace <owner>/<repo> with your GitHub repo
[![CI](https://github.com/<owner>/<repo>/actions/workflows/ci.yml/badge.svg)](https://github.com/<owner>/<repo>/actions/workflows/ci.yml)

# Smart Garden

A small Django app to model and manage Smart Garden pods. This repository contains the web app, templates, and static assets for viewing and editing garden pods.

## Features
- Garden and Pod management (owner and guest modes)
- SVG and grid layout for pod placement
- HTMX-powered side panel for quick pod editing
- Clean front/back visual overlays on garden detail

## Prerequisites
- macOS / Linux / Windows with a POSIX-like shell
- Python 3.10+ (or the version your project uses)
- Git (optional)
- A virtual environment (recommended)

Note: This repository expects a virtualenv at `../.venv` in developer workflows used here; adjust commands below if you use a different environment.

## Quickstart (development)
1. Clone the repo (if not already):

```bash
git clone <repo-url> smartgarden
cd smartgarden
```

2. Activate the project's virtual environment (if provided):

```bash
source ../.venv/bin/activate
```

3. Install dependencies (if you maintain `requirements.txt`):

```bash
pip install -r requirements.txt
```

Or install Django directly if no `requirements.txt` exists:

```bash
pip install Django
```

4. Apply database migrations:

```bash
python manage.py migrate
```

5. (Optional) Create a superuser:

```bash
python manage.py createsuperuser
```

6. Run the development server:

```bash
python manage.py runserver
```

7. Open http://127.0.0.1:8000/ in your browser and navigate to a garden detail page to view pods and the UI.

## Static files (assets)
During development Django serves static files from `STATICFILES_DIRS`. For production, run:

```bash
python manage.py collectstatic --noinput
```

Important settings used by this project (see `smartgarden/settings.py`):

- `STATIC_URL = '/static/'`
- `STATICFILES_DIRS = [BASE_DIR / 'static']`
- `STATIC_ROOT = BASE_DIR / 'staticfiles'`

If your CSS is not loading in dev, ensure `STATIC_URL` is an absolute path (starts with `/`) and that `BASE_DIR / 'static'` exists.

## Docker

This project includes a `Dockerfile` for running the app in a container.

Build the image:

```bash
docker build -t smartgarden:latest .
```

Run the container (example):

```bash
docker run -it --rm -p 8000:8000 \
	-e SECRET_KEY='replace-me' \
	-e DEBUG='False' \
	-e ALLOWED_HOSTS='*' \
	smartgarden:latest
```

Notes:
- The `Dockerfile` runs migrations and `collectstatic` at container start. Ensure you provide production-ready env vars (database, `SECRET_KEY`, `ALLOWED_HOSTS`).
- For local development you may prefer `docker-compose.yml` (not included by default) that mounts the source and skips `collectstatic`.

### WhiteNoise (static files)

This project uses WhiteNoise in production to efficiently serve static assets directly from the Gunicorn container when Nginx is not used. WhiteNoise provides gzip/brotli compression and long-lived caching headers.

WhiteNoise is enabled via `MIDDLEWARE` and `STATICFILES_STORAGE` in `smartgarden/settings.py`. When deploying with Docker/Gunicorn you do not need a separate static file server unless you prefer Nginx in front.

### Docker Compose — Development

A development `docker-compose.yml` is provided that mounts your source directory so code changes are visible without rebuilding the image. It runs the Django development server.

Start development compose:

```bash
docker compose up --build
```

This exposes the app on `http://localhost:8000`. The service mounts a `staticfiles` volume for collected static, and the container runs migrations at startup.

### Docker Compose — Production

A production compose file `docker-compose.prod.yml` is provided. It uses PostgreSQL for the database, Gunicorn for the application server, and Nginx to serve static files and proxy requests.

Create a `.env.prod` file (example):

```ini
# Django settings
SECRET_KEY=replace-me
DEBUG=False
ALLOWED_HOSTS=your.domain.com

# Postgres (if not using managed DB)
POSTGRES_DB=smartgarden
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_HOST=db
POSTGRES_PORT=5432
```

Start production compose (detached):

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

Notes:
- The production compose runs `migrate` and `collectstatic` before starting Gunicorn.
- Nginx is configured to serve `/static/` from a Docker volume and proxy other requests to the `web` service. See `deploy/nginx.prod.conf`.
- Replace `SECRET_KEY` and database credentials with secure values and ensure `ALLOWED_HOSTS` is set correctly.


## Tests
Run Django tests with:

```bash
python manage.py test
```

## Notes / Recent UI changes
- The garden detail page shows `FRONT` and `BACK` overlays on the left/right edges to indicate orientation; the flip-view control and the orientation card have been removed for a cleaner interface.
- CSS for the garden detail page lives in `static/gardens/css/garden_detail.css`.

## Contributing
- Create a branch for your change, keep commits focused, and open a PR when ready.
- Run tests and ensure `collectstatic` is used if you change static assets.

## Troubleshooting
- "CSS not loading": verify `STATIC_URL`, `STATICFILES_DIRS`, and that static files exist under `static/`.
- "Django not found": activate the virtualenv used by the project (`source ../.venv/bin/activate`).

If you need a tailored setup (Docker, CI, or deployment guidance), open an issue or ask for specific instructions.
