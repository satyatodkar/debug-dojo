"""
Debug Dojo – Phase 2 Backend
==============================
FastAPI application that:
  • Serves the static frontend from the /static folder.
  • Exposes GET /api/health so the frontend can verify the server is running.
  • Exposes GET /api/challenges and GET /api/challenges/{id} for the
    challenge catalogue (Phase 2).

Nothing here runs learner code – that is saved for Phase 3.
"""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from routers.challenges import router as challenges_router
from routers.submit import router as submit_router
from routers.hints import router as hints_router
from routers.learner import router as learner_router
from routers.exam import router as exam_router
from routers.auth import router as auth_router
from routers.account import router as account_router

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = FastAPI(title="Debug Dojo", version="0.8.0")

# Register routes
app.include_router(auth_router)
app.include_router(account_router)
app.include_router(challenges_router)
app.include_router(submit_router)
app.include_router(hints_router)
app.include_router(learner_router)
app.include_router(exam_router)

# Serve every file inside the "static/" folder automatically.
# e.g. http://localhost:8000/static/style.css
app.mount("/static", StaticFiles(directory="static"), name="static")


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/")
@app.get("/home")
@app.get("/login")
@app.get("/signup")
@app.get("/account")
@app.get("/challenges")
@app.get("/workspace")
@app.get("/dashboard")
async def homepage():
    """Return the main single-page application HTML page."""
    return FileResponse("static/index.html")


@app.get("/exam")
async def exam_page():
    """Return the separate examination HTML page."""
    return FileResponse("static/exam.html")


@app.get("/api/health")
async def health_check():
    """
    Simple health endpoint.
    The frontend calls this to confirm the backend is alive.
    Returns: {"status": "ok"}
    """
    return JSONResponse(content={"status": "ok"})
