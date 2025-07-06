#!/usr/bin/env python3
"""
Populate symbols_json from article_symbols table
Uses existing article_symbols relationships to populate symbols_json field
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models import NewsSearchIndex, ArticleSymbol, NewsArticle
import json
import logging
from sqlalchemy import text

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def populate_symbols_from_article_symbols(dry_run: bool = False):
    """
    Populate symbols_json field using existing article_symbols table
    
    Args:
        dry_run: If True, show what would be done without making changes
    
    Returns:
        Dict with operation results
    """
    try:
        # Get search index entries that need symbols_json populated
        search_entries = NewsSearchIndex.query.filter(
            NewsSearchIndex.symbols_json.is_(None)
        ).all()
        
        logger.info(f"Found {len(search_entries)} search index entries with missing symbols_json")
        
        results = {
            'processed': 0,
            'symbols_added': 0,
            'failed': 0,
            'no_symbols_found': 0,
            'sample_results': []
        }
        
        for entry in search_entries:
            try:
                # Get symbols for this article from article_symbols table
                if entry.article_id:
                    # Use article_id to find symbols
                    symbols_query = ArticleSymbol.query.filter_by(article_id=entry.article_id).all()
                    symbols = [s.symbol for s in symbols_query]
                else:
                    # If no article_id, try to find by external_id
                    article = NewsArticle.query.filter_by(external_id=entry.external_id).first()
                    if article:
                        symbols_query = ArticleSymbol.query.filter_by(article_id=article.id).all()
                        symbols = [s.symbol for s in symbols_query]
                    else:
                        symbols = []
                
                # Store sample for verification
                if len(results['sample_results']) < 10:
                    results['sample_results'].append({
                        'search_id': entry.id,
                        'article_id': entry.article_id,
                        'external_id': entry.external_id,
                        'title': entry.title[:100] + "..." if len(entry.title) > 100 else entry.title,
                        'symbols_found': symbols,
                        'symbol_count': len(symbols)
                    })
                
                results['processed'] += 1
                
                if symbols:
                    if not dry_run:
                        # Store symbols as JSON
                        entry.symbols_json = json.dumps(symbols)
                        results['symbols_added'] += len(symbols)
                        logger.debug(f"Search entry {entry.id}: Added {len(symbols)} symbols: {symbols}")
                    else:
                        results['symbols_added'] += len(symbols)
                        logger.debug(f"DRY RUN - Would add {len(symbols)} symbols to entry {entry.id}")
                else:
                    results['no_symbols_found'] += 1
                    logger.debug(f"No symbols found for search entry {entry.id}")
                
            except Exception as e:
                logger.error(f"Error processing search entry {entry.id}: {str(e)}")
                results['failed'] += 1
                continue
        
        if not dry_run and results['symbols_added'] > 0:
            db.session.commit()
            logger.info(f"✅ Committed changes to database")
        
        return results
        
    except Exception as e:
        logger.error(f"Error in populate_symbols_from_article_symbols: {str(e)}")
        if not dry_run:
            db.session.rollback()
        return {'error': str(e)}

def get_article_symbols_stats():
    """Get statistics about article_symbols table"""
    try:
        # Get total count
        total_symbols = db.session.query(ArticleSymbol).count()
        
        # Get unique symbols count
        unique_symbols = db.session.query(ArticleSymbol.symbol).distinct().count()
        
        # Get articles with symbols
        articles_with_symbols = db.session.query(ArticleSymbol.article_id).distinct().count()
        
        # Get sample symbols
        sample_symbols = db.session.query(ArticleSymbol.symbol).distinct().limit(20).all()
        
        return {
            'total_symbol_entries': total_symbols,
            'unique_symbols': unique_symbols,
            'articles_with_symbols': articles_with_symbols,
            'sample_symbols': [s.symbol for s in sample_symbols]
        }
        
    except Exception as e:
        logger.error(f"Error getting article_symbols stats: {str(e)}")
        return {'error': str(e)}

def main():
    """Main execution function"""
    print("🔗 Populate symbols_json from article_symbols table")
    print("=" * 60)
    
    # Create Flask app context
    app = create_app()
    
    with app.app_context():
        # First, get stats about article_symbols table
        print("\n📊 Article Symbols Table Statistics:")
        stats = get_article_symbols_stats()
        
        if 'error' in stats:
            print(f"❌ Error getting stats: {stats['error']}")
            return
        
        print(f"   Total symbol entries: {stats['total_symbol_entries']}")
        print(f"   Unique symbols: {stats['unique_symbols']}")
        print(f"   Articles with symbols: {stats['articles_with_symbols']}")
        print(f"   Sample symbols: {', '.join(stats['sample_symbols'][:10])}")
        
        # Run dry run first
        print("\n🔍 Running DRY RUN to preview results...")
        dry_results = populate_symbols_from_article_symbols(dry_run=True)
        
        if 'error' in dry_results:
            print(f"❌ Error: {dry_results['error']}")
            return
        
        print(f"\n📈 DRY RUN Results:")
        print(f"   Search entries processed: {dry_results['processed']}")
        print(f"   Total symbols that would be added: {dry_results['symbols_added']}")
        print(f"   Entries with no symbols: {dry_results['no_symbols_found']}")
        print(f"   Failed entries: {dry_results['failed']}")
        
        if dry_results['symbols_added'] > 0:
            avg_symbols = dry_results['symbols_added'] / (dry_results['processed'] - dry_results['no_symbols_found'])
            print(f"   Average symbols per article: {avg_symbols:.1f}")
        
        print(f"\n🎯 Sample Results:")
        for sample in dry_results['sample_results']:
            print(f"   • Search ID {sample['search_id']}: {sample['symbol_count']} symbols")
            print(f"     Article ID: {sample['article_id']}")
            print(f"     Title: {sample['title']}")
            print(f"     Symbols: {sample['symbols_found']}")
            print()
        
        # Ask for confirmation
        if dry_results['processed'] > 0 and dry_results['symbols_added'] > 0:
            response = input(f"\n✅ Apply changes to populate symbols_json? (y/N): ")
            if response.lower() == 'y':
                print("\n🚀 Applying changes...")
                final_results = populate_symbols_from_article_symbols(dry_run=False)
                
                if 'error' in final_results:
                    print(f"❌ Error: {final_results['error']}")
                else:
                    print(f"\n✅ SUCCESS!")
                    print(f"   Search entries processed: {final_results['processed']}")
                    print(f"   Total symbols added: {final_results['symbols_added']}")
                    print(f"   Entries with no symbols: {final_results['no_symbols_found']}")
                    print(f"   Failed entries: {final_results['failed']}")
                    
                    if final_results['symbols_added'] > 0:
                        avg_symbols = final_results['symbols_added'] / (final_results['processed'] - final_results['no_symbols_found'])
                        print(f"   Average symbols per article: {avg_symbols:.1f}")
            else:
                print("\n❌ Operation cancelled")
        elif dry_results['processed'] == 0:
            print("\n⚠️  No search entries found that need symbols_json population")
        else:
            print("\n⚠️  No symbols found to populate")

if __name__ == "__main__":
    main() 