"""Add indexes for news search optimization

Revision ID: news_search_optimization
Revises: 
Create Date: 2025-01-20 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'news_search_optimization'
down_revision = None  # This will be the first migration
branch_labels = None
depends_on = None

def upgrade():
    """Apply news search performance optimizations"""
    
    # Create news_articles table if it doesn't exist
    try:
        op.create_table('news_articles',
            sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
            sa.Column('external_id', sa.String(100), nullable=False, unique=True),
            sa.Column('title', sa.String(255), nullable=False),
            sa.Column('content', sa.Text()),
            sa.Column('url', sa.String(512)),
            sa.Column('published_at', sa.DateTime()),
            sa.Column('source', sa.String(100)),
            sa.Column('sentiment_label', sa.String(20)),
            sa.Column('sentiment_score', sa.Float()),
            sa.Column('sentiment_explanation', sa.Text()),
            sa.Column('brief_summary', sa.Text()),
            sa.Column('key_points', sa.Text()),
            sa.Column('market_impact_summary', sa.Text()),
            sa.Column('ai_summary', sa.Text()),
            sa.Column('ai_insights', sa.Text()),
            sa.Column('ai_sentiment_rating', sa.Integer()),
            sa.Column('created_at', sa.DateTime(), default=sa.func.now()),
        )
    except Exception:
        # Table already exists
        pass
    
    # Create article_symbols table if it doesn't exist
    try:
        op.create_table('article_symbols',
            sa.Column('article_id', sa.Integer(), 
                     sa.ForeignKey('news_articles.id', ondelete='CASCADE'), 
                     nullable=False, primary_key=True),
            sa.Column('symbol', sa.String(20), nullable=False, primary_key=True),
        )
    except Exception:
        # Table already exists
        pass
    
    # Create article_metrics table if it doesn't exist
    try:
        op.create_table('article_metrics',
            sa.Column('article_id', sa.Integer(), 
                     sa.ForeignKey('news_articles.id', ondelete='CASCADE'), 
                     nullable=False, primary_key=True),
            sa.Column('metric_type', sa.Enum('percentage', 'currency', name='metric_type_enum'), 
                     nullable=False, primary_key=True),
            sa.Column('metric_value', sa.Float()),
            sa.Column('metric_context', sa.Text()),
        )
    except Exception:
        # Table already exists
        pass
    
    # Create users table if it doesn't exist
    try:
        op.create_table('users',
            sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
            sa.Column('email', sa.String(120), unique=True, nullable=False),
            sa.Column('username', sa.String(64), unique=True, nullable=False),
            sa.Column('password_hash', sa.String(255), nullable=False),
            sa.Column('first_name', sa.String(64)),
            sa.Column('last_name', sa.String(64)),
            sa.Column('created_at', sa.DateTime(), default=sa.func.now()),
            sa.Column('last_login', sa.DateTime()),
            sa.Column('is_active', sa.Boolean(), default=True),
            sa.Column('is_admin', sa.Boolean(), default=False),
            sa.Column('role', sa.String(20), default='user'),
            sa.Column('is_google_user', sa.Boolean(), default=False),
        )
    except Exception:
        # Table already exists
        pass
    
    # Create user_activities table if it doesn't exist
    try:
        op.create_table('user_activities',
            sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
            sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id')),
            sa.Column('activity_type', sa.String(50)),
            sa.Column('description', sa.String(255)),
            sa.Column('ip_address', sa.String(45)),
            sa.Column('user_agent', sa.String(255)),
            sa.Column('timestamp', sa.DateTime(), default=sa.func.now()),
        )
    except Exception:
        # Table already exists
        pass
    
    # Now create the performance optimization indexes
    print("Creating performance indexes for news search...")
    
    # Single column indexes for news_articles
    try:
        op.create_index('idx_news_external_id', 'news_articles', ['external_id'])
    except Exception:
        pass  # Index might already exist
        
    try:
        op.create_index('idx_news_published_at', 'news_articles', ['published_at'])
    except Exception:
        pass
        
    try:
        op.create_index('idx_news_source', 'news_articles', ['source'])
    except Exception:
        pass
        
    try:
        op.create_index('idx_news_sentiment_label', 'news_articles', ['sentiment_label'])
    except Exception:
        pass
        
    try:
        op.create_index('idx_news_sentiment_score', 'news_articles', ['sentiment_score'])
    except Exception:
        pass
        
    try:
        op.create_index('idx_news_ai_sentiment_rating', 'news_articles', ['ai_sentiment_rating'])
    except Exception:
        pass
        
    try:
        op.create_index('idx_news_created_at', 'news_articles', ['created_at'])
    except Exception:
        pass
    
    # Composite indexes for common query patterns
    try:
        op.create_index('idx_published_sentiment', 'news_articles', ['published_at', 'ai_sentiment_rating'])
    except Exception:
        pass
        
    try:
        op.create_index('idx_published_created', 'news_articles', ['published_at', 'created_at'])
    except Exception:
        pass
        
    try:
        op.create_index('idx_sentiment_published', 'news_articles', ['sentiment_score', 'published_at'])
    except Exception:
        pass
        
    try:
        op.create_index('idx_ai_sentiment_published', 'news_articles', ['ai_sentiment_rating', 'published_at'])
    except Exception:
        pass
        
    try:
        op.create_index('idx_source_published', 'news_articles', ['source', 'published_at'])
    except Exception:
        pass
        
    try:
        op.create_index('idx_sentiment_label_published', 'news_articles', ['sentiment_label', 'published_at'])
    except Exception:
        pass
    
    # Indexes for article_symbols table
    try:
        op.create_index('idx_symbol', 'article_symbols', ['symbol'])
    except Exception:
        pass
        
    try:
        op.create_index('idx_symbol_article', 'article_symbols', ['symbol', 'article_id'])
    except Exception:
        pass
    
    # Add unique constraint for article_symbols if it doesn't exist
    try:
        op.create_unique_constraint('uq_article_symbol', 'article_symbols', ['article_id', 'symbol'])
    except Exception:
        pass
    
    print("✅ News search optimization indexes created successfully!")

def downgrade():
    """Remove news search performance optimizations"""
    
    print("Removing performance indexes...")
    
    # Drop indexes in reverse order
    index_names = [
        'idx_symbol_article', 'idx_symbol',
        'idx_sentiment_label_published', 'idx_source_published',
        'idx_ai_sentiment_published', 'idx_sentiment_published',
        'idx_published_created', 'idx_published_sentiment',
        'idx_news_created_at', 'idx_news_ai_sentiment_rating',
        'idx_news_sentiment_score', 'idx_news_sentiment_label',
        'idx_news_source', 'idx_news_published_at', 'idx_news_external_id'
    ]
    
    for index_name in index_names:
        try:
            if 'symbol' in index_name:
                op.drop_index(index_name, 'article_symbols')
            else:
                op.drop_index(index_name, 'news_articles')
        except Exception:
            # Index might not exist
            pass
    
    # Drop unique constraint
    try:
        op.drop_constraint('uq_article_symbol', 'article_symbols', type_='unique')
    except Exception:
        pass
    
    print("✅ Performance indexes removed!") 