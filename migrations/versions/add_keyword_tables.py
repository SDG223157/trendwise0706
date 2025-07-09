"""Add keyword tables for AI-powered search suggestions

Revision ID: add_keyword_tables
Revises: add_ai_fields_search
Create Date: 2025-01-20 15:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_keyword_tables'
down_revision = 'add_ai_fields_search'
branch_labels = None
depends_on = None

def upgrade():
    """Add keyword tables for AI-powered search suggestions"""
    
    print("Creating keyword tables for AI-powered search suggestions...")
    
    # Create news_keywords table
    op.create_table('news_keywords',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('keyword', sa.String(100), nullable=False),
        sa.Column('normalized_keyword', sa.String(100), nullable=False),
        sa.Column('category', sa.String(50), nullable=False),
        sa.Column('relevance_score', sa.Float(), default=0.0),
        sa.Column('frequency', sa.Integer(), default=1),
        sa.Column('sentiment_association', sa.Float(), default=0.0),
        sa.Column('first_seen', sa.DateTime(), default=sa.func.now()),
        sa.Column('last_seen', sa.DateTime(), default=sa.func.now()),
        sa.Column('created_at', sa.DateTime(), default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), default=sa.func.now(), onupdate=sa.func.now()),
        sa.UniqueConstraint('normalized_keyword', 'category')
    )
    
    # Create indexes for news_keywords
    op.create_index('idx_keyword_relevance', 'news_keywords', ['keyword', 'relevance_score'])
    op.create_index('idx_keyword_frequency', 'news_keywords', ['keyword', 'frequency'])
    op.create_index('idx_keyword_category_relevance', 'news_keywords', ['category', 'relevance_score'])
    op.create_index('idx_keyword_search', 'news_keywords', ['normalized_keyword', 'category', 'frequency'])
    op.create_index('idx_keyword_normalized', 'news_keywords', ['normalized_keyword'])
    op.create_index('idx_keyword_category', 'news_keywords', ['category'])
    op.create_index('idx_keyword_frequency_single', 'news_keywords', ['frequency'])
    op.create_index('idx_keyword_relevance_single', 'news_keywords', ['relevance_score'])
    op.create_index('idx_keyword_first_seen', 'news_keywords', ['first_seen'])
    op.create_index('idx_keyword_last_seen', 'news_keywords', ['last_seen'])
    
    # Create article_keywords table
    op.create_table('article_keywords',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('article_id', sa.Integer(), 
                 sa.ForeignKey('news_articles.id', ondelete='CASCADE'), 
                 nullable=False),
        sa.Column('keyword_id', sa.Integer(), 
                 sa.ForeignKey('news_keywords.id', ondelete='CASCADE'), 
                 nullable=False),
        sa.Column('relevance_in_article', sa.Float(), default=0.0),
        sa.Column('extraction_source', sa.String(20), default='ai_summary'),
        sa.Column('position_weight', sa.Float(), default=1.0),
        sa.Column('created_at', sa.DateTime(), default=sa.func.now()),
        sa.UniqueConstraint('article_id', 'keyword_id')
    )
    
    # Create indexes for article_keywords
    op.create_index('idx_article_keyword_relevance', 'article_keywords', ['article_id', 'relevance_in_article'])
    op.create_index('idx_keyword_article_relevance', 'article_keywords', ['keyword_id', 'relevance_in_article'])
    op.create_index('idx_article_id', 'article_keywords', ['article_id'])
    op.create_index('idx_keyword_id', 'article_keywords', ['keyword_id'])
    
    # Create keyword_similarities table
    op.create_table('keyword_similarities',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('keyword1_id', sa.Integer(), 
                 sa.ForeignKey('news_keywords.id', ondelete='CASCADE'), 
                 nullable=False),
        sa.Column('keyword2_id', sa.Integer(), 
                 sa.ForeignKey('news_keywords.id', ondelete='CASCADE'), 
                 nullable=False),
        sa.Column('similarity_score', sa.Float(), nullable=False),
        sa.Column('relationship_type', sa.String(50), default='semantic'),
        sa.Column('confidence', sa.Float(), default=0.0),
        sa.Column('created_at', sa.DateTime(), default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), default=sa.func.now(), onupdate=sa.func.now()),
        sa.UniqueConstraint('keyword1_id', 'keyword2_id')
    )
    
    # Create indexes for keyword_similarities
    op.create_index('idx_similarity_score', 'keyword_similarities', ['similarity_score'])
    op.create_index('idx_keyword_similarity', 'keyword_similarities', ['keyword1_id', 'similarity_score'])
    op.create_index('idx_keyword1_id', 'keyword_similarities', ['keyword1_id'])
    op.create_index('idx_keyword2_id', 'keyword_similarities', ['keyword2_id'])
    
    # Create search_analytics table
    op.create_table('search_analytics',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('user_id', sa.Integer(), 
                 sa.ForeignKey('users.id', ondelete='SET NULL'), 
                 nullable=True),
        sa.Column('session_id', sa.String(100), nullable=False),
        sa.Column('search_query', sa.String(500), nullable=False),
        sa.Column('search_type', sa.String(20), nullable=False),
        sa.Column('results_count', sa.Integer(), default=0),
        sa.Column('clicked_suggestions', sa.Text(), nullable=True),
        sa.Column('selected_keywords', sa.Text(), nullable=True),
        sa.Column('search_duration_ms', sa.Integer(), default=0),
        sa.Column('result_clicked', sa.Boolean(), default=False),
        sa.Column('search_satisfied', sa.Boolean(), nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(), default=sa.func.now()),
    )
    
    # Create indexes for search_analytics
    op.create_index('idx_search_analytics_query', 'search_analytics', ['search_query'])
    op.create_index('idx_search_analytics_time', 'search_analytics', ['created_at'])
    op.create_index('idx_search_analytics_session', 'search_analytics', ['session_id', 'created_at'])
    op.create_index('idx_search_analytics_user_time', 'search_analytics', ['user_id', 'created_at'])
    op.create_index('idx_search_analytics_user_id', 'search_analytics', ['user_id'])
    op.create_index('idx_search_analytics_session_id', 'search_analytics', ['session_id'])
    op.create_index('idx_search_analytics_type', 'search_analytics', ['search_type'])
    
    print("✅ Keyword tables created successfully!")
    print("🔄 Next steps:")
    print("   1. Run keyword extraction: python extract_keywords_from_articles.py")
    print("   2. Test search suggestions: curl '/news/api/suggestions?q=artificial'")
    print("   3. Monitor analytics: check /news/api/analytics/suggestions")

def downgrade():
    """Remove keyword tables"""
    print("Removing keyword tables...")
    
    # Drop tables in reverse order (due to foreign key constraints)
    op.drop_table('search_analytics')
    op.drop_table('keyword_similarities')
    op.drop_table('article_keywords')
    op.drop_table('news_keywords')
    
    print("✅ Keyword tables removed successfully!") 