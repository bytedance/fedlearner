"""add user sso name

Revision ID: ed5502db91ec
Revises: efc25abe02fa
Create Date: 2021-08-31 13:23:19.444151

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'ed5502db91ec'
down_revision = 'efc25abe02fa'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('users_v2', sa.Column('sso_name', sa.String(length=255), nullable=True, comment='sso_name'))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('users_v2', 'sso_name')
    # ### end Alembic commands ###
