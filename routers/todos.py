from fastapi import Depends, HTTPException, Path, APIRouter
from fastapi.responses import JSONResponse
from fastapi_pagination import Page, paginate
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, Field
from sqlalchemy import or_

from database import SessionLocal
from typing import Annotated
from sqlalchemy.orm import Session
from starlette import status

from models import Todos
from .auth import get_current_user

router = APIRouter(
    tags=['todos']
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[dict, Depends(get_current_user)]


class TodoRequest(BaseModel):
    title: str = Field(min_length=3)
    description: str = Field(min_length=3, max_length=100)
    priority: int = Field(gt=0, lt=6)
    complete: bool

    class Config:
        json_schema_extra = {
            'example': {
                'title': 'Learn FastAPI',
                'description': 'Complete all sections',
                'priority': 5,
                'complete': False
            }
        }


class TodoOut(BaseModel):
    id: int
    title: str
    description: str
    priority: int
    complete: bool
    owner_id: int


def check_current_user(current_user):
    if current_user is None:
        raise HTTPException(status_code=401, detail='Authentication Failed')


def get_todo_by_owner_id_and_id(db, todo_model, todo_id, current_user):
    todo = db.query(todo_model).filter(todo_model.id == todo_id) \
        .filter(todo_model.owner_id == current_user.get('user_id')).first()
    if todo is None:
        raise HTTPException(status_code=404, detail='The todo was not found!')
    return todo


def filter_todos(todos, query):
    return todos.filter(or_(Todos.title.like(f"%{query}%"), Todos.description.like(f"%{query}%")))


@router.get('/', name='Get all the todos of the current user', response_model=Page[TodoOut])
async def read_all(current_user: user_dependency, db: db_dependency, q: str | None = None):
    check_current_user(current_user)
    current_user_id = current_user.get('user_id')
    todos_for_current_user = db.query(Todos).filter(Todos.owner_id == current_user_id)
    if q:
        todos_for_current_user = filter_todos(todos_for_current_user, q)
    result = paginate(todos_for_current_user.all())
    return result


@router.get('/todos/{todo_id}', name='Get the detail of the todo of the current user', status_code=status.HTTP_200_OK)
async def read_todo(current_user: user_dependency, db: db_dependency, todo_id: int = Path(gt=0)):
    check_current_user(current_user)
    return get_todo_by_owner_id_and_id(db, Todos, todo_id, current_user)


@router.post('/todos/', response_model=TodoOut, name='Create new todo', status_code=status.HTTP_201_CREATED)
async def create_todo(current_user: user_dependency, db: db_dependency, new_todo: TodoRequest):
    check_current_user(current_user)
    todo = Todos(**new_todo.model_dump(), owner_id=current_user.get('user_id'))
    db.add(todo)
    db.commit()
    db.refresh(todo)  # Refresh the instance to get the data as it is in the database, including the generated ID
    return jsonable_encoder(todo)  # Serialize and return the created todo object


@router.put('/todos/{todo_id}', name='Update the todo of the current user')
async def update_todo(current_user: user_dependency, db: db_dependency,
                      updated_todo: TodoRequest, todo_id: int = Path(gt=0)):
    check_current_user(current_user)
    todo = get_todo_by_owner_id_and_id(db, Todos, todo_id, current_user)
    todo.title = updated_todo.title
    todo.description = updated_todo.description
    todo.priority = updated_todo.priority
    todo.complete = updated_todo.complete
    todo.owner_id = current_user.get('user_id')

    db.add(todo)
    db.commit()
    return JSONResponse(content={'message': 'The todo was updated successfully!'})


@router.delete('/todos/{todo_id}', name='Delete a todo of the current user')
async def delete_todo(current_user: user_dependency, db: db_dependency, todo_id: int = Path(gt=0)):
    check_current_user(current_user)
    todo = get_todo_by_owner_id_and_id(db, Todos, todo_id, current_user)
    db.delete(todo)
    db.commit()
    return JSONResponse(content={'message': 'The todo was deleted successfully!'})
