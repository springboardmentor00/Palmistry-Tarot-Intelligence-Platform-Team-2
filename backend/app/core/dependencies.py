from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.core.security import verify_token


oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/auth/login"
)


def get_current_user(
    token: str = Depends(oauth2_scheme)
):

    payload = verify_token(token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )

    return payload


def require_role(role: str):

    def role_checker(
        current_user=Depends(get_current_user)
    ):

        if current_user["role"] != role:

            raise HTTPException(
                status_code=403,
                detail="Access Denied"
            )

        return current_user

    return role_checker