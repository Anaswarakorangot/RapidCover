from fastapi import APIRouter

from app.api.partners import router as partners_router
from app.api.experience import router as experience_router   # NEW – Person 1 Phase 2
from app.api.policies import router as policies_router
from app.api.payments import router as payments_router  # Stripe integration
from app.api.claims import router as claims_router
from app.api.zones import router as zones_router
from app.api.triggers import router as triggers_router
from app.api.admin import router as admin_router
from app.api.admin_panel import router as admin_panel_router
from app.api.admin_drills import router as admin_drills_router
from app.api.notifications import router as notifications_router

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(partners_router)
# experience_router shares the /partners prefix; mount after partners_router
api_router.include_router(experience_router)
api_router.include_router(policies_router)
api_router.include_router(payments_router)
api_router.include_router(claims_router)
api_router.include_router(zones_router)
api_router.include_router(triggers_router)
api_router.include_router(admin_router)
api_router.include_router(admin_panel_router)
api_router.include_router(admin_drills_router)
api_router.include_router(notifications_router)
