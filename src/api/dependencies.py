"""FastAPI dependency injection."""

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import APIKeyHeader

from src.config import Settings, get_settings

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(
    request: Request,
    api_key: str = Depends(api_key_header),
    settings: Settings = Depends(get_settings),
) -> str:
    """Verify API key from request header.

    Args:
        request: FastAPI request object
        api_key: API key from header
        settings: Application settings

    Returns:
        str: Validated API key

    Raises:
        HTTPException: If API key is invalid or missing

    """
    if not settings.api_key:
        # Development mode - no API key required
        return "dev"

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    if api_key != settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    return api_key
