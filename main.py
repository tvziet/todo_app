from typing import Union

from fastapi import FastAPI
from starlette.responses import JSONResponse

from database import engine
from routers import auth, todos, admin, users
from fastapi_pagination import add_pagination
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError

import models


# Define a custom exception class
class RecordInvalidException(Exception):
    def __init__(self, detail: Union[str, list]):
        self.detail = detail


# Custom error handler for Pydantic validation errors
async def validation_exception_handler(request, exc: RequestValidationError):
    # Transform the Pydantic validation error details into your desired format
    details = [{'type': error['type'], 'msg': error['msg'], 'field': ' '.join(word.capitalize() for word in error['loc'][1].split('_'))} for error in exc.errors()]
    raise RecordInvalidException(detail=details)


# Custom error handler for your RecordInvalidException
async def record_invalid_exception_handler(request, exc: RecordInvalidException):
    return JSONResponse(
        status_code=422,
        content={"detail": exc.detail},
    )


app = FastAPI()

# Register your custom error handlers with FastAPI
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(RecordInvalidException, record_invalid_exception_handler)

origins = [
    'http://localhost',
    'http://localhost:5173'
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
