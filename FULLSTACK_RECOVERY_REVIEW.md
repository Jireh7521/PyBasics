# Full-Stack Recovery Review

## Recovery record

- Recovered source: commit `2e7274ee1811755b10cb1671d5c1a65da1b4489d` (2026-10-07).
- Recovery branch: `feature/recover-fullstack`.
- Recovery approach: restore the historical `pybasics-fullstack/` directory onto the current `main` snapshot. The current single-file HTML learning app remains in place.
- This remains a recovery and verification effort, not a production-readiness claim.

## What is included

The restored directory contains the FastAPI backend, plain HTML/CSS/JavaScript frontend, 30-day course content, five exam levels, account and progress APIs, certificate generation, pinned backend requirements, environment examples, and deployment configuration. See `pybasics-fullstack/README.md`.

## Findings and changes

1. **Production configuration:** addressed in `backend/app/config.py`. The application defaults to production mode unless `ENVIRONMENT` is explicitly set. Production requires a strong unique signing secret, PostgreSQL, and explicit HTTPS CORS origins. Wildcard origins and local SQLite defaults are rejected.
2. **CORS policy:** the local environment example uses explicit localhost origins. The Render Blueprint uses an explicit HTTPS origin that must be checked against the actual service URL before deployment.
3. **Automated verification:** added pytest coverage for configuration, registration/login, authenticated profiles, lesson answer-key privacy, lesson progress, exam gating and server-side grading, certificate eligibility, and the sandbox oversized-input guard. Added GitHub Actions for pushes and pull requests.
4. **Sandbox release blocker:** `backend/app/sandbox.py` executes learner-submitted code. The oversized-input test is not proof of process isolation. Do not expose public code execution until independent security review and isolation tests are complete.
5. **Authentication follow-up:** password hashing currently truncates input at bcrypt's 72-byte limit. Define and test the intended behavior before treating authentication as production-ready.
6. **Manual verification gap:** CI installs pinned dependencies in a clean Python 3.11 environment and the automated suite passes. A fresh local checkout, live server startup, browser-level frontend/API flow, and deployment smoke test have not yet been recorded.

## Verification evidence

- CI workflow: [Python tests](https://github.com/Jireh7521/PyBasics/actions).
- Verified commit: `797b1143f25be9de547e915af939e29684eac613`.
- Push workflow result: passed.
- Pull-request workflow result: passed.
- Test command: `python -m pytest -q` from `pybasics-fullstack/backend`.

## Remaining work

- Complete manual fresh-checkout setup and verify the health/root endpoints and frontend in a browser.
- Review password length behavior and remaining authentication controls.
- Independently review sandbox isolation, resource limits, filesystem and network access. This is a release blocker.
- Complete frontend/API end-to-end and deployment smoke tests.
- Decide and document whether the recovered full-stack app or the single-file HTML app is the canonical product before removing either.

## Verification checklist

- [x] Pinned dependencies install in a clean CI environment
- [x] Automated test suite added and passing
- [x] API integration tests for covered account/course/exam flows passing
- [x] Production configuration fails safely for missing or unsafe settings
- [x] Configuration tests reject wildcard CORS and require explicit production origins
- [ ] Fresh local setup and manual server/browser verification
- [ ] Frontend/API end-to-end browser test
- [ ] Sandbox independently reviewed and tested in isolation
- [ ] Deployment smoke test completed

Unchecked boxes mean not yet verified.
