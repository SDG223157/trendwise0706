"""Add news search index table

Revision ID: add_news_search_index
Revises: news_search_optimization
Create Date: 2025-01-20 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_news_search_index'
down_revision = 'news_search_optimization'
branch_labels = None
depends_on = None

def upgrade():
    """Create news search index table"""
    
    print("Creating news search index table...")
    
    # Create news_search_index table
    op.create_table('news_search_index',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('article_id', sa.Integer(), 
                 sa.ForeignKey('news_articles.id', ondelete='CASCADE'), 
                 nullable=False),
        sa.Column('external_id', sa.String(100), nullable=False, unique=True),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('content_excerpt', sa.Text()),
        sa.Column('url', sa.String(512)),
        sa.Column('published_at', sa.DateTime(), nullable=False),
        sa.Column('source', sa.String(100), nullable=False),
        sa.Column('sentiment_label', sa.String(20)),
        sa.Column('sentiment_score', sa.Float()),
        sa.Column('ai_sentiment_rating', sa.Integer()),
        sa.Column('symbols_json', sa.Text()),
        sa.Column('created_at', sa.DateTime(), default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), default=sa.func.now(), onupdate=sa.func.now()),
    )
    
    # Create indexes for optimal search performance
    print("Creating search indexes...")
    
    # Primary indexes
    op.create_index('idx_search_article_id', 'news_search_index', ['article_id'])
    op.create_index('idx_search_external_id', 'news_search_index', ['external_id'])
    op.create_index('idx_search_title', 'news_search_index', ['title'])
    op.create_index('idx_search_published_at', 'news_search_index', ['published_at'])
    op.create_index('idx_search_source', 'news_search_index', ['source'])
    op.create_index('idx_search_sentiment_label', 'news_search_index', ['sentiment_label'])
    op.create_index('idx_search_sentiment_score', 'news_search_index', ['sentiment_score'])
    op.create_index('idx_search_ai_sentiment_rating', 'news_search_index', ['ai_sentiment_rating'])
    op.create_index('idx_search_created_at', 'news_search_index', ['created_at'])
    op.create_index('idx_search_updated_at', 'news_search_index', ['updated_at'])
    
    # Composite indexes for common search patterns
    op.create_index('idx_search_published_sentiment', 'news_search_index', ['published_at', 'ai_sentiment_rating'])
    op.create_index('idx_search_source_published', 'news_search_index', ['source', 'published_at'])
    op.create_index('idx_search_sentiment_published', 'news_search_index', ['sentiment_score', 'published_at'])
    op.create_index('idx_search_external_published', 'news_search_index', ['external_id', 'published_at'])
    op.create_index('idx_search_title_content', 'news_search_index', ['title', 'content_excerpt'])
    op.create_index('idx_search_created_updated', 'news_search_index', ['created_at', 'updated_at'])
    
    print("✅ News search index table created successfully!")

def downgrade():
    """Remove news search index table"""
    
    print("Removing news search index table...")
    
    # Drop indexes first
    op.drop_index('idx_search_created_updated', 'news_search_index')
    op.drop_index('idx_search_title_content', 'news_search_index')
    op.drop_index('idx_search_external_published', 'news_search_index')
    op.drop_index('idx_search_sentiment_published', 'news_search_index')
    op.drop_index('idx_search_source_published', 'news_search_index')
    op.drop_index('idx_search_published_sentiment', 'news_search_index')
    op.drop_index('idx_search_updated_at', 'news_search_index')
    op.drop_index('idx_search_created_at', 'news_search_index')
    op.drop_index('idx_search_ai_sentiment_rating', 'news_search_index')
    op.drop_index('idx_search_sentiment_score', 'news_search_index')
    op.drop_index('idx_search_sentiment_label', 'news_search_index')
    op.drop_index('idx_search_source', 'news_search_index')
    op.drop_index('idx_search_published_at', 'news_search_index')
    op.drop_index('idx_search_title', 'news_search_index')
    op.drop_index('idx_search_external_id', 'news_search_index')
    op.drop_index('idx_search_article_id', 'news_search_index')
    
    # Drop table
    op.drop_table('news_search_index')
    
    print("✅ News search index table removed successfully!") 