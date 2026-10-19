import base64
import binascii
import time

from fastapi import Header, HTTPException

from app.schemas import AuthenticatedIdentity

LEGACY_SECRET = "WORKSHOP_SECRET_2026"
INVALID_TOKEN_MESSAGE = "Invalid token"


def legacy_identity(authorization: str = Header(default="")) -> AuthenticatedIdentity:
    try:
        token = authorization.replace("Bearer ", "")
        decoded = base64.b64decode(token).decode("utf-8")
        parts = decoded.split("|")
        if len(parts) != 4 or parts[3] != LEGACY_SECRET or int(parts[2]) < int(time.time()):
            raise ValueError("invalid token")
        return AuthenticatedIdentity(username=parts[0], role=parts[1])
    except (binascii.Error, UnicodeError, ValueError) as error:
        raise HTTPException(status_code=401, detail=INVALID_TOKEN_MESSAGE) from error