# Project 8 — Portfolio CMS

Project 8 is a full-stack portfolio CMS with a Django REST Framework API and a
React/Vite frontend. The frontend contains both the visitor-facing portfolio and
the authenticated content studio.

## Project status

- Phases 0–6 are approved and closed; Project 8 is complete.
- No Phase 7 work is authorized.
- PostgreSQL 17 is configured locally on `127.0.0.1:55432`.

## Requirements

- Python 3.12 and the workspace `.venv`
- PostgreSQL 17
- Node.js and npm

## Local configuration

The backend loads environment variables from the workspace-root `.env`. Start
from `.env.example` when creating a fresh local configuration. Keep real
credentials and secret keys out of source control.

The configured local database is `portfolio_db` on PostgreSQL port `55432`.
The cluster data directory is `%LOCALAPPDATA%\Project8Postgres17`; the cluster
must be running before starting Django.

For local HTTP development, use `DEBUG=True`, a local secret key, and the
development security-cookie and HTTPS settings shown in `.env.example`.
Production must use `DEBUG=False`, a unique secret key of at least 50
characters, HTTPS, secure cookies, and a real SMTP configuration. Django
serves local media only while `DEBUG=True`; production media serving/storage
must be provided by the deployment environment.

CMS media uploads accept PNG/JPEG/GIF/WebP images and PDF documents up to
10 MB. The backend verifies file signatures and matching extensions.

## Run locally on Windows

From the workspace root, create the virtual environment and install backend
dependencies:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
Copy-Item .env.example .env
```

Replace the example local secret and database password in `.env` with
locally-generated values before use. The placeholder secret is not suitable
for production; production settings reject a missing or weak secret.

Start the backend from `backend\`:

```powershell
..\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
```

Start the frontend from `frontend\`:

```powershell
npm.cmd install
npm.cmd run dev
```

The frontend API URL defaults to `http://127.0.0.1:8000/api`; override it with
`VITE_API_BASE_URL` in the frontend environment when needed.

## Validation

Run backend configuration/authentication/security/OpenAPI tests without
connecting to the local PostgreSQL database:

```powershell
..\.venv\Scripts\python.exe manage.py test config.tests --settings=config.test_settings
```

Run the complete backend suite from `backend\`:

```powershell
..\.venv\Scripts\python.exe manage.py test
```

The complete suite uses PostgreSQL and Django creates and removes a separate
`test_portfolio_db`. The database role used by the test runner therefore needs
temporary `CREATEDB` capability; restore its original privilege after testing.
Do not leave this capability enabled solely for application runtime.

Run the frontend checks from `frontend\`:

```powershell
npm.cmd test
npm.cmd run lint
npm.cmd run build
```

Additional backend checks, from `backend\`:

```powershell
..\.venv\Scripts\python.exe manage.py check
..\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
..\.venv\Scripts\python.exe manage.py spectacular --validate
..\.venv\Scripts\python.exe -m pip check
```

## Repositories

`backend\` and `frontend\` are part of this repository. Review and commit
project changes from the workspace root.
