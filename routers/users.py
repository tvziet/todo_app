from enum import Enum
from typing import Annotated

from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, Field, EmailStr
from sqlalchemy.orm import Session
from starlette import status

from database import SessionLocal
from fastapi import APIRouter, Depends, HTTPException
from passlib.context import CryptContext

from routers.auth import get_current_user
from models import Users

router = APIRouter(
    prefix='/users',
    tags=['users']
)

bcrypt_context = CryptContext(schemes=['bcrypt'], deprecated='auto')


class Role(str, Enum):
    admin = 'admin'
    user = 'user'


class UserUpdateRequest(BaseModel):
    password: str = Field(description='The current password')
    new_password: str = Field(min_length=6)
    username: str = Field(description='Must be unique along with the email attribute')
    email: EmailStr = Field(..., description='Must be unique along with the username attribute')
    first_name: str
    last_name: str
    role: Role
    phone_number: str


class UserOut(BaseModel):
    id: int
    username: str
    email: str
    first_name: str
    last_name: str
    role: str
    is_active: bool
    phone_number: str


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[dict, Depends(get_current_user)]


def get_current_user_from_db(current_username, db):
    current_user_from_db = db.query(Users).filter(Users.username == current_username).first()
    if current_user_from_db is None:
        raise HTTPException(status_code=404, detail='The user was not found')
    return current_user_from_db


def check_current_user(current_user):
    if current_user is None:
        raise HTTPException(status_code=401, detail='Authentication Failed')


@router.get('/me', name='Get the current user', status_code=status.HTTP_200_OK, response_model=UserOut)
async def me(current_user: user_dependency, db: db_dependency):
    check_current_user(current_user)
    current_user_id = current_user.get('user_id')
    return db.query(Users).filter(Users.id == current_user_id).first()


@router.put('/me/update', name='Update the information of the current user',
            status_code=status.HTTP_200_OK, response_model=UserOut)
async def update_user_details(current_user: user_dependency, db: db_dependency, update_model: UserUpdateRequest):
    check_current_user(current_user)
    current_user_id = current_user.get('user_id')
    user = db.query(Users).filter(Users.id == current_user_id).first()

    if not bcrypt_context.verify(update_model.password, user.hashed_password):
        raise HTTPException(status_code=401, detail='Error on password change')

    user.hashed_password = bcrypt_context.hash(update_model.new_password)

    # Using a dictionary to map update_models fields to user fields
    user_attributes = {
        'phone_number': update_model.phone_number,
        'role': update_model.role,
        'username': update_model.username,
        'first_name': update_model.first_name,
        'last_name': update_model.last_name,
        'email': update_model.email
    }

    # Loop through the dictionary and update the user object
    for field, value in user_attributes.items():
        if value:
            setattr(user, field, value)
    db.commit()
    db.refresh(user)
    return jsonable_encoder(user)  # Serialize and return the created user object