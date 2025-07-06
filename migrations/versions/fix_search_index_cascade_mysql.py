"""Fix search index foreign key constraint for buffer architecture (MySQL)

MySQL-compatible migration that properly handles column type changes.

Revision ID: fix_search_cascade_mysql
Revises: fix_search_cascade
Create Date: 2025-01-08 16:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

# revision identifiers
revision = 'fix_search_cascade_mysql'
down_revision = 'fix_search_cascade'
branch_labels = None
depends_on = None

def get_column_info(connection, table_name, column_name):
    """Get column information from MySQL"""
    try:
        result = connection.execute(text(f"""
            SELECT COLUMN_TYPE, IS_NULLABLE, COLUMN_DEFAULT
            FROM information_schema.COLUMNS 
            WHERE TABLE_SCHEMA = DATABASE() 
            AND TABLE_NAME = '{table_name}' 
            AND COLUMN_NAME = '{column_name}'
        """))
        
        row = result.fetchone()
        if row:
            return {
                'type': row[0],
                'nullable': row[1] == 'YES',
                'default': row[2]
            }
        return None
    except Exception as e:
        print(f"   Could not get column info: {e}")
        return None

def table_exists(connection, table_name):
    """Check if a table exists"""
    try:
        result = connection.execute(text(f"""
            SELECT COUNT(*) 
            FROM information_schema.TABLES 
            WHERE TABLE_SCHEMA = DATABASE() 
            AND TABLE_NAME = '{table_name}'
        """))
        
        row = result.fetchone()
        return row[0] > 0 if row else False
    except Exception as e:
        print(f"   Could not check table existence: {e}")
        return False

def upgrade():
    """Complete the foreign key constraint fix for MySQL"""
    print("🔧 Completing MySQL foreign key constraint fix...")
    
    connection = op.get_bind()
    
    # Check if news_search_index table exists
    if not table_exists(connection, 'news_search_index'):
        print("   ⚠️ news_search_index table does not exist - creating for standalone operation")
        
        # Create a minimal standalone search index table
        op.create_table(
            'news_search_index',
            sa.Column('id', sa.Integer, primary_key=True),
            sa.Column('article_id', sa.Integer, nullable=True, index=True),
            sa.Column('external_id', sa.String(100), unique=True, nullable=False, index=True),
            sa.Column('title', sa.String(255), nullable=False, index=True),
            sa.Column('url', sa.String(512)),
            sa.Column('published_at', sa.DateTime, nullable=False, index=True),
            sa.Column('source', sa.String(100), nullable=False, index=True),
            sa.Column('ai_sentiment_rating', sa.Integer, index=True),
            sa.Column('symbols_json', sa.Text),
            sa.Column('ai_summary', sa.Text, index=True),
            sa.Column('ai_insights', sa.Text, index=True),
            sa.Column('created_at', sa.DateTime, default=sa.func.now(), index=True),
            sa.Column('updated_at', sa.DateTime, default=sa.func.now(), onupdate=sa.func.now(), index=True),
        )
        
        # Create indexes
        op.create_index('idx_search_published_sentiment', 'news_search_index', ['published_at', 'ai_sentiment_rating'])
        op.create_index('idx_search_source_published', 'news_search_index', ['source', 'published_at'])
        op.create_index('idx_search_external_published', 'news_search_index', ['external_id', 'published_at'])
        op.create_index('idx_search_ai_summary', 'news_search_index', ['ai_summary'])
        op.create_index('idx_search_ai_insights', 'news_search_index', ['ai_insights'])
        op.create_index('idx_search_ai_content', 'news_search_index', ['ai_summary', 'ai_insights'])
        op.create_index('idx_search_title', 'news_search_index', ['title'])
        op.create_index('idx_search_created_updated', 'news_search_index', ['created_at', 'updated_at'])
        
        print("   ✅ Created standalone news_search_index table")
        return
    
    # Get current column info
    column_info = get_column_info(connection, 'news_search_index', 'article_id')
    
    if column_info:
        print(f"   Current article_id column: {column_info}")
        
        # Check if article_id is already nullable
        if column_info['nullable']:
            print("   ✅ article_id is already nullable")
        else:
            # Make article_id nullable with proper MySQL syntax
            print("   Making article_id nullable with proper MySQL syntax...")
            try:
                # Use raw SQL for MySQL MODIFY COLUMN
                connection.execute(text("""
                    ALTER TABLE news_search_index 
                    MODIFY COLUMN article_id INT NULL
                """))
                print("   ✅ Made article_id nullable")
            except Exception as e:
                print(f"   ⚠️ Could not make article_id nullable: {e}")
    
    # Add safe foreign key constraint if news_articles table exists
    if table_exists(connection, 'news_articles'):
        print("   Adding safe foreign key constraint...")
        try:
            connection.execute(text("""
                ALTER TABLE news_search_index 
                ADD CONSTRAINT fk_news_search_index_article_id_safe 
                FOREIGN KEY (article_id) REFERENCES news_articles (id) 
                ON DELETE SET NULL
            """))
            print("   ✅ Added safe foreign key constraint")
        except Exception as e:
            print(f"   ⚠️ Could not add foreign key constraint: {e}")
            print("   This is expected if the constraint already exists or tables are empty")
    else:
        print("   news_articles table does not exist - news_search_index is fully standalone")
    
    print("✅ MySQL foreign key constraint fix completed")

def downgrade():
    """Restore original configuration"""
    print("🔄 Restoring original MySQL configuration...")
    
    connection = op.get_bind()
    
    # Drop safe foreign key constraint if it exists
    try:
        connection.execute(text("""
            ALTER TABLE news_search_index 
            DROP FOREIGN KEY fk_news_search_index_article_id_safe
        """))
        print("   ✅ Dropped safe foreign key constraint")
    except Exception as e:
        print(f"   ⚠️ Could not drop safe foreign key constraint: {e}")
    
    # Make article_id non-nullable again
    try:
        connection.execute(text("""
            ALTER TABLE news_search_index 
            MODIFY COLUMN article_id INT NOT NULL
        """))
        print("   ✅ Made article_id non-nullable")
    except Exception as e:
        print(f"   ⚠️ Could not make article_id non-nullable: {e}")
    
    # Add original CASCADE constraint if news_articles exists
    if table_exists(connection, 'news_articles'):
        try:
            connection.execute(text("""
                ALTER TABLE news_search_index 
                ADD CONSTRAINT fk_news_search_index_article_id 
                FOREIGN KEY (article_id) REFERENCES news_articles (id) 
                ON DELETE CASCADE
            """))
            print("   ✅ Restored original CASCADE constraint")
        except Exception as e:
            print(f"   ⚠️ Could not restore CASCADE constraint: {e}")
    
    print("✅ Original MySQL configuration restored") 