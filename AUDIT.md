# PyBasics — Initial Project Audit

**Audit date:** 2026-10-20  
**Audited repository:** `Jireh7521/PyBasics`  
**Base branch:** `main`  
**Base commit:** `b26a5803600865d68993f29ab44bc93fc0b262be`  
**Audit branch:** `audit/initial-project-review`

## Executive summary

PyBasics has a substantial Python-learning product concept: a 30-day course, lessons and quizzes, progressive exams, progress tracking, and a completion certificate. The current default branch, however, contains only a single browser-based HTML application. The immediately preceding commit contains a more ambitious full-stack implementation (FastAPI backend, SQLAlchemy models, authentication, API routers, separate frontend, and deployment configuration) that was removed from the current tree.

**The first decision is to establish which version is the intended product.** Given the stated goal of completing the project and the existing full-stack work in history, the recommended direction is to recover and review that implementation on a feature branch rather than silently overwrite or discard either version. No source files on `main` were changed by this audit.

This is a source review, not a completed runtime or security test. The application has not been launched, dependencies have not been installed, and no test suite has been executed during this audit.

## Repository snapshot

### Current `main`

The recursive tree at the audited commit contains one file:

- `PyBasics — Python Fundamentals Program (Copy).html` — approximately 479 KB; HTML, CSS, JavaScript, lesson content, quiz logic, browser storage, and certificate generation are bundled together.

The repository currently has no root README, automated test files, dependency manifest, or GitHub Actions workflow visible in that tree.

### Previous commit: `2e7274ee1811755b10cb1671d5c1a65da1b4489d`

The parent commit contained two project directories:

- `pybasics/` — a backend/frontend split with Python backend modules and static frontend assets.
- `pybasics-fullstack/` — a FastAPI backend, SQLAlchemy models, routers, lesson and exam content, a separate HTML/CSS/JS frontend, requirements, environment example, and Render configuration.

The commit now at `main` added the single HTML file and removed the `pybasics-fullstack/` tree. This may have been intentional, but it is a major product-architecture change and should be resolved explicitly before more implementation work.

## Findings and priorities

### P0 — Decide and recover the intended application baseline

**Evidence:** The current tree contains only the browser-only HTML file; the preceding commit contains the full-stack directories and their implementation.

**Risk:** Continuing from the single-file version could abandon the server-side authentication, persistence, and grading work already present in history. Conversely, restoring the old full-stack version without reviewing it could reintroduce unverified bugs.

**Recommendation:**
1. Treat the current main branch as preserved history; do not force-push or rewrite it.
2. Use a separate branch for recovery and review.
3. Compare the old full-stack code with the current single-file version and identify features that must be preserved.
4. Select one canonical implementation only after the comparison and tests.

### P1 — Authentication and progress are not secure in the current browser-only version

**Evidence:** The current HTML source stores account credentials and progress in browser `localStorage`; the login path compares the entered password to the stored value.

**Risk:** Browser storage is accessible to scripts running on the page and can be edited by the user. This is not suitable for protecting account credentials or authoritative course/exam results. The application itself warns that its storage is not secure.

**Recommendation:** Prefer the full-stack server-side account model. Store password hashes only, keep authorization and scoring on the server, validate input server-side, and add tests for unauthenticated access and account separation. A client-only prototype should clearly be labelled as a local learning demo, not secure account storage.

### P1 — Exam restrictions in the browser are deterrents, not security controls

**Evidence:** The current HTML uses visibility, blur, keyboard, copy, and context-menu event handlers during an exam. Such handlers execute in the user's browser and can be bypassed or disabled.

**Risk:** Client-side restrictions cannot reliably enforce exam rules or hide answer keys. The browser-only implementation also contains its own Python-subset interpreter and answer logic.

**Recommendation:** Keep authoritative attempt state, correct answers, grading, pass thresholds, and attempt abandonment on the backend. Treat browser restrictions as user-experience deterrents only. Test the API directly as well as through the UI.

### P1 — No automated verification is present in the current tree

**Evidence:** The current default-branch tree contains no test suite, test configuration, dependency file, or CI workflow.

**Risk:** Changes to login, lesson unlocking, grading, progress persistence, and PDF generation could regress without detection. There is currently no reproducible evidence that the checked-in version passes an automated suite.

**Recommendation:** Add a documented test strategy and CI checks. At minimum, test authentication validation, per-user progress isolation, course unlock rules, quiz scoring and retries, exam attempt lifecycle, code grading boundaries, and certificate eligibility. Record test results only after running them.

### P1 — The previous full-stack configuration has an unsafe development secret fallback

**Evidence:** In the previous commit's `pybasics-fullstack/backend/app/config.py`, `secret_key` defaults to `dev-only-insecure-key-change-me`.

**Risk:** If deployed without overriding this value, signed sessions/tokens could be forgeable.

**Recommendation:** Fail fast in production when a strong secret is not configured; keep any development-only default explicitly restricted to local development. Add configuration tests. Do not assume the old full-stack branch is production-ready simply because it has server-side authentication.

### P1 — Submitted Python code needs focused sandbox verification

**Evidence:** The previous full-stack version includes `backend/app/sandbox.py`, which validates submitted code using Python's AST, then executes accepted code in a subprocess with resource limits.

**Risk:** Code execution boundaries are security-sensitive and can be platform-dependent. The module imports Unix-oriented `resource` and `signal` facilities and attempts to use `fork`; portability and failure handling need to be verified in the actual deployment environment. Static inspection alone cannot establish that the sandbox is safe.

**Recommendation:** Add positive and negative tests for allowed challenge solutions, imports, dunder/attribute access, huge inputs, timeouts, memory pressure, malformed syntax, subprocess failures, and platform behavior. Keep the code runner isolated and do not expose unrestricted Python execution.

### P2 — The single-file architecture makes changes difficult to maintain

**Evidence:** Current HTML bundles styling, screen rendering, course content, a Python-subset interpreter, quiz logic, local storage, and certificate PDF generation into one large file.

**Risk:** Feature changes are difficult to isolate and test; repeated UI rendering and state transitions are harder to reason about.

**Recommendation:** If the full-stack architecture is selected, retain separate frontend files and Python modules with clear responsibilities. Move lesson and question content into structured data. Refactor incrementally and preserve a working checkpoint after each step.

### P2 — Dependencies and external assets need reproducible handling

**Evidence:** The current HTML loads jsPDF and fonts from external CDNs. The previous full-stack backend has pinned Python dependencies in `requirements.txt`.

**Risk:** CDN availability can affect PDF generation and typography; old dependency pins may need compatibility and vulnerability review.

**Recommendation:** Document external runtime dependencies, test the app with network failures where feasible, and review/update Python packages deliberately rather than blindly upgrading them.

### P2 — Course unlock and exam behavior need explicit acceptance tests

**Evidence:** The current browser version derives lesson availability from a timestamp and `Date.now()`, and stores completion in local storage. Exam focus/visibility handlers also change the current state.

**Risk:** Client-side time and stored state can be manipulated; edge cases around time zones, repeated attempts, refreshes, and interrupted sessions may be inconsistent.

**Recommendation:** Define the course calendar/time-zone rule and exam attempt lifecycle. Enforce authoritative unlock and grading rules server-side in the selected full-stack implementation and test boundary dates, retries, refreshes, logout, and interrupted attempts.

### P2 — Project documentation and contribution workflow are missing on current `main`

**Evidence:** The current tree has no root README, license, contribution guidance, or CI workflow. A detailed README exists in the prior full-stack commit, but it is not present in the current tree.

**Risk:** A new contributor cannot reliably tell which version is canonical, how to install it, how to run it, or how to verify it.

**Recommendation:** After selecting the implementation, restore/update a root README, include setup and test commands, explain environment variables, document known limitations, add a license if the owner intends to license the project, and configure CI.

## Proposed work plan

1. **Baseline recovery:** compare current HTML with both prior project directories; select and recover the intended baseline on a dedicated feature branch.
2. **Reproducible startup:** verify installation instructions and launch the app in a clean environment.
3. **Automated test foundation:** add unit/API tests and CI before major refactors.
4. **Security and correctness:** verify password handling, authorization, course unlocks, exam lifecycle, and sandbox limits.
5. **Maintainability:** separate responsibilities and content while preserving behavior.
6. **UX and accessibility:** check keyboard navigation, labels, error feedback, mobile layout, and certificate generation.
7. **Documentation and deployment:** verify setup, environment configuration, deployment, and final acceptance scenarios.

## Acceptance criteria for calling the project complete

- The chosen implementation and its trade-offs are documented.
- A clean checkout can be installed and run by following the README.
- Automated tests and CI pass, with the observed result recorded.
- Passwords are never stored in plaintext in the production implementation.
- Course progress and exam results are authoritative and isolated per user.
- Submitted code is handled by a tested, restricted execution path.
- Lesson, exam, retry, logout, and certificate flows pass documented end-to-end checks.
- No change is merged into `main` without review of the branch diff and verification results.

## Verification status

- [x] Inspected the current default-branch tree and latest commit metadata.
- [x] Inspected the preceding commit's project tree and full-stack README.
- [x] Inspected the previous full-stack configuration, password helpers, sandbox, and requirements.
- [ ] Installed dependencies and launched the application.
- [ ] Executed automated tests.
- [ ] Performed browser/API end-to-end verification.
- [ ] Performed an independent security review of the sandbox and authentication flows.

**Important:** Checked items above describe source inspection only. All runtime, automated-test, deployment, and security-validation items remain open.
