from typing import Annotated

from pydantic import BaseModel
from sqlalchemy.orm import Session
from starlette import status

from database import SessionLocal
from fastapi import APIRouter, Depends, HTTPException, Path

from fastapi_pagination import Page, paginate

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


class TodoOut(BaseModel):
    id: int
    title: str
    description: str
    priority: int
    complete: bool
    owner_id: int


def check_admin_user(current_user):
    if current_user is None or current_user.get('user_role') != 'admin':
        raise HTTPException(status_code=401, detail='Authentication Failed')


@router.get('/todos', name='Get all todos on admin interface', status_code=status.HTTP_200_OK, response_model=Page[TodoOut])
async def read_all(current_user: user_dependency, db: db_dependency):
    check_admin_user(current_user)
    todos = db.query(Todos).all()
    return paginate(todos)


@router.delete('/todos/{todo_id}', name='Delete a specific todo on admin interface', status_code=status.HTTP_204_NO_CONTENT)
async def delete_todo(current_user: user_dependency, db: db_dependency, todo_id: int = Path(gt=0)):
    check_admin_user(current_user)
    todo = db.query(Todos).filter(Todos.id == todo_id).first()
    if todo is None:
        raise HTTPException(status_code=404, detail='The todo was not found!')
    db.delete(todo)
    db.commit()
