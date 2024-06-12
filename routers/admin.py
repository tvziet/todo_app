from typing import Annotated

from sqlalchemy.orm import Session
from starlette import status

from database import SessionLocal
from fastapi import APIRouter, Depends, HTTPException, Path

from routers.auth import get_current_user
from models import Todos

router = APIRouter(
    prefix='/admin',
    tags=['admin']
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[dict, Depends(get_current_user)]


def check_admin_user(current_user):
    if current_user is None or current_user.get('user_role') != 'admin':
        raise HTTPException(status_code=401, detail='Authentication Failed')


@router.get('/todos', status_code=status.HTTP_200_OK)
async def read_all(current_user: user_dependency, db: db_dependency):
    check_admin_user(current_user)
    return db.query(Todos).all()


@router.delete('/todos/{todo_id}', status_code=status.HTTP_204_NO_CONTENT)
async def delete_todo(current_user: user_dependency, db: db_dependency, todo_id: int = Path(gt=0)):
    check_admin_user(current_user)
    todo = db.query(Todos).filter(Todos.id == todo_id).first()
    if todo is None:
        raise HTTPException(status_code=404, detail='The todo was not found!')
    db.delete(todo)
    db.commit()
