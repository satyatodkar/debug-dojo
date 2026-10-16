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

---

## Running the Test Suites

We have comprehensive automated tests across all 5 completed phases:

```bash
# Phase 2: Challenge Catalogue & Endpoint checks (162 tests)
venv/bin/python3 test_api.py

# Phase 3: Docker Sandbox & Test Outcomes (38 tests)
venv/bin/python3 test_phase3.py

# Phase 4: Explanations, Hints & Mistake Taxonomy (48 tests)
venv/bin/python3 test_phase4.py

# Phase 5: Learner Progress, Mastery & Recommendations (42 tests)
venv/bin/python3 test_phase5.py

# Phase 6: Full UI & Navigation Integration (43 tests)
venv/bin/python3 test_phase6.py
```
*(All 333 tests passing!)*

---

## Tech Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| Backend | Python + FastAPI | Fast to write, type-safe with Pydantic, auto-generates API docs |
| Server | Uvicorn | High-performance ASGI server |
| Sandbox | Docker (`python:3.12-slim`) | Unprivileged, read-only root, no network, memory/CPU bounded |
| Database | SQLite | Lightweight zero-config relational storage for learner history |
| Frontend | HTML5 + CSS3 + Vanilla JS | Fast, zero build step, dark developer-tool design, responsive & accessible |

---

Made with ☕ and 🐛 at Hackathon 2026.
