

from fastapi import FastAPI

from .auth.routes import router as auth_router
from .documents.routes import router as documents_router

app = FastAPI(
    title="TrustVault API",
    description="Secure Document Access and Audit Platform",
    version="1.0.0",
)

app.include_router(auth_router)
app.include_router(documents_router)


@app.get("/")
def home():
    return {
        "message": "Welcome to TrustVault",
        "status": "running",
    }


@app.get("/health")
def health_check():
    return {"status": "healthy"}