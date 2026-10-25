



from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import models as _models
from .auth.routes import router as auth_router
from .database import Base, engine
from .documents.routes import router as documents_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="TrustVault API",
    description="Secure Document Access and Audit Platform",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://trust-vault-mu-snowy.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
