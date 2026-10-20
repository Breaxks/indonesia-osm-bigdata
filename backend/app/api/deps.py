from fastapi import HTTPException

from app.services.data_service import NotProcessedError


def run_or_503(fn, *args, **kwargs):
    """Run a data-service function; convert NotProcessedError to HTTP 503."""
    try:
        return fn(*args, **kwargs)
    except NotProcessedError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
