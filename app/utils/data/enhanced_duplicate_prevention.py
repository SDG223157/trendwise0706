"""
Enhanced Duplicate Prevention Service

This service provides comprehensive duplicate prevention for news articles
across multiple levels: database, application, and batch processing.
"""

import logging
from typing import Dict, List, Optional, Set, Tuple
from datetime import datetime, timedelta
from sqlalchemy import text, and_, or_
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.models import NewsArticle, NewsSearchIndex, ArticleSymbol
from app import db

logger = logging.getLogger(__name__)

class DuplicatePreventionService:
    """
    Comprehensive duplicate prevention service for news articles
    
    Features:
    - External ID duplicate prevention
    - Content similarity checking
    - URL-based duplicate detection
    - Symbol-level deduplication
    - Batch processing duplicate prevention
    - Database constraint violation handling
    """
    
    def __init__(self, session: Optional[Session] = None):
        self.session = session or db.session
        self.logger = logger
        
    def check_article_duplicate(self, article_data: Dict) -> Dict:
        """
        Comprehensive duplicate check for an article
        
        Args:
            article_data: Dictionary containing article data
            
        Returns:
            Dict with duplicate check results
        """
        results = {
            'is_duplicate': False,
            'duplicate_type': None,
            'existing_id': None,
            'duplicate_reason': None,
            'existing_article': None
        }
        
        try:
            # 1. Check by external_id (primary key)
            external_id = article_data.get('external_id')
            if external_id:
                existing = self._check_external_id_duplicate(external_id)
                if existing:
                    results.update({
                        'is_duplicate': True,
                        'duplicate_type': 'external_id',
                        'existing_id': existing.id,
                        'duplicate_reason': f'External ID already exists: {external_id}',
                        'existing_article': existing
                    })
                    return results
            
            # 2. Check by URL (secondary check)
            url = article_data.get('url')
            if url:
                existing = self._check_url_duplicate(url)
                if existing:
                    results.update({
                        'is_duplicate': True,
                        'duplicate_type': 'url',
                        'existing_id': existing.id,
                        'duplicate_reason': f'URL already exists: {url}',
                        'existing_article': existing
                    })
                    return results
            
            # 3. Check by content similarity (advanced check)
            title = article_data.get('title')
            published_at = article_data.get('published_at')
            if title and published_at:
                existing = self._check_content_similarity(title, published_at)
                if existing:
                    results.update({
                        'is_duplicate': True,
                        'duplicate_type': 'content_similarity',
                        'existing_id': existing.id,
                        'duplicate_reason': f'Similar content found: {title[:50]}...',
                        'existing_article': existing
                    })
                    return results
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error checking article duplicate: {str(e)}")
            return results
    
    def _check_external_id_duplicate(self, external_id: str) -> Optional[NewsArticle]:
        """
        Check if external_id already exists in BOTH news_articles (buffer) and news_search_index (permanent)
        
        Args:
            external_id: The external ID to check for duplicates
            
        Returns:
            NewsArticle if found in buffer table, or None if not found in either table
        """
        try:
            # Check buffer table (news_articles) first
            existing_in_buffer = self.session.query(NewsArticle).filter_by(external_id=external_id).first()
            if existing_in_buffer:
                self.logger.debug(f"External ID {external_id} found in buffer table (news_articles)")
                return existing_in_buffer
            
            # Check permanent storage (news_search_index)
            existing_in_search = self.session.query(NewsSearchIndex).filter_by(external_id=external_id).first()
            if existing_in_search:
                self.logger.info(f"External ID {external_id} found in permanent storage (news_search_index) - skipping buffer storage")
                # Return a mock NewsArticle with the ID from search index for consistency
                # This prevents storage in buffer since article already exists in permanent storage
                mock_article = type('MockArticle', (), {'id': existing_in_search.article_id or existing_in_search.id})()
                return mock_article
            
            # Not found in either table
            return None
            
        except Exception as e:
            self.logger.error(f"Error checking external ID duplicate in both tables: {str(e)}")
            return None

    def _check_external_id_comprehensive(self, external_id: str) -> Dict:
        """
        Comprehensive check for external_id in both tables with detailed results
        
        Args:
            external_id: The external ID to check for duplicates
            
        Returns:
            Dict with detailed information about where duplicates were found
        """
        result = {
            'exists': False,
            'in_buffer': False,
            'in_permanent': False,
            'buffer_article': None,
            'permanent_article': None,
            'location': None,
            'article_id': None,
            'message': None
        }
        
        try:
            # Check buffer table (news_articles)
            buffer_article = self.session.query(NewsArticle).filter_by(external_id=external_id).first()
            if buffer_article:
                result.update({
                    'exists': True,
                    'in_buffer': True,
                    'buffer_article': buffer_article,
                    'location': 'buffer',
                    'article_id': buffer_article.id,
                    'message': f'External ID {external_id} exists in buffer table (news_articles) with ID {buffer_article.id}'
                })
            
            # Check permanent storage (news_search_index)
            permanent_article = self.session.query(NewsSearchIndex).filter_by(external_id=external_id).first()
            if permanent_article:
                result.update({
                    'exists': True,
                    'in_permanent': True,
                    'permanent_article': permanent_article,
                    'article_id': permanent_article.article_id or permanent_article.id
                })
                
                if result['in_buffer']:
                    result.update({
                        'location': 'both',
                        'message': f'External ID {external_id} exists in BOTH tables - buffer ID: {buffer_article.id}, permanent ID: {permanent_article.id}'
                    })
                else:
                    result.update({
                        'location': 'permanent',
                        'message': f'External ID {external_id} exists in permanent storage (news_search_index) with ID {permanent_article.id}'
                    })
            
            if not result['exists']:
                result['message'] = f'External ID {external_id} not found in either table - safe to store'
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error in comprehensive external ID check: {str(e)}")
            result.update({
                'exists': False,
                'message': f'Error checking external ID: {str(e)}'
            })
            return result
    
    def _check_url_duplicate(self, url: str) -> Optional[NewsArticle]:
        """Check if URL already exists"""
        try:
            return self.session.query(NewsArticle).filter_by(url=url).first()
        except Exception as e:
            self.logger.error(f"Error checking URL duplicate: {str(e)}")
            return None
    
    def _check_content_similarity(self, title: str, published_at: datetime, 
                                 similarity_threshold: float = 0.8) -> Optional[NewsArticle]:
        """
        Check for content similarity based on title and publish date
        
        Args:
            title: Article title
            published_at: Publication date
            similarity_threshold: Similarity threshold (0.0-1.0)
            
        Returns:
            Existing article if similar content found
        """
        try:
            # Look for articles with similar titles within 24 hours
            date_range_start = published_at - timedelta(hours=24)
            date_range_end = published_at + timedelta(hours=24)
            
            similar_articles = self.session.query(NewsArticle).filter(
                and_(
                    NewsArticle.published_at >= date_range_start,
                    NewsArticle.published_at <= date_range_end,
                    NewsArticle.title.ilike(f"%{title[:30]}%")  # Check first 30 chars
                )
            ).all()
            
            # Calculate similarity score
            for article in similar_articles:
                similarity = self._calculate_title_similarity(title, article.title)
                if similarity >= similarity_threshold:
                    return article
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error checking content similarity: {str(e)}")
            return None
    
    def _calculate_title_similarity(self, title1: str, title2: str) -> float:
        """Calculate similarity between two titles"""
        try:
            # Simple similarity calculation based on common words
            words1 = set(title1.lower().split())
            words2 = set(title2.lower().split())
            
            if not words1 or not words2:
                return 0.0
            
            intersection = len(words1.intersection(words2))
            union = len(words1.union(words2))
            
            return intersection / union if union > 0 else 0.0
            
        except Exception as e:
            self.logger.error(f"Error calculating title similarity: {str(e)}")
            return 0.0
    
    def deduplicate_symbols(self, symbols: List) -> List[str]:
        """
        Remove duplicate symbols from a list
        
        Args:
            symbols: List of symbols (can be strings or dicts)
            
        Returns:
            List of unique symbols as strings
        """
        seen_symbols = set()
        unique_symbols = []
        
        for symbol_data in symbols:
            # Handle both string and dict formats
            if isinstance(symbol_data, dict):
                symbol = symbol_data.get('symbol', '')
            else:
                symbol = str(symbol_data)
            
            symbol = symbol.strip().upper()
            
            if symbol and symbol not in seen_symbols:
                seen_symbols.add(symbol)
                unique_symbols.append(symbol)
        
        return unique_symbols
    
    def check_batch_duplicates(self, external_ids: List[str]) -> Dict:
        """
        Check for duplicates in a batch of external IDs
        
        Args:
            external_ids: List of external IDs to check
            
        Returns:
            Dict with duplicate analysis results
        """
        results = {
            'total_checked': len(external_ids),
            'duplicates_found': 0,
            'duplicate_ids': [],
            'unique_ids': [],
            'existing_in_db': [],
            'existing_in_search_index': []
        }
        
        try:
            # Check for duplicates within the batch
            seen_ids = set()
            for external_id in external_ids:
                if external_id in seen_ids:
                    results['duplicate_ids'].append(external_id)
                    results['duplicates_found'] += 1
                else:
                    seen_ids.add(external_id)
                    results['unique_ids'].append(external_id)
            
            # Check existing in buffer table (news_articles)
            existing_in_buffer = self.session.query(NewsArticle.external_id).filter(
                NewsArticle.external_id.in_(external_ids)
            ).all()
            results['existing_in_db'] = [row.external_id for row in existing_in_buffer]
            
            # Check existing in permanent storage (news_search_index)
            existing_in_search = self.session.query(NewsSearchIndex.external_id).filter(
                NewsSearchIndex.external_id.in_(external_ids)
            ).all()
            results['existing_in_search_index'] = [row.external_id for row in existing_in_search]
            
            # Combine both to get all existing external_ids
            all_existing = set(results['existing_in_db'] + results['existing_in_search_index'])
            results['existing_anywhere'] = list(all_existing)
            results['truly_unique'] = [eid for eid in results['unique_ids'] if eid not in all_existing]
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error checking batch duplicates: {str(e)}")
            return results
    
    def safe_insert_with_duplicate_handling(self, article_data: Dict) -> Dict:
        """
        Safely insert article with comprehensive duplicate handling
        
        Args:
            article_data: Article data dictionary
            
        Returns:
            Dict with insertion results
        """
        result = {
            'success': False,
            'article_id': None,
            'action': None,
            'message': None,
            'duplicate_info': None
        }
        
        try:
            # Step 1: Comprehensive duplicate check (both tables)
            external_id = article_data.get('external_id')
            if external_id:
                comprehensive_check = self._check_external_id_comprehensive(external_id)
                if comprehensive_check['exists']:
                    result.update({
                        'success': True,
                        'article_id': comprehensive_check['article_id'],
                        'action': 'skipped_duplicate',
                        'message': comprehensive_check['message'],
                        'duplicate_info': {
                            'is_duplicate': True,
                            'duplicate_type': 'external_id',
                            'existing_id': comprehensive_check['article_id'],
                            'location': comprehensive_check['location'],
                            'in_buffer': comprehensive_check['in_buffer'],
                            'in_permanent': comprehensive_check['in_permanent']
                        }
                    })
                    return result
            
            # Step 1.5: Additional duplicate checks (URL, content similarity)
            duplicate_check = self.check_article_duplicate(article_data)
            
            if duplicate_check['is_duplicate'] and duplicate_check['duplicate_type'] != 'external_id':
                result.update({
                    'success': True,
                    'article_id': duplicate_check['existing_id'],
                    'action': 'skipped_duplicate',
                    'message': f"Article already exists: {duplicate_check['duplicate_reason']}",
                    'duplicate_info': duplicate_check
                })
                return result
            
            # Step 2: Create new article with duplicate prevention
            new_article = NewsArticle(
                external_id=article_data.get('external_id'),
                title=article_data.get('title'),
                content=article_data.get('content'),
                url=article_data.get('url'),
                published_at=article_data.get('published_at'),
                source=article_data.get('source'),
                sentiment_label=article_data.get('sentiment', {}).get('overall_sentiment'),
                sentiment_score=article_data.get('sentiment', {}).get('confidence'),
                sentiment_explanation=article_data.get('sentiment', {}).get('explanation'),
                brief_summary=article_data.get('summary', {}).get('brief'),
                key_points=article_data.get('summary', {}).get('key_points'),
                market_impact_summary=article_data.get('summary', {}).get('market_impact'),
                ai_summary=None,
                ai_insights=None,
                ai_sentiment_rating=None
            )
            
            # Step 3: Add symbols with deduplication
            if article_data.get('symbols'):
                unique_symbols = self.deduplicate_symbols(article_data['symbols'])
                for symbol in unique_symbols:
                    new_article.symbols.append(ArticleSymbol(symbol=symbol))
            
            # Step 4: Save with integrity error handling
            try:
                self.session.add(new_article)
                self.session.commit()
                
                result.update({
                    'success': True,
                    'article_id': new_article.id,
                    'action': 'inserted',
                    'message': f"Article inserted successfully: {new_article.external_id}"
                })
                
            except IntegrityError as e:
                self.session.rollback()
                
                # Handle database constraint violations
                if 'external_id' in str(e) or 'UNIQUE constraint' in str(e):
                    # Race condition occurred - check both tables for the existing article
                    constraint_check = self._check_external_id_comprehensive(article_data.get('external_id'))
                    if constraint_check['exists']:
                        result.update({
                            'success': True,
                            'article_id': constraint_check['article_id'],
                            'action': 'skipped_constraint_violation',
                            'message': f"Article already exists (constraint violation): {constraint_check['message']}"
                        })
                    else:
                        result.update({
                            'success': False,
                            'action': 'constraint_violation',
                            'message': f"Database constraint violation but article not found: {str(e)}"
                        })
                else:
                    raise  # Re-raise if it's not a duplicate constraint issue
            
            return result
            
        except Exception as e:
            self.session.rollback()
            self.logger.error(f"Error in safe insert: {str(e)}")
            result.update({
                'success': False,
                'action': 'error',
                'message': f"Error inserting article: {str(e)}"
            })
            return result
    
    def cleanup_duplicate_external_ids(self, table_name: str = 'news_search_index') -> Dict:
        """
        Clean up duplicate external_ids in specified table
        
        Args:
            table_name: Name of table to clean up
            
        Returns:
            Dict with cleanup results
        """
        results = {
            'cleaned_count': 0,
            'error_count': 0,
            'duplicates_found': 0,
            'errors': []
        }
        
        try:
            # Find duplicates
            if table_name == 'news_search_index':
                duplicate_query = text("""
                    SELECT external_id, COUNT(*) as count, MIN(id) as keep_id
                    FROM news_search_index 
                    GROUP BY external_id 
                    HAVING COUNT(*) > 1
                """)
            else:
                duplicate_query = text("""
                    SELECT external_id, COUNT(*) as count, MIN(id) as keep_id
                    FROM news_articles 
                    GROUP BY external_id 
                    HAVING COUNT(*) > 1
                """)
            
            duplicates = self.session.execute(duplicate_query).fetchall()
            results['duplicates_found'] = len(duplicates)
            
            if not duplicates:
                return results
            
            # Clean up duplicates (keep the earliest entry)
            for duplicate in duplicates:
                try:
                    if table_name == 'news_search_index':
                        delete_query = text("""
                            DELETE FROM news_search_index 
                            WHERE external_id = :external_id AND id != :keep_id
                        """)
                    else:
                        delete_query = text("""
                            DELETE FROM news_articles 
                            WHERE external_id = :external_id AND id != :keep_id
                        """)
                    
                    result = self.session.execute(delete_query, {
                        'external_id': duplicate.external_id,
                        'keep_id': duplicate.keep_id
                    })
                    
                    deleted_count = result.rowcount
                    results['cleaned_count'] += deleted_count
                    
                except Exception as e:
                    results['error_count'] += 1
                    results['errors'].append({
                        'external_id': duplicate.external_id,
                        'error': str(e)
                    })
            
            self.session.commit()
            return results
            
        except Exception as e:
            self.session.rollback()
            self.logger.error(f"Error cleaning up duplicates: {str(e)}")
            results['errors'].append({'general_error': str(e)})
            return results
    
    def generate_duplicate_report(self) -> Dict:
        """
        Generate a comprehensive duplicate report
        
        Returns:
            Dict with duplicate statistics
        """
        report = {
            'timestamp': datetime.now().isoformat(),
            'news_articles': {
                'total_count': 0,
                'unique_external_ids': 0,
                'duplicate_external_ids': 0,
                'duplicate_urls': 0
            },
            'news_search_index': {
                'total_count': 0,
                'unique_external_ids': 0,
                'duplicate_external_ids': 0
            },
            'recommendations': []
        }
        
        try:
            # News articles analysis
            news_articles_count = self.session.query(NewsArticle).count()
            unique_external_ids = self.session.query(NewsArticle.external_id).distinct().count()
            
            report['news_articles'].update({
                'total_count': news_articles_count,
                'unique_external_ids': unique_external_ids,
                'duplicate_external_ids': news_articles_count - unique_external_ids
            })
            
            # Search index analysis
            search_index_count = self.session.query(NewsSearchIndex).count()
            search_unique_external_ids = self.session.query(NewsSearchIndex.external_id).distinct().count()
            
            report['news_search_index'].update({
                'total_count': search_index_count,
                'unique_external_ids': search_unique_external_ids,
                'duplicate_external_ids': search_index_count - search_unique_external_ids
            })
            
            # Generate recommendations
            if report['news_articles']['duplicate_external_ids'] > 0:
                report['recommendations'].append(
                    f"Clean up {report['news_articles']['duplicate_external_ids']} duplicate external_ids in news_articles table"
                )
            
            if report['news_search_index']['duplicate_external_ids'] > 0:
                report['recommendations'].append(
                    f"Clean up {report['news_search_index']['duplicate_external_ids']} duplicate external_ids in news_search_index table"
                )
            
            if not report['recommendations']:
                report['recommendations'].append("No duplicate issues found - system is clean!")
            
            return report
            
        except Exception as e:
            self.logger.error(f"Error generating duplicate report: {str(e)}")
            report['error'] = str(e)
            return report

    def check_external_id_in_both_tables(self, external_id: str) -> Dict:
        """
        Public method to check if external_id exists in either buffer or permanent table
        
        Args:
            external_id: The external ID to check
            
        Returns:
            Dict with comprehensive duplicate information including:
            - exists: Boolean indicating if duplicate found
            - in_buffer: Boolean indicating if found in news_articles table
            - in_permanent: Boolean indicating if found in news_search_index table
            - location: String indicating where found ('buffer', 'permanent', 'both', or None)
            - article_id: ID of the existing article
            - message: Human-readable description
        """
        return self._check_external_id_comprehensive(external_id)