#!/usr/bin/env python3
"""
Duplicate-safe keyword extraction from news_search_index
This version handles duplicate article-keyword relationships gracefully
"""

import os
import sys
import logging
from datetime import datetime
from typing import Dict, List, Any

# Add app directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app import create_app
from app.models import db
from sqlalchemy import text

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def extract_keywords_for_article(article_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract keywords from article using multiple methods"""
    
    keywords = []
    article_id = article_data['id']
    title = article_data.get('title', '')
    content = article_data.get('content_excerpt', '')
    ai_summary = article_data.get('ai_summary', '')
    
    # Combine all text for processing
    full_text = f"{title} {content} {ai_summary}".strip()
    
    if not full_text:
        logger.warning(f"No text content for article {article_id}")
        return keywords
    
    # Simple keyword extraction (fallback method)
    # This is a basic implementation - can be enhanced with AI/NLP methods
    
    # Financial terms
    financial_terms = [
        'stock', 'market', 'trading', 'investment', 'earnings', 'revenue',
        'profit', 'dividend', 'shares', 'portfolio', 'analyst', 'forecast',
        'growth', 'decline', 'bullish', 'bearish', 'volatility', 'momentum'
    ]
    
    # Technology terms
    tech_terms = [
        'technology', 'software', 'hardware', 'AI', 'artificial intelligence',
        'machine learning', 'blockchain', 'cryptocurrency', 'innovation',
        'digital', 'platform', 'cloud', 'data', 'cybersecurity'
    ]
    
    text_lower = full_text.lower()
    
    # Extract financial keywords
    for term in financial_terms:
        if term in text_lower:
            keywords.append({
                'keyword': term,
                'category': 'financial',
                'relevance': 0.8,
                'extraction_source': 'financial_terms'
            })
    
    # Extract technology keywords
    for term in tech_terms:
        if term in text_lower:
            keywords.append({
                'keyword': term,
                'category': 'technology',
                'relevance': 0.7,
                'extraction_source': 'tech_terms'
            })
    
    # Extract company names from title (simple extraction)
    words = title.split()
    for word in words:
        if word.isupper() and len(word) > 2:
            keywords.append({
                'keyword': word,
                'category': 'company',
                'relevance': 0.9,
                'extraction_source': 'title_analysis'
            })
    
    # Deduplicate keywords
    unique_keywords = {}
    for kw in keywords:
        key = (kw['keyword'].lower(), kw['category'])
        if key not in unique_keywords or unique_keywords[key]['relevance'] < kw['relevance']:
            unique_keywords[key] = kw
    
    return list(unique_keywords.values())

def insert_keyword_safe(keyword_data: Dict[str, Any]) -> int:
    """Insert keyword safely and return keyword_id"""
    
    try:
        # Use INSERT IGNORE to handle duplicates
        result = db.session.execute(text("""
            INSERT IGNORE INTO news_keywords 
            (keyword, normalized_keyword, category, relevance_score, frequency, 
             sentiment_association, first_seen, last_seen, created_at, updated_at)
            VALUES 
            (:keyword, :normalized_keyword, :category, :relevance_score, 1, 
             0.0, NOW(), NOW(), NOW(), NOW())
        """), {
            'keyword': keyword_data['keyword'],
            'normalized_keyword': keyword_data['keyword'].lower().strip(),
            'category': keyword_data['category'],
            'relevance_score': keyword_data['relevance']
        })
        
        # Get the keyword ID
        keyword_id = db.session.execute(text("""
            SELECT id FROM news_keywords 
            WHERE normalized_keyword = :normalized_keyword AND category = :category
        """), {
            'normalized_keyword': keyword_data['keyword'].lower().strip(),
            'category': keyword_data['category']
        }).scalar()
        
        return keyword_id
        
    except Exception as e:
        logger.error(f"Error inserting keyword {keyword_data['keyword']}: {e}")
        return None

def insert_article_keyword_safe(article_id: int, keyword_id: int, keyword_data: Dict[str, Any]) -> bool:
    """Insert article-keyword relationship safely"""
    
    try:
        # Use INSERT IGNORE to handle duplicates
        db.session.execute(text("""
            INSERT IGNORE INTO article_keywords 
            (article_id, keyword_id, relevance_in_article, extraction_source, position_weight, created_at)
            VALUES 
            (:article_id, :keyword_id, :relevance_in_article, :extraction_source, 1.0, NOW())
        """), {
            'article_id': article_id,
            'keyword_id': keyword_id,
            'relevance_in_article': keyword_data['relevance'],
            'extraction_source': keyword_data['extraction_source']
        })
        
        return True
        
    except Exception as e:
        logger.error(f"Error inserting article-keyword relationship: {e}")
        return False

def process_batch(articles: List[Dict[str, Any]]) -> Dict[str, int]:
    """Process a batch of articles safely"""
    
    stats = {
        'processed': 0,
        'skipped': 0,
        'errors': 0,
        'keywords_extracted': 0
    }
    
    for article in articles:
        try:
            article_id = article['id']
            
            # Extract keywords for this article
            keywords = extract_keywords_for_article(article)
            
            if not keywords:
                stats['skipped'] += 1
                continue
            
            # Insert keywords and relationships
            for keyword_data in keywords:
                # Insert keyword
                keyword_id = insert_keyword_safe(keyword_data)
                
                if keyword_id:
                    # Insert article-keyword relationship
                    if insert_article_keyword_safe(article_id, keyword_id, keyword_data):
                        stats['keywords_extracted'] += 1
            
            stats['processed'] += 1
            
            # Commit every article to avoid large transactions
            db.session.commit()
            
        except Exception as e:
            logger.error(f"Error processing article {article.get('id', 'unknown')}: {e}")
            db.session.rollback()
            stats['errors'] += 1
    
    return stats

def main():
    """Main extraction function"""
    
    app = create_app()
    
    with app.app_context():
        logger.info("🚀 Starting duplicate-safe keyword extraction...")
        
        # Get total article count
        total_articles = db.session.execute(text("""
            SELECT COUNT(*) FROM news_search_index 
            WHERE ai_summary IS NOT NULL AND ai_summary != ''
        """)).scalar()
        
        logger.info(f"📊 Total articles to process: {total_articles}")
        
        # Process in batches
        batch_size = 50  # Smaller batch size for safety
        processed_total = 0
        
        for offset in range(0, total_articles, batch_size):
            batch_num = (offset // batch_size) + 1
            logger.info(f"🔄 Processing batch {batch_num} (articles {offset + 1} to {min(offset + batch_size, total_articles)})")
            
            # Get batch of articles
            articles = db.session.execute(text("""
                SELECT id, title, content_excerpt, ai_summary, ai_insights
                FROM news_search_index 
                WHERE ai_summary IS NOT NULL AND ai_summary != ''
                ORDER BY id
                LIMIT :batch_size OFFSET :offset
            """), {
                'batch_size': batch_size,
                'offset': offset
            }).fetchall()
            
            # Convert to dictionaries
            articles_data = [dict(article._mapping) for article in articles]
            
            # Process batch
            batch_stats = process_batch(articles_data)
            
            processed_total += batch_stats['processed']
            
            logger.info(f"📊 Batch {batch_num} results: {batch_stats}")
            
            # Small delay to avoid overwhelming the database
            import time
            time.sleep(0.1)
        
        # Final statistics
        final_stats = {
            'unique_keywords': db.session.execute(text('SELECT COUNT(*) FROM news_keywords')).scalar(),
            'article_keywords': db.session.execute(text('SELECT COUNT(*) FROM article_keywords')).scalar(),
            'processed_articles': processed_total
        }
        
        logger.info("✅ Keyword extraction completed!")
        logger.info(f"📈 Final statistics: {final_stats}")

if __name__ == "__main__":
    main() 