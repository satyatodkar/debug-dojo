# 🥋 Debug Dojo

> **A beginner-friendly Python debugging playground — built at a 24-hour hackathon.**

Students are given broken Python code, progressive hints, and instant feedback
to build real debugging skills.

---

## Quick Start (copy-paste these 5 commands)

```bash
# 1. Move into the project folder
cd Debug

# 2. Create a virtual environment
#    (this keeps Debug Dojo's packages separate from everything else on your computer)
python3 -m venv venv

# 3. Activate it
#    On macOS / Linux:
source venv/bin/activate
#    On Windows (Command Prompt):
#    venv\Scripts\activate.bat

# 4. Install dependencies
pip install -r requirements.txt

# 5. Start the server
uvicorn main:app --reload
```

Once it starts you should see something like:

```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

Now open your browser and visit:

| URL | What you see |
|-----|-------------|
| `http://localhost:8000` | The Debug Dojo homepage |
| `http://localhost:8000/api/health` | `{"status":"ok"}` (raw JSON) |

The **badge** in the top-right corner of the page will turn green and say
**✓ Connected** when the frontend can reach the backend.

---

## Why a virtual environment?

A virtual environment is like a clean room for your project.
Every Python project can need different package versions; a virtual environment
makes sure they don't conflict.

The `venv/` folder is created inside the project – it's safe to delete and
recreate at any time by running steps 2-4 again.

---

## Project Structure

```
Debug/
├── main.py            ← FastAPI server (start here to understand the backend)
├── requirements.txt   ← Python packages the project needs
├── README.md          ← This file
└── static/
    ├── index.html     ← The webpage
    ├── style.css      ← All the colours and layout
    └── app.js         ← Calls /api/health and updates the status badge
```

---

## How it works (big picture)

```
Browser                       FastAPI (main.py)
  |                                |
  |---  GET /            -------->  |  serves static/index.html
  |<-- HTML page  ---------------  |
  |                                |
  |--- GET /static/style.css  -->  |  (served automatically by StaticFiles)
  |--- GET /static/app.js     -->  |
  |                                |
  |--- GET /api/health        -->  |  returns {"status": "ok"}
  |<-- {"status": "ok"}  -------  |
  |                                |
  (badge turns green)
```

---

## Stopping the server

Press **Ctrl + C** in the terminal where uvicorn is running.

---

## Completed Phases

- [x] **Phase 1**: Project foundation, FastAPI backend, health check, and developer-tool design.
- [x] **Phase 2**: 10 beginner Python challenges with 3 difficulty tiers and visible/hidden test cases.
- [x] **Phase 3**: Secure Docker isolated execution (`POST /api/submit`) with strict memory/CPU/PID bounds and timeout enforcement.
- [x] **Phase 4**: Safe plain-language failure explanations, 3-tier progressive hint ladder (`POST /api/hint`), and mistake taxonomy.
- [x] **Phase 5**: Persistent SQLite learner history, concept mastery, recurring mistake tracking across challenges, and smart recommendations (`GET /api/learner/{id}`).
- [x] **Phase 6**: Integrated, polished developer-tool UI with top navbar views (Workspace, My Progress), live challenge search, in-memory code preservation, Tab key indentation, and accessible dark mode styling.
- [x] **Phase 7**: Formal Examination Panel in separate browser tab, difficulty-based countdown timers (Easy: 15m, Medium: 25m, Hard: 40m), anti-paste & focus integrity audit signals, disposable Docker code execution sandbox (128 MiB, 64 KiB output cap, `--network none`, `--read-only`, fail-closed), and confidential hidden-test protection.
- [x] **Phase 8**: Authentication, Beautiful Public Landing Page, and Personal Account System with Argon2id password hashing, HttpOnly session cookies, CSRF validation, rate limiting, personal dashboard, profile management, and strict user data isolation.
- [x] **Phase 9**: Anime.js Integration, View Separation, Learner Intelligence Dashboard, Per-Test Results Table, and Enforced Docker Resource Limits.

---

## Anime.js UI & Navigation Architecture

Debug Dojo integrates [Anime.js](https://animejs.com/) (`v3.2.2`, vendored in `static/anime.min.js`) for restrained, high-performance UI animations:

1. **Accessibility & Reduced Motion**:
   - Strictly respects `window.matchMedia('(prefers-reduced-motion: reduce)')`.
   - When reduced motion is preferred or Anime.js fails to load, animations degrade gracefully into instant zero-delay transitions.
2. **Landing Page Animations**:
   - Hero text reveal (`#hero-title`, `#hero-desc`) with smooth vertical slide and opacity fade (`duration: 700ms`).
   - Staggered entrance for feature cards (`.hero-feature-card`, `delay: anime.stagger(100)`).
   - CTA entrance with subtle pulse.
3. **Authenticated Home & Navigation**:
   - Distinct Single-Page Views: `view-landing`, `view-home`, `view-challenges`, `view-workspace`, `view-dashboard`, `view-account`.
   - Centralized `showView(viewName)` switches active tabs, preserves unsaved editor code (`learnerCodeCache`), synchronizes browser history via `history.pushState`, and runs smooth directional opacity fades.
   - Dedicated authenticated **Home View (`#view-home`)** displaying personalized greeting, quick action shortcuts, recommended challenge card, concept mastery mini-summary, recurring mistakes summary, and recent submission activity.

---

## Learner Intelligence & Mastery Calculation

### 1. Deterministic Concept Mastery Formula
Mastery is estimated deterministically on a strict 0–100% scale:
- **Clean Pass (no hints used)**: `+25.0%`
- **Pass After Hints**: `+15.0%`
- **Failed Attempts**: `+0.0%` (failed attempts receive no pass reward; prior mastery is not penalized)
- **Unattempted Concepts**: Displayed accurately at `0.0%` (no fabricated progress)
- **Bounded Clamping**: All mastery values are strictly clamped between `0.0%` and `100.0%`.
- **Idempotency Guarantee**: Submissions are stamped with `processed_for_progress = 1`. Duplicate requests or double clicks will never award mastery multiple times.
- **Strict Scope**: Only concepts linked to the evaluated challenge in its metadata tags are updated.

### 2. Recurring Mistakes Analysis
To prevent false pattern attribution, a mistake category qualifies as **recurring** if and only if it appears in failed submissions across **at least two distinct challenge IDs** for that learner.

- **Required Mistake Identifiers**:
  - `off_by_one`: Indexing errors, boundary offsets, or range loop miscalculations.
  - `unhandled_short_input`: Crashes or wrong outputs on empty collections or length-1 inputs.
  - `print_not_return`: Printing to standard output instead of returning values from functions.
  - `boundary_comparison`: Using `>` instead of `>=` or `<` instead of `<=`.
  - `mutates_input`: Modifying caller arguments in-place when a fresh result is expected.
- **Dedicated Dashboard View**:
  - Summary metrics banner (Distinct Recurring Categories, Affected Challenges, Primary Weakness).
  - Categorized weakness cards with human-readable titles, priority indicators (High/Medium/Low based on failure frequency), evidence descriptions, and affected challenge lists.
  - Direct **"Practice This Weakness"** action buttons loading targeted challenges directly into the Workspace.

### 3. Personalized Challenge Recommendations
The recommendation engine selects the next challenge according to strict evidentiary priorities:
1. **Target Confirmed Recurring Mistake**: Prioritizes an unsolved challenge that teaches the learner's most frequent recurring mistake.
2. **Target Lowest Mastery Concept**: If no recurring mistake is confirmed, targets the concept with lowest non-100% mastery.
3. **Avoid Mastered Challenges**: Excludes challenges already completed with full passes.
4. **Completion Handling**: When all 10 challenges are passed, displays a congratulatory completion state.

---

## Per-Test Results & Resource Limits Enforcement

### 1. Outcome Mapping (Canonical Judge Compatibility)
To maintain 100% compatibility with automated hackathon judges, backend outcome values remain strictly canonical, while the frontend displays human-friendly labels:

| Canonical Backend Outcome | User-Facing Display Label | Description |
|---|---|---|
| `passed` | **Right** | Function produced the correct expected result. |
| `wrong output` | **Wrong** | Function executed, but return value did not match expected value. |
| `runtime error` | **Runtime Error** | Python exception raised, or resource limit exceeded. |
| `timeout` | **Run Forever / Timeout** | Program did not finish within the allowed execution deadline. |

### 2. Explicit Resource Limit Reporting
When a test case is terminated due to exceeding a sandbox limit, the runner identifies the actual enforcement event and displays an explicit limit description:
- **Memory Limit (128 MB)**: `Runtime Error — Memory limit exceeded` (detected via Docker exit code 137, OOMKilled flag, or `MemoryError`).
- **Output Limit (64 KB)**: `Runtime Error — Output limit exceeded` (detected via stream byte-counting in `BoundedWriter` and runner process termination).
- **Disk Limit (4 MB tmpfs / read-only root)**: `Runtime Error — Disk limit exceeded` (detected via `errno 28 ENOSPC` or read-only filesystem violations).
- **Process Limit (32 PIDs)**: `Runtime Error — Process limit exceeded` (detected via `errno 11 EAGAIN` or Docker PID exhaustion).

### 3. Hidden-Test Secrecy
For hidden evaluation tests:
- Inputs (`args`), calls, and expected answers are **never** mounted or passed into the container.
- Comparison occurs outside the learner process on the trusted server side.
- API responses omit `call`, `expected`, `actual`, and raw tracebacks for all hidden tests, disclosing only the final permitted outcome (`passed`, `wrong output`, etc.), safe details, and execution time.

---

## Examination Mode & Anti-Cheating Architecture

Debug Dojo provides two distinct environments:

1. **Practice Mode (`/`)**:
   - Iterative debugging, progressive tiered hints, plain-language explanations, mastery score tracking, and standard clipboard usage.
2. **Examination Mode (`/exam?challenge_id=<id>`)**:
   - **Separate Tab & Viewport**: Opens in dedicated window/tab filling the viewport with an accessible Fullscreen toggle.
   - **Two-Column Layout**: Left column question paper (38%) with problem statements, signatures, constraints, and sample tests; Right column coding workspace (62%) with Python editor, Run Tests (visible tests only), and Submit Answer (with confirmation modal).
   - **Authoritative Server Timers**:
     - Easy: 15 minutes (`900s`)
     - Medium: 25 minutes (`1500s`)
     - Hard: 40 minutes (`2400s`)
     - Re-checking or refreshing the tab recalculates remaining time from server deadline without resetting or extending time.
     - Visual & textual warnings at 5 minutes and 1 minute remaining.
     - Auto-finalization on deadline expiry; duplicate submissions prevented.
   - **Anti-Paste Deterrents**:
     - Blocks `paste` and `beforeinput` events in the exam editor.
     - Intercepts shortcuts: `Ctrl+V`, `Cmd+V`, `Ctrl+Shift+V`, `Cmd+Shift+V`, `Shift+Insert`.
     - Blocks drag-and-drop and editor context-menu paste.
     - Preserves normal typing, navigation, and 4-space Tab indentation.
   - **Integrity Event Audit**:
     - Logs paste attempts, drag-and-drop attempts, tab switches (`visibilitychange`), window blur, and fullscreen exit events to `exam_integrity_events` table.
     - Displays advisory alert banner if 3 or more events are logged. Focus loss does not automatically fail the student.
   - **Disposable Docker Sandbox Execution**:
     - Each test executes in an ephemeral container (`python:3.12-slim`).
     - Security bounds: `--network none`, `--read-only`, `--tmpfs /tmp:size=4m,noexec`, `--memory 128m`, `--cpus 0.5`, `--pids-limit 32`, `--cap-drop ALL`, `--security-opt no-new-privileges`, `--user 65534:65534`.
     - Output cap: 64 KiB max combined output per test.
     - Hidden tests remain confidential on trusted server side; input args, expected values, actual outputs, and raw tracebacks are never disclosed to the student.
     - Fail-closed: execution fails closed if Docker is unavailable. Containers and temporary folders are purged immediately after execution.

---

## Authentication & Personal Account Architecture

Debug Dojo implements authentic, server-side session authentication with strict privacy boundaries:

### 1. Password Security
- **Argon2id Hashing**: Passwords are securely hashed with Argon2id (RFC 9106) using a 16-byte random salt, 64 MB memory cost (`m=65536`), 3 time iterations (`t=3`), and 4 parallel threads (`p=4`). An automatic scrypt fallback is provided.
- **Zero Plaintext Exposure**: Passwords are never stored in plaintext, never logged, and never included in API responses or frontend payloads.
- **Generic Invalid Credentials**: Login failures return a general `"Invalid email or password."` error to prevent account enumeration.

### 2. Session Management & CSRF Defense
- **HttpOnly Cookies**: Sessions are issued via an `HttpOnly`, `SameSite=Lax`, path-restricted (`/`) cookie named `dojo_session` with a 7-day server-authoritative lifespan.
- **Dynamic Secure Flag**: Automatically switches to `Secure=True` in production or over HTTPS, while permitting seamless local HTTP development.
- **Server-Side Revocation**: Logging out revokes the session token in the SQLite `user_sessions` table and deletes the client cookie.
- **CSRF Protection**: All state-changing requests (`POST`, `PATCH`, `DELETE`) with session cookies validate the `Origin` / `Referer` header against the expected host.
- **Brute-Force Rate Limiting**: In-memory sliding-window rate limiting throttles signup and login attempts (max 15 attempts per minute per IP) to prevent automated credential stuffing.

### 3. User Data Isolation
- **Server-Derived Identity**: The active user is always derived from the validated server-side session (`Depends(get_current_user)`). Client-supplied IDs in `localStorage` or request parameters are never trusted as proof of identity.
- **Authorization Boundaries**:
  - `GET /api/account` and `PATCH /api/account` restrict viewing and updating to the active user's record.
  - `GET /api/learner/{id}` blocks unauthorized third-party inspection of user profiles.
  - Examination attempts (`/api/exam/{attempt_id}`) and submissions (`/api/submit`) enforce ownership: User A cannot inspect, test, or submit User B's attempts.

### 4. Authentication Endpoints

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| `POST` | `/api/auth/signup` | Register new user (Argon2id hash, normalized email) and set session cookie | No |
| `POST` | `/api/auth/login` | Verify credentials, return user profile, and issue session cookie | No |
| `POST` | `/api/auth/logout` | Revoke active session in SQLite and clear cookie | Yes |
| `GET` | `/api/auth/me` | Return currently authenticated user profile | Yes |
| `GET` | `/api/account` | Return personal details and authentic learning statistics | Yes |
| `PATCH` | `/api/account` | Update permitted profile fields (`full_name`, `age`) | Yes |
| `POST` | `/api/account/change-password` | Verify current password and securely hash new password | Yes |

---

## Running the Automated Test Suites

We have comprehensive automated test suites covering all platform layers (518 tests across 8 suites, 100% passing):

```bash
# 1. Phase 2: Challenge Catalogue & Endpoint checks (162 tests)
venv/bin/python3 test_api.py

# 2. Phase 3: Docker Sandbox & Test Outcomes (38 tests)
venv/bin/python3 test_phase3.py

# 3. Phase 4: Explanations, Hints & Mistake Taxonomy (48 tests)
venv/bin/python3 test_phase4.py

# 4. Phase 5: Learner Progress, Mastery & Recommendations (42 tests)
venv/bin/python3 test_phase5.py

# 5. Phase 6: Full UI & Navigation Integration (43 tests)
venv/bin/python3 test_phase6.py

# 6. Phase 7: Examination Panel, Timers, Anti-Paste & Docker Sandbox (64 tests)
venv/bin/python3 test_phase7_exam.py

# 7. Phase 8: Authentication, Sessions, Account Profile & Data Isolation (64 tests)
venv/bin/python3 test_auth_and_account.py

# 8. Phase 9: Per-Test Outcomes, Resource Limits & Frontend Table (57 tests)
venv/bin/python3 test_per_test_outcomes.py
```
*(All 518 tests passing!)*

---

## Tech Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| Backend | Python 3.12+ + FastAPI | High-performance ASGI framework with type safety and Pydantic validation |
| Authentication | Argon2id (`argon2-cffi`) | State-of-the-art password hashing resistant to GPU and side-channel attacks |
| Sessions | Server-side SQLite + HttpOnly Cookie | Safe against XSS script access and client tampering |
| Sandbox | Docker (`python:3.12-slim`) | Disposable containers, read-only root, no network, memory/CPU bounded |
| Database | SQLite | Relational persistence for users, sessions, submissions, and exam attempts |
| UI Animation | Anime.js (`v3.2.2`) | Smooth, restrained transitions, zero external bundle overhead |
| Frontend | HTML5 + Modern CSS + Vanilla JS | Fast, responsive, dark developer aesthetic, zero build step |

---

Made with ☕ and 🐛 at Hackathon 2026.

