"""Make discnumber nullable

Revision ID: a942e7027d58
Revises: c41cf2cd9ac6
Create Date: 2026-11-07 00:19:33.487292

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a942e7027d58'
down_revision = 'c41cf2cd9ac6'
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column('songs', 'discnumber', existing_type=sa.Integer,
                    nullable=True,
                    schema='public')
    op.execute(
        sa.update(sa.table('songs', sa.column('discnumber'), schema='public'))
        .values(discnumber=None)
        .where(sa.column('discnumber') == 0)
    )


def downgrade():
    op.execute(
        sa.update(sa.table('songs', sa.column('discnumber'), schema='public'))
        .values(discnumber=0)
        .where(sa.column('discnumber').is_(None))
    )
    op.alter_column('songs', 'discnumber', existing_type=sa.Integer,
                    nullable=False,
                    schema='public')
