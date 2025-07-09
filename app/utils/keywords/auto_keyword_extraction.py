#!/usr/bin/env python3
"""
Automatic keyword extraction service
Integrates with AI processing pipeline to extract keywords from news_articles (buffer table)
"""

import os
import sys
import logging
import json
import re
from datetime import datetime
from typing import Dict, List, Any, Optional

# Add app directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app.models import db, NewsArticle
from sqlalchemy import text
from flask import current_app

# Set up logging
logger = logging.getLogger(__name__)

class AutoKeywordExtractor:
    """Automatic keyword extraction service for the AI processing pipeline"""
    
    def __init__(self):
        """Initialize the auto keyword extractor"""
        self.financial_terms = {
            'stock', 'market', 'trading', 'investment', 'portfolio', 'dividend',
            'earnings', 'revenue', 'profit', 'loss', 'shares', 'equity', 'bond',
            'futures', 'options', 'etf', 'ipo', 'merger', 'acquisition', 'valuation',
            'bull', 'bear', 'volatility', 'liquidity', 'hedge', 'leverage', 'margin',
            'nasdaq', 'nyse', 'dow', 'sp500', 's&p', 'russell', 'ftse', 'nikkei',
            'federal', 'fed', 'interest', 'rates', 'inflation', 'gdp', 'unemployment',
            'economic', 'economy', 'fiscal', 'monetary', 'policy', 'regulation',
            'sec', 'fintech', 'blockchain', 'cryptocurrency', 'bitcoin', 'ethereum'
        }
        
    def extract_keywords_for_article(self, article_id: int) -> Dict[str, Any]:
        """
        Extract keywords for a single article from the news_articles table
        This is designed to work with the buffer table architecture
        """
        try:
            # Get the article from the buffer table (news_articles)
            article = NewsArticle.query.get(article_id)
            if not article:
                return {
                    'success': False,
                    'message': f'Article {article_id} not found in buffer table',
                    'keywords_extracted': 0
                }
                
            # Check if article has AI content (required for keyword extraction)
            if not article.ai_summary or not article.ai_insights:
                return {
                    'success': False,
                    'message': 'Article missing AI content for keyword extraction',
                    'keywords_extracted': 0
                }
                
            # Check if keywords already exist for this article
            existing_keywords = db.session.execute(
                text('SELECT COUNT(*) FROM article_keywords WHERE article_id = :article_id'),
                {'article_id': article_id}
            ).scalar()
            
            if existing_keywords > 0:
                return {
                    'success': True,
                    'message': 'Keywords already exist',
                    'keywords_extracted': existing_keywords
                }
                
            # Extract keywords using multiple methods
            keywords = self._extract_keywords_multi_method(article)
            
            if not keywords:
                return {
                    'success': False,
                    'message': 'No keywords extracted',
                    'keywords_extracted': 0
                }
                
            # Store keywords in database
            stored_count = self._store_keywords_in_database(article_id, keywords)
            
            return {
                'success': True,
                'message': f'Successfully extracted {stored_count} keywords',
                'keywords_extracted': stored_count
            }
            
        except Exception as e:
            logger.error(f"Error in extract_keywords_for_article: {str(e)}")
            return {
                'success': False,
                'message': f'Error: {str(e)}',
                'keywords_extracted': 0
            }
    
    def _extract_keywords_multi_method(self, article: NewsArticle) -> List[Dict[str, Any]]:
        """Extract keywords using multiple methods"""
        keywords = []
        
        # Combine all text content
        text_content = f"{article.title} {article.ai_summary} {article.ai_insights}"
        
        # Method 1: Extract from symbols_json if available
        if hasattr(article, 'symbols_json') and article.symbols_json:
            try:
                symbols_data = json.loads(article.symbols_json)
                if isinstance(symbols_data, list):
                    for symbol in symbols_data:
                        if isinstance(symbol, dict) and 'symbol' in symbol:
                            keywords.append({
                                'keyword': symbol['symbol'],
                                'category': 'company',
                                'relevance_score': 0.9
                            })
            except:
                pass
        
        # Method 2: Named Entity Recognition (simple approach)
        keywords.extend(self._extract_entities(text_content))
        
        # Method 3: Financial terms detection
        keywords.extend(self._extract_financial_terms(text_content))
        
        # Method 4: Key phrases from AI content
        keywords.extend(self._extract_key_phrases(article.ai_summary))
        keywords.extend(self._extract_key_phrases(article.ai_insights))
        
        # Remove duplicates and limit to top keywords
        unique_keywords = self._deduplicate_keywords(keywords)
        
        return unique_keywords[:20]  # Limit to top 20 keywords
    
    def _extract_entities(self, text: str) -> List[Dict[str, Any]]:
        """Extract named entities (simple approach)"""
        keywords = []
        
        # Look for company names (capitalized words)
        company_pattern = r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b'
        companies = re.findall(company_pattern, text)
        
        for company in companies:
            if len(company) > 2 and company.lower() not in ['the', 'and', 'for', 'with']:
                keywords.append({
                    'keyword': company,
                    'category': 'company',
                    'relevance_score': 0.7
                })
        
        return keywords
    
    def _extract_financial_terms(self, text: str) -> List[Dict[str, Any]]:
        """Extract financial terms from text"""
        keywords = []
        text_lower = text.lower()
        
        for term in self.financial_terms:
            if term in text_lower:
                keywords.append({
                    'keyword': term,
                    'category': 'financial',
                    'relevance_score': 0.8
                })
        
        return keywords
    
    def _extract_key_phrases(self, text: str) -> List[Dict[str, Any]]:
        """Extract key phrases from AI-generated content"""
        keywords = []
        
        if not text:
            return keywords
        
        # Look for phrases in bullet points
        bullet_pattern = r'[-•]\s*([^\\n]+)'
        bullet_points = re.findall(bullet_pattern, text)
        
        for point in bullet_points:
            # Extract meaningful phrases (2-4 words)
            phrase_pattern = r'\b[A-Za-z]+(?:\s+[A-Za-z]+){1,3}\b'
            phrases = re.findall(phrase_pattern, point)
            
            for phrase in phrases:
                if len(phrase) > 4:  # Skip very short phrases
                    keywords.append({
                        'keyword': phrase.strip(),
                        'category': 'concept',
                        'relevance_score': 0.6
                    })
        
        return keywords
    
    def _deduplicate_keywords(self, keywords: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate keywords and merge relevance scores"""
        keyword_map = {}
        
        for kw in keywords:
            keyword_lower = kw['keyword'].lower()
            if keyword_lower not in keyword_map:
                keyword_map[keyword_lower] = kw
            else:
                # Keep the one with higher relevance score
                if kw['relevance_score'] > keyword_map[keyword_lower]['relevance_score']:
                    keyword_map[keyword_lower] = kw
        
        # Sort by relevance score
        unique_keywords = list(keyword_map.values())
        unique_keywords.sort(key=lambda x: x['relevance_score'], reverse=True)
        
        return unique_keywords
    
    def _store_keywords_in_database(self, article_id: int, keywords: List[Dict[str, Any]]) -> int:
        """Store extracted keywords in the database"""
        try:
            stored_count = 0
            
            for kw_data in keywords:
                # Insert or get keyword
                keyword_insert = text("""
                    INSERT IGNORE INTO news_keywords (keyword, category, relevance_score, created_at)
                    VALUES (:keyword, :category, :relevance_score, :created_at)
                """)
                
                db.session.execute(keyword_insert, {
                    'keyword': kw_data['keyword'],
                    'category': kw_data['category'],
                    'relevance_score': kw_data['relevance_score'],
                    'created_at': datetime.utcnow()
                })
                
                # Get the keyword ID
                keyword_id_query = text("""
                    SELECT id FROM news_keywords 
                    WHERE keyword = :keyword AND category = :category
                """)
                
                result = db.session.execute(keyword_id_query, {
                    'keyword': kw_data['keyword'],
                    'category': kw_data['category']
                })
                
                keyword_row = result.fetchone()
                if keyword_row:
                    keyword_id = keyword_row[0]
                    
                    # Insert article-keyword relationship
                    article_keyword_insert = text("""
                        INSERT IGNORE INTO article_keywords (article_id, keyword_id, relevance_score, created_at)
                        VALUES (:article_id, :keyword_id, :relevance_score, :created_at)
                    """)
                    
                    db.session.execute(article_keyword_insert, {
                        'article_id': article_id,
                        'keyword_id': keyword_id,
                        'relevance_score': kw_data['relevance_score'],
                        'created_at': datetime.utcnow()
                    })
                    
                    stored_count += 1
            
            db.session.commit()
            return stored_count
            
        except Exception as e:
            logger.error(f"Error storing keywords in database: {str(e)}")
            db.session.rollback()
            return 0 