from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .api.predictions import router as tumor_router
from fastapi.staticfiles import StaticFiles
from pathlib import Path



app = FastAPI(
    title="Digital Twin API",
    description="Example application for the Digital Twin course",
    version="1.0.0",
)

# Allow the Vite development server to access the API
# This is necessary for local development, but should be removed in production
# In production, replace this with a static mount of the frontend build directory into the FastAPI app
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API endpoints

app.include_router(tumor_router, prefix="/api")


app.mount('/', StaticFiles(directory=Path(__file__).resolve().parents[2] / 'frontend', html=True), name='frontend')

