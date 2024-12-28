from fastapi import APIRouter, HTTPException, Form
from app.core.utils import hash_password, verify_password
from app.db.models import UserCreate, LoginRequest, users
from sqlmodel import select
from app.routers.deps import SessionDep
from uuid import uuid4

router = APIRouter(prefix="/auth", tags=["Authentication"])

def get_user_by_email(email: str, session: SessionDep) -> users | None:
    statement = select(users).where(users.email == email)
    session_user = session.exec(statement).first()
    return session_user

@router.post("/register", summary="Register a new user")
def register_user(session: SessionDep, user: UserCreate = Form(...)):
    hashed_password = hash_password(user.password)
    uid = str(uuid4())
    try:
        user = get_user_by_email(email=user.email, session=SessionDep)
        if user:
            raise HTTPException(
                status_code=400,
                detail="The user with this email already exists in the system",
            )
    
        new_user = users(
            user_id=uid,
            email=user.email,
            username=user.username,
            password=hashed_password
        )
        session.add(new_user)
        session.commit()
        return {"message": "User registered successfully", "user_id": uid}
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Error registering user: {e}")

@router.post("/login", summary="Authenticate user and return user_id")
def login_user(session: SessionDep, loginrequest: LoginRequest = Form(...)):
    try:
        credentials = session.exec(
            select(users).where(users.email == loginrequest.email)
        ).first()
        if not credentials or not verify_password(loginrequest.password, credentials.password):
            raise HTTPException(status_code=401, detail="Invalid credentials")
        return {"message": "Login successful", "user_id": credentials.user_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error logging in: {e}")
