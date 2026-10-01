# Portfolio CMS backend

This is the Django project repository for the portfolio CMS.

## Local setup

1. Create and activate a Python virtual environment.
2. Install backend dependencies with `pip install -r requirements.txt`.
3. Copy `.env.example` to the workspace root as `.env` and set the local PostgreSQL credentials.
4. Start Django from this directory:

```powershell
..\.venv\Scripts\python.exe manage.py runserver
```

The PostgreSQL connection is configured from environment variables. Django REST Framework is enabled with JSON and browsable renderers. Its authentication foundation uses Django's built-in user model, JWT bearer authentication (15-minute access and one-day refresh token lifetimes), and session authentication for the browsable API. DRF views require a staff user by default (`IsAdminUser`); ordinary authenticated users are denied protected operations. Future public views must explicitly opt into public access.

### CORS and security configuration

CORS uses an explicit origin allowlist. The local Vite origins (`http://localhost:5173` and `http://127.0.0.1:5173`) are enabled by default and may be overridden with `CORS_ALLOWED_ORIGINS`; cookies are not allowed cross-origin because the frontend uses bearer JWTs. `CSRF_TRUSTED_ORIGINS` is separately configurable for Django session/admin requests.

Django's security middleware sends content-type, framing, and referrer-policy protections. HTTPS redirect, HSTS, and secure session/CSRF cookies are environment-configurable. The sample `.env.example` explicitly disables these transport-only settings for local HTTP; for production, set `DEBUG=False`, `SECURE_SSL_REDIRECT=True`, `SECURE_HSTS_SECONDS=31536000`, and both secure-cookie variables to `True`. Enable HTTPS/HSTS only when deployment is HTTPS-capable and correctly handles proxy TLS headers.

When `DEBUG=False`, Django requires an explicitly configured, unique `SECRET_KEY`
of at least 50 characters and rejects the development fallback. The default
email backend also switches from the development console backend to SMTP.
Configure `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`,
`EMAIL_HOST_PASSWORD`, and exactly one of `EMAIL_USE_TLS` or `EMAIL_USE_SSL`
for authenticated SMTP; production rejects incomplete credential pairs and
refuses to send authenticated SMTP credentials without TLS/SSL. The contact
workflow currently stores messages in the CMS inbox and does not send
notification email.

`SECURE_HSTS_PRELOAD` remains opt-in. Only enable it after verifying that the
apex domain and every subdomain can remain HTTPS-only; browsers may retain
preload policy for a long time.

### Authentication endpoints

- `POST /api/auth/token/` accepts `username` and `password`, returning access and refresh JWTs for valid credentials.
- `POST /api/auth/token/refresh/` accepts a refresh token, returning a new access JWT.

Authentication endpoint tests run with an isolated in-memory SQLite database, so they do not require changes to the local PostgreSQL database:

```powershell
..\.venv\Scripts\python.exe manage.py test config.tests --settings=config.test_settings
```

The same test command includes CORS allowlist, preflight, and security-header checks.

The full suite is run with `python manage.py test` and uses the configured
PostgreSQL database to create and destroy `test_portfolio_db`. The PostgreSQL
role must have `CREATEDB` only while that test command runs; remove the
privilege afterward.

### OpenAPI documentation

- OpenAPI schema: `GET /api/schema/`
- Swagger UI: `/api/docs/swagger/`
- ReDoc: `/api/docs/redoc/`

The schema documents the JWT login and refresh endpoints and declares HTTP Bearer authentication with JWT format for protected API operations. Generate and validate the schema with:

```powershell
..\.venv\Scripts\python.exe manage.py spectacular --validate
```

### Phase 3 content API

All public routes are anonymous and return only published content. Lists use
page-number pagination (`page` and `page_size`, capped at 100); list endpoints
support `search` and documented `ordering` fields, with resource-specific
filters where applicable.

- `GET /api/public/profile/`
- `GET /api/public/skills/`, `/api/public/skill-categories/`
- `GET /api/public/projects/` and `/api/public/projects/{slug}/`
- `GET /api/public/experience/`, `/api/public/education/`
- `GET /api/public/services/` and `/api/public/services/{slug}/`
- `GET /api/public/testimonials/`
- `GET /api/public/blog/` and `/api/public/blog/{slug}/`
- `GET /api/public/social-links/`, `/api/public/resume/`
- `POST /api/public/contact/` to submit a contact message

Public projects, profile, testimonials, blog posts, and resumes expose media
only through their associated content; there is no public media listing.

CMS endpoints use `/api/cms/` with standard list/detail/create/update/delete
routes for profiles, skill categories, skills, projects, experience, education,
services, testimonials, blog posts, social links, resumes, media, project-media
links, and contact messages. Every CMS route explicitly requires a staff user.
Publishable content also has staff-only `POST .../{id}/publish/`,
`POST .../{id}/unpublish/`, and `GET .../{id}/preview/` actions. Preview returns
the CMS representation of draft or published content without changing its
status. Publication timestamps are set on each publish, retained on unpublish,
and unaffected by ordinary edits.

CMS input serializers enforce model constraints and media-kind relationships.
Media uploads are limited to 10 MB and accept PNG, JPEG, GIF, or WebP images
and PDF documents. The server checks file signatures and matching filename
extensions rather than trusting the multipart MIME type; changing an existing
asset's media kind requires uploading a matching file.
The public contact endpoint validates submitted name, email, and message, and
limits anonymous submissions to five per hour using Django's configured
default cache. The default local-memory cache is process-local; configure a
shared cache in a multi-worker production deployment to enforce a global
per-client limit. Public categories are included only when they contain at
least one published skill.

### Domain model foundations

The `content` app contains the portfolio domain models and a generated migration. Publishing metadata is inherited from an abstract base (not a shared table). `published_at` means latest publication time: first publish and each republish update it, unpublishing preserves it, and draft edits do not update it. `SkillCategory` is structural metadata with no publishing state; categories are intended to appear publicly only when they have published skills. Media assets are not public content; public exposure must occur only through published parent-content relationships. No public media listing endpoint is provided. Uploaded files use Django's local `MEDIA_ROOT` storage.

Models are also registered in Django Admin for inspection. These APIs use the
existing schema and do not require an additional migration.

During local development, Django serves uploaded files from `MEDIA_ROOT` at
`MEDIA_URL` while `DEBUG=True`. This development-only file serving is not
enabled when `DEBUG=False`; production media should be served by the deployment's
web server or object storage.
