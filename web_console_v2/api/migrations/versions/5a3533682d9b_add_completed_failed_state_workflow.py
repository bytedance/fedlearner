"""add_state_workflow

Revision ID: 5a3533682d9b
Revises: 40569c37cb87
Create Date: 2022-04-13 14:26:02.608377

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '5a3533682d9b'
down_revision = '815ae1dcd9db'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('workflow_v2', 'state', nullable=True, comment='state', type_=sa.Enum('INVALID', 'NEW', 'READY', 'RUNNING', 'STOPPED', 'COMPLETED', 'FAILED', name='workflow_state', native_enum=False, create_constraint=False, length=32))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('workflow_v2', 'state', nullable=True, comment='state', type_=sa.Enum('INVALID', 'NEW', 'READY', 'RUNNING', 'STOPPED', name='workflow_state', native_enum=False, create_constraint=False, length=7))
    # ### end Alembic commands ###
