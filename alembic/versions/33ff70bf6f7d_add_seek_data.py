"""Add seek data

Revision ID: 33ff70bf6f7d
Revises: b507c9ae6cc2
Create Date: 2024-06-17 13:13:31.546456

"""
from typing import Sequence, Union

from sqlalchemy import create_engine, Table, MetaData
from sqlalchemy.orm import sessionmaker
from passlib.context import CryptContext
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '33ff70bf6f7d'
down_revision: Union[str, None] = 'b507c9ae6cc2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

bcrypt_context = CryptContext(schemes=['bcrypt'], deprecated='auto')


def upgrade() -> None:
    engine = create_engine('sqlite:///./todosapp.db')
    Session = sessionmaker(bind=engine)
    session = Session()

    metadata = MetaData()
    users = Table('users', metadata, autoload_with=engine)

    new_user = users.insert().values(
        username='tonti',
        hashed_password=bcrypt_context.hash('123123'),
        email='tonti@example.com',
        first_name='Ton',
        last_name='Ti',
        role='user',
        is_active=True,
        phone_number='0999999999'
    )

    session.execute(new_user)
    session.commit()



def downgrade() -> None:
    pass
