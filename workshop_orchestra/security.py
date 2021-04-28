"""security for app
"""
from fastapi import Depends, HTTPException
from fastapi.security import APIKeyHeader
from starlette import status
from .config import config

X_API_KEY = APIKeyHeader(name="X-API-Key")


def check_authentication_header(x_api_key: str = Depends(X_API_KEY)):
    """takes the X-API-Key header and converts it into the matching user object from the database"""

    # this is where the SQL query for converting the API key into a user_id will go
    if x_api_key == config("API_KEY", default="123456"):
        # if passes validation check, return user data for API Key
        # future DB query will go here
        return True
    # else raise 401
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid API Key",
    )
