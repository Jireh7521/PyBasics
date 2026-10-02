# PyBasics — Python Fundamentals Program

A self-contained, single-file HTML web app that teaches Python fundamentals through five progressively harder levels, ending in a downloadable certificate. No build step, no server, no dependencies to install — open `index.html` (or `PyBasics.html`) in a browser and it runs.

## What it does

- Account creation (username, password, full name) and login, so a learner can log out and pick up where they left off.
- Five levels of questions, each drawing from a random pool of topics so no two attempts look identical.
- A 75% pass mark per level; levels unlock in order as the previous one is passed.
- A certificate screen once all five levels are passed, with the learner's full name, an official-style seal, a director's signature, and a **Save as PDF** button that generates a real, downloadable PDF (not just `window.print()`).

## Levels

| Level | Difficulty | Format | Topics |
|---|---|---|---|
| 1 | Beginner | Multiple choice | Arithmetic, data types, booleans |
| 2 | Basic | Multiple choice | + Strings, type conversion |
| 3 | Intermediate | Multiple choice | + Lists, conditional expressions |
| 4 | Advanced | **Write real code** | Arithmetic, `//`/`%`, strings, lists, type conversion, dictionaries, booleans/logic |
| 5 | Expert | **Write real code** | Longer multi-step versions of the above: time/fare math, string cleaning, list slicing, dict lookups with defaults, chained conditionals, f-strings |

Levels 4 and 5 present a short word problem ("Instructions" + "Your Task") and a pre-filled code editor. The learner writes real Python-style code to set a handful of named variables correctly, clicks **Run & check**, and can only move on once every variable is correct. Only a first-try correct answer counts toward the score; a question solved after retries still lets the learner continue, but doesn't add a point.

## How the code challenges are checked

There's no server and no real Python interpreter here, so Levels 4 and 5 are graded by a small Python-subset interpreter written from scratch in JavaScript (no `eval`). It supports:

- Variable assignment, including `+=`, `-=`, `*=`, `/=`
- Arithmetic (`+ - * / // % **`), comparisons, `and`/`or`/`not`, `in`/`not in`
- Strings (with f-strings), lists, and dictionaries, including indexing and slicing
- Common built-ins: `len`, `str`, `int`, `float`, `bool`, `round`, `abs`, `min`, `max`, `sum`, `sorted`, `list`, `range`
- Common methods: string methods (`.upper()`, `.lower()`, `.strip()`, `.title()`, `.replace()`, `.split()`, etc.), list methods (`.append()`, `.sort()`, `.index()`, etc.), dict methods (`.get()`, `.keys()`, `.values()`)
- Conditional expressions (`x if cond else y`)
- Python-style runtime errors (`TypeError`, `ZeroDivisionError`, `NameError`, `IndexError`, `KeyError`, `ValueError`, `AttributeError`) with the offending line number

**What it does *not* support:** `def`, `if`/`for`/`while` blocks, classes, imports, or comprehensions. Challenges are written as flat assignment/expression lines so they stay within what the interpreter can run — there's no way to define a function or loop. Extending this to real block logic (functions, loops) would need a proper parser/interpreter rewrite, not just more vocabulary.

## Certificate

- Collected once per account: full name (required at signup, used verbatim on the certificate), not the username.
- A seal (SVG on-screen, hand-drawn equivalent in the PDF) and a director's signature image are baked in as defaults and can be replaced via the certificate screen.
- **Save as PDF** builds an actual PDF client-side with [jsPDF](https://github.com/parallax/jsPDF) (loaded from cdnjs) and hands it to the browser's save dialog — it does not rely on the browser's print dialog.

## Data & accounts

Everything is stored in the browser's `localStorage` — there is no backend:

- Accounts (username/password) — **passwords are stored in plain text**, which is disclosed in the UI. Fine for a learning tool; don't reuse a real password.
- Per-user progress (best score and pass/fail per level)
- Per-user full name
- The director's signature image

This means: no cross-device sync (an account only exists in the browser it was created in), no password recovery flow, and clearing browser data wipes everything.

## Known limitations / possible next steps

- "Start over from Level 1" (shown after failing the final level) currently wipes progress on **all** levels, not just the one failed.
- No progress percentage shown for an in-progress level on the dashboard — only "Not started" or "Best: x/10".
- Question pools are randomized per attempt, so the same question can repeat across retries.
- The code-challenge interpreter is intentionally a subset of Python; see above.

## Running it

Just open the HTML file in any modern browser. Nothing to install, no server required.
