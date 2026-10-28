
import hashlib
import secrets
import smtplib
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import DateTime, ForeignKey, String, func, select, update
from sqlalchemy.dialects.mysql import BIGINT
from sqlalchemy.orm import Mapped, Session, mapped_column

from backend.auth import hash_password
from backend.config import settings
from backend.database import Base, get_db
from backend.models import User


router = APIRouter(prefix="/auth", tags=["Authentication"])

INVALID_LINK_MESSAGE = (
    "This reset link is invalid or expired. Request a new one."
)

GENERIC_MESSAGE = (
    "If an account with that email exists, password-reset instructions "
    "will be sent shortly."
)


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    reset_id: Mapped[int] = mapped_column(
        BIGINT(unsigned=True),
        primary_key=True,
        autoincrement=True,
    )
    user_id: Mapped[int] = mapped_column(
        BIGINT(unsigned=True),
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    token_hash: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
    )
    used_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
    )


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=32, max_length=256)
    new_password: str = Field(min_length=10, max_length=128)


def _utcnow_naive() -> datetime:
    """Use naive UTC timestamps to match MySQL DATETIME."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _hash_token(token: str) -> str:
    """Only the SHA-256 digest is stored in the database."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _send_reset_email(recipient: str, reset_url: str) -> None:
    """Send the reset link when SMTP is configured."""
    required_settings = (
        settings.SMTP_HOST,
        settings.SMTP_USERNAME,
        settings.SMTP_PASSWORD,
        settings.SMTP_FROM_EMAIL,
    )

    if not all(required_settings):
        raise RuntimeError("SMTP settings are incomplete.")

    message = EmailMessage()
    message["Subject"] = "CKD Care password reset"
    message["From"] = settings.SMTP_FROM_EMAIL
    message["To"] = recipient
    message.set_content(
        "A password reset was requested for your CKD Care account.\n\n"
        f"Open this link within "
        f"{settings.PASSWORD_RESET_EXPIRE_MINUTES} minutes:\n\n"
        f"{reset_url}\n\n"
        "If you did not request this, ignore this email."
    )

    with smtplib.SMTP(
        settings.SMTP_HOST,
        settings.SMTP_PORT,
        timeout=20,
    ) as smtp:
        smtp.ehlo()

        if settings.SMTP_USE_TLS:
            smtp.starttls()
            smtp.ehlo()

        smtp.login(
            settings.SMTP_USERNAME,
            settings.SMTP_PASSWORD,
        )
        smtp.send_message(message)


@router.post("/forgot-password")
def forgot_password(
    payload: ForgotPasswordRequest,
    db: Session = Depends(get_db),
):
    email = str(payload.email).strip()

    # Case-insensitive email lookup.
    user = db.scalar(
        select(User).where(func.lower(User.email) == email.lower()).limit(1)
    )

    if user is None:
        # Do not reveal whether an account exists.
        return {"message": GENERIC_MESSAGE}

    now = _utcnow_naive()

    # Invalidate earlier, unused reset links for this account.
    db.execute(
        update(PasswordResetToken)
        .where(
            PasswordResetToken.user_id == user.user_id,
            PasswordResetToken.used_at.is_(None),
        )
        .values(used_at=now)
    )

    # Create a fresh, unpredictable token.
    raw_token = secrets.token_urlsafe(32)

    reset_record = PasswordResetToken(
        user_id=user.user_id,
        token_hash=_hash_token(raw_token),
        expires_at=now + timedelta(
            minutes=settings.PASSWORD_RESET_EXPIRE_MINUTES
        ),
    )

    db.add(reset_record)

    try:
        # Persist the token before presenting the link.
        db.commit()
        db.refresh(reset_record)
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Could not save the password reset request.",
        ) from exc

    frontend_url = settings.FRONTEND_BASE_URL.rstrip("/")
    reset_url = f"{frontend_url}/#reset_token={raw_token}"

    # ALWAYS print the URL for local development and testing,
    # independently of DEBUG or SMTP configuration.
    print("\n" + "=" * 72, flush=True)
    print("CKD CARE PASSWORD RESET LINK", flush=True)
    print(f"Account: {email}", flush=True)
    print(f"Expires in: {settings.PASSWORD_RESET_EXPIRE_MINUTES} minutes", flush=True)
    print(reset_url, flush=True)
    print("=" * 72 + "\n", flush=True)

    # Email delivery is optional for the local terminal-link workflow.
    # Crucially, an SMTP failure must NOT delete the valid token.
    try:
        _send_reset_email(email, reset_url)
        print("Password reset email sent successfully.", flush=True)
    except Exception as exc:
        print(
            "Password reset email was not sent. "
            f"Use the link printed above. Reason: {exc}",
            flush=True,
        )

    return {"message": GENERIC_MESSAGE}


@router.post("/reset-password")
def reset_password(
    payload: ResetPasswordRequest,
    db: Session = Depends(get_db),
):
    raw_token = payload.token.strip()
    token_digest = _hash_token(raw_token)
    now = _utcnow_naive()

    try:
        # Lock the token row while validating and consuming it.
        reset_record = (
            db.query(PasswordResetToken)
            .filter(PasswordResetToken.token_hash == token_digest)
            .with_for_update()
            .first()
        )

        if (
            reset_record is None
            or reset_record.used_at is not None
            or reset_record.expires_at <= now
        ):
            raise HTTPException(
                status_code=400,
                detail=INVALID_LINK_MESSAGE,
            )

        user = (
            db.query(User)
            .filter(User.user_id == reset_record.user_id)
            .with_for_update()
            .first()
        )

        if user is None:
            raise HTTPException(
                status_code=400,
                detail=INVALID_LINK_MESSAGE,
            )

        # Use the same password hashing method used by normal authentication.
        user.password_hash = hash_password(payload.new_password)
        reset_record.used_at = now

        # Invalidate any other unused reset links for this account.
        (
            db.query(PasswordResetToken)
            .filter(
                PasswordResetToken.user_id == user.user_id,
                PasswordResetToken.reset_id != reset_record.reset_id,
                PasswordResetToken.used_at.is_(None),
            )
            .update(
                {PasswordResetToken.used_at: now},
                synchronize_session=False,
            )
        )

        db.commit()

        return {
            "message": "Password reset successfully. You can now log in."
        }

    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        # Keep details in the server logs, not in the API response.
        print(f"Password reset failed: {exc}", flush=True)
        raise HTTPException(
            status_code=500,
            detail="Unable to reset the password. Please try again.",
        ) from exc
