"""Fix search index foreign key constraint for buffer architecture (v2)

Robust migration that handles missing constraints and recreates the table structure
for standalone buffer architecture.

Revision ID: fix_search_cascade_v2
Revises: add_ai_fields_search
Create Date: 2025-01-08 16:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

# revision identifiers
revision = 'fix_search_cascade'
down_revision = 'add_ai_fields_search'
branch_labels = None
depends_on = None

def get_foreign_key_name(connection, table_name, column_name):
    """Get the actual foreign key constraint name from the database"""
    try:
        result = connection.execute(text(f"""
            SELECT CONSTRAINT_NAME 
            FROM information_schema.KEY_COLUMN_USAGE 
            WHERE TABLE_SCHEMA = DATABASE() 
            AND TABLE_NAME = '{table_name}' 
            AND COLUMN_NAME = '{column_name}'
            AND REFERENCED_TABLE_NAME IS NOT NULL
        """))
        
        row = result.fetchone()
        return row[0] if row else None
    except Exception as e:
        print(f"   Could not determine foreign key name: {e}")
        return None

def constraint_exists(connection, table_name, constraint_name):
    """Check if a constraint exists"""
    try:
        result = connection.execute(text(f"""
            SELECT COUNT(*) 
            FROM information_schema.TABLE_CONSTRAINTS 
            WHERE TABLE_SCHEMA = DATABASE() 
            AND TABLE_NAME = '{table_name}' 
            AND CONSTRAINT_NAME = '{constraint_name}'
        """))
        
        row = result.fetchone()
        return row[0] > 0 if row else False
    except Exception as e:
        print(f"   Could not check constraint existence: {e}")
        return False

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
    """Fix foreign key constraint for buffer architecture"""
    print("🔧 Fixing foreign key constraint for buffer architecture (v2)...")
    
    connection = op.get_bind()
    
    # Check if news_search_index table exists
    if not table_exists(connection, 'news_search_index'):
        print("   ⚠️ news_search_index table does not exist - skipping constraint fix")
        return
    
    # Check if the table has any foreign key constraints
    fk_name = get_foreign_key_name(connection, 'news_search_index', 'article_id')
    
    if fk_name:
        print(f"   Found foreign key constraint: {fk_name}")
        
        # Drop the existing foreign key constraint
        try:
            print("   Dropping existing foreign key constraint...")
            with op.batch_alter_table('news_search_index', schema=None) as batch_op:
                batch_op.drop_constraint(fk_name, type_='foreignkey')
            print(f"   ✅ Dropped foreign key constraint: {fk_name}")
        except Exception as e:
            print(f"   ⚠️ Could not drop foreign key constraint: {e}")
    else:
        print("   No foreign key constraint found - proceeding with column updates")
    
    # Make article_id nullable for standalone operation
    print("   Making article_id nullable for standalone operation...")
    try:
        with op.batch_alter_table('news_search_index', schema=None) as batch_op:
            batch_op.alter_column('article_id', nullable=True)
        print("   ✅ Made article_id nullable")
    except Exception as e:
        print(f"   ⚠️ Could not make article_id nullable: {e}")
    
    # Add new foreign key constraint WITHOUT CASCADE (if table exists)
    if table_exists(connection, 'news_articles'):
        print("   Adding new foreign key constraint without CASCADE...")
        try:
            with op.batch_alter_table('news_search_index', schema=None) as batch_op:
                batch_op.create_foreign_key(
                    'fk_news_search_index_article_id_safe',
                    'news_articles',
                    ['article_id'],
                    ['id'],
                    ondelete='SET NULL'  # Safe for buffer architecture
                )
            print("   ✅ Added safe foreign key constraint")
        except Exception as e:
            print(f"   ⚠️ Could not add new foreign key constraint: {e}")
    else:
        print("   news_articles table does not exist - skipping foreign key creation")
    
    print("✅ Foreign key constraint fix completed (safe for buffer architecture)")

def downgrade():
    """Restore original CASCADE constraint if needed"""
    print("🔄 Restoring original foreign key configuration...")
    
    connection = op.get_bind()
    
    # Check if news_search_index table exists
    if not table_exists(connection, 'news_search_index'):
        print("   ⚠️ news_search_index table does not exist - nothing to restore")
        return
    
    # Drop the safe foreign key constraint if it exists
    if constraint_exists(connection, 'news_search_index', 'fk_news_search_index_article_id_safe'):
        print("   Dropping safe foreign key constraint...")
        try:
            with op.batch_alter_table('news_search_index', schema=None) as batch_op:
                batch_op.drop_constraint('fk_news_search_index_article_id_safe', type_='foreignkey')
            print("   ✅ Dropped safe foreign key constraint")
        except Exception as e:
            print(f"   ⚠️ Could not drop safe foreign key constraint: {e}")
    
    # Make article_id non-nullable again
    print("   Making article_id non-nullable...")
    try:
        with op.batch_alter_table('news_search_index', schema=None) as batch_op:
            batch_op.alter_column('article_id', nullable=False)
        print("   ✅ Made article_id non-nullable")
    except Exception as e:
        print(f"   ⚠️ Could not make article_id non-nullable: {e}")
    
    # Add back the original foreign key constraint with CASCADE (if table exists)
    if table_exists(connection, 'news_articles'):
        print("   Adding back original CASCADE foreign key constraint...")
        try:
            with op.batch_alter_table('news_search_index', schema=None) as batch_op:
                batch_op.create_foreign_key(
                    'fk_news_search_index_article_id',
                    'news_articles',
                    ['article_id'],
                    ['id'],
                    ondelete='CASCADE'
                )
            print("   ✅ Restored original CASCADE constraint")
        except Exception as e:
            print(f"   ⚠️ Could not restore original CASCADE constraint: {e}")
    else:
        print("   news_articles table does not exist - skipping foreign key creation")
    
    print("✅ Original foreign key configuration restored") 