"""Fix keyword table foreign keys to reference news_search_index

Revision ID: fix_keyword_fk
Revises: add_keyword_tables
Create Date: 2025-01-20 15:30:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'fix_keyword_fk'
down_revision = 'add_keyword_tables'
branch_labels = None
depends_on = None

def upgrade():
    """Fix foreign key constraint in article_keywords to reference news_search_index"""
    
    print("🔧 Fixing foreign key constraints in keyword tables...")
    
    # Drop the existing foreign key constraint
    print("   Dropping old foreign key constraint...")
    op.drop_constraint('article_keywords_ibfk_1', 'article_keywords', type_='foreignkey')
    
    # Add new foreign key constraint pointing to news_search_index
    print("   Adding new foreign key constraint to news_search_index...")
    op.create_foreign_key(
        'article_keywords_search_index_fk',
        'article_keywords',
        'news_search_index',
        ['article_id'],
        ['id'],
        ondelete='CASCADE'
    )
    
    print("✅ Foreign key constraints fixed successfully!")
    print("🔄 Now the article_keywords table correctly references news_search_index")
    print("   This allows keyword extraction from the permanent news_search_index table")

def downgrade():
    """Revert foreign key constraint back to news_articles"""
    
    print("🔧 Reverting foreign key constraints in keyword tables...")
    
    # Drop the new foreign key constraint
    print("   Dropping new foreign key constraint...")
    op.drop_constraint('article_keywords_search_index_fk', 'article_keywords', type_='foreignkey')
    
    # Add old foreign key constraint pointing to news_articles
    print("   Adding old foreign key constraint to news_articles...")
    op.create_foreign_key(
        'article_keywords_ibfk_1',
        'article_keywords',
        'news_articles',
        ['article_id'],
        ['id'],
        ondelete='CASCADE'
    )
    
    print("✅ Foreign key constraints reverted successfully!") 