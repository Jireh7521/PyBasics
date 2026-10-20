# PyBasics — full-stack edition

A Python/FastAPI backend with a PostgreSQL database and a plain HTML/CSS/JS
frontend. The API owns accounts, course progress, and exam grading. The
learner-code sandbox still requires independent security review before public
exposure; static checks are not a guarantee of isolation.

## Project layout

- `backend/app/`: FastAPI app, configuration, database models, authentication,
  course/exam routes, and sandbox
- `backend/tests/`: automated tests
- `backend/requirements.txt`: Python dependencies
- `backend/.env.example`: local environment template
- `frontend/`: static browser UI
- `render.yaml`: optional Render Blueprint

## Local development

From the repository root:

```bash
cd pybasics-fullstack/backend
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000. Local defaults use SQLite and explicit localhost
CORS origins. The example secret is only for local development and must never
be used in production.

Run the configuration tests from `pybasics-fullstack/backend`:

```bash
pytest
```

## Production configuration

Set these environment variables in your hosting provider's configuration panel.
Never commit real secrets or a production `.env` file.

- `APP_ENV=production`
- `SECRET_KEY`: unique random value with at least 32 characters. Generate one
  locally with `python -c "import secrets; print(secrets.token_hex(32))"`.
- `DATABASE_URL`: explicit production database connection URL.
- `CORS_ORIGINS`: comma-separated exact frontend origins including scheme,
  e.g. `https://learn.example.com`. Do not use `*`.
- `ACCESS_TOKEN_EXPIRE_MINUTES`: optional; defaults to 720.

Production startup rejects a missing or implicit secret, a weak or known
development secret, an implicit database URL, missing CORS configuration, or
wildcard CORS origins. Since credentialed CORS is enabled, origins must be
explicit. Values are parsed as comma-separated origins.

## Deploying to Render

The included `render.yaml` creates a PostgreSQL database and web service.
Review the generated environment values in Render before deploying. Set
`CORS_ORIGINS` to the exact public frontend origin; if the frontend is served
from this same service, use that service's actual HTTPS URL. Confirm the URL in
the dashboard rather than relying on an example hostname.

Do not treat a successful deployment as a security sign-off. The learner-code
sandbox needs independent security review and isolation testing before the app
is exposed to untrusted public submissions.

## Known limitations

- No admin role: any logged-in user can currently replace the director's
  signature. Add role-based authorization before team use.
- No password-reset flow is configured.
- Course and exam content are carried over from the original edition.
