"""add_2pc_transaction_table

Revision ID: ec68faa511cc
Revises: 8b179c0111a8
Create Date: 2021-10-21 14:22:43.292766

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'ec68faa511cc'
down_revision = '8b179c0111a8'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('transactions_v2',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False, comment='id'),
    sa.Column('uuid', sa.String(length=64), nullable=True, comment='uuid'),
    sa.Column('type', sa.String(length=32), nullable=True, comment='2pc type name'),
    sa.Column('state', sa.Enum('NEW', 'PREPARE_SUCCEEDED', 'PREPARE_FAILED', 'COMMITTED', 'ABORTED', 'INVALID', name='transactionstate', native_enum=False, create_constraint=False, length=32), nullable=True, comment='state'),
    sa.Column('message', sa.Text(), nullable=True, comment='message of the last action'),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True, comment='created_at'),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True, comment='update_at'),
    sa.PrimaryKeyConstraint('id'),
    comment='2pc transactions',
    mysql_charset='utf8mb4',
    mysql_engine='innodb'
    )
    op.create_index('uniq_uuid', 'transactions_v2', ['uuid'], unique=True)
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index('uniq_uuid', table_name='transactions_v2')
    op.drop_table('transactions_v2')
    # ### end Alembic commands ###
