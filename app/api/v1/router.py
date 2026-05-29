# app/api/v1/router.py
from fastapi import APIRouter
from app.api.v1.endpoints import auth, health, pdf, users
from app.api.v1.endpoints.admin import router as admin_router

api_router = APIRouter()
api_router.include_router(auth.router,   prefix="/auth",   tags=["Auth"])
api_router.include_router(health.router, prefix="/health", tags=["Health"])
api_router.include_router(pdf.router,    prefix="/pdf",    tags=["PDF"])
api_router.include_router(users.router,  prefix="/users",  tags=["Users"])
api_router.include_router(admin_router,  prefix="/admin")