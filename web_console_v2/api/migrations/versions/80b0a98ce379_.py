"""empty message

Revision ID: 80b0a98ce379
Revises: b3512a6ce912
Create Date: 2021-03-18 21:11:17.902485

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql
# revision identifiers, used by Alembic.
revision = '80b0a98ce379'
down_revision = 'b3512a6ce912'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('workflow_v2', 'config', existing_type=sa.LargeBinary(), type_=sa.LargeBinary(16777216))
    op.alter_column('template_v2', 'config', existing_type=sa.LargeBinary(), type_=sa.LargeBinary(16777216))
    op.alter_column('workflow_v2', 'fork_proposal_config', existing_type=sa.LargeBinary(), type_=sa.LargeBinary(16777216))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('workflow_v2', 'config', existing_type=sa.LargeBinary(16777216), type_=mysql.BLOB)
    op.alter_column('template_v2', 'config', existing_type=sa.LargeBinary(16777216), type_=mysql.BLOB)
    op.alter_column('workflow_v2', 'fork_proposal_config', existing_type=sa.LargeBinary(16777216), type_=mysql.BLOB)
    # ### end Alembic commands ###
