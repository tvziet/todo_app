from datetime import timedelta, datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Body
from pydantic import BaseModel, Field
from sqlalchemy import or_
from sqlalchemy.orm import Session
from starlette import status
from enum import Enum
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from jose import jwt, JWTError

from database import SessionLocal
from models import Users

router = APIRouter(
    prefix='/auth',
    tags=['auth']
)

SECRET_KEY = '2f3af4136fd3471a5e3effb2df2f2bd3d5c665574129c4ddd720c24ab0afed4d'
ALGORITHM = 'HS256'

bcrypt_context = CryptContext(schemes=['bcrypt'], deprecated='auto')
oauth2_bearer = OAuth2PasswordBearer(tokenUrl='auth/token')


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


class Token(BaseModel):
    access_token: str
    token_type: str


class LoginRequest(BaseModel):
    username: str
    password: str


class UserOut(BaseModel):
    id: int
    username: str
    email: str
    first_name: str
    last_name: str
    role: str
    is_active: bool
    phone_number: str


class CreateUserRequest(BaseModel):
    username: str
    email: str
    first_name: str
    last_name: str
    password: str = Field(min_length=6)
    role: Role
    is_active: bool
    phone_number: str

    class Config:
        json_schema_extra = {
            'example': {
                'username': 'vietle.uit',
                'email': 'vietleuit@example.com',
                'first_name': 'Le',
                'last_name': 'Thanh Viet',
                'password': 'p@ssw0rd',
                'role': 'user',
                'is_active': True,
                'phone_number': '0987654321'
            }
        }


def authenticate_user(username: str, password: str, db):
    user = db.query(Users).filter(Users.username == username).first()
    if not user:
        return None
    if not bcrypt_context.verify(password, user.hashed_password):
        return None

    return user


async def get_current_user(token: Annotated[str, Depends(oauth2_bearer)]):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=ALGORITHM)
        username: str = payload.get('sub')
        user_id: int = payload.get('id')
        user_role: str = payload.get('role')
        if username is None or user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                detail='Could not validate user')
        return {'username': username, 'user_id': user_id, 'user_role': user_role}
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail='Could not validate user')


def generate_access_token(username: str, user_id: int, role: str, expires_delta: timedelta):
    encode = {'sub': username, 'id': user_id, 'role': role}
    expires = datetime.now(timezone.utc) + expires_delta
    encode.update({'exp': expires})
    return jwt.encode(encode, SECRET_KEY, algorithm=ALGORITHM)


@router.post('/', name='Generate a new user', status_code=status.HTTP_201_CREATED, response_model=UserOut)
async def create_user(db: db_dependency, new_user: CreateUserRequest):
    user = db.query(Users).filter(or_(Users.username == new_user.username, Users.email == new_user.email)).first()
    if user is not None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail='The user is exists!')
    try:
        user_model = Users(
            username=new_user.username,
            email=new_user.email,
            first_name=new_user.first_name,
            last_name=new_user.last_name,
            hashed_password=bcrypt_context.hash(new_user.password),
            role=new_user.role,
            is_active=new_user.is_active,
            phone_number=new_user.phone_number
        )
        db.add(user_model)
        db.commit()
        db.refresh(user_model)
        return user_model
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post('/login', name='Generate token when user login', response_model=Token)
async def login(db: db_dependency, login_request: LoginRequest = Body(...)):
    current_user = authenticate_user(login_request.username, login_request.password, db)
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail='Could not validate user')
    token = generate_access_token(current_user.username, current_user.id, current_user.role, timedelta(minutes=20))
    return {'access_token': token, 'token_type': 'bearer'}


@router.post('/token', name='Generate token when user login', response_model=Token, include_in_schema=False)
async def login_for_access_token(form_data: Annotated[OAuth2PasswordRequestForm, Depends()], db: db_dependency):
    current_user = authenticate_user(form_data.username, form_data.password, db)
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail='Could not validate user')
    token = generate_access_token(current_user.username, current_user.id, current_user.role, timedelta(minutes=20))
    return {'access_token': token, 'token_type': 'bearer'}
