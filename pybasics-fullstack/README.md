# PyBasics — full-stack edition

A Python/FastAPI backend with a PostgreSQL database, and a plain HTML/CSS/JS
frontend that talks to it over a REST API. This replaces the earlier
single-file, browser-only version — accounts, progress, and grading now live
on a real server instead of the browser's local storage, which means:

- Accounts and progress work across devices (log in from your phone, see the
  same progress you had on your laptop).
- Passwords are hashed with bcrypt before they're ever stored.
- The exam's correct answers are **never sent to the browser** — multiple-choice
  questions omit the correct option, and Level 4/5 code challenges are graded
  by actually *running* the submitted code, server-side, inside a locked-down
  sandbox. Reading the page's source or the network tab doesn't reveal answers
  the way it did in the old static-HTML version.
- The "leave the exam → logged out" rule is now enforced on the server too: a
  detected tab-switch calls `/exam/attempt/{id}/abandon`, which marks that
  attempt dead — the frontend can't keep submitting answers to it even if
  someone tampers with the page's JavaScript.

## Project layout

```
pybasics-fullstack/
├── backend/
│   ├── app/
│   │   ├── main.py            FastAPI app, mounts the frontend, creates DB tables
│   │   ├── config.py          settings read from environment variables
│   │   ├── database.py        SQLAlchemy engine/session (SQLite locally, Postgres in prod)
│   │   ├── models.py          User, LessonCompletion, LevelProgress, ExamAttempt, AppSetting
│   │   ├── schemas.py         Pydantic request/response shapes
│   │   ├── security.py        bcrypt password hashing + JWT issuing/verification
│   │   ├── sandbox.py         the restricted Python executor that grades Level 4/5 code
│   │   ├── content/
│   │   │   ├── course.json        all 30 lesson days (reading, code sample, 2-question quiz)
│   │   │   ├── exam_mcq.py        Level 1-3 multiple-choice question generators
│   │   │   └── exam_code.py       Level 4-5 code-challenge generators
│   │   └── routers/
│   │       ├── auth.py        /api/auth/signup, /login, /me
│   │       ├── course.py      /api/course/status, /day/{n}, /day/{n}/submit
│   │       └── exam.py        /api/exam/overview, /level/{n}/start, /attempt/..., /certificate
│   ├── requirements.txt
│   ├── .env.example
│   └── Procfile
├── frontend/
│   ├── index.html
│   ├── style.css
│   └── app.js                 the whole UI — fetches the API, no build step, no framework
└── render.yaml                 optional one-click Render Blueprint
```

The backend serves the frontend itself (`main.py` mounts `frontend/` as
static files and returns `index.html` at `/`), so in production there's just
one URL and no separate frontend host or CORS headache. Locally you'll hit
the same single URL too.

## How the pieces work

### Accounts & sessions
Signup takes a username, password, and full name (used verbatim on the
certificate — this is asked for before anything else, same as before).
Passwords are hashed with bcrypt. Logging in returns a JWT that the frontend
stores in `localStorage` and sends as `Authorization: Bearer <token>` on
every request; it's valid for 12 hours by default (`ACCESS_TOKEN_EXPIRE_MINUTES`).

**Trade-off worth knowing:** storing the JWT in `localStorage` is simple and
works well for this kind of app, but it means a successful XSS attack on the
page could steal it. The usual harder-to-implement alternative is an
`httpOnly` cookie plus CSRF protection — reasonable to add later if this ever
handles something more sensitive than a practice certificate.

### The 30-day course
Each user's day-1 unlock date is stamped (`course_start_date`) the first time
they open the class. `GET /api/course/status` computes which days are
unlocked by comparing today's date to that stamp — calendar days, not
24-hour windows. Lesson quiz answers are graded by `POST
/api/course/day/{n}/submit`; the correct option is never sent to the browser
beforehand.

### The exam
`POST /api/exam/level/{n}/start` generates a fresh randomized question set
server-side (using the same generators as the original version, now native
Python) and stores it — *with* the correct answers — in an `ExamAttempt` row.
The frontend only ever receives the sanitized version. Each answer is graded
against that stored copy, one question at a time, so there's no way to see
upcoming questions or answers in advance.

**Level 4 and 5 (write-the-code challenges)** are graded by actually running
the submitted code through `sandbox.py`:
1. The code is parsed with Python's `ast` module and checked against a strict
   whitelist — only assignment/expression lines, a small set of builtins
   (`len`, `str`, `int`, `round`, …) and string/list/dict methods are allowed.
   No `import`, no `def`/`class`, no loops, no file or network access.
2. It's then executed in a **separate subprocess** with a 2-second CPU-time
   limit and a 256MB memory limit, so even something that slips past the
   whitelist (or just a huge computation) can't hang or crash the server.
3. The resulting variables are compared against the expected values.

This was fuzz-tested during development: all 7 MCQ generators and all 13 code
generators were run dozens of times each to confirm they always produce valid
questions, and the sandbox was confirmed to block `import os`, `def`, `while
True`, dunder access, and oversized memory use, while still correctly
accepting legitimate solutions (including list comprehensions and f-strings).

### Exam lockdown
While a quiz question is on screen, the frontend disables copy/paste,
right-click, and common devtools shortcuts (same caveat as before: this
deters casual screenshotting but cannot block OS-level screenshot tools).
If the tab is switched, the window loses focus, or the page is closed, the
frontend calls `/api/exam/attempt/{id}/abandon` (marking that attempt dead
server-side) and discards the login token. Logging back in requires
retaking that level from question 1 — already-passed levels are untouched.

**Honest limit:** this closes the loophole of disabling the page's JS to keep
submitting answers after leaving, but a sufficiently determined person who
scripts raw API calls — bypassing the browser entirely and never triggering a
blur/visibility event — could still submit answers without being flagged.
No client-side (or client-triggered) enforcement can fully close that gap;
truly preventing it would need things like timed server-side expiry per
question or proctoring, which weren't part of what was asked for here.

### The certificate
Unlocked once all 5 levels are passed. The director's signature is now a
single row in the database (`AppSetting`, key `director_signature`) shared by
every user and device — uploading it once updates it everywhere, which is a
genuine improvement over the old per-browser version. The PDF itself is still
generated client-side with jsPDF (drawing it is a presentation concern, not
something that needs grading or secrecy).

## Running it locally

```bash
cd backend
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env            # defaults to a local SQLite file if you don't set DATABASE_URL
uvicorn app.main:app --reload
```

Open **http://127.0.0.1:8000** — that one URL serves both the UI and the API.
SQLite is used automatically if `DATABASE_URL` isn't set, so you don't need
Postgres running locally just to try it out. The whole flow (signup → course
→ exam → certificate, including the sandboxed code grading) was verified
against this exact setup.

## Deploying to Render (free tier)

You need two things on Render: a Postgres database, and a web service for
this app. Either follow the manual steps below, or use the included
`render.yaml` — in the Render dashboard, **New +** → **Blueprint**, point it
at this repo, and it creates both resources for you with sensible defaults
(skip to step 6 if you do this).

1. **Push this project to a GitHub (or GitLab) repo.** Render deploys from a
   git repo, not a local folder — `git init`, commit everything, push it up.
2. **Create the database.** In the Render dashboard: **New +** → **PostgreSQL**.
   Give it a name (e.g. `pybasics-db`), pick the **Free** plan, and create it.
   Once it's up, open it and copy the **Internal Database URL** (starts with
   `postgresql://`) — you'll need it in step 4. Use the *internal* URL if your
   web service will be in the same Render account/region, since it's faster
   and doesn't count against external bandwidth.
3. **Create the web service.** **New +** → **Web Service**, connect the repo.
   - **Root Directory:** `backend`
   - **Runtime:** Python 3
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Plan:** Free
4. **Set environment variables** on the web service (Render's "Environment"
   tab):
   - `DATABASE_URL` — the Internal Database URL from step 2
   - `SECRET_KEY` — any long random string. Generate one locally with
     `python -c "import secrets; print(secrets.token_hex(32))"`
   - `ACCESS_TOKEN_EXPIRE_MINUTES` — `720` (or whatever you prefer)
   - `CORS_ORIGINS` — `*` is fine since the frontend is served from the same
     origin as the API in this setup
5. **Deploy.** Render builds and starts it automatically; watch the Logs tab
   for `Application startup complete.` The database tables are created
   automatically on first startup (`Base.metadata.create_all`).
6. **Open the URL Render gives you** (something like
   `https://pybasics-api.onrender.com`) — that's your live site.

**Free-tier notes:** Render's free web services spin down after periods of
inactivity and take 30-60 seconds to wake back up on the next request — the
first load after a quiet spell will feel slow, that's normal, not a bug.
Render's free Postgres databases expire after 30 days unless upgraded; you'll
get an email warning before that happens.

## Known limitations

- No admin role — any logged-in user can replace the director's signature,
  since there's no concept of an administrator yet. Fine for one person
  running this; worth adding a role check before handing it to a team.
- No password-reset flow. Forgetting a password currently means asking
  whoever runs the database to delete that account so the user can sign up
  again — there's no "forgot password" email flow (this app has no email
  sending set up at all).
- The exam content and course lessons are identical to the original version
  — carried over and fuzz-tested, not rewritten.
