"""
Auth0 JWT Verification Dependency.
Validates RS256-signed JWTs against Auth0's JWKS endpoint.
Checks subscription status from the users table.
FR-007, Security Architecture: Authentication & Authorization.
"""

from __future__ import annotations

import logging
from functools import lru_cache

import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from jose.exceptions import ExpiredSignatureError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models import User

logger = logging.getLogger(__name__)

_security = HTTPBearer()


@lru_cache(maxsize=1)
def _get_jwks() -> dict:  # type: ignore[type-arg]
    """
    Fetches Auth0's JWKS (JSON Web Key Set) for RS256 signature verification.
    Cached for the lifetime of the process to avoid redundant HTTP calls.
    """
    url = f"https://{settings.AUTH0_DOMAIN}/.well-known/jwks.json"
    try:
        response = httpx.get(url, timeout=10)
        response.raise_for_status()
        return response.json()  # type: ignore[no-any-return]
    except httpx.HTTPError as exc:
        logger.error("Failed to fetch JWKS from Auth0: %s", exc)
        raise RuntimeError("Unable to fetch Auth0 JWKS") from exc


def _decode_jwt(token: str) -> dict:  # type: ignore[type-arg]
    """
    Decodes and verifies an Auth0 RS256 JWT.
    Raises HTTPException 401 on any verification failure.
    """
    jwks = _get_jwks()

    try:
        unverified_header = jwt.get_unverified_header(token)
    except JWTError as exc:
        logger.warning("Malformed JWT header: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token header",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    rsa_key: dict = {}  # type: ignore[type-arg]
    for key in jwks.get("keys", []):
        if key.get("kid") == unverified_header.get("kid"):
            rsa_key = {
                "kty": key["kty"],
                "kid": key["kid"],
                "use": key["use"],
                "n": key["n"],
                "e": key["e"],
            }
            break

    if not rsa_key:
        logger.warning("No matching JWKS key found for token KID")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unable to find appropriate key",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = jwt.decode(
            token,
            rsa_key,
            algorithms=["RS256"],
            audience=settings.AUTH0_AUDIENCE,
            issuer=f"https://{settings.AUTH0_DOMAIN}/",
        )
        return payload  # type: ignore[return-value]
    except ExpiredSignatureError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except JWTError as exc:
        logger.warning("JWT verification failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token verification failed",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


class AuthTokenClaims:
    """Typed wrapper for validated Auth0 JWT claims."""

    def __init__(self, payload: dict) -> None:  # type: ignore[type-arg]
        self.sub: str = payload["sub"]
        self.email: str = payload.get("email", "")
        self.raw: dict = payload  # type: ignore[type-arg]


async def require_auth(
    credentials: HTTPAuthorizationCredentials = Depends(_security),
) -> AuthTokenClaims:
    """
    FastAPI dependency: validates Bearer JWT and returns typed claims.
    Returns HTTP 401 on any auth failure.
    """
    claims = _decode_jwt(credentials.credentials)
    return AuthTokenClaims(claims)


async def require_subscription(
    auth: AuthTokenClaims = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
) -> AuthTokenClaims:
    """
    FastAPI dependency: validates JWT and checks active Stripe subscription.
    Returns HTTP 403 if the user is not subscribed.
    Row-level isolation: only accesses the authenticated user's record.
    """
    result = await db.execute(select(User).where(User.id == auth.sub))
    user = result.scalar_one_or_none()

    if user is None:
        # Auto-provision user on first authenticated request
        user = User(id=auth.sub, email=auth.email, is_subscribed=False)
        db.add(user)
        await db.flush()

    if not user.is_subscribed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Active subscription required to access this feature.",
        )

    return auth
