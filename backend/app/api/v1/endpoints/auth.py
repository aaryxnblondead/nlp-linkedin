from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.db import SessionLocal
from app.models.user import User, UserRole
from passlib.context import CryptContext
from jose import jwt, JWTError
from pydantic import BaseModel, validator
import os

SECRET_KEY = os.environ.get("SECRET_KEY", "supersecretkey")
ALGORITHM = "HS256"

router = APIRouter()
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

class UserCreate(BaseModel):
    username: str
    password: str
    role: UserRole

    @validator('password')
    def password_length(cls, v):
        if len(v.encode('utf-8')) > 72:
            raise ValueError('Password must be 72 characters or less')
        return v

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_access_token(data: dict):
    return jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)

@router.api_route("/register/", methods=["POST", "OPTIONS"])
def register(user: UserCreate, db: Session = Depends(get_db)):
    try:
        if db.query(User).filter(User.username == user.username).first():
            raise HTTPException(status_code=400, detail="Username already registered")
        # Accept both string and enum for role
        role_value = user.role
        if isinstance(role_value, str):
            try:
                role_value = UserRole(role_value.lower())
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Invalid role: {user.role}")
        hashed = pwd_context.hash(user.password)
        db_user = User(username=user.username, password_hash=hashed, role=role_value)
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return {"msg": "User registered"}
    except Exception as e:
        print(f"Registration error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.api_route("/login/", methods=["POST", "OPTIONS"])
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.username == form_data.username).first()
    if not db_user or not pwd_context.verify(form_data.password, getattr(db_user, "password_hash")):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token({"sub": db_user.username, "role": db_user.role.value})
    return {"access_token": token, "token_type": "bearer", "role": db_user.role.value}
