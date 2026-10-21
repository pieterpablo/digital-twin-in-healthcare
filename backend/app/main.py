from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .api.tumor import router as tumor_router

from .api.bmi import router as bmi_router

app = FastAPI(
    title="BMI Example API",
    description="Example application for the Digital Twin course",
    version="1.0.0",
)

# Allow the Vite development server to access the API
# This is necessary for local development, but should be removed in production
# In production, replace this with a static mount of the frontend build directory into the FastAPI app
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API endpoints
app.include_router(bmi_router, prefix="/api")
app.include_router(tumor_router, prefix="/api")


@app.get("/")
def root():
    return {"message": "BMI API is running"}

