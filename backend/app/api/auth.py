"""
HealthBridge AI - Authentication API Endpoints
Registration, Login, and Current User profile retrieval.
"""

from fastapi import APIRouter, HTTPException, status, Depends
from backend.app.database.connection import get_db
from backend.app.schemas.auth import UserRegisterRequest, UserLoginRequest, TokenResponse, UserResponse
from backend.app.utils.security import hash_password, verify_password, create_access_token, get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(req: UserRegisterRequest):
    if req.password != req.confirm_password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Passwords do not match.")

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE email = ?", (req.email.lower().strip(),))
        if cursor.fetchone():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email is already registered.")

        pwd_hash = hash_password(req.password)
        cursor.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            (req.name.strip(), req.email.lower().strip(), pwd_hash)
        )
        user_id = cursor.lastrowid

        cursor.execute("SELECT id, name, email, created_at FROM users WHERE id = ?", (user_id,))
        user_row = dict(cursor.fetchone())

    token = create_access_token(data={"sub": str(user_id), "email": user_row["email"]})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": user_row
    }

@router.post("/login", response_model=TokenResponse)
def login(req: UserLoginRequest):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, email, password_hash, created_at FROM users WHERE email = ?", (req.email.lower().strip(),))
        row = cursor.fetchone()

        if not row:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password.")

        user_dict = dict(row)
        if not verify_password(req.password, user_dict["password_hash"]):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password.")

        user_data = {
            "id": user_dict["id"],
            "name": user_dict["name"],
            "email": user_dict["email"],
            "created_at": user_dict["created_at"]
        }

    token = create_access_token(data={"sub": str(user_data["id"]), "email": user_data["email"]})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": user_data
    }

@router.get("/me", response_model=UserResponse)
def get_profile(current_user: dict = Depends(get_current_user)):
    return current_user
