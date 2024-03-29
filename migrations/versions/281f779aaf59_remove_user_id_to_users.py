"""remove user_id to users

Revision ID: 281f779aaf59
Revises: 5e5be1d7003e
Create Date: 2023-02-23 06:26:28.219800

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '281f779aaf59'
down_revision = '5e5be1d7003e'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint('users_user_id_key', 'users', type_='unique')
    op.drop_column('users', 'user_id')
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('users', sa.Column('user_id', sa.INTEGER(), autoincrement=False, nullable=False))
    op.create_unique_constraint('users_user_id_key', 'users', ['user_id'])
    # ### end Alembic commands ###
