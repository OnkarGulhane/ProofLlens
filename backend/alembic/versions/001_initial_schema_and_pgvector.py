"""initial schema and pgvector

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-10-12 19:35:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision: str = '001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Enable pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")

    # 2. Workspaces table
    op.create_table(
        'workspaces',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('idx_workspaces_id', 'workspaces', ['id'])

    # 3. Documents table
    op.create_table(
        'documents',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=False),
        sa.Column('filename', sa.String(length=255), nullable=False),
        sa.Column('file_path', sa.String(length=512), nullable=False),
        sa.Column('file_hash_sha256', sa.String(length=64), nullable=False),
        sa.Column('file_size_bytes', sa.Integer(), nullable=False),
        sa.Column('total_pages', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='PENDING'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('idx_documents_id', 'documents', ['id'])
    op.create_index('idx_documents_workspace_id', 'documents', ['workspace_id'])
    op.create_index('idx_documents_file_hash', 'documents', ['file_hash_sha256'])

    # 4. Document Pages table
    op.create_table(
        'document_pages',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('document_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('documents.id', ondelete='CASCADE'), nullable=False),
        sa.Column('page_number', sa.Integer(), nullable=False),
        sa.Column('raw_text', sa.Text(), nullable=False),
        sa.Column('character_count', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('document_id', 'page_number', name='uq_doc_page_number'),
    )
    op.create_index('idx_document_pages_document_id', 'document_pages', ['document_id'])

    # 5. Document Chunks table (with pgvector column)
    op.create_table(
        'document_chunks',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('document_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('documents.id', ondelete='CASCADE'), nullable=False),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=False),
        sa.Column('page_number', sa.Integer(), nullable=False),
        sa.Column('chunk_index', sa.Integer(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('token_count', sa.Integer(), nullable=False),
        sa.Column('embedding', Vector(1536), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('idx_chunks_id', 'document_chunks', ['id'])
    op.create_index('idx_chunks_workspace_id', 'document_chunks', ['workspace_id'])
    op.create_index('idx_chunks_doc_id', 'document_chunks', ['document_id'])
    op.create_index('idx_chunks_doc_page', 'document_chunks', ['document_id', 'page_number'])
    
    # HNSW vector index for fast cosine similarity search
    op.execute(
        "CREATE INDEX idx_chunks_embedding_hnsw ON document_chunks "
        "USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);"
    )

    # 6. Query Runs table
    op.create_table(
        'query_runs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=False),
        sa.Column('question', sa.Text(), nullable=False),
        sa.Column('selected_document_ids', postgresql.JSONB(), nullable=True),
        sa.Column('similarity_threshold', sa.Float(), nullable=False, server_default='0.65'),
        sa.Column('top_k', sa.Integer(), nullable=False, server_default='5'),
        sa.Column('execution_time_ms', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('idx_query_runs_workspace_id', 'query_runs', ['workspace_id'])

    # 7. Answers table
    op.create_table(
        'answers',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('query_run_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('query_runs.id', ondelete='CASCADE'), nullable=False, unique=True),
        sa.Column('answer_text', sa.Text(), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='SUCCESS'),
        sa.Column('is_abstained', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('abstention_reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('idx_answers_query_run_id', 'answers', ['query_run_id'])

    # 8. Retrieved Evidences table
    op.create_table(
        'retrieved_evidences',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('query_run_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('query_runs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('chunk_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('document_chunks.id', ondelete='CASCADE'), nullable=False),
        sa.Column('similarity_score', sa.Float(), nullable=False),
        sa.Column('rank', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('idx_retrieved_evidences_query_run_id', 'retrieved_evidences', ['query_run_id'])
    op.create_index('idx_retrieved_evidences_chunk_id', 'retrieved_evidences', ['chunk_id'])

    # 9. Citations table
    op.create_table(
        'citations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('answer_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('answers.id', ondelete='CASCADE'), nullable=False),
        sa.Column('chunk_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('document_chunks.id', ondelete='CASCADE'), nullable=False),
        sa.Column('document_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('documents.id', ondelete='CASCADE'), nullable=False),
        sa.Column('page_number', sa.Integer(), nullable=False),
        sa.Column('cited_excerpt', sa.Text(), nullable=False),
        sa.Column('verification_status', sa.String(length=32), nullable=False, server_default='VERIFIED'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('idx_citations_answer_id', 'citations', ['answer_id'])
    op.create_index('idx_citations_chunk_id', 'citations', ['chunk_id'])
    op.create_index('idx_citations_document_id', 'citations', ['document_id'])

    # 10. Comparison Runs table
    op.create_table(
        'comparison_runs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=False),
        sa.Column('topic', sa.Text(), nullable=False),
        sa.Column('document_ids', postgresql.JSONB(), nullable=False),
        sa.Column('comparison_matrix', postgresql.JSONB(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('idx_comparison_runs_workspace_id', 'comparison_runs', ['workspace_id'])

    # 11. Evaluation Runs table
    op.create_table(
        'evaluation_runs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=False),
        sa.Column('suite_name', sa.String(length=128), nullable=False),
        sa.Column('total_cases', sa.Integer(), nullable=False),
        sa.Column('passed_cases', sa.Integer(), nullable=False),
        sa.Column('retrieval_hit_rate', sa.Float(), nullable=False),
        sa.Column('citation_validity_rate', sa.Float(), nullable=False),
        sa.Column('abstention_accuracy', sa.Float(), nullable=False),
        sa.Column('raw_results', postgresql.JSONB(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('idx_evaluation_runs_workspace_id', 'evaluation_runs', ['workspace_id'])


def downgrade() -> None:
    op.drop_table('evaluation_runs')
    op.drop_table('comparison_runs')
    op.drop_table('citations')
    op.drop_table('retrieved_evidences')
    op.drop_table('answers')
    op.drop_table('query_runs')
    op.drop_table('document_chunks')
    op.drop_table('document_pages')
    op.drop_table('documents')
    op.drop_table('workspaces')
    op.execute("DROP EXTENSION IF EXISTS vector;")
