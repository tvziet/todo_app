from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from starlette import status
from enum import Enum
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordRequestForm

from database import SessionLocal
from models import Users

router = APIRouter()

bcrypt_context = CryptContext(schemes=['bcrypt'], deprecated='auto')


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


db_dependency = Annotated[Session, Depends(get_db)]


class Role(str, Enum):
    admin = 'admin'
    user = 'user'


class CreateUserRequest(BaseModel):
    username: str
    email: str
    first_name: str
    last_name: str
    password: str
    role: Role
    is_active: bool

    class Config:
        json_schema_extra = {
            'example': {
                'username': 'vietle.uit',
                'email': 'vietleuit@example.com',
                'first_name': 'Le',
                'last_name': 'Thanh Viet',
                'password': 'p@ssw0rd',
                'role': 'user',
                'is_active': True
            }
        }


def authenticate_user(username: str, password: str, db):
    user = db.query(Users).filter(Users.username == username).first()
    if not user:
        return False
    if not bcrypt_context.verify(password, user.hashed_password):
        return False

    return True


@router.post('/auth', status_code=status.HTTP_201_CREATED)
async def create_user(db: db_dependency, new_user: CreateUserRequest):
    user_model = Users(
        username=new_user.username,
        email=new_user.email,
        first_name=new_user.first_name,
        last_name=new_user.last_name,
        hashed_password=bcrypt_context.hash(new_user.password),
        role=new_user.role,
        is_active=new_user.is_active
    )
    db.add(user_model)
    db.commit()


@router.post('/token')
async def create_token(form_data: Annotated[OAuth2PasswordRequestForm, Depends()], db: db_dependency):
    current_user = authenticate_user(form_data.username, form_data.password, db)
    if not current_user:
        return 'Failed authenticate'
    return 'Successfully authenticate'
