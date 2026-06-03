"""add German translation

Revision ID: d3f13671e778
Revises: 6035d97b0817
Create Date: 2026-06-03 08:36:02.820865

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd3f13671e778'
down_revision: Union[str, Sequence[str], None] = '6035d97b0817'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add the column as nullable first so existing rows can be updated
    op.add_column('pages', sa.Column('language', sa.String(), nullable=True))
    
    # 2. Update existing rows to have a default value ('en')
    op.execute("UPDATE pages SET language = 'en'")
    
    # 3. Now that no rows have NULL, we can safely set the column to NOT NULL
    op.alter_column('pages', 'language', nullable=False)
    
    # 4. Handle Primary Key change to support composite (slug, language)
    # The default primary key name in Postgres is 'tablename_pkey'
    op.drop_constraint('pages_pkey', 'pages', type_='primary')
    op.create_primary_key('pages_pkey', 'pages', ['slug', 'language'])
    
    # 5. Handle indices as detected by autogenerate
    op.create_index(op.f('ix_pages_language'), 'pages', ['language'], unique=False)
    # Drop the old index on slug if it exists (Alembic detected its removal)
    op.drop_index('ix_pages_slug', table_name='pages')


def downgrade() -> None:
    # 1. Restore the old index
    op.create_index('ix_pages_slug', 'pages', ['slug'], unique=False)
    
    # 2. Revert Primary Key to just 'slug'
    op.drop_index(op.f('ix_pages_language'), table_name='pages')
    op.drop_constraint('pages_pkey', 'pages', type_='primary')
    op.create_primary_key('pages_pkey', 'pages', ['slug'])
    
    # 3. Drop the column
    op.drop_column('pages', 'language')
