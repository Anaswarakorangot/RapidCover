from fastapi import APIRouter

from app.api.partners import router as partners_router
from app.api.policies import router as policies_router
from app.api.claims import router as claims_router
from app.api.zones import router as zones_router
from app.api.triggers import router as triggers_router
from app.api.admin import router as admin_router
from app.api.notifications import router as notifications_router

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(partners_router)
api_router.include_router(policies_router)
api_router.include_router(claims_router)
api_router.include_router(zones_router)
api_router.include_router(triggers_router)
api_router.include_router(admin_router)
api_router.include_router(notifications_router)
