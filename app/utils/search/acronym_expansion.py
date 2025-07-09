#!/usr/bin/env python3
"""
Acronym Expansion Service for Search Enhancement
Handles expansion of short forms, acronyms, and financial terminology
"""

import logging
import re
from typing import Dict, List, Optional, Set
from fuzzywuzzy import fuzz
from app.models import NewsKeyword, NewsSearchIndex, db
from sqlalchemy import func, or_

logger = logging.getLogger(__name__)

class AcronymExpansionService:
    """Service to expand acronyms and short forms in search queries"""
    
    def __init__(self):
        # Financial acronyms and expansions
        self.financial_acronyms = {
            'fed': ['federal reserve', 'federal', 'fed'],
            'sec': ['securities and exchange commission', 'security', 'securities'],
            'ipo': ['initial public offering', 'public offering'],
            'etf': ['exchange traded fund', 'exchange traded funds'],
            'gdp': ['gross domestic product', 'economic growth'],
            'cpi': ['consumer price index', 'inflation'],
            'ppi': ['producer price index', 'inflation'],
            'fomc': ['federal open market committee', 'federal reserve'],
            'qe': ['quantitative easing', 'monetary policy'],
            'ceo': ['chief executive officer', 'executive', 'leadership'],
            'cfo': ['chief financial officer', 'financial officer'],
            'cto': ['chief technology officer', 'technology officer'],
            'ai': ['artificial intelligence', 'machine learning', 'technology'],
            'ev': ['electric vehicle', 'electric vehicles', 'automotive'],
            'esg': ['environmental social governance', 'sustainability'],
            'reit': ['real estate investment trust', 'real estate'],
            'spac': ['special purpose acquisition company', 'acquisition'],
            'fintech': ['financial technology', 'technology', 'finance'],
            'crypto': ['cryptocurrency', 'bitcoin', 'blockchain'],
            'nft': ['non fungible token', 'blockchain', 'digital assets'],
            'defi': ['decentralized finance', 'blockchain', 'finance'],
            'vc': ['venture capital', 'investment', 'startup'],
            'pe': ['private equity', 'investment', 'equity'],
            'roe': ['return on equity', 'profitability', 'returns'],
            'roi': ['return on investment', 'profitability', 'returns'],
            'eps': ['earnings per share', 'earnings', 'profitability'],
            'pe_ratio': ['price to earnings ratio', 'valuation', 'earnings'],
            'pbv': ['price to book value', 'valuation', 'book value'],
            'ebitda': ['earnings before interest tax depreciation amortization', 'earnings'],
            'capex': ['capital expenditure', 'investment', 'spending'],
            'opex': ['operational expenditure', 'operating costs'],
            'r&d': ['research and development', 'innovation', 'technology'],
            'eu': ['european union', 'europe', 'european'],
            'uk': ['united kingdom', 'britain', 'british'],
            'us': ['united states', 'america', 'american'],
            'china': ['china', 'chinese', 'prc'],
            'jp': ['japan', 'japanese', 'nikkei'],
            'hk': ['hong kong', 'hongkong', 'asian'],
            'sg': ['singapore', 'asian', 'southeast asia'],
            'covid': ['coronavirus', 'pandemic', 'health crisis'],
            'wfh': ['work from home', 'remote work', 'workplace'],
            'saas': ['software as a service', 'cloud computing', 'technology'],
            'paas': ['platform as a service', 'cloud computing', 'technology'],
            'iaas': ['infrastructure as a service', 'cloud computing', 'technology'],
            'api': ['application programming interface', 'technology', 'software'],
            'iot': ['internet of things', 'technology', 'connected devices'],
            'ar': ['augmented reality', 'technology', 'virtual reality'],
            'vr': ['virtual reality', 'technology', 'augmented reality'],
            'ml': ['machine learning', 'artificial intelligence', 'technology'],
            'nlp': ['natural language processing', 'artificial intelligence'],
            'ui': ['user interface', 'design', 'technology'],
            'ux': ['user experience', 'design', 'technology'],
            'b2b': ['business to business', 'enterprise', 'commercial'],
            'b2c': ['business to consumer', 'consumer', 'retail'],
            'p2p': ['peer to peer', 'decentralized', 'sharing'],
            'kpi': ['key performance indicator', 'metrics', 'performance'],
            'crm': ['customer relationship management', 'sales', 'customer'],
            'erp': ['enterprise resource planning', 'business software'],
            'hr': ['human resources', 'employment', 'workforce'],
            'pr': ['public relations', 'marketing', 'communications'],
            'csr': ['corporate social responsibility', 'sustainability'],
            'esg': ['environmental social governance', 'sustainability'],
            'kyc': ['know your customer', 'compliance', 'regulation'],
            'aml': ['anti money laundering', 'compliance', 'regulation'],
            'gdpr': ['general data protection regulation', 'privacy', 'data'],
            'hipaa': ['health insurance portability accountability act', 'healthcare'],
            'sox': ['sarbanes oxley act', 'compliance', 'regulation'],
            'osha': ['occupational safety health administration', 'workplace safety'],
        }
        
        # Industry-specific terms
        self.industry_terms = {
            'tech': ['technology', 'software', 'digital'],
            'auto': ['automotive', 'automobile', 'vehicle'],
            'pharma': ['pharmaceutical', 'medicine', 'healthcare'],
            'biotech': ['biotechnology', 'biological', 'medicine'],
            'finserv': ['financial services', 'banking', 'finance'],
            'telecom': ['telecommunications', 'communication', 'network'],
            'retail': ['retail', 'consumer', 'shopping'],
            'energy': ['energy', 'oil', 'gas', 'renewable'],
            'realestate': ['real estate', 'property', 'housing'],
            'aerospace': ['aerospace', 'aviation', 'defense'],
            'agri': ['agriculture', 'farming', 'food'],
            'mining': ['mining', 'metals', 'commodities'],
            'logistics': ['logistics', 'supply chain', 'transportation'],
            'hospitality': ['hospitality', 'travel', 'tourism'],
            'media': ['media', 'entertainment', 'content'],
            'gaming': ['gaming', 'video games', 'entertainment'],
            'edu': ['education', 'learning', 'schools'],
            'health': ['healthcare', 'medical', 'health'],
            'insurance': ['insurance', 'coverage', 'risk'],
            'construction': ['construction', 'building', 'infrastructure'],
        }
        
        # Combine all expansions
        self.all_expansions = {**self.financial_acronyms, **self.industry_terms}
    
    def expand_query(self, query: str) -> Dict[str, any]:
        """
        Expand a search query to include acronym expansions and related terms
        
        Args:
            query: Original search query
            
        Returns:
            Dictionary with expanded terms and metadata
        """
        if not query:
            return {'original': query, 'expanded': [], 'related': []}
        
        query_lower = query.lower().strip()
        expanded_terms = []
        related_terms = []
        
        # 1. Direct acronym expansion
        if query_lower in self.all_expansions:
            expanded_terms.extend(self.all_expansions[query_lower])
            logger.info(f"Direct acronym expansion: '{query}' → {self.all_expansions[query_lower]}")
        
        # 2. Partial word matching
        for word in query_lower.split():
            if word in self.all_expansions:
                expanded_terms.extend(self.all_expansions[word])
                logger.info(f"Partial word expansion: '{word}' → {self.all_expansions[word]}")
        
        # 3. Fuzzy matching for similar terms
        fuzzy_matches = self._find_fuzzy_matches(query_lower)
        related_terms.extend(fuzzy_matches)
        
        # 4. Database-driven expansion from existing keywords
        db_expansions = self._get_database_expansions(query_lower)
        related_terms.extend(db_expansions)
        
        # Remove duplicates and clean up
        expanded_terms = list(set(expanded_terms))
        related_terms = list(set(related_terms))
        
        # Remove original query from expansions
        expanded_terms = [term for term in expanded_terms if term.lower() != query_lower]
        related_terms = [term for term in related_terms if term.lower() != query_lower]
        
        return {
            'original': query,
            'expanded': expanded_terms,
            'related': related_terms,
            'search_terms': [query] + expanded_terms + related_terms
        }
    
    def _find_fuzzy_matches(self, query: str, threshold: int = 80) -> List[str]:
        """Find fuzzy matches for the query in acronym database"""
        matches = []
        
        for acronym, expansions in self.all_expansions.items():
            # Check if query is similar to any acronym
            if fuzz.ratio(query, acronym) >= threshold:
                matches.extend(expansions)
            
            # Check if query is similar to any expansion
            for expansion in expansions:
                if fuzz.ratio(query, expansion) >= threshold:
                    matches.append(expansion)
        
        return matches
    
    def _get_database_expansions(self, query: str, limit: int = 10) -> List[str]:
        """Get expansions from database keywords using semantic similarity"""
        expansions = []
        
        try:
            # Search for similar keywords in the database
            similar_keywords = db.session.query(NewsKeyword).filter(
                NewsKeyword.frequency >= 3  # Only frequently used keywords
            ).all()
            
            # Find semantically similar keywords
            for keyword in similar_keywords:
                similarity = fuzz.ratio(query, keyword.keyword.lower())
                if similarity >= 60:  # Lower threshold for database matches
                    expansions.append(keyword.keyword)
            
            # Limit results
            expansions = expansions[:limit]
            
        except Exception as e:
            logger.warning(f"Database expansion failed: {str(e)}")
        
        return expansions
    
    def get_expanded_search_results(self, query: str, limit: int = 20) -> List[Dict]:
        """
        Get search results using expanded query terms
        
        Args:
            query: Original search query
            limit: Maximum number of results
            
        Returns:
            List of articles with relevance scores
        """
        expansion_result = self.expand_query(query)
        search_terms = expansion_result['search_terms']
        
        if not search_terms:
            return []
        
        try:
            # Build search query with expanded terms
            search_conditions = []
            for term in search_terms:
                search_conditions.append(
                    or_(
                        NewsSearchIndex.title.ilike(f'%{term}%'),
                        NewsSearchIndex.ai_summary.ilike(f'%{term}%'),
                        NewsSearchIndex.ai_insights.ilike(f'%{term}%')
                    )
                )
            
            # Execute search
            articles = db.session.query(NewsSearchIndex).filter(
                or_(*search_conditions)
            ).order_by(NewsSearchIndex.created_at.desc()).limit(limit).all()
            
            # Calculate relevance scores
            results = []
            for article in articles:
                relevance_score = self._calculate_relevance_score(article, search_terms)
                results.append({
                    'id': article.id,
                    'title': article.title,
                    'ai_summary': article.ai_summary,
                    'ai_insights': article.ai_insights,
                    'published_at': article.published_at,
                    'relevance_score': relevance_score,
                    'matched_terms': self._get_matched_terms(article, search_terms)
                })
            
            # Sort by relevance score
            results.sort(key=lambda x: x['relevance_score'], reverse=True)
            
            return results
            
        except Exception as e:
            logger.error(f"Expanded search failed: {str(e)}")
            return []
    
    def _calculate_relevance_score(self, article, search_terms: List[str]) -> float:
        """Calculate relevance score for an article based on search terms"""
        score = 0.0
        total_terms = len(search_terms)
        
        if total_terms == 0:
            return 0.0
        
        article_text = f"{article.title} {article.ai_summary or ''} {article.ai_insights or ''}".lower()
        
        for term in search_terms:
            term_lower = term.lower()
            
            # Title matches get higher weight
            if term_lower in article.title.lower():
                score += 0.5
            
            # AI summary matches
            if article.ai_summary and term_lower in article.ai_summary.lower():
                score += 0.3
            
            # AI insights matches
            if article.ai_insights and term_lower in article.ai_insights.lower():
                score += 0.2
        
        return min(1.0, score / total_terms)
    
    def _get_matched_terms(self, article, search_terms: List[str]) -> List[str]:
        """Get list of terms that matched in the article"""
        matched = []
        article_text = f"{article.title} {article.ai_summary or ''} {article.ai_insights or ''}".lower()
        
        for term in search_terms:
            if term.lower() in article_text:
                matched.append(term)
        
        return matched
    
    def get_acronym_suggestions(self, query: str, limit: int = 5) -> List[Dict]:
        """Get acronym-based suggestions for a query"""
        suggestions = []
        
        expansion_result = self.expand_query(query)
        
        # Add expanded terms as suggestions
        for term in expansion_result['expanded'][:limit]:
            suggestions.append({
                'text': term,
                'type': 'acronym_expansion',
                'category': 'concept',
                'relevance_score': 0.9,
                'source': 'acronym_expansion',
                'original_query': query
            })
        
        # Add related terms as suggestions
        for term in expansion_result['related'][:limit]:
            suggestions.append({
                'text': term,
                'type': 'related_term',
                'category': 'concept',
                'relevance_score': 0.7,
                'source': 'related_expansion',
                'original_query': query
            })
        
        return suggestions[:limit]

# Global instance
acronym_expansion_service = AcronymExpansionService() 