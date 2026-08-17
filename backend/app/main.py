from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.core.config import settings
from app.api.routes import router

app = FastAPI(title="YouTube Video RAG Assistant", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.include_router(router)

# Docker production image places the built Vite app here. API routes are registered first.
if settings.frontend_dist_dir.exists():
    app.mount("/", StaticFiles(directory=str(settings.frontend_dist_dir), html=True), name="frontend")
