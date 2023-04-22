import traceback

from fastapi import FastAPI, APIRouter, Request, Response
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import StreamingResponse

from .bays import router as bays_router
from .device import router as device_router
from .item_history import router as item_history_router
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
router.include_router(device_router, prefix='/api/v1/depot')
router.include_router(item_history_router, prefix='/api/v1/depot')
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


@app.middleware('http')
async def catch_exceptions_middleware(request: Request, call_next):
    try:
        resp = await call_next(request)
        if isinstance(resp, StreamingResponse):
            if resp.status_code >= 400:
                print(f"Header: {resp.headers}")

                async def stream_print(orig_iterator):
                    async for chunk in orig_iterator:
                        if len(chunk) > 1024:
                            print(f"Body: {chunk[:1024]}")
                        else:
                            print(f"Body: {chunk}")
                        yield chunk

                resp.body_iterator = stream_print(resp.body_iterator)
        elif isinstance(resp, Response):
            if resp.status_code >= 400:
                print(f"Header: {resp.headers}")
                print(f"Body: {resp.body!r}")
        else:
            print(f"Unknown response type: {type(resp)}")
        return resp
    except Exception:
        traceback.print_exc()
        return Response("Internal server error", status_code=500)
