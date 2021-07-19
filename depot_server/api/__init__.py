from fastapi import FastAPI, APIRouter
from starlette.middleware.cors import CORSMiddleware

from .bays import router as bays_router
from .items import router as items_router
from .report_elements import router as report_elements_router
from .report_profiles import router as report_profiles_router
from .reservations import router as reservations_router
from .pictures import router as pictures_router
from .users import router as users_router
from depot_server.config import config
from depot_server.db import startup as db_startup, shutdown as db_shutdown

from depot_server.mail.return_reservation_mail import startup as mail_cron_startup, shutdown as mail_cron_shutdown

router = APIRouter()
router.include_router(bays_router, prefix='/api/v1/depot')
router.include_router(items_router, prefix='/api/v1/depot')
router.include_router(report_elements_router, prefix='/api/v1/depot')
router.include_router(report_profiles_router, prefix='/api/v1/depot')
router.include_router(reservations_router, prefix='/api/v1/depot')
router.include_router(pictures_router, prefix='/api/v1/depot')
router.include_router(users_router, prefix='/api/v1/depot')


@router.on_event('startup')
async def startup():
    await db_startup()
    await mail_cron_startup()


@router.on_event('shutdown')
async def shutdown():
    await mail_cron_shutdown()
    await db_shutdown()


app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.allow_origins,
    allow_credentials=True,
    allow_methods=['GET', 'POST', 'PUT', 'PATCH', 'DELETE'],
    allow_headers=['*'],
)

app.include_router(router)
