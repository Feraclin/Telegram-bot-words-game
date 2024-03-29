"""add user_id to users

Revision ID: 5e5be1d7003e
Revises: cfc7e26c24d9
Create Date: 2023-02-22 23:11:47.944145

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '5e5be1d7003e'
down_revision = 'cfc7e26c24d9'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('users', sa.Column('user_id', sa.Integer(), nullable=False))
    op.create_unique_constraint(None, 'users', ['user_id'])
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, 'users', type_='unique')
    op.drop_column('users', 'user_id')
    # ### end Alembic commands ###
