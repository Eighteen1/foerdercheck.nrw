from fastapi import Request, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
import os
from typing import List

security = HTTPBearer()

# List of allowed developer emails
ALLOWED_DEVELOPER_EMAILS = os.getenv("ALLOWED_DEVELOPER_EMAILS", "").split(",")

async def verify_jwt(request: Request) -> dict:
    try:
        credentials: HTTPAuthorizationCredentials = await security(request)
        if not credentials:
            raise HTTPException(status_code=401, detail="No credentials provided")
        
        token = credentials.credentials
        payload = jwt.decode(
            token,
            os.getenv("SUPABASE_JWT_SECRET"),
            algorithms=["HS256"]
        )
        
        # Check if the user's email is in the allowed list
        user_email = payload.get("email")
        if user_email not in ALLOWED_DEVELOPER_EMAILS:
            raise HTTPException(status_code=403, detail="Access denied")
        
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e)) 