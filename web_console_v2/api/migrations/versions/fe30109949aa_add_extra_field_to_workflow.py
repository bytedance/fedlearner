"""add extra field to workflow

Revision ID: fe30109949aa
Revises: 27a868485bf7
Create Date: 2021-06-06 14:31:29.833200

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'fe30109949aa'
down_revision = '27a868485bf7'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('workflow_v2', sa.Column('extra', sa.Text(), nullable=True, comment='extra'))


def downgrade():
    op.drop_column('workflow_v2', 'extra')
