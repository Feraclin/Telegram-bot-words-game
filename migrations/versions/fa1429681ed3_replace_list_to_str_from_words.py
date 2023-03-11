"""replace list to str from words

Revision ID: fa1429681ed3
Revises: 9e5c6abfb6c4
Create Date: 2023-03-09 21:51:03.326641

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'fa1429681ed3'
down_revision = '9e5c6abfb6c4'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('game_sessions', 'words',
                    existing_type=sa.ARRAY(sa.VARCHAR()),
                    type_=sa.VARCHAR(),
                    postgresql_using='words::character varying[]',
                    existing_nullable=False)
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('game_sessions', 'words',
                    existing_type=sa.VARCHAR(),
                    type_=sa.ARRAY(sa.VARCHAR()),
                    postgresql_using='words::character varying[]',
                    existing_nullable=False)

    # ### end Alembic commands ###

