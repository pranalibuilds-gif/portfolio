# Public portfolio and CMS frontend

The React 19 frontend serves both the public visitor-facing portfolio and the authenticated Phase 4 content studio. It uses Vite and Tailwind CSS, with public content read from the backend API and no seeded or mock portfolio content.

## Local setup

```powershell
npm install
npm run dev
```

The backend API defaults to `http://127.0.0.1:8000/api`. Override it in `.env.local`:

```env
VITE_API_BASE_URL=http://127.0.0.1:8000/api
```

The configured API URL should include the `/api` prefix. Public read endpoints are available without login. Sign in to `/login` with a Django staff/superuser account to use the CMS; the API protects CMS endpoints with administrator permissions.

## Public portfolio

- `/` — portfolio landing page with published profile, skills, projects, experience, education, services, testimonials, blog highlights, social links, résumé download, and contact form.
- `/projects/:slug` — published project details, media gallery, links, and skills.
- `/blog` and `/blog/:slug` — published article list and detail pages.
- Contact form submissions use the public contact endpoint. The UI reports field/API errors and submission success.
- Published content is fetched live; empty collections, missing profile content, loading, and recoverable API failures have dedicated states.
- Public navigation, layouts, forms, and content grids adapt to mobile and desktop. Semantic landmarks, skip navigation, visible keyboard focus, labelled form controls, and status/error announcements are included.

The portfolio reads from `GET /public/profile/`, `/public/skill-categories/`, `/public/projects/`, `/public/projects/{slug}/`, `/public/experience/`, `/public/education/`, `/public/services/`, `/public/testimonials/`, `/public/blog/`, `/public/blog/{slug}/`, `/public/social-links/`, and `/public/resume/`. Contact submissions use `POST /public/contact/`. These paths are relative to `VITE_API_BASE_URL`.

## Content studio

- `/cms/dashboard` — authenticated overview and navigation for profiles, skill categories, skills, projects, experience, education, services, testimonials, blog posts, social links, resumes, media, project galleries, and the contact inbox.
- JWT login, automatic access-token refresh on `401`, and local sign-out. Tokens are held in browser `sessionStorage` and cleared when refresh fails. The backend does not expose a logout/revocation endpoint, so sign-out clears this browser session only.
- Create, edit, search, paginate, filter, and delete content where the API supports it. Publishable resources expose publish/unpublish actions and an authenticated preview action.
- Upload and maintain image/document media, manage project gallery entries, and review/update contact-message status.
- Server validation feedback, API/network errors, loading indicators, and empty states.

Existing `/cms/:resource` paths and `/login` remain available. The public portfolio is now the root route.

## Validation

```powershell
npm.cmd test
npm.cmd run lint
npm.cmd run build
```

The dependency-free Node test suite covers API request helpers, session token
handling, JWT refresh and failure events, and API/network error reporting.
Commands are expected to be run from this `frontend` directory.
