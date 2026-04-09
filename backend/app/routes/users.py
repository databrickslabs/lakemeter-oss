"""User API routes."""
from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.schemas import UserCreate, UserUpdate, UserResponse
from app.auth.databricks_auth import FORWARDED_EMAIL_HEADER

router = APIRouter(prefix="/users", tags=["users"])


# NOTE: /me route MUST be defined BEFORE /{user_id} to avoid "me" being parsed as UUID
@router.get("/me", response_model=UserResponse)
def get_current_user_me(
    request: Request,
    db: Session = Depends(get_db)
):
    """Get the current authenticated user."""
    # Get email from forwarded header (Databricks Apps SSO)
    email = request.headers.get(FORWARDED_EMAIL_HEADER)
    
    if not email:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Find or create user
    user = db.query(User).filter(User.email == email).first()
    
    if not user:
        # Create new user from SSO
        full_name = email.split('@')[0].replace('.', ' ').title()
        user = User(
            email=email,
            full_name=full_name,
            is_active=True
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    
    return user


@router.get("", response_model=List[UserResponse])
@router.get("/", response_model=List[UserResponse])
def list_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """List all users."""
    users = db.query(User).filter(User.is_active == True).offset(skip).limit(limit).all()
    return users


@router.post("/", response_model=UserResponse, status_code=201)
def create_user(
    user: UserCreate,
    db: Session = Depends(get_db)
):
    """Create a new user."""
    # Check if email already exists
    existing = db.query(User).filter(User.email == user.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    db_user = User(**user.model_dump())
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


@router.get("/{user_id}", response_model=UserResponse)
def get_user(
    user_id: UUID,
    db: Session = Depends(get_db)
):
    """Get a user by ID."""
    user = db.query(User).filter(User.user_id == user_id).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return user


@router.get("/email/{email}", response_model=UserResponse)
def get_user_by_email(
    email: str,
    db: Session = Depends(get_db)
):
    """Get a user by email."""
    user = db.query(User).filter(User.email == email).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return user


@router.put("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: UUID,
    user_update: UserUpdate,
    db: Session = Depends(get_db)
):
    """Update a user."""
    user = db.query(User).filter(User.user_id == user_id).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    update_data = user_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)
    
    db.commit()
    db.refresh(user)
    return user


