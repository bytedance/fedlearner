"""add_username_to_workflow

Revision ID: c06f66dbebc1
Revises: cf4d3ba429e0
Create Date: 2021-10-09 19:03:18.301277

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c06f66dbebc1'
down_revision = 'cf4d3ba429e0'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('workflow_v2', sa.Column('creator', sa.String(length=255), nullable=True, comment='the username of the creator'))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('workflow_v2', 'creator')
    # ### end Alembic commands ###
