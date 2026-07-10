from fastapi import APIRouter

from app.api.routes.auth import router as auth_router
from app.api.routes.billing import router as billing_router
from app.api.routes.hardware import router as hardware_router
from app.api.routes.history import router as history_router
from app.api.routes.learning import router as learning_router
from app.api.routes.realtime import router as realtime_router
from app.api.routes.realtime_voice import router as realtime_voice_router
from app.api.routes.reviews import router as reviews_router
from app.api.routes.simulations import router as simulations_router
from app.api.routes.system import router as system_router
from app.api.routes.user_twin import router as user_twin_router
from app.api.routes.voice_profiles import router as voice_profiles_router

api_router = APIRouter()
api_router.include_router(system_router)
api_router.include_router(auth_router)
api_router.include_router(learning_router)
api_router.include_router(simulations_router)
api_router.include_router(voice_profiles_router)
api_router.include_router(realtime_router)
api_router.include_router(realtime_voice_router)
api_router.include_router(reviews_router)
api_router.include_router(history_router)
api_router.include_router(hardware_router)
api_router.include_router(billing_router)
api_router.include_router(user_twin_router)
