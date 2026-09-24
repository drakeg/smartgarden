# CI status: replace <owner>/<repo> with your GitHub repo
[![CI](https://github.com/drakeg/smartgarden/actions/workflows/ci.yml/badge.svg)](https://github.com/drakeg/smartgarden/actions/workflows/ci.yml)

# Smart Garden

A small Django app to model and manage Smart Garden pods. This repository contains the web app, templates, and static assets for viewing and editing garden pods.

## Features
- Garden and Pod management (owner and guest modes)
- Account garden lifecycle controls for rename/edit and confirmed deletion
- SVG and grid layout for pod placement
- HTMX-powered side panel for quick pod editing
- Inline pod-note add, edit, delete, and optional photo management
- Quick pod planting actions for "Plant Today" and confirmed reset while preserving note history
- Garden-level pod status overview with counts for each growth state
- Read-only public garden snapshots with pod status/age while keeping notes and photos private
- My Gardens dashboard summaries for active, harvesting, total pods, sharing state, and latest activity
- Clean front/back visual overlays on garden detail

## Prerequisites
- macOS / Linux / Windows with a POSIX-like shell
- Python 3.12+ (required for Django 6+ used in this project)
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

Create a local `.env` from the example and choose the host port:

```bash
cp .env.example .env
# edit APP_PORT if desired, for example APP_PORT=8085
docker compose up --build
```

The default is `http://localhost:8000`. If `APP_PORT=8085`, use `http://localhost:8085`. The container still uses port 8000 internally.

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

Set `APP_PORT` in `.env.prod` (default example: `APP_PORT=80`) and start production Compose using that file for both Compose substitution and container environment:

```bash
docker compose --env-file .env.prod -f docker-compose.prod.yml up -d --build
```

Notes:
- The production compose runs `migrate` and `collectstatic` before starting Gunicorn.
- Nginx is configured to serve `/static/` from a Docker volume and proxy other requests to the `web` service. See `deploy/nginx.prod.conf`.
- Replace `SECRET_KEY` and database credentials with secure values and ensure `ALLOWED_HOSTS` is set correctly.


## Tests
Run Django tests with:

```bash
python manage.py check
python manage.py test --verbosity=2
```

CI also creates the `staticfiles/` directory and supplies a CI-only `SECRET_KEY` so test output stays free of avoidable development-environment warnings.

## Registration & Account Activation

- This project supports user registration. Behavior depends on your `EMAIL_BACKEND` configuration:
	- Development / console backend (or when `EMAIL_BACKEND` is unset): new accounts are activated immediately and the user is logged in. This keeps onboarding friction low during development.
	- Real SMTP / transactional backends: registrations are created inactive and a confirmation email is sent with a time-limited token. The user must click the confirmation link to activate the account.

- Confirmation and welcome emails are sent as multipart messages with both plain-text and HTML bodies. Templates live under `templates/emails/`.
- Ensure you configure `DEFAULT_FROM_EMAIL` and SMTP settings when sending real emails. Smart Garden reads these directly from environment variables. Development defaults to Django's console email backend, so real mail is not sent unless you configure a real backend.

Generic SMTP example:

```ini
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
DEFAULT_FROM_EMAIL=noreply@yourdomain.com
EMAIL_HOST=smtp.example.com
EMAIL_PORT=587
EMAIL_HOST_USER=replace-me
EMAIL_HOST_PASSWORD=replace-me
EMAIL_USE_TLS=True
EMAIL_USE_SSL=False
EMAIL_TIMEOUT=10
```

Provider examples use the same Django SMTP backend:

**SendGrid**

```ini
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
DEFAULT_FROM_EMAIL=noreply@yourdomain.com
EMAIL_HOST=smtp.sendgrid.net
EMAIL_PORT=587
EMAIL_HOST_USER=apikey
EMAIL_HOST_PASSWORD=<sendgrid-api-key>
EMAIL_USE_TLS=True
EMAIL_USE_SSL=False
```

**Mailgun**

```ini
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
DEFAULT_FROM_EMAIL=noreply@yourdomain.com
EMAIL_HOST=smtp.mailgun.org
EMAIL_PORT=587
EMAIL_HOST_USER=<mailgun-smtp-username>
EMAIL_HOST_PASSWORD=<mailgun-smtp-password>
EMAIL_USE_TLS=True
EMAIL_USE_SSL=False
```

**Amazon SES SMTP**

Use the SMTP endpoint for the AWS Region where SES is configured.

```ini
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
DEFAULT_FROM_EMAIL=noreply@yourdomain.com
EMAIL_HOST=email-smtp.us-east-1.amazonaws.com
EMAIL_PORT=587
EMAIL_HOST_USER=<ses-smtp-username>
EMAIL_HOST_PASSWORD=<ses-smtp-password>
EMAIL_USE_TLS=True
EMAIL_USE_SSL=False
```

Do not enable both `EMAIL_USE_TLS` and `EMAIL_USE_SSL` at the same time. Provider credentials should be supplied through deployment secrets or environment variables and should never be committed.


### Optional Celery email delivery

Registration and welcome emails are sent synchronously by default. To queue them through Celery instead, configure a broker:

```ini
CELERY_BROKER_URL=redis://localhost:6379/0
```

Then start a worker from the project root:

```bash
celery -A smartgarden worker --loglevel=info
```

When `CELERY_BROKER_URL` is unset or empty, Smart Garden does not require a running worker and sends email directly from the web process. This keeps local development and simple deployments unchanged.

For test/dev environments you can also force Celery tasks to execute eagerly:

```ini
CELERY_TASK_ALWAYS_EAGER=True
```

## SECRET_KEY and Production

- Smart Garden reads `SECRET_KEY` from the environment for shared and production deployments.
- When `DEBUG=True` and no `SECRET_KEY` is supplied, the app uses a fixed **development-only** key. This prevents Django database sessions from becoming unreadable every time the development process restarts.
- When `DEBUG=False`, startup fails unless `SECRET_KEY` is explicitly configured. This avoids accidentally running production with a transient or insecure key.

- To generate a secure key locally you can run:

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

- In production, set `SECRET_KEY` as an environment variable and rotate it only when you must (rotating will invalidate existing sessions).

Add these env vars to your deployment configuration or Docker `.env` file and keep them secret.


## Notes / Recent UI changes
- The garden detail page shows `FRONT` and `BACK` overlays on the left/right edges to indicate orientation; the flip-view control and the orientation card have been removed for a cleaner interface.
- CSS for the garden detail page lives in `static/gardens/css/garden_detail.css`.

## Global Notes (site-wide)

This project includes a simple site-wide notes feature (`GlobalNote`) that allows authenticated users to create short notes visible across the site. Notes can be managed from the `/gardens/notes/` UI and via the JSON API.

- UI: Manage notes at `/gardens/notes/`. The list and create/edit/delete flows support HTMX for inline updates without a full-page reload.
- HTMX examples:

	- Inline create (in templates):

		<form hx-post="/gardens/notes/create/" hx-target="#global-notes-list" hx-swap="innerHTML">
			<input name="title" placeholder="Title">
			<textarea name="note" placeholder="Note"></textarea>
			<button>Save</button>
		</form>

	- HTMX fetch of edit form:

		<button hx-get="/gardens/notes/123/edit/" hx-target="#global-note-123" hx-swap="innerHTML">Edit</button>

	- If you need to simulate an HTMX request from a quick script or test, send the `HX-Request: true` header with your POST/GET.

		Example using `curl` to create a note (requires auth/cookies/session):

		```bash
		curl -X POST \
			-H "HX-Request: true" \
			-F "title=Tip" -F "note=Plant in sun" \
			http://localhost:8000/gardens/notes/create/
		```

## API

This project exposes a JSON API (via Django REST Framework). The API root is mounted at `/api/`.

- Obtain an auth token (DRF token auth):

	POST credentials to `/api-token-auth/` (username + password) to receive a token.

- Global notes endpoints:

	- `GET /api/global-notes/` — list notes
	- `POST /api/global-notes/` — create note (requires token or session auth)
	- `GET /api/global-notes/{id}/` — retrieve a note
	- `PUT/PATCH /api/global-notes/{id}/` — update note (author only)
	- `DELETE /api/global-notes/{id}/` — delete note (author only)

Example using `curl` with token auth:

```bash
# obtain token (one-time)
curl -X POST -d "username=alice&password=secret" http://localhost:8000/api-token-auth/
# then use the token
curl -H "Authorization: Token <your-token>" http://localhost:8000/api/global-notes/
```

The DRF router also provides endpoints for gardens, pods and pod-notes under `/api/`.

Garden, pod, and pod-note API endpoints require authentication and are scoped to the signed-in user's non-guest gardens. Cross-user objects are not exposed through those endpoints. Global notes remain publicly readable, but only their author can update or delete them.

### Optional developer API paywall

Smart Garden has a provider-neutral developer entitlement gate. It is disabled by default.

```ini
API_PAYWALL_ENABLED=False
```

When set to `True`, API viewsets require an active `DeveloperAccess` record. Plans and subscription state are stored independently of any payment processor, so a future Stripe, Paddle, or other billing webhook can activate/suspend access without changing API authentication.

See [Developer API Access and Paywall](docs/DEVELOPER_API.md) for the architecture and rollout plan.

## Development standards

Project development follows documented sprint, coding, testing, and review standards:

- [Contributing](CONTRIBUTING.md)
- [Sprint process and baseline history](docs/SPRINTS.md)
- [Coding standards](docs/CODING_STANDARDS.md)
- [Development workflow](docs/DEVELOPMENT_WORKFLOW.md)

These documents are part of the project definition of done and should be updated whenever the development process changes.

## Contributing

Start with [CONTRIBUTING.md](CONTRIBUTING.md). Keep changes focused, include tests for behavior changes, update documentation in the same PR, and require green CI before merge.

## Troubleshooting

- **"Session data corrupted" after changing `SECRET_KEY`:** Django session payloads are signed with the secret key. If the key changes, existing sessions cannot be decoded. Clear the site's session cookie (or run `python manage.py clearsessions` for expired database sessions), then log in again. Do not rotate `SECRET_KEY` casually in production because active sessions will be invalidated.
- "CSS not loading": verify `STATIC_URL`, `STATICFILES_DIRS`, and that static files exist under `static/`.
- "Django not found": activate the virtualenv used by the project (`source ../.venv/bin/activate`).

If you need a tailored setup (Docker, CI, or deployment guidance), open an issue or ask for specific instructions.

## Admin (local development)

The Django admin is available at `/admin/`. For local development you can create a superuser with:

```bash
python manage.py createsuperuser
# follow the prompts to set username/email/password
```

If you prefer a quick test admin account for local-only testing, create one and use it only in non-production environments. Do NOT reuse these credentials on any public or production server.

Example (for local testing only):

- Username: `admin`
- Password: `adminpass`

To add an example screenshot to the repo, place image files under `docs/screenshots/` and reference them in the README. Example markdown for an admin screenshot:

```
![Admin dashboard](docs/screenshots/admin_dashboard.png)
```

You can capture and commit small, low-resolution screenshots for documentation, but avoid committing sensitive data or real user information.
