from typing import Annotated, Optional, List

from pydantic import BaseModel
from sqlalchemy import or_
from sqlalchemy.orm import Session
from starlette import status
from starlette.responses import JSONResponse

from database import SessionLocal
from fastapi import APIRouter, Depends, HTTPException, Path

from fastapi_pagination import Page, paginate

from routers.auth import get_current_user
from models import Todos, Users

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


class UserOut(BaseModel):
    id: int
    username: str
    email: str
    first_name: str
    last_name: str
    role: str
    is_active: bool
    phone_number: Optional[str] = None


class UserBatchDeleteRequest(BaseModel):
    user_ids: List[int]


def check_admin_user(current_user):
    if current_user is None or current_user.get('user_role') != 'admin':
        raise HTTPException(status_code=403, detail=[{'msg': 'You can not perform this action!'}])


def filter_users(users, query):
    return users.filter(
        or_(Users.first_name.like(f"%{query}%"), Users.last_name.like(f"%{query}%"), Users.username.like(f"%{query}%")))


@router.get('/todos', name='Get all todos on admin interface', status_code=status.HTTP_200_OK,
            response_model=Page[TodoOut])
async def read_all(current_user: user_dependency, db: db_dependency, q: str | None = None):
    check_admin_user(current_user)
    query = db.query(Todos)
    if q:
        query = query.filter(or_(Todos.title.like(f"%{q}%"), Todos.description.like(f"%{q}%")))
    todos = query.all()
    result = paginate(todos)
    return result


@router.delete('/todos/{todo_id}', name='Delete a specific todo on admin interface',
               status_code=status.HTTP_204_NO_CONTENT)
async def delete_todo(current_user: user_dependency, db: db_dependency, todo_id: int = Path(gt=0)):
    check_admin_user(current_user)
    todo = db.query(Todos).filter(Todos.id == todo_id).first()
    if todo is None:
        raise HTTPException(status_code=404, detail=[{'msg': 'The todo was not found!'}])
    db.delete(todo)
    db.commit()


@router.get('/users', name='Get all the users', response_model=Page[UserOut])
async def read_all(current_user: user_dependency, db: db_dependency, q: str | None = None):
    check_admin_user(current_user)
    users_query = db.query(Users)
    if q:
        users = filter_users(users_query, q).all()
    else:
        users = users_query.filter(Users.id != current_user.get('user_id')).all()
    result = paginate(users)
    return result


@router.delete('/users/batch_delete', response_model=dict)
def delete_users_batch(current_user: user_dependency, db: db_dependency,
                       user_batch_delete_request: UserBatchDeleteRequest):
    check_admin_user(current_user)
    # Exclude the current user's ID from the deletion operation
    user_ids_to_delete = [user_id for user_id in user_batch_delete_request.user_ids if user_id != current_user.get('user_id')]
    if not user_ids_to_delete:
        raise HTTPException(status_code=422, detail=[{'msg': "No user IDs to delete. Ensure the list is not empty and "
                                                             "does not only contain the current user's ID."}])
    db.query(Users).filter(Users.id.in_(user_ids_to_delete)).delete(synchronize_session=False)
    db.commit()
    return {'user_deleted_ids': user_ids_to_delete}


@router.delete('/{user_id}', name='Destroy an user', status_code=status.HTTP_200_OK)
async def delete_user(current_user: user_dependency, db: db_dependency, user_id: int = Path(gt=0)):
    check_admin_user(current_user)
    if current_user.get('user_id') == user_id:
        raise HTTPException(status_code=422, detail=[{'msg': "The user_id params cannot be the current user's ID"}])
    user = db.query(Users).filter(Users.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail=[{'msg': 'The user was not found'}])
    db.delete(user)
    db.commit()
    return JSONResponse(content={'msg': 'The user was deleted successfully!'})
