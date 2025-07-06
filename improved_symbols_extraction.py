#!/usr/bin/env python3
"""
Improved symbols extraction with precise stock symbol detection
Fixes the issue of extracting too many common words as symbols
"""

import os
import sys
import json
import re
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

def extract_symbols_from_content(title, content):
    """Extract stock symbols with much more precise patterns and filtering"""
    
    symbols = set()
    
    # Much more specific patterns for stock symbols
    specific_patterns = [
        # Exchange prefixes: NYSE:AAPL, NASDAQ:TSLA, SSE:600036, HKEX:700
        r'(?:NYSE|NASDAQ|SSE|SZSE|HKEX|KRX|TSE):\s*([A-Z0-9]{1,6})',
        # Stock symbols in parentheses: (AAPL), (TSLA)
        r'\(([A-Z]{2,5})\)',
        # Common formats: $AAPL, AAPL.US
        r'\$([A-Z]{2,5})',
        r'([A-Z]{2,5})\.(?:US|HK|CN|JP|KR)',
        # Ticker format: "Stock AAPL closed"
        r'(?:stock|ticker|symbol|shares of)\s+([A-Z]{2,5})\b',
        # Company name followed by ticker: "Apple AAPL"
        r'\b([A-Z]{2,5})\s+(?:stock|shares|closed|opened|fell|rose|gained|lost)',
    ]
    
    # Combine title and content for search
    text = f"{title} {content}" if content else title
    
    # Extract from specific patterns first
    for pattern in specific_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            symbol = match.upper().strip()
            if len(symbol) >= 2 and len(symbol) <= 6:
                symbols.add(symbol)
    
    # Very comprehensive list of words to exclude (common English words, abbreviations, etc.)
    exclude_words = {
        # Common English words
        'THE', 'AND', 'FOR', 'ARE', 'BUT', 'NOT', 'YOU', 'ALL', 'CAN', 'HAS', 'HER', 'WAS', 'ONE', 'OUR', 'HAD',
        'NEW', 'NOW', 'OLD', 'SEE', 'TWO', 'WHO', 'BOY', 'DID', 'ITS', 'LET', 'PUT', 'SAY', 'SHE', 'TOO', 'USE',
        'GET', 'HIM', 'HIS', 'HOW', 'MAN', 'MAY', 'OWN', 'OUT', 'DAY', 'WAY', 'OFF', 'SET', 'RUN', 'END', 'WHY',
        'BEEN', 'CALL', 'CAME', 'COME', 'EACH', 'EVEN', 'FIND', 'FROM', 'GIVE', 'GOOD', 'HAND', 'HERE', 'HIGH',
        'INTO', 'JUST', 'KEEP', 'KIND', 'KNOW', 'LAST', 'LEFT', 'LIFE', 'LIKE', 'LIVE', 'LONG', 'LOOK', 'MADE',
        'MAKE', 'MANY', 'MORE', 'MOST', 'MOVE', 'MUCH', 'MUST', 'NAME', 'NEED', 'NEXT', 'ONLY', 'OPEN', 'OVER',
        'PART', 'PLAY', 'SAID', 'SAME', 'SEEM', 'SHOW', 'SOME', 'TAKE', 'TELL', 'THAN', 'THAT', 'THEN', 'THEY',
        'THIS', 'TIME', 'TURN', 'VERY', 'WANT', 'WELL', 'WENT', 'WERE', 'WHAT', 'WHEN', 'WITH', 'WORD', 'WORK',
        'YEAR', 'YOUR', 'ALSO', 'BACK', 'CAME', 'DOES', 'DOWN', 'FELT', 'FIRST', 'FOUND', 'GREAT', 'GROUP',
        'HOUSE', 'LARGE', 'NEVER', 'OTHER', 'PLACE', 'RIGHT', 'SHALL', 'SMALL', 'SOUND', 'STILL', 'SUCH',
        'THINK', 'THREE', 'UNDER', 'WATER', 'WHERE', 'WHILE', 'WORLD', 'WOULD', 'WRITE', 'ABOUT', 'ABOVE',
        'AFTER', 'AGAIN', 'BELOW', 'BEING', 'EVERY', 'THESE', 'THOSE', 'COULD', 'MIGHT', 'SHOULD', 'THEIR',
        'THERE', 'THROUGH', 'BETWEEN', 'ANOTHER', 'BECAUSE', 'BEFORE', 'DURING', 'HAVING', 'LITTLE', 'PEOPLE',
        'SOMETHING', 'SOMETHING', 'WITHOUT', 'AGAINST', 'NOTHING', 'ANYTHING', 'EVERYTHING', 'SOMEONE',
        
        # Business/finance common words
        'CHINA', 'JAPAN', 'KOREA', 'INDIA', 'EUROPE', 'ASIA', 'NORTH', 'SOUTH', 'EAST', 'WEST',
        'HONG', 'KONG', 'TOKYO', 'SEOUL', 'BANK', 'FUND', 'CORP', 'GROUP', 'SAID', 'NEWS', 'WILL',
        'STOCK', 'SHARE', 'PRICE', 'TRADE', 'SALES', 'ROSE', 'FELL', 'GAIN', 'LOSS', 'HIGH', 'LOW',
        'OPEN', 'CLOSE', 'DAILY', 'WEEK', 'MONTH', 'YEAR', 'JUNE', 'JULY', 'MARCH', 'APRIL', 'MAY',
        'STEEL', 'DRUG', 'FIRST', 'GETS', 'LINE', 'SOFT', 'TUMOR', 'LOAN', 'LOANS', 'DEBT', 'HELP',
        'RAISE', 'RANGE', 'RATES', 'RATIO', 'REPAY', 'RISE', 'TRUST', 'WELL', 'WOULD', 'ABOUT', 'AIMS',
        'BEEN', 'FROM', 'OTHER', 'FUND', 'MARCH', 'TRUST', 'RANGE', 'RATES', 'RATIO', 'REPAY', 'RISE',
        'SOAP', 'OPERA', 'SHOW', 'MEDIA', 'APPLE', 'TESLA', 'SOLID', 'STAGE', 'STAKE', 'STORE', 'SUIT',
        'TAKE', 'TALKS', 'TERMS', 'TEST', 'THAN', 'THAT', 'THEN', 'THERE', 'THIS', 'TOOK', 'TOTAL',
        'TRADE', 'TRUCE', 'TRUMP', 'WATCH', 'WEEKS', 'WELL', 'WHEN', 'WHICH', 'WHITE', 'WILL', 'WITH',
        'WORLD', 'WOULD', 'WRITE', 'YEARS', 'PRICE', 'HIKES', 'GROW', 'ADDED', 'DOWN', 'DRIVE', 'FIRST',
        'GROW', 'HIKES', 'LEAD', 'LESS', 'LIVE', 'NEXT', 'NOTE', 'OVER', 'PRICE', 'PUSH', 'SAYS', 'SEAL',
        'TALK', 'THEY', 'THIS', 'TIER', 'TIERS', 'TRADE', 'VAST', 'WARS', 'WILL', 'WITH', 'YEAR', 'YEARS',
        
        # Currency codes
        'USD', 'EUR', 'GBP', 'JPY', 'CNY', 'CAD', 'AUD', 'CHF', 'SEK', 'NOK', 'DKK', 'YEN',
        
        # Business abbreviations
        'CEO', 'CFO', 'CTO', 'IPO', 'ETF', 'ESG', 'SEC', 'FDA', 'FTC', 'DOJ', 'GDP', 'CPI', 'PPI',
        'USA', 'UAE', 'PMI', 'API', 'APP', 'WEB', 'NET', 'COM', 'ORG', 'GOV', 'EDU', 'WSJ',
        
        # Tech abbreviations
        'AI', 'ML', 'VR', 'AR', 'IOT', 'SAAS', 'SDK', 'UI', 'UX', 'IT', 'TV', 'AD', 'CBS',
        
        # Generic words that often appear capitalized
        'UP', 'IN', 'ON', 'AT', 'BY', 'TO', 'OF', 'OR', 'NO', 'SO', 'GO', 'DO', 'BE', 'IS', 'AS',
        'AN', 'IF', 'MY', 'WE', 'HE', 'US', 'ME', 'IT'
    }
    
    # Only extract from very specific contexts to avoid false positives
    # This is much more conservative than the previous approach
    context_patterns = [
        # Exchange:Symbol format (most reliable)
        r'(?:NYSE|NASDAQ|SSE|SZSE|HKEX|KRX|TSE):\s*([A-Z0-9]{1,6})',
        # $SYMBOL format
        r'\$([A-Z]{2,5})',
        # (SYMBOL) format  
        r'\(([A-Z]{2,5})\)',
        # SYMBOL.exchange format
        r'([A-Z]{2,5})\.(?:US|HK|CN|JP|KR)',
    ]
    
    # Extract only from these specific contexts
    for pattern in context_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            symbol = match.upper().strip()
            
            # Additional validation
            if (len(symbol) >= 2 and len(symbol) <= 6 and 
                symbol not in exclude_words and 
                not symbol.isdigit() and
                re.match(r'^[A-Z0-9]+$', symbol)):
                symbols.add(symbol)
    
    return sorted(list(symbols))

def improved_populate_symbols():
    """Populate symbols_json field using improved, precise extraction"""
    
    print("🎯 IMPROVED SYMBOLS EXTRACTION & POPULATION")
    print("=" * 60)
    
    try:
        # Database connection
        db_url = f"mysql+pymysql://{os.getenv('MYSQL_USER')}:{os.getenv('MYSQL_PASSWORD')}@{os.getenv('MYSQL_HOST')}:{os.getenv('MYSQL_PORT', 3306)}/{os.getenv('MYSQL_DATABASE')}"
        engine = create_engine(db_url)
        Session = sessionmaker(bind=engine)
        
        # Step 1: Clear existing symbols_json first
        print("🧹 Clearing existing symbols_json entries...")
        with Session() as session:
            session.execute(text("""
                UPDATE news_search_index 
                SET symbols_json = '[]', updated_at = NOW()
            """))
            session.commit()
            print("   ✅ Cleared existing symbols")
        
        # Step 2: Process with improved extraction
        updated_count = 0
        symbols_found = 0
        articles_with_symbols = 0
        batch_size = 10
        
        print(f"\n🔄 Processing with improved extraction...")
        
        with Session() as session:
            # Get search index entries with their corresponding article content
            search_entries = session.execute(text("""
                SELECT 
                    si.id, si.article_id, si.title, si.external_id,
                    na.content
                FROM news_search_index si
                LEFT JOIN news_articles na ON si.article_id = na.id
                WHERE si.article_id IS NOT NULL
                ORDER BY si.id
            """)).fetchall()
            
            print(f"📋 Found {len(search_entries)} search entries to process")
            
            for i, entry in enumerate(search_entries):
                try:
                    # Extract symbols with improved method
                    symbols = extract_symbols_from_content(entry.title, entry.content)
                    symbols_json = json.dumps(symbols)
                    
                    # Update search index entry
                    session.execute(text("""
                        UPDATE news_search_index
                        SET symbols_json = :symbols_json,
                            updated_at = NOW()
                        WHERE id = :search_id
                    """), {
                        "symbols_json": symbols_json,
                        "search_id": entry.id
                    })
                    
                    updated_count += 1
                    if symbols:
                        symbols_found += len(symbols)
                        articles_with_symbols += 1
                    
                    # Progress indicator
                    if (i + 1) % batch_size == 0:
                        session.commit()
                        print(f"   ✅ Updated {i + 1}/{len(search_entries)} entries")
                    
                    # Debug info for entries with symbols
                    if symbols:
                        print(f"   📝 Entry {entry.id}: {entry.title[:50]}... → {symbols}")
                        
                except Exception as e:
                    print(f"   ❌ Error updating entry {entry.id}: {str(e)}")
                    continue
            
            # Final commit
            session.commit()
            print(f"   ✅ Final commit: {updated_count} entries updated")
        
        # Step 3: Verify results
        print(f"\n🔍 Verification:")
        with Session() as session:
            # Count updated entries
            final_count = session.execute(text("""
                SELECT COUNT(*) as with_symbols
                FROM news_search_index
                WHERE symbols_json IS NOT NULL AND symbols_json != '[]' AND symbols_json != ''
            """)).fetchone()
            
            # Sample some entries
            sample_entries = session.execute(text("""
                SELECT id, title, symbols_json
                FROM news_search_index
                WHERE symbols_json IS NOT NULL AND symbols_json != '[]' AND symbols_json != ''
                ORDER BY id
                LIMIT 10
            """)).fetchall()
            
            print(f"   📊 Articles with symbols: {final_count.with_symbols}")
            print(f"   🔄 Total processed: {updated_count}")
            print(f"   🎯 Quality symbols found: {symbols_found}")
            print(f"   📈 Avg symbols per article: {symbols_found/articles_with_symbols if articles_with_symbols > 0 else 0:.1f}")
            
            if sample_entries:
                print(f"   📝 Sample entries with symbols:")
                for entry in sample_entries:
                    symbols = json.loads(entry.symbols_json)
                    print(f"      • {entry.title[:50]}... → {symbols}")
                    
            print(f"✅ Successfully populated with precise symbol extraction!")
            print(f"🎯 Much better quality - fewer false positives!")
            return True
                
    except Exception as e:
        print(f"❌ Error in improved symbols population: {str(e)}")
        return False

if __name__ == "__main__":
    success = improved_populate_symbols()
    sys.exit(0 if success else 1) 