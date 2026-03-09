
import os
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.database import User

# KAVACH-AI Day 10: JWT Authentication
# Handles login and token generation

SECRET_KEY = os.getenv("SECRET_KEY", "supersecretkey_change_me_in_prod")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

auth_router = APIRouter(prefix="/auth", tags=["Authentication"])

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception
        
    user = db.query(User).filter(User.email == token_data.username).first()
    if user is None:
        raise credentials_exception
    return user

@auth_router.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

from backend.config import settings
import logging
logger = logging.getLogger(__name__)

@auth_router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    summary="Register a new admin user",
    description="Only available when REGISTER_ENABLED=true in environment.",
)
async def register(
    email: str, password: str,
    db: Session = Depends(get_db),
):
    """
    Create a new user account.
    Gated by REGISTER_ENABLED environment variable.
    Set REGISTER_ENABLED=true only during initial system setup.
    This endpoint should be disabled (REGISTER_ENABLED=false) in production.
    """
    if not settings.REGISTER_ENABLED:
        logger.warning(
            "Registration attempt blocked: REGISTER_ENABLED is false. "
            "Set REGISTER_ENABLED=true in .env to allow registration."
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "registration_disabled",
                "message": "Registration is disabled in this environment.",
                "hint": "Contact your system administrator.",
            },
        )

    existing = db.query(User).filter(User.email == email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": "email_taken",
                "message": f"An account with {email} already exists.",
            },
        )

    hashed = get_password_hash(password)
    user = User(
        email=email,
        hashed_password=hashed,
        role="admin",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    logger.info(f"New admin account created: {email}")
    return {"status": "User created", "email": email}
