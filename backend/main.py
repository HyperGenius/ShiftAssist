# backend/main.py
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers.workers import router as workers_router

app = FastAPI(title="ShiftAssist API", redirect_slashes=False)

# --- CORS設定 ---
# ローカル環境と本番環境のオリジンを設定
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

# 本番環境のVercelドメインを追加
allowed_origins_env = os.getenv("ALLOWED_ORIGINS", "")
if allowed_origins_env:
    # カンマ区切りで複数のオリジンを追加可能
    origins.extend(
        [origin.strip() for origin in allowed_origins_env.split(",") if origin.strip()]
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Routerの登録 ---
app.include_router(workers_router)

# --- Response Schemas ---

# --- API Endpoints ---


@app.get("/health")
def health() -> dict[str, str]:
    """ヘルスチェック."""
    return {"status": "ok", "message": "ShiftAssist API is running"}
