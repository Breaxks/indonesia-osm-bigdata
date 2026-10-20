"""
FastAPI entrypoint.

Run with:
    uvicorn app.main:app --reload

Swagger docs available at /docs once running.
"""
from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import graph, health, ml, overview, regions, roads
from app.config import API_TITLE, API_VERSION, CORS_ORIGINS, RAW_PBF_FILE
from app.services.data_service import NotProcessedError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("indonesia-osm-api")

app = FastAPI(
    title=API_TITLE,
    version=API_VERSION,
    description=(
        "Big Data analysis of road infrastructure and accessibility in "
        "Indonesia, derived from OpenStreetMap (Geofabrik extract). "
        "See /api/health and /api/pipeline-status for dataset processing state."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(NotProcessedError)
async def not_processed_handler(request: Request, exc: NotProcessedError):
    return JSONResponse(status_code=503, content={"detail": str(exc)})


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error on %s", request.url)
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred. Check the backend logs."},
    )


app.include_router(health.router)
app.include_router(overview.router)
app.include_router(roads.router)
app.include_router(regions.router)
app.include_router(ml.router)
app.include_router(graph.router)


@app.on_event("startup")
async def startup_message():
    logger.info("Indonesia Road Infrastructure API starting up.")
    if not RAW_PBF_FILE.exists():
        logger.warning(
            "Raw PBF file not found at %s. Place 'indonesia-latest.osm.pbf' "
            "there and run the processing pipeline before expecting real data.",
            RAW_PBF_FILE,
        )
