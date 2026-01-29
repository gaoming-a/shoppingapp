import hashlib
import secrets

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from .database import SessionLocal
from .models import Merchant


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def create_token() -> str:
    return secrets.token_hex(16)


def get_current_merchant(
    x_merchant_token: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> Merchant:
    if not x_merchant_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing token")
    merchant = (
        db.query(Merchant).filter(Merchant.token == x_merchant_token).one_or_none()
    )
    if not merchant:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    return merchant
