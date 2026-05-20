# auth.py
from dotenv import load_dotenv
load_dotenv()   
import os
import logging
from datetime import datetime, timedelta, timezone
from enum import Enum
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from database import SessionLocal, Admin

# ── LOGGING ───────────────────────────────────────────────────────────────────
# Auth failures are recorded — useful for spotting brute-force attempts
logger = logging.getLogger(__name__)

# ── SECRET KEY (from .env — app refuses to start if missing) ──────────────────
# Add this to your .env file:  JWT_SECRET_KEY=some-long-random-string
SECRET_KEY = os.environ.get("JWT_SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError(
        "JWT_SECRET_KEY is not set. Add it to your .env file before starting."
    )

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 8

# ── ROLES (Enum prevents silent typos) ────────────────────────────────────────
class AdminRole(str, Enum):
    DFRI          = "dfri"              # DFRI: all read/write + audit log
    DIRECTEUR     = "directeur"         # Director: all read-only + audit log view
    CHEF_SERVICE  = "chef_service"      # Department head: own dept only, manage interns
    SECRETAIRE    = "secretaire"        # Secretary: global view read-only, export, alerts

# ── PASSWORD HASHING ──────────────────────────────────────────────────────────
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ── OAUTH2 SCHEME ─────────────────────────────────────────────────────────────
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


# ── DB HELPER ─────────────────────────────────────────────────────────────────
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ── PASSWORD HELPERS ──────────────────────────────────────────────────────────
def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


# ── TOKEN CREATION ────────────────────────────────────────────────────────────
def create_access_token(
    username: str,
    role: AdminRole,
    department_id: str | None = None   # str UUID, None for super_admin
) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    payload = {
        "sub":           username,
        "role":          role.value,   # store the string value, not the Enum object
        "department_id": department_id,
        "exp":           expire
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


# ── DOMAIN EXCEPTION (not tied to HTTP) ───────────────────────────────────────
# Raised by decode_token — converted to HTTP 401 only inside FastAPI dependencies
class AuthError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


# ── TOKEN DECODING ────────────────────────────────────────────────────────────
def decode_token(token: str) -> dict:
    """
    Verify and decode a JWT token.
    Raises AuthError (not HTTPException) so this can be called
    from background jobs, CLI scripts, or tests without side effects.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError as e:
        logger.warning(f"Token validation failed: {e}")
        raise AuthError("Token invalide ou expiré")


# ── FASTAPI DEPENDENCY — any valid admin ──────────────────────────────────────
def get_current_admin(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> Admin:
    """
    Inject into any route that requires a logged-in admin.
    Converts AuthError → HTTP 401 here, at the HTTP boundary.
    """
    try:
        payload = decode_token(token)
    except AuthError as e:
        logger.warning(f"Unauthorized access attempt: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=e.message,
            headers={"WWW-Authenticate": "Bearer"},
        )

    username = payload.get("sub")
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token malformé"
        )

    admin = db.query(Admin).filter(Admin.username == username).first()
    if not admin:
        logger.warning(f"Token valid but admin not found in DB: {username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Compte administrateur introuvable"
        )

    return admin


# ── FASTAPI DEPENDENCY — super_admin only ─────────────────────────────────────
def require_super_admin(admin: Admin = Depends(get_current_admin)) -> Admin:
    """
    Inject into routes that require DFRI (super admin) role only.
    Non-DFRI users will get HTTP 403.
    """
    if admin.role != AdminRole.DFRI.value:
        logger.warning(
            f"Forbidden: {admin.username} (role={admin.role}) "
            f"attempted a DFRI action"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès refusé — droits DFRI requis"
        )
    return admin


def require_dfri_or_chef(admin: Admin = Depends(get_current_admin)) -> Admin:
    """
    Inject into routes that require DFRI or Chef de Service.
    Secretaire and Directeur will get HTTP 403.
    """
    if admin.role not in (AdminRole.DFRI.value, AdminRole.CHEF_SERVICE.value):
        logger.warning(
            f"Forbidden: {admin.username} (role={admin.role}) "
            f"attempted a DFRI/Chef action"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès refusé"
        )
    return admin
