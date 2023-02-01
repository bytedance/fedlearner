"""create table events_v2

Revision ID: 7cf3168e68fb
Revises: 3b4198785f3d
Create Date: 2021-09-25 13:37:11.752303

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '7cf3168e68fb'
down_revision = '3b4198785f3d'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('events_v2',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False, comment='auto-incremented id'),
    sa.Column('uuid', sa.String(length=255), nullable=False, comment='UUID of the event'),
    sa.Column('name', sa.String(length=255), nullable=False, comment='the name of the event'),
    sa.Column('user_id', sa.Integer(), nullable=False, comment='the ID of the user who triggered the event'),
    sa.Column('resource_type', sa.Enum('IAM', 'WORKSPACE', 'TEMPLATE', 'WORKFLOW', 'DATASET', 'MODEL', 'USER', 'SYSTEM', 'PARTICIPANT', name='resource_type', native_enum=False, length=32, create_constraint=False), nullable=False, comment='the type of the resource'),
    sa.Column('resource_name', sa.String(length=512), nullable=False, comment='the name of the resource'),
    sa.Column('op_type', sa.Enum('CREATE', 'DELETE', 'UPDATE', name='op_type', native_enum=False, length=32, create_constraint=False), nullable=False, comment='the type of the operation of the event'),
    sa.Column('result', sa.Enum('SUCCESS', 'FAILURE', name='result', native_enum=False, length=32, create_constraint=False), nullable=False, comment='the result of the operation'),
    sa.Column('source', sa.Enum('UI', 'API', name='source', native_enum=False, length=32, create_constraint=False), nullable=False, comment='the source that triggered the event'),
    sa.Column('extra', sa.Text(), nullable=True, comment='extra info in JSON'),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True, comment='created at'),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True, comment='updated at'),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True, comment='deleted at'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('uuid', name='uniq_uuid'),
    comment='webconsole audit events',
    mysql_charset='utf8mb4',
    mysql_engine='innodb'
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('events_v2')
    # ### end Alembic commands ###
