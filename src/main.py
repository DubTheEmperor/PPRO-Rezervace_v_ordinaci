import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from src.config import settings
from src.infrastructure.database import engine, Base, SessionLocal
from src.infrastructure.seed import seed_initial_users, seed_initial_patients
from src.presentation.api.auth_router import router as auth_router
from src.presentation.api.user_router import router as user_router
from src.presentation.api.patient_router import router as patient_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Inicializace databáze a seed dat při startu
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_initial_users(db)
        seed_initial_patients(db)
    finally:
        db.close()
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Informační a rezervační systém pro lékařskou praxi (Varianta A – Ordinace Na Vyhlídce). Předmět PPRO, ZS 2026/2027.",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registrace API routerů
app.include_router(auth_router, prefix=settings.API_V1_PREFIX)
app.include_router(user_router, prefix=settings.API_V1_PREFIX)
app.include_router(patient_router, prefix=settings.API_V1_PREFIX)


@app.get("/", include_in_schema=False)
def serve_web_ui():
    """Servíruje webové administrační a přihlašovací rozhraní."""
    index_path = os.path.join(os.path.dirname(__file__), "presentation", "web", "index.html")
    return FileResponse(index_path)


@app.get("/health", tags=["Healthcheck"])
def healthcheck():
    """Zdravotní stav aplikace."""
    return {"status": "ok", "app": settings.PROJECT_NAME, "version": settings.VERSION}
