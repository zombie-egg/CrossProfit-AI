from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.routes import public_router, router
from .api.auth import router as auth_router
from .api.merchant import router as merchant_router
from .config import settings
from .database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not settings.secret_key and settings.cookie_secure:
        raise RuntimeError("CROSSPROFIT_SECRET_KEY must be configured in production")
    init_db()
    yield


app = FastAPI(title="CrossProfit AI API", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(public_router)
app.include_router(auth_router)
app.include_router(merchant_router)
app.include_router(router)
