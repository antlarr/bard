"""dr14 table

Revision ID: c41cf2cd9ac6
Revises: 9c004703b14a
Create Date: 2024-05-11 10:22:02.033633

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c41cf2cd9ac6'
down_revision = '9c004703b14a'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('dynamic_range_data',
    sa.Column('song_id', sa.Integer(), nullable=False),
    sa.Column('dr14', sa.Integer(), nullable=False),
    sa.Column('db_peak', sa.REAL(), nullable=False),
    sa.Column('db_rms', sa.REAL(), nullable=False),
    sa.Column('insert_time', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
    sa.ForeignKeyConstraint(['song_id'], ['songs.id'], ondelete='CASCADE')
    )
    op.create_index('dynamic_range_data_song_id_idx', 'dynamic_range_data', ['song_id'], unique=False)


def downgrade():
    op.drop_index('dynamic_range_data_song_id_idx', table_name='dynamic_range_data')
    op.drop_table('dynamic_range_data')
