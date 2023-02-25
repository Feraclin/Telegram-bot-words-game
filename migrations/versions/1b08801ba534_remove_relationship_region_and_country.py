"""remove relationship region and country

Revision ID: 1b08801ba534
Revises: 52c6200e6487
Create Date: 2023-02-23 08:41:20.617616

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '1b08801ba534'
down_revision = '52c6200e6487'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint('city_region_id_fkey', 'city', type_='foreignkey')
    op.drop_column('city', 'region_id')
    op.drop_constraint('region_country_id_fkey', 'region', type_='foreignkey')
    op.drop_column('region', 'country_id')
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('region', sa.Column('country_id', sa.INTEGER(), autoincrement=False, nullable=False))
    op.create_foreign_key('region_country_id_fkey', 'region', 'country', ['country_id'], ['id'], ondelete='CASCADE')
    op.add_column('city', sa.Column('region_id', sa.INTEGER(), autoincrement=False, nullable=False))
    op.create_foreign_key('city_region_id_fkey', 'city', 'region', ['region_id'], ['id'], ondelete='CASCADE')
    # ### end Alembic commands ###