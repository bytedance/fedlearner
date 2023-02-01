"""drop_old_dataset_kind_column

Revision ID: 7549e6d94cbb
Revises: 8bde5b704062
Create Date: 2022-06-27 13:04:30.412819

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '7549e6d94cbb'
down_revision = '8bde5b704062'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('datasets_v2', 'kind')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('datasets_v2', sa.Column('kind', mysql.INTEGER(), autoincrement=False, nullable=True, comment='dataset kind for different purposes'))
    # ### end Alembic commands ###
