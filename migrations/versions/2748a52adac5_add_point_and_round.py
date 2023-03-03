"""add point and round

Revision ID: 2748a52adac5
Revises: c1e82216ea0b
Create Date: 2023-03-01 12:51:23.494635

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2748a52adac5'
down_revision = 'c1e82216ea0b'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('teams', sa.Column('round_', sa.Integer(), nullable=True))
    op.add_column('teams', sa.Column('point', sa.Integer(), nullable=True))
    op.add_column('users', sa.Column('total_point', sa.Integer(), nullable=True))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('users', 'total_point')
    op.drop_column('teams', 'point')
    op.drop_column('teams', 'round_')
    # ### end Alembic commands ###
