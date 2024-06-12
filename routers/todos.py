from fastapi import Depends, HTTPException, Path, APIRouter
from pydantic import BaseModel, Field

from database import SessionLocal
from typing import Annotated
from sqlalchemy.orm import Session
from starlette import status


from models import Todos

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


db_dependency = Annotated[Session, Depends(get_db)]


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


@router.get('/')
async def read_all(db: db_dependency):
    return db.query(Todos).all()


@router.get('/todos/{todo_id}', status_code=status.HTTP_200_OK)
async def read_todo(db: db_dependency, todo_id: int = Path(gt=0)):
    todo = db.query(Todos).filter(Todos.id == todo_id).first()
    if todo is not None:
        return todo
    raise HTTPException(status_code=404, detail='The todo was not found!')


@router.post('/todos/', status_code=status.HTTP_201_CREATED)
async def create_todo(db: db_dependency, new_todo: TodoRequest):
    todo = Todos(**new_todo.model_dump())
    db.add(todo)
    db.commit()


@router.put('/todos/{todo_id}', status_code=status.HTTP_204_NO_CONTENT)
async def update_todo(db: db_dependency, updated_todo: TodoRequest, todo_id: int = Path(gt=0)):
    todo = db.query(Todos).filter(Todos.id == todo_id).first()
    if todo is None:
        raise HTTPException(status_code=404, detail='The todo was not found!')
    todo.title = updated_todo.title
    todo.description = updated_todo.description
    todo.priority = updated_todo.priority
    todo.complete = updated_todo.complete

    db.add(todo)
    db.commit()


@router.delete('/todos/{todo_id}', status_code=status.HTTP_204_NO_CONTENT)
async def delete_todo(db: db_dependency, todo_id: int = Path(gt=0)):
    todo_model = db.query(Todos).filter(Todos.id == todo_id)
    todo = todo_model.first()
    if todo is None:
        raise HTTPException(status_code=404, detail='The todo was not found!')
    todo_model.delete()

    db.commit()