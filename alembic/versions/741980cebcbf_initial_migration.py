"""Initial Migration

Revision ID: 741980cebcbf
Revises: 
Create Date: 2026-07-06 07:38:03.288840

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '741980cebcbf'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("""
        CREATE EXTENSION IF NOT EXISTS vector;
        
        ALTER EXTENSION vector UPDATE;
        
        CREATE TABLE documents (
	        document_id bigserial PRIMARY KEY,
	        name        varchar   NOT NULL 
        );
        
        CREATE TABLE chunks (
	        chunk_id      bigserial PRIMARY KEY,
	        document_id   int8 REFERENCES documents(document_id) NOT NULL,
	        chunk_content text                                   NOT NULL,
	        chunk_order   int                                    NOT NULL,
	        embeddings    halfvec(3072)                           NOT NULL 
        );
        
        CREATE INDEX ON chunks USING ivfflat (embeddings halfvec_cosine_ops) WITH (lists = 100);
        """)


def downgrade() -> None:
    """Downgrade schema."""
    pass
