import os

import urllib3

from app.schemas import BackendHealthResponse

DEFAULT_AUTH_HEALTH_URL = "http://localhost:8080/q/health"
BACKEND_HEALTH_TIMEOUT_SECONDS = 3.0
BACKEND_HEALTH_FAILURE_MESSAGE = "Backend health request failed"
BACKEND_REQUEST_ERRORS = (urllib3.exceptions.HTTPError, OSError, UnicodeDecodeError)


def get_backend_health(username: str) -> BackendHealthResponse:
    url = os.getenv("AUTH_HEALTH_URL", DEFAULT_AUTH_HEALTH_URL)
    try:
        response = urllib3.PoolManager().request(
            "GET",
            url,
            timeout=BACKEND_HEALTH_TIMEOUT_SECONDS,
        )
    except BACKEND_REQUEST_ERRORS:
        return BackendHealthResponse(
            requestedBy=username,
            status=0,
            body=BACKEND_HEALTH_FAILURE_MESSAGE,
        )

    return BackendHealthResponse(
        requestedBy=username,
        status=response.status,
        body=response.data.decode("utf-8"),
    )