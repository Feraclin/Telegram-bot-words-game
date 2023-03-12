"""create_game_settings

Revision ID: 1fe91cbdaf6b
Revises: fa1429681ed3
Create Date: 2023-03-10 08:57:40.623059

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '1fe91cbdaf6b'
down_revision = 'fa1429681ed3'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('game_settings',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('response_time', sa.Integer(), nullable=False),
    sa.Column('anonymous_poll', sa.Boolean(), nullable=False),
    sa.Column('poll_time', sa.Integer(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('game_settings')
    # ### end Alembic commands ###
