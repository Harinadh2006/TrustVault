

from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jwt.exceptions import InvalidTokenError
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import User
from .security import decode_access_token

bearer_scheme = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    credentials_error = HTTPException(
        status_code=401,
        detail="Invalid or expired authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_access_token(credentials.credentials)
        subject = payload.get("sub")

        if not isinstance(subject, str) or not subject.isdigit():
            raise credentials_error

        user_id = int(subject)

    except (InvalidTokenError, ValueError):
        raise credentials_error from None

    user = db.get(User, user_id)

    if user is None or not user.is_active:
        raise credentials_error

    return user
