"""add local_extra field to workflow

Revision ID: e5d91f0f59a7
Revises: b659f5763a27
Create Date: 2021-06-24 16:43:39.271702

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'e5d91f0f59a7'
down_revision = 'b659f5763a27'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        'workflow_v2',
        sa.Column('local_extra',
                  sa.Text(),
                  nullable=True,
                  comment='local_extra'))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('workflow_v2', 'local_extra')
    # ### end Alembic commands ###
