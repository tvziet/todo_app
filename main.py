from fastapi import FastAPI

from database import engine
from routers import auth, todos, admin, users
from fastapi_pagination import add_pagination

import models

app = FastAPI()

models.Base.metadata.create_all(bind=engine)


@app.get('/healthy')
def health_check():
    return {'status': 'Healthy'}


# Need to add pagination to all app
add_pagination(app)


app.include_router(auth.router)
app.include_router(todos.router)
app.include_router(admin.router)
app.include_router(users.router)
