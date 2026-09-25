from __future__ import annotations

import base64
import hashlib
import hmac
import re
import secrets
import smtplib
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage

from cryptography.fernet import Fernet
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..models import LoginFailure, Merchant, MerchantSession, VerificationCode

router = APIRouter(prefix="/auth", tags=["auth"])
SECRET = (settings.secret_key or secrets.token_urlsafe(48)).encode()
FERNET = Fernet(base64.urlsafe_b64encode(hashlib.sha256(SECRET + b"encryption").digest()))
COOKIE_NAME = "crossprofit_session"


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1)
    return f"scrypt${salt.hex()}${digest.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, salt, digest = encoded.split("$")
        if algorithm != "scrypt":
            return False
        actual = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=2**14, r=8, p=1)
        return hmac.compare_digest(actual, bytes.fromhex(digest))
    except (ValueError, TypeError):
        return False


def encrypt_secret(value: str | None) -> str | None:
    return FERNET.encrypt(value.encode()).decode() if value else None


def decrypt_secret(value: str | None) -> str | None:
    return FERNET.decrypt(value.encode()).decode() if value else None


def code_digest(email: str, purpose: str, code: str) -> str:
    return hmac.new(SECRET, f"{email}:{purpose}:{code}".encode(), hashlib.sha256).hexdigest()


class EmailPayload(BaseModel):
    email: str = Field(max_length=254)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        value = value.strip().lower()
        if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", value):
            raise ValueError("邮箱格式不正确")
        return value


class CodeRequest(EmailPayload):
    purpose: str

    @field_validator("purpose")
    @classmethod
    def validate_purpose(cls, value: str) -> str:
        if value not in {"register", "login", "reset"}:
            raise ValueError("验证码用途不正确")
        return value


class PasswordLogin(EmailPayload):
    password: str


class CodeLogin(EmailPayload):
    code: str = Field(min_length=6, max_length=6)


class Register(CodeLogin):
    password: str = Field(min_length=8, max_length=128)


class ResetPassword(Register):
    pass


class LocaleUpdate(BaseModel):
    locale: str

    @field_validator("locale")
    @classmethod
    def validate_locale(cls, value: str) -> str:
        if value not in {"zh", "en"}:
            raise ValueError("不支持的语言")
        return value


def _send_code(email: str, code: str, purpose: str) -> None:
    if not settings.qq_email or not settings.qq_email_auth_code:
        raise HTTPException(503, "邮件服务尚未配置")
    message = EmailMessage()
    message["From"] = settings.qq_email
    message["To"] = email
    message["Subject"] = "CrossProfit AI verification code"
    message.set_content(f"Your CrossProfit AI {purpose} code is {code}. It expires in 10 minutes.\n\nCrossProfit AI {purpose} 验证码：{code}，10 分钟内有效。")
    try:
        with smtplib.SMTP_SSL("smtp.qq.com", 465, timeout=10) as smtp:
            smtp.login(settings.qq_email, settings.qq_email_auth_code)
            smtp.send_message(message)
    except (smtplib.SMTPException, OSError) as exc:
        raise HTTPException(503, "验证码邮件发送失败，请稍后重试") from exc


def _consume_code(db: Session, email: str, purpose: str, code: str) -> None:
    row = db.scalar(select(VerificationCode).where(VerificationCode.email == email, VerificationCode.purpose == purpose, VerificationCode.consumed.is_(False)).order_by(VerificationCode.id.desc()))
    if row is None or row.expires_at < utcnow() or row.attempts >= 5:
        raise HTTPException(400, "验证码无效或已过期")
    row.attempts += 1
    if not hmac.compare_digest(row.code_hash, code_digest(email, purpose, code)):
        db.commit()
        raise HTTPException(400, "验证码无效或已过期")
    row.consumed = True
    db.flush()


def _issue_session(db: Session, response: Response, merchant: Merchant) -> dict[str, str | int]:
    token = secrets.token_urlsafe(32)
    db.add(MerchantSession(merchant_id=merchant.id, token_hash=hashlib.sha256(token.encode()).hexdigest(), expires_at=utcnow() + timedelta(days=30)))
    db.commit()
    response.set_cookie(COOKIE_NAME, token, max_age=30 * 86400, httponly=True, secure=settings.cookie_secure, samesite="lax", path="/")
    return {"id": merchant.id, "email": merchant.email, "locale": merchant.locale}


def require_merchant(request: Request, db: Session = Depends(get_db)) -> Merchant:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise HTTPException(401, "请先登录")
    row = db.scalar(select(MerchantSession).where(MerchantSession.token_hash == hashlib.sha256(token.encode()).hexdigest(), MerchantSession.expires_at > utcnow()))
    if row is None:
        raise HTTPException(401, "登录已过期，请重新登录")
    merchant = db.get(Merchant, row.merchant_id)
    if merchant is None:
        raise HTTPException(401, "登录已过期，请重新登录")
    return merchant


@router.post("/code")
def request_code(payload: CodeRequest, db: Session = Depends(get_db)):
    merchant = db.scalar(select(Merchant).where(Merchant.email == payload.email))
    if (payload.purpose == "register" and merchant) or (payload.purpose != "register" and not merchant):
        return {"sent": True}
    now = utcnow()
    latest = db.scalar(select(VerificationCode).where(VerificationCode.email == payload.email).order_by(VerificationCode.id.desc()))
    if latest and latest.sent_at > now - timedelta(seconds=60):
        raise HTTPException(429, "请 60 秒后再发送")
    count = db.scalar(select(func.count(VerificationCode.id)).where(VerificationCode.email == payload.email, VerificationCode.sent_at > now - timedelta(hours=1))) or 0
    if count >= 5:
        raise HTTPException(429, "发送过于频繁，请稍后再试")
    code = f"{secrets.randbelow(1000000):06d}"
    _send_code(payload.email, code, payload.purpose)
    db.add(VerificationCode(email=payload.email, purpose=payload.purpose, code_hash=code_digest(payload.email, payload.purpose, code), expires_at=now + timedelta(minutes=10), sent_at=now))
    db.commit()
    return {"sent": True}


@router.post("/register")
def register(payload: Register, response: Response, db: Session = Depends(get_db)):
    if db.scalar(select(Merchant.id).where(Merchant.email == payload.email)):
        raise HTTPException(409, "该邮箱已注册")
    _consume_code(db, payload.email, "register", payload.code)
    merchant = Merchant(email=payload.email, password_hash=hash_password(payload.password))
    db.add(merchant)
    db.flush()
    return _issue_session(db, response, merchant)


@router.post("/login")
def login(payload: PasswordLogin, response: Response, db: Session = Depends(get_db)):
    recent = db.scalar(select(func.count(LoginFailure.id)).where(LoginFailure.email == payload.email, LoginFailure.attempted_at > utcnow() - timedelta(minutes=15))) or 0
    if recent >= 10:
        raise HTTPException(429, "登录尝试过于频繁，请 15 分钟后重试")
    merchant = db.scalar(select(Merchant).where(Merchant.email == payload.email))
    if merchant is None or not verify_password(payload.password, merchant.password_hash):
        db.add(LoginFailure(email=payload.email, attempted_at=utcnow()))
        db.commit()
        raise HTTPException(401, "邮箱或密码错误")
    return _issue_session(db, response, merchant)


@router.post("/login/code")
def login_with_code(payload: CodeLogin, response: Response, db: Session = Depends(get_db)):
    merchant = db.scalar(select(Merchant).where(Merchant.email == payload.email))
    if merchant is None:
        raise HTTPException(401, "验证码无效或已过期")
    _consume_code(db, payload.email, "login", payload.code)
    return _issue_session(db, response, merchant)


@router.post("/reset-password")
def reset_password(payload: Register, response: Response, db: Session = Depends(get_db)):
    merchant = db.scalar(select(Merchant).where(Merchant.email == payload.email))
    if merchant is None:
        raise HTTPException(400, "验证码无效或已过期")
    _consume_code(db, payload.email, "reset", payload.code)
    merchant.password_hash = hash_password(payload.password)
    for session in db.scalars(select(MerchantSession).where(MerchantSession.merchant_id == merchant.id)):
        db.delete(session)
    db.flush()
    return _issue_session(db, response, merchant)


@router.get("/me")
def me(merchant: Merchant = Depends(require_merchant)):
    return {"id": merchant.id, "email": merchant.email, "locale": merchant.locale}


@router.put("/locale")
def update_locale(payload: LocaleUpdate, merchant: Merchant = Depends(require_merchant), db: Session = Depends(get_db)):
    merchant.locale = payload.locale
    db.commit()
    return {"locale": merchant.locale}


@router.post("/logout")
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    token = request.cookies.get(COOKIE_NAME)
    if token:
        row = db.scalar(select(MerchantSession).where(MerchantSession.token_hash == hashlib.sha256(token.encode()).hexdigest()))
        if row:
            db.delete(row)
            db.commit()
    response.delete_cookie(COOKIE_NAME, path="/")
    return {"ok": True}
