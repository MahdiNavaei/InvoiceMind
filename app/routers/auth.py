from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException, status

from app.i18n import pick_lang, t
from app.schemas import TokenRequest, TokenResponse
from app.security import authenticate_user, create_access_token

router = APIRouter(prefix="/v1/auth", tags=["auth"])


@router.post("/token", response_model=TokenResponse)
def issue_token(payload: TokenRequest, accept_language: str | None = Header(default=None)):
    lang = pick_lang(accept_language)
    user = authenticate_user(payload.username, payload.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=t("unauthorized", lang))
    token = create_access_token(
        user["username"],
        user["roles"],
        tenant_id=user["tenant_id"],
        mfa_verified=bool(user.get("mfa_verified", False)),
    )
    return TokenResponse(access_token=token, message=t("token_issued", lang))
