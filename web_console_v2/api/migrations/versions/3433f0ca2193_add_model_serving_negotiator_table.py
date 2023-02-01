"""add model serving negotiator table

Revision ID: 3433f0ca2193
Revises: e9ce77d87969
Create Date: 2021-11-12 19:10:01.277875

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '3433f0ca2193'
down_revision = 'e9ce77d87969'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('serving_negotiators_v2',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False, comment='id'),
    sa.Column('project_id', sa.Integer(), nullable=False, comment='project id'),
    sa.Column('serving_model_id', sa.Integer(), nullable=False, comment='serving model id'),
    sa.Column('is_local', sa.Boolean(), nullable=True, comment='can serving locally'),
    sa.Column('with_label', sa.Boolean(), nullable=True, comment='federal side with label or not'),
    sa.Column('serving_model_uuid', sa.String(length=255), nullable=True, comment='uuid for federal model'),
    sa.Column('feature_dataset_id', sa.Integer(), nullable=True, comment='feature dataset id'),
    sa.Column('data_source_map', sa.Text(), nullable=True, comment='where to get model inference arguments'),
    sa.Column('raw_signature', sa.Text(), nullable=True, comment='save raw signature from tf serving'),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=True, comment='created_at'),
    sa.Column('extra', sa.Text(), nullable=True, comment='extra'),
    sa.PrimaryKeyConstraint('id'),
    comment='serving negotiators in webconsole',
    mysql_charset='utf8mb4',
    mysql_engine='innodb'
    )
    op.create_index('idx_serving_model_uuid', 'serving_negotiators_v2', ['serving_model_uuid'], unique=False)
    op.add_column('algorithms_v2', sa.Column('algorithm_project_id', sa.Integer(), nullable=True, comment='algorithm project id'))
    op.create_unique_constraint('uniq_source_name_version', 'algorithms_v2', ['source', 'name', 'version'])
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint('uniq_source_name_version', 'algorithms_v2', type_='unique')
    op.drop_column('algorithms_v2', 'algorithm_project_id')
    op.drop_index('idx_serving_model_uuid', table_name='serving_negotiators_v2')
    op.drop_table('serving_negotiators_v2')
    # ### end Alembic commands ###
