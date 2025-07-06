"""Add AI fields to news_search_index for standalone AI search

Revision ID: add_ai_fields_search
Revises: news_search_optimization
Create Date: 2025-01-08 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

# revision identifiers
revision = 'add_ai_fields_search'
down_revision = 'add_news_search_index'
branch_labels = None
depends_on = None

def upgrade():
    """Add essential AI search fields to news_search_index table and remove unnecessary fields"""
    
    # Drop content_excerpt since it's no longer used for search
    op.drop_column('news_search_index', 'content_excerpt')
    
    # Add only essential AI fields for search
    op.add_column('news_search_index', sa.Column('ai_summary', sa.Text(), nullable=True))
    op.add_column('news_search_index', sa.Column('ai_insights', sa.Text(), nullable=True))
    
    # Remove old content_excerpt index and create AI search indexes
    op.drop_index('idx_search_title_content', 'news_search_index')
    op.create_index('idx_search_ai_summary', 'news_search_index', ['ai_summary'])
    op.create_index('idx_search_ai_insights', 'news_search_index', ['ai_insights'])
    op.create_index('idx_search_ai_content', 'news_search_index', ['ai_summary', 'ai_insights'])
    
    print("✅ Optimized news_search_index table for AI-only search")
    print("🗑️ Removed content_excerpt (no longer needed)")
    print("➕ Added ai_summary and ai_insights for search")
    print("🔄 Run populate_search_index_ai_data.py to migrate existing data")

def downgrade():
    """Revert news_search_index table changes"""
    
    # Drop AI indexes
    op.drop_index('idx_search_ai_content', 'news_search_index')
    op.drop_index('idx_search_ai_insights', 'news_search_index')
    op.drop_index('idx_search_ai_summary', 'news_search_index')
    
    # Drop AI columns
    op.drop_column('news_search_index', 'ai_insights')
    op.drop_column('news_search_index', 'ai_summary')
    
    # Add back content_excerpt and its index
    op.add_column('news_search_index', sa.Column('content_excerpt', sa.Text(), nullable=True))
    op.create_index('idx_search_title_content', 'news_search_index', ['title', 'content_excerpt'])
    
    print("❌ Reverted news_search_index table to original structure") 