# Full-Stack Recovery Review

## Recovery record

- Recovered source: commit `2e7274ee1811755b10cb1671d5c1a65da1b4489d` (2026-10-07).
- Recovery branch: `feature/recover-fullstack`.
- Recovery approach: restore the historical `pybasics-fullstack/` directory onto the current `main` snapshot. The current single-file HTML learning app remains in place.
- This is a source recovery, not a claim that the application has been installed, run, tested, deployed, or security-validated.

## What is included

The restored directory contains the earlier FastAPI backend, plain HTML/CSS/JavaScript frontend, course and exam content, requirements, environment example, and deployment configuration. See `pybasics-fullstack/README.md` for the historical setup description.

## Initial review findings

1. **Configuration safety:** `backend/app/config.py` contains a development-only default secret. A production run must fail closed unless a strong secret is configured outside source control.
2. **CORS policy:** review the wildcard CORS configuration and restrict allowed origins for the actual deployment.
3. **Code execution sandbox:** `backend/app/sandbox.py` runs learner-submitted code. Static inspection is not proof of isolation. Treat this as a high-risk component; do not expose it publicly until it has dedicated tests and independent security review. Prefer OS/container-level isolation with strict resource limits and no network or sensitive filesystem access.
4. **Authentication:** review password length/encoding handling, rate limiting, session/token lifetime, secret management, and error behavior. The password hashing helper truncates input to 72 bytes; the behavior needs explicit product decisions and tests.
5. **Verification gap:** no dependencies were installed and no automated, integration, browser, deployment, or sandbox escape tests were run as part of this recovery.

## Recommended next steps

- Create a clean virtual environment and install the pinned backend requirements.
- Add automated tests for configuration, registration/login, course progress, exam grading, and malformed inputs.
- Add explicit production configuration validation and restrictive CORS defaults.
- Test sandbox timeouts, memory/CPU limits, process creation, filesystem access, imports, and network access in an isolated environment.
- Add CI to run tests and lint/type checks.
- Keep the restored full-stack application and the current HTML app separate until a documented product decision selects the canonical path.

## Verification checklist

- [ ] Dependencies installed from a clean environment
- [ ] Automated test suite added and passing
- [ ] API integration tests passing
- [ ] Frontend/API end-to-end flow tested
- [ ] Production configuration fails safely when secrets are missing
- [ ] CORS policy verified for intended origins
- [ ] Sandbox independently reviewed and tested in isolation
- [ ] Deployment smoke test completed

Unchecked boxes mean not yet verified.
