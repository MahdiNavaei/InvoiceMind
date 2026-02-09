from __future__ import annotations

import base64
import hashlib
import hmac
import json
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status

from app.config import settings

ROLE_ALIASES = {
    "admin": "Admin",
    "reviewer": "Reviewer",
    "reader": "Viewer",
    "viewer": "Viewer",
    "approver": "Approver",
    "auditor": "Auditor",
    "service": "Admin",
}

_USERS = {
    "admin": {
        "password": "admin123",
        "roles": ["Admin", "Approver", "Reviewer", "Viewer", "Auditor"],
        "tenant_id": settings.default_tenant_id,
        "mfa_verified": True,
    },
    "reviewer": {
        "password": "review123",
        "roles": ["Reviewer", "Viewer"],
        "tenant_id": settings.default_tenant_id,
        "mfa_verified": False,
    },
    "approver": {
        "password": "approve123",
        "roles": ["Approver", "Viewer"],
        "tenant_id": settings.default_tenant_id,
        "mfa_verified": True,
    },
    "viewer": {
        "password": "viewer123",
        "roles": ["Viewer"],
        "tenant_id": settings.default_tenant_id,
        "mfa_verified": False,
    },
    "auditor": {
        "password": "audit123",
        "roles": ["Auditor", "Viewer"],
        "tenant_id": settings.default_tenant_id,
        "mfa_verified": False,
    },
    # Legacy compatibility accounts
    "reader": {
        "password": "reader123",
        "roles": ["Viewer"],
        "tenant_id": settings.default_tenant_id,
        "mfa_verified": False,
    },
    "service": {
        "password": "service123",
        "roles": ["Admin"],
        "tenant_id": settings.default_tenant_id,
        "mfa_verified": True,
    },
}


def normalize_role(role: str) -> str:
    return ROLE_ALIASES.get(role.lower(), role)


def normalize_roles(roles: list[str]) -> list[str]:
    seen = set()
    out: list[str] = []
    for role in roles:
        normalized = normalize_role(role)
        if normalized in seen:
            continue
        seen.add(normalized)
        out.append(normalized)
    return out


def authenticate_user(username: str, password: str) -> dict | None:
    user = _USERS.get(username)
    if not user or user["password"] != password:
        return None
    return {
        "username": username,
        "roles": normalize_roles(user["roles"]),
        "tenant_id": user["tenant_id"],
        "mfa_verified": bool(user.get("mfa_verified", False)),
    }


def create_access_token(username: str, roles: list[str], *, tenant_id: str, mfa_verified: bool = False) -> str:
    exp = datetime.now(timezone.utc) + timedelta(minutes=settings.token_exp_minutes)
    payload = {
        "sub": username,
        "roles": normalize_roles(roles),
        "tenant_id": tenant_id,
        "mfa_verified": bool(mfa_verified),
        "exp": exp.isoformat(),
    }
    raw = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    b64 = base64.urlsafe_b64encode(raw).decode("utf-8")
    sig = hmac.new(settings.jwt_secret.encode("utf-8"), b64.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{b64}.{sig}"


def _decode_token(token: str) -> dict:
    try:
        b64, sig = token.split(".", 1)
        expected = hmac.new(settings.jwt_secret.encode("utf-8"), b64.encode("utf-8"), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected):
            raise ValueError("invalid signature")
        raw = base64.urlsafe_b64decode(b64.encode("utf-8"))
        payload = json.loads(raw.decode("utf-8"))
        exp = datetime.fromisoformat(payload["exp"])
        if datetime.now(timezone.utc) > exp:
            raise ValueError("token expired")
        return payload
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc


def get_current_user(authorization: Annotated[str | None, Header()] = None) -> dict:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
    token = authorization.split(" ", 1)[1].strip()
    payload = _decode_token(token)
    return {
        "username": payload.get("sub", "unknown"),
        "roles": normalize_roles(payload.get("roles", [])),
        "tenant_id": payload.get("tenant_id", settings.default_tenant_id),
        "mfa_verified": bool(payload.get("mfa_verified", False)),
    }


def require_roles(*required: str, require_mfa: bool = False):
    required_roles = {normalize_role(role) for role in required}

    def dependency(user: dict = Depends(get_current_user)) -> dict:
        roles = set(normalize_roles(user.get("roles", [])))
        if required_roles and not roles.intersection(required_roles):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
        if require_mfa and not bool(user.get("mfa_verified")):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="MFA required")
        return user

    return dependency
