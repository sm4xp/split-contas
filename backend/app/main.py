import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from .database import engine, Base
from .routers import auth, sessoes

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Divisor de Contas API", version="1.0.0")

FRONTEND_ORIGIN = os.getenv("FRONTEND_URL", "http://localhost:5500")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(sessoes.router)


@app.get("/health")
def health():
    return {"status": "ok"}


# Serve frontend in production (Railway)
frontend_path = os.path.join(os.path.dirname(__file__), "..", "..", "frontend")
if os.path.isdir(frontend_path):
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")

    @app.get("/verify")
    def verify_page():
        return FileResponse(os.path.join(frontend_path, "index.html"))

    @app.get("/", include_in_schema=False)
    def root():
        return FileResponse(os.path.join(frontend_path, "index.html"))
