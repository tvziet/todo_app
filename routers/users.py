from enum import Enum
from typing import Annotated

from pydantic import BaseModel, Field
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


class UserVerification(BaseModel):
    password: str
    new_password: str = Field(min_length=6)

    class Config:
        json_schema_extra = {
            'example': {
                'password': 'p@ssw0rd',
                'new_password': 'n3wp@ssw0rd'
            }
        }


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


@router.get('/me', name='Get the current user', status_code=status.HTTP_200_OK)
async def me(current_user: user_dependency, db: db_dependency):
    check_current_user(current_user)
    current_user_id = current_user.get('user_id')
    return db.query(Users).filter(Users.id == current_user_id).first()


@router.put('/update_password', name='Update the password of the current user', status_code=status.HTTP_204_NO_CONTENT)
async def update_password(current_user: user_dependency, db: db_dependency, user_verification: UserVerification):
    check_current_user(current_user)
    current_user_id = current_user.get('user_id')
    user = db.query(Users).filter(Users.id == current_user_id).first()

    if not bcrypt_context.verify(user_verification.password, user.hashed_password):
        raise HTTPException(status_code=401, detail='Error on password change')

    user.hashed_password = bcrypt_context.hash(user_verification.new_password)
    db.add(user)
    db.commit()


@router.put('/update_phone_number', name='Update the phone number of the current user', status_code=status.HTTP_204_NO_CONTENT)
async def update_phone_number(current_user: user_dependency, db: db_dependency, phone_number: str):
    check_current_user(current_user)
    current_user_id = current_user.get('user_id')
    user = db.query(Users).filter(Users.id == current_user_id).first()

    user.phone_number = phone_number
    db.add(user)
    db.commit()