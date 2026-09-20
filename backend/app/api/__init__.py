from fastapi import APIRouter

from app.api import analysis, catchment, chat, explain, hotspots, meta, ml, polygon, recommend, reports, sites

api_router = APIRouter()
api_router.include_router(meta.router, tags=["meta"])
api_router.include_router(ml.router, tags=["ml"])
api_router.include_router(sites.router, tags=["sites"])
api_router.include_router(analysis.router, tags=["analysis"])
api_router.include_router(hotspots.router, tags=["hotspots"])
api_router.include_router(recommend.router, tags=["recommend"])
api_router.include_router(polygon.router, tags=["polygon"])
api_router.include_router(catchment.router, tags=["catchment"])
api_router.include_router(chat.router, tags=["assistant"])
api_router.include_router(explain.router, tags=["ai"])
api_router.include_router(reports.router, tags=["reports"])
