#!/usr/bin/env python3
"""
Test script for acronym expansion functionality
"""

import os
import sys
import logging

# Add app directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app import create_app
from app.models import db
from app.utils.search.acronym_expansion import acronym_expansion_service
from app.utils.search.intelligent_suggestions import intelligent_suggestion_service

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_acronym_expansion():
    """Test the acronym expansion service"""
    
    logger.info("🧪 Testing acronym expansion service...")
    
    # Create Flask app context
    app = create_app()
    
    with app.app_context():
        # Test cases
        test_queries = [
            "fed",
            "sec",
            "ai",
            "covid",
            "ipo",
            "etf",
            "fintech",
            "crypto",
            "ev",
            "esg"
        ]
        
        for query in test_queries:
            logger.info(f"\n🔍 Testing query: '{query}'")
            
            # Test expansion
            expansion_result = acronym_expansion_service.expand_query(query)
            
            logger.info(f"   📋 Original: {expansion_result['original']}")
            logger.info(f"   🔄 Expanded: {expansion_result['expanded']}")
            logger.info(f"   🔗 Related: {expansion_result['related']}")
            logger.info(f"   🎯 All search terms: {expansion_result['search_terms']}")
            
            # Test suggestions
            suggestions = acronym_expansion_service.get_acronym_suggestions(query, 5)
            
            if suggestions:
                logger.info(f"   💡 Suggestions:")
                for suggestion in suggestions:
                    logger.info(f"      • {suggestion['text']} ({suggestion['type']}) - Score: {suggestion['relevance_score']}")
            else:
                logger.info(f"   💡 No suggestions found")

def test_intelligent_suggestions():
    """Test the enhanced intelligent suggestions with acronym expansion"""
    
    logger.info("\n🧪 Testing intelligent suggestions with acronym expansion...")
    
    app = create_app()
    
    with app.app_context():
        test_queries = ["fed", "sec", "ai", "covid"]
        
        for query in test_queries:
            logger.info(f"\n🔍 Testing intelligent suggestions for: '{query}'")
            
            suggestions = intelligent_suggestion_service.get_search_suggestions(
                query=query,
                limit=10,
                include_context=True
            )
            
            if suggestions:
                logger.info(f"   📊 Found {len(suggestions)} suggestions:")
                for suggestion in suggestions:
                    logger.info(f"      • {suggestion['text']} ({suggestion['type']}) - "
                               f"Score: {suggestion['relevance_score']:.2f}")
            else:
                logger.info(f"   📊 No suggestions found")

def test_search_apis():
    """Test the search APIs"""
    
    logger.info("\n🧪 Testing search APIs...")
    
    app = create_app()
    
    with app.app_context():
        # Test the enhanced search API
        logger.info("🔍 Testing enhanced search for 'fed':")
        
        results = acronym_expansion_service.get_expanded_search_results("fed", 5)
        
        if results:
            logger.info(f"   📰 Found {len(results)} articles:")
            for result in results:
                logger.info(f"      • {result['title'][:80]}...")
                logger.info(f"        Relevance: {result['relevance_score']:.2f}")
                logger.info(f"        Matched terms: {result['matched_terms']}")
        else:
            logger.info("   📰 No articles found")

def test_specific_fed_case():
    """Test the specific 'fed' case that the user mentioned"""
    
    logger.info("\n🎯 Testing specific 'fed' case...")
    
    app = create_app()
    
    with app.app_context():
        query = "fed"
        
        # Test expansion
        expansion = acronym_expansion_service.expand_query(query)
        logger.info(f"🔄 'fed' expands to: {expansion['expanded']}")
        
        # Test search results
        results = acronym_expansion_service.get_expanded_search_results(query, 10)
        logger.info(f"📰 'fed' search found {len(results)} articles")
        
        # Test suggestions
        suggestions = intelligent_suggestion_service.get_search_suggestions(query, limit=5)
        logger.info(f"💡 'fed' suggestions: {len(suggestions)} found")
        
        for suggestion in suggestions:
            logger.info(f"   • {suggestion['text']} ({suggestion['type']})")
        
        # Show expected behavior
        logger.info("\n✅ Expected behavior:")
        logger.info("   When user searches 'fed', they should see:")
        logger.info("   1. Articles about Federal Reserve")
        logger.info("   2. Suggestions for 'federal reserve', 'federal', 'monetary policy'")
        logger.info("   3. Related financial terms")

if __name__ == "__main__":
    logger.info("🚀 Starting acronym expansion tests")
    
    # Test the core functionality
    test_acronym_expansion()
    
    # Test intelligent suggestions integration
    test_intelligent_suggestions()
    
    # Test search APIs
    test_search_apis()
    
    # Test specific user case
    test_specific_fed_case()
    
    logger.info("\n✅ All tests completed!")
    logger.info("\n🎯 Next steps:")
    logger.info("   1. Deploy these changes to your Coolify server")
    logger.info("   2. Test the enhanced search: https://trendwise.biz/news/api/enhanced-search?q=fed")
    logger.info("   3. Test the suggestions: https://trendwise.biz/news/api/suggestions?q=fed")
    logger.info("   4. Use the regular search with improved suggestions") 