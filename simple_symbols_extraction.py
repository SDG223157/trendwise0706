#!/usr/bin/env python3
"""
Simple symbols extraction and population for news_search_index
Extracts symbols directly from article content without using article_symbols table
"""

import os
import sys
import json
import re
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

def extract_symbols_from_content(title, content):
    """Extract stock symbols from article title and content using simple patterns"""
    
    symbols = set()
    
    # Common patterns for stock symbols
    patterns = [
        # NYSE/NASDAQ: AAPL, TSLA, etc.
        r'\b[A-Z]{2,5}\b',
        # Exchange prefixes: NYSE:AAPL, NASDAQ:TSLA
        r'(?:NYSE|NASDAQ|SSE|SZSE|HKEX|KRX):\s*([A-Z0-9]{2,6})',
        # Stock symbols in parentheses: (AAPL), (TSLA)
        r'\(([A-Z]{2,5})\)',
        # Common formats: $AAPL, AAPL.US
        r'\$([A-Z]{2,5})',
        r'([A-Z]{2,5})\.US',
    ]
    
    # Combine title and content for search
    text = f"{title} {content}" if content else title
    
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            if isinstance(match, tuple):
                match = match[0] if match[0] else match[1]
            
            # Clean up the symbol
            symbol = match.upper().strip()
            
            # Filter out common words that look like symbols
            exclude_words = {
                'THE', 'AND', 'FOR', 'ARE', 'BUT', 'NOT', 'YOU', 'ALL', 'CAN', 'HAS', 'HER', 'WAS', 'ONE', 'OUR', 'HAD', 'BUT', 'CAN', 'HAS', 'HER', 'WAS', 'ONE', 'OUR', 'HAD', 'BUT', 'CAN', 'HAS', 'HER', 'WAS', 'ONE', 'OUR', 'HAD',
                'NEW', 'NOW', 'OLD', 'SEE', 'TWO', 'WHO', 'BOY', 'DID', 'ITS', 'LET', 'PUT', 'SAY', 'SHE', 'TOO', 'USE',
                'USD', 'EUR', 'GBP', 'JPY', 'CNY', 'CAD', 'AUD', 'CHF', 'SEK', 'NOK', 'DKK',
                'CEO', 'CFO', 'CTO', 'IPO', 'ETF', 'ESG', 'SEC', 'FDA', 'FTC', 'DOJ', 'GDP', 'CPI', 'PPI',
                'USA', 'UAE', 'CEO', 'PMI', 'API', 'APP', 'WEB', 'NET', 'COM', 'ORG', 'GOV', 'EDU',
                'AI', 'ML', 'VR', 'AR', 'IoT', 'SaaS', 'API', 'SDK', 'UI', 'UX'
            }
            
            # Only include if it looks like a real stock symbol
            if (len(symbol) >= 2 and len(symbol) <= 6 and 
                symbol not in exclude_words and 
                not symbol.isdigit() and
                re.match(r'^[A-Z0-9]+$', symbol)):
                symbols.add(symbol)
    
    return sorted(list(symbols))

def simple_populate_symbols():
    """Populate symbols_json field using simple content extraction"""
    
    print("🔧 SIMPLE SYMBOLS EXTRACTION & POPULATION")
    print("=" * 60)
    
    try:
        # Database connection
        db_url = f"mysql+pymysql://{os.getenv('MYSQL_USER')}:{os.getenv('MYSQL_PASSWORD')}@{os.getenv('MYSQL_HOST')}:{os.getenv('MYSQL_PORT', 3306)}/{os.getenv('MYSQL_DATABASE')}"
        engine = create_engine(db_url)
        Session = sessionmaker(bind=engine)
        
        # Step 1: Check current status
        with Session() as session:
            search_count = session.execute(text("""
                SELECT COUNT(*) as total_entries
                FROM news_search_index
            """)).fetchone()
            
            print(f"📊 Current Status:")
            print(f"   • Search index entries: {search_count.total_entries}")
            
            if search_count.total_entries == 0:
                print("⚠️ No search index entries found. Run population script first.")
                return False
        
        # Step 2: Process search index entries and extract symbols
        updated_count = 0
        symbols_found = 0
        batch_size = 10
        
        print(f"\n🔄 Processing in batches of {batch_size}...")
        
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
                    # Extract symbols from title and content
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
                    
                    # Progress indicator
                    if (i + 1) % batch_size == 0:
                        session.commit()
                        print(f"   ✅ Updated {i + 1}/{len(search_entries)} entries (batch commit)")
                    
                    # Debug info for first few entries
                    if i < 5:
                        print(f"   📝 Entry {entry.id}: {entry.title[:40]}... → {len(symbols)} symbols")
                        if symbols:
                            print(f"      Symbols: {symbols}")
                        
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
                LIMIT 5
            """)).fetchall()
            
            print(f"   📊 Entries with symbols: {final_count.with_symbols}")
            print(f"   🔄 Total processed: {updated_count}")
            print(f"   🏷️  Total symbols found: {symbols_found}")
            
            if sample_entries:
                print(f"   📝 Sample entries with symbols:")
                for entry in sample_entries:
                    symbols = json.loads(entry.symbols_json)
                    print(f"      • {entry.title[:50]}... → {symbols}")
                    
            print(f"✅ Successfully populated symbols_json using simple extraction!")
            print(f"🗑️  You can now safely delete the article_symbols table if desired")
            return True
                
    except Exception as e:
        print(f"❌ Error in simple symbols population: {str(e)}")
        return False

if __name__ == "__main__":
    success = simple_populate_symbols()
    sys.exit(0 if success else 1) 