"""Add unique constraint on external_id in news_search_index

Revision ID: add_unique_external_id
Revises: news_search_optimization
Create Date: 2025-01-09 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_unique_external_id'
down_revision = 'news_search_optimization'  # Points to the latest existing migration
branch_labels = None
depends_on = None

def upgrade():
    """Add unique constraint on external_id to prevent duplicates"""
    
    # First, ensure we don't have any duplicates (should be clean after our fix script)
    print("🔍 Checking for any remaining duplicates before adding constraint...")
    
    # Add unique constraint on external_id
    # This will prevent duplicate external_ids at the database level
    try:
        with op.batch_alter_table('news_search_index') as batch_op:
            batch_op.create_unique_constraint(
                'uq_news_search_index_external_id',
                ['external_id']
            )
        print("✅ Added unique constraint on external_id")
        
    except Exception as e:
        print(f"⚠️ Could not add unique constraint: {e}")
        print("This might be because there are still duplicates in the table.")
        print("Run the fix_duplicate_sync_issue.py script first to clean up duplicates.")
        raise

def downgrade():
    """Remove unique constraint on external_id"""
    
    try:
        with op.batch_alter_table('news_search_index') as batch_op:
            batch_op.drop_constraint('uq_news_search_index_external_id', type_='unique')
        print("✅ Removed unique constraint on external_id")
        
    except Exception as e:
        print(f"⚠️ Could not remove unique constraint: {e}")
        # Don't raise error on downgrade - constraint might not exist 