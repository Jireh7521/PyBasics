# PyBasics \u2014 full-stack edition

A 30-day Python fundamentals course plus a 5-level exam and certificate, now
built as a real client/server app: a **Flask + SQLite backend** and a
**vanilla JS frontend**, instead of a single localStorage-only HTML file.

This README exists to get it running. I can't host a live server for you
from inside this chat \u2014 you'll need to run it yourself (locally, or deploy
it somewhere like Render, Railway, Fly.io, PythonAnywhere, or a VPS).

## Why a backend changes what's real here

In the old single-file version, *everything* \u2014 accounts, passwords, course
progress, exam scores, even the correct answers to questions \u2014 lived in the
browser's localStorage. Anyone could open devtools and edit it directly:
mark every level passed, unlock day 30 on day one, see the correct answer to
a question before answering it. That's fine for a demo, not for something
you'd actually use to certify people.

With a real backend:

- **Accounts and passwords live in a database**, with passwords hashed
  (never stored in plain text).
- **The 30-day unlock clock is computed server-side** from each account's
  signup date \u2014 a user can't unlock day 30 early by changing their system
  clock or editing browser storage.
- **Exam questions are generated and graded server-side.** The browser only
  ever receives the question text and options \u2014 never the correct answer
  or the expected variable values for a code challenge \u2014 until after it
  submits an answer.
- **Level 4/5 code submissions run through a real sandboxed Python
  evaluator** (see "The code grader" below), not a hand-rolled JS clone of
  Python syntax.

## Project layout

```
pybasics/
  backend/
    app.py            Flask app: routes, SQLite setup, sessions
    grader.py          Sandboxed Python-subset evaluator for Level 4/5 code
    questions.py        Ports of all MCQ and code-challenge generators
    course.json          The 30 lesson contents (reading, code, quiz, link)
    requirements.txt
  frontend/
    index.html
    css/styles.css
    js/api.js            Thin fetch() wrapper
    js/app.js            All screen rendering + app logic
    assets/default-signature.png
```

## Running it locally

```bash
cd pybasics/backend
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
python3 app.py
```

Open **http://127.0.0.1:5000** \u2014 Flask serves both the API and the frontend
files from this one process. A `pybasics.db` SQLite file is created
automatically on first run.

There's nothing to build or compile on the frontend side \u2014 it's plain JS,
no bundler, no npm install.

## Deploying it for real

The Flask dev server (`python3 app.py`) is explicitly not meant for
production \u2014 it says so when it starts. For a real deployment:

1. Run it behind a production WSGI server, e.g. `gunicorn app:app`.
2. Set a real `PYBASICS_SECRET_KEY` environment variable (used to sign
   session cookies) \u2014 don't use the `dev-secret-change-me` default.
3. Put it behind HTTPS (a platform like Render/Railway handles this for
   you; on your own VPS, use Caddy or nginx + Let's Encrypt).
4. SQLite is fine for a small cohort of learners on a single server. If you
   expect concurrent writes at scale, move to Postgres (would mean swapping
   the `sqlite3` calls in `app.py` for `psycopg2`/SQLAlchemy \u2014 not done
   here, to keep the dependency list to just Flask).
5. `ACTIVE_ATTEMPTS` (in-progress exam attempts) is an in-memory Python
   dict, not the database \u2014 it's wiped if the server restarts, meaning
   anyone mid-level loses that attempt (their already-passed levels are
   unaffected). For a real deployment, move this to Redis or a DB table if
   that's a problem for you.

## The code grader (Level 4 & 5 submissions)

`grader.py` parses a learner's submission with Python's own `ast` module
(so it's real Python grammar), then walks the tree evaluating only an
explicit allow-list of node types: assignment, arithmetic, comparisons,
booleans, f-strings, list/dict/set/tuple literals, indexing and slicing, a
small set of built-ins (`len`, `str`, `int`, `float`, `bool`, `round`,
`abs`, `min`, `max`, `sum`, `sorted`, `list`, `range`), and a fixed set of
string/list/dict methods.

It rejects (before running a single line): `import`, `def`, `class`,
`for`, `while`, `if`-as-a-statement, `lambda`, comprehensions, and any
attribute or name starting with `_` \u2014 which closes off the usual
sandbox-escape tricks (`().__class__.__bases__`, `__import__`, etc.). This
is tested in the file's own test block and in the project's manual test
runs, including several deliberate escape attempts.

**This is a reasonable sandbox for a learning tool, not a security
boundary for hostile, incentivized attackers.** If you deploy this
publicly, also run the backend as a low-privilege, resource-limited
process (container, seccomp profile, short wall-clock timeout) as defense
in depth \u2014 don't rely on the AST allow-list alone.

## What changed from the single-file version

- **Full name is now required at signup** (used verbatim on the
  certificate) \u2014 no separate "add your name later" screen needed, since
  there's no such thing as an "existing account from before this feature."
- **Retrying a failed level no longer wipes your other passed levels.**
  The old version's "Start over from Level 1" button reset *everything* on
  a fail, even levels you'd already passed. The backend only ever updates
  the level you just attempted \u2014 failing Level 4 doesn't touch your
  Level 1\u20133 results. Flagging this because it's a deliberate behavior
  change, not just a port.
- **The exam-lockdown anti-copy/leave-detection behavior is preserved**
  (right-click/copy/devtools-shortcut blocking, and a tab-switch or window
  blur during a question logs you out and discards that level's
  in-progress attempt) \u2014 now additionally logged server-side
  (`violations` table) and enforced by invalidating the attempt on the
  server, not just the client.
- **Certificate PDF generation is still client-side** (via jsPDF), fed by
  data fetched from `/api/certificate` and `/api/signature`. Reimplementing
  PDF generation in Python (e.g. with `reportlab`) was in scope but skipped
  to keep the dependency list to just Flask \u2014 say the word if you'd
  rather have it generated server-side.

## Known limitations

- No password reset flow (no email sending is set up).
- No admin role \u2014 anyone logged in can replace the director's signature.
  Add a role check in `app.py` if that matters for your use case.
- No rate limiting on login/signup.
- `ACTIVE_ATTEMPTS` is in-memory (see "Deploying it for real" above).
- The code grader's subset doesn't support `def`, loops, or comprehensions
  \u2014 see `grader.py`'s module docstring for the full rationale and list.
